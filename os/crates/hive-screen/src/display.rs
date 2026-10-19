//! The display: the scene on the console through DRM/KMS, with no X, no
//! Wayland and no GPU driver on our side. One connected connector, its
//! preferred mode, one dumb buffer the CPU writes into (mapped once: a
//! mapping a frame costs a page fault a page), and the scene scaled up by
//! a whole number in the middle of it, black around.

use crate::image::Image;
use anyhow::{bail, Context as _, Result};
use drm::buffer::{Buffer as _, DrmFourcc};
use drm::control::dumbbuffer::DumbBuffer;
use drm::control::{
    connector, crtc, framebuffer, ClipRect, Device as ControlDevice, Mode, ModeTypeFlags,
};
use drm::Device;
use std::os::fd::{AsFd, AsRawFd, BorrowedFd};
use std::path::Path;

struct Card(std::fs::File);

impl AsFd for Card {
    fn as_fd(&self) -> BorrowedFd<'_> {
        self.0.as_fd()
    }
}
impl Device for Card {}
impl ControlDevice for Card {}

/// Where the scene goes on the screen: scaled `scale` times, its top left
/// at (x, y).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Fit {
    pub scale: u32,
    pub x: u32,
    pub y: u32,
}

/// The largest whole-number scale at which the scene fits the screen,
/// centred; 1 when the screen is smaller than the scene (it is then cut).
pub fn fit(screen: (u32, u32), scene: (u32, u32)) -> Fit {
    let scale = (screen.0 / scene.0.max(1))
        .min(screen.1 / scene.1.max(1))
        .max(1);
    let (w, h) = (scene.0 * scale, scene.1 * scale);
    Fit {
        scale,
        x: screen.0.saturating_sub(w) / 2,
        y: screen.1.saturating_sub(h) / 2,
    }
}

pub struct Display {
    card: Card,
    crtc: crtc::Handle,
    connector: connector::Handle,
    mode: Mode,
    fb: framebuffer::Handle,
    buffer: Option<DumbBuffer>,
    /// The buffer's pages, mapped for the display's life.
    map: *mut u8,
    map_len: usize,
    pitch: u32,
    pub width: u32,
    pub height: u32,
    pub fit: Fit,
    /// The picture size the fit is for: another size is fitted again.
    fit_for: (u32, u32),
    /// Whether the screen is to be cleared before the next picture.
    clear: bool,
}

impl Display {
    /// Opens the card, takes the first connected connector at its
    /// preferred mode, and puts a black buffer on it.
    pub fn open(path: &Path, scene: (u32, u32)) -> Result<Display> {
        let file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open(path)
            .with_context(|| format!("cannot open {}", path.display()))?;
        let card = Card(file);
        if let Err(e) = card.acquire_master_lock() {
            // the first client of a card is its master already; anything
            // else here means another program draws on this card
            tracing::debug!("acquire_master_lock: {}", e);
        }
        let res = card.resource_handles().context("DRM resources")?;
        let mut found = None;
        for &handle in res.connectors() {
            let info = card.get_connector(handle, false)?;
            if info.state() == connector::State::Connected && !info.modes().is_empty() {
                found = Some(info);
                break;
            }
        }
        let Some(conn) = found else {
            bail!("no connected display on {}", path.display());
        };
        let mode = conn
            .modes()
            .iter()
            .find(|m| m.mode_type().contains(ModeTypeFlags::PREFERRED))
            .or_else(|| conn.modes().first())
            .copied()
            .context("the display has no mode")?;
        let encoder = match conn.current_encoder() {
            Some(e) => card.get_encoder(e)?,
            None => {
                let handle = *conn
                    .encoders()
                    .first()
                    .context("the connector has no encoder")?;
                card.get_encoder(handle)?
            }
        };
        let crtc = match encoder.crtc() {
            Some(c) => c,
            None => res
                .filter_crtcs(encoder.possible_crtcs())
                .first()
                .copied()
                .context("no CRTC for the connector")?,
        };
        let (width, height) = (mode.size().0 as u32, mode.size().1 as u32);
        let buffer = card
            .create_dumb_buffer((width, height), DrmFourcc::Xrgb8888, 32)
            .context("cannot create the scanout buffer (dumb buffers)")?;
        let pitch = buffer.pitch();
        let offset = drm_ffi::mode::dumbbuffer::map(card.as_fd(), u32::from(buffer.handle()), 0, 0)
            .context("cannot map the scanout buffer")?
            .offset;
        let map_len = pitch as usize * height as usize;
        // SAFETY: a shared mapping of the buffer's pages at the offset the
        // driver gave for them, of the rows the mode has; unmapped in Drop.
        let map = unsafe {
            libc::mmap(
                std::ptr::null_mut(),
                map_len,
                libc::PROT_READ | libc::PROT_WRITE,
                libc::MAP_SHARED,
                card.0.as_raw_fd(),
                offset as libc::off_t,
            )
        };
        if map == libc::MAP_FAILED {
            bail!(
                "cannot map the scanout buffer: {}",
                std::io::Error::last_os_error()
            );
        }
        let map = map as *mut u8;
        // SAFETY: the mapping just made, of map_len bytes.
        unsafe { std::slice::from_raw_parts_mut(map, map_len) }.fill(0);
        let fb = card
            .add_framebuffer(&buffer, 24, 32)
            .context("cannot add the framebuffer")?;
        card.set_crtc(crtc, Some(fb), (0, 0), &[conn.handle()], Some(mode))
            .context("cannot set the mode")?;
        let fit = fit((width, height), scene);
        tracing::info!(
            "display {}x{} ({}), the scene {}x{} at x{} from ({}, {})",
            width,
            height,
            mode.name().to_string_lossy(),
            scene.0,
            scene.1,
            fit.scale,
            fit.x,
            fit.y
        );
        Ok(Display {
            card,
            crtc,
            connector: conn.handle(),
            mode,
            fb,
            buffer: Some(buffer),
            map,
            map_len,
            pitch,
            width,
            height,
            fit,
            fit_for: scene,
            clear: false,
        })
    }

