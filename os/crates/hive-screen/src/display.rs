//! The display: the scene on the console through DRM/KMS, with no X, no
//! Wayland and no GPU driver on our side. One connected connector, its
//! preferred mode, one dumb buffer the CPU writes into, and the scene
//! scaled up by a whole number in the middle of it, black around.

use crate::image::Image;
use anyhow::{bail, Context as _, Result};
use drm::buffer::{Buffer as _, DrmFourcc};
use drm::control::dumbbuffer::DumbBuffer;
use drm::control::{
    connector, crtc, framebuffer, ClipRect, Device as ControlDevice, Mode, ModeTypeFlags,
};
use drm::Device;
use std::os::fd::{AsFd, BorrowedFd};
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
    pitch: u32,
    pub width: u32,
    pub height: u32,
    pub fit: Fit,
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
        let mut buffer = card
            .create_dumb_buffer((width, height), DrmFourcc::Xrgb8888, 32)
            .context("cannot create the scanout buffer (dumb buffers)")?;
        let pitch = buffer.pitch();
        {
            let mut map = card.map_dumb_buffer(&mut buffer)?;
            map.as_mut().fill(0);
        }
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
            pitch,
            width,
            height,
            fit,
        })
    }

    /// The scene's picture, scaled up and put on the screen.
    pub fn present(&mut self, image: &Image) -> Result<()> {
        let fit = self.fit;
        let (sw, sh) = (image.width, image.height);
        let Some(buffer) = self.buffer.as_mut() else {
            return Ok(());
        };
        let mut map = self.card.map_dumb_buffer(buffer)?;
        let bytes = map.as_mut();
        let pitch = self.pitch as usize;
        let scale = fit.scale as usize;
        let out_w = (sw as usize * scale).min(self.width as usize - fit.x as usize);
        let rows_available = self.height as usize - fit.y as usize;
        let mut row = vec![0u8; out_w * 4];
        for y in 0..sh as usize {
            let src = &image.pixels[y * sw as usize..(y + 1) * sw as usize];
            for (i, chunk) in row.chunks_exact_mut(4).enumerate() {
                let px = src[(i / scale).min(sw as usize - 1)];
                chunk.copy_from_slice(&(px & 0x00FF_FFFF).to_le_bytes());
            }
            for k in 0..scale {
                let dy = y * scale + k;
                if dy >= rows_available {
                    break;
                }
                let start = (fit.y as usize + dy) * pitch + fit.x as usize * 4;
                bytes[start..start + row.len()].copy_from_slice(&row);
            }
        }
        drop(map);
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