    /// The scene's picture, scaled up and put on the screen, its rows in
    /// `threads` bands at once. A picture of another size (another level)
    /// is fitted again, and the screen cleared around it.
    pub fn present(&mut self, image: &Image, threads: usize) -> Result<()> {
        let (sw, sh) = (image.width, image.height);
        if self.fit_for != (sw, sh) {
            self.fit = fit((self.width, self.height), (sw, sh));
            self.fit_for = (sw, sh);
            self.clear = true;
            tracing::info!(
                "the scene {}x{} at x{} from ({}, {})",
                sw,
                sh,
                self.fit.scale,
                self.fit.x,
                self.fit.y
            );
        }
        let fit = self.fit;
        // SAFETY: the mapping lives as long as the display, and only this
        // method writes it; the bands below get disjoint parts of it.
        let bytes = unsafe { std::slice::from_raw_parts_mut(self.map, self.map_len) };
        if std::mem::take(&mut self.clear) {
            bytes.fill(0);
        }
        let pitch = self.pitch as usize;
        let scale = fit.scale as usize;
        let out_w = (sw as usize * scale).min(self.width as usize - fit.x as usize);
        let rows_available = self.height as usize - fit.y as usize;
        // the source rows that land on the screen, in bands of whole rows,
        // each band its own stretch of the buffer
        let rows = (sh as usize).min(rows_available.div_ceil(scale));
        let bands = threads.clamp(1, rows.max(1));
        let per = rows.div_ceil(bands).max(1);
        let x_off = fit.x as usize * 4;
        let region = &mut bytes[fit.y as usize * pitch..];
        std::thread::scope(|s| {
            for (b, chunk) in region.chunks_mut(per * scale * pitch).enumerate() {
                let (y0, y1) = (b * per, ((b + 1) * per).min(rows));
                if y0 >= y1 {
                    break;
                }
                let mut work = move || {
                    let mut row = vec![0u8; out_w * 4];
                    for y in y0..y1 {
                        let src = &image.pixels[y * sw as usize..(y + 1) * sw as usize];
                        for (i, px) in row.chunks_exact_mut(4).enumerate() {
                            let p = src[(i / scale).min(sw as usize - 1)];
                            px.copy_from_slice(&(p & 0x00FF_FFFF).to_le_bytes());
                        }
                        for k in 0..scale {
                            if y * scale + k >= rows_available {
                                break;
                            }
                            let start = ((y - y0) * scale + k) * pitch + x_off;
                            if start + row.len() > chunk.len() {
                                break;
                            }
                            chunk[start..start + row.len()].copy_from_slice(&row);
                        }
                    }
                };
                if bands == 1 {
                    work();
                } else {
                    s.spawn(work);
                }
            }
        });
        let x2 = (fit.x as usize + out_w).min(u16::MAX as usize) as u16;
        let y2 = (fit.y as usize + (sh as usize * scale).min(rows_available)).min(u16::MAX as usize)
            as u16;
        // a driver that has no dirty-rectangle support answers ENOSYS: the
        // scanout buffer is live, so the picture is there anyway
        let _ = self.card.dirty_framebuffer(
            self.fb,
            &[ClipRect::new(fit.x as u16, fit.y as u16, x2, y2)],
        );
        Ok(())
    }
}

impl Drop for Display {
    fn drop(&mut self) {
        // SAFETY: the mapping made in open, unmapped once, before its buffer goes.
        unsafe {
            libc::munmap(self.map as *mut libc::c_void, self.map_len);
        }
        let _ = self
            .card
            .set_crtc(self.crtc, None, (0, 0), &[self.connector], Some(self.mode));
        let _ = self.card.destroy_framebuffer(self.fb);
        if let Some(buffer) = self.buffer.take() {
            let _ = self.card.destroy_dumb_buffer(buffer);
        }
        let _ = self.card.release_master_lock();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_scene_fits_the_screen_by_a_whole_number_and_sits_in_the_middle() {
        assert_eq!(
            fit((1280, 720), (320, 180)),
            Fit {
                scale: 4,
                x: 0,
                y: 0
            }
        );
        assert_eq!(
            fit((1024, 768), (320, 180)),
            Fit {
                scale: 3,
                x: 32,
                y: 114
            }
        );
        assert_eq!(
            fit((1920, 1080), (320, 180)),
            Fit {
                scale: 6,
                x: 0,
                y: 0
            }
        );
        assert_eq!(
            fit((800, 600), (640, 360)),
            Fit {
                scale: 1,
                x: 80,
                y: 120
            }
        );
        assert_eq!(
            fit((200, 100), (320, 180)),
            Fit {
                scale: 1,
                x: 0,
                y: 0
            }
        );
    }
}
