//! The keyboard, straight from the kernel: every `/dev/input/event*` that
//! has an Enter key is read for presses of Up, Down, Enter and Escape, the
//! only keys the screen knows. No library: an input event is 24 bytes on
//! a 64-bit system, and the two ioctls that tell a keyboard from a mouse
//! are stable.

use crate::world::Key;
use anyhow::Result;
use std::fs::File;
use std::io::Read;
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;

const EV_KEY: u16 = 1;
const KEY_ESC: u16 = 1;
const KEY_ENTER: u16 = 28;
const KEY_KPENTER: u16 = 96;
const KEY_UP: u16 = 103;
const KEY_DOWN: u16 = 108;
const KEY_MAX: usize = 0x2ff;

/// `EVIOCGBIT(ev, len)`: `_IOC(_IOC_READ, 'E', 0x20 + ev, len)`.
fn eviocgbit(ev: u32, len: usize) -> libc::c_ulong {
    const IOC_READ: libc::c_ulong = 2;
    (IOC_READ << 30)
        | ((len as libc::c_ulong) << 16)
        | ((b'E' as libc::c_ulong) << 8)
        | (0x20 + ev as libc::c_ulong)
}

fn has_bit(bits: &[u8], n: usize) -> bool {
    bits.get(n / 8).is_some_and(|b| b & (1 << (n % 8)) != 0)
}

/// Whether the device reports keys, Enter among them: a keyboard, not a
/// mouse, a power button or a lid switch.
fn is_keyboard(file: &File) -> bool {
    let mut types = [0u8; 4];
    // SAFETY: EVIOCGBIT writes at most `len` bytes into the buffer given.
    let n = unsafe {
        libc::ioctl(
            file.as_raw_fd(),
            eviocgbit(0, types.len()),
            types.as_mut_ptr(),
        )
    };
    if n < 0 || !has_bit(&types, EV_KEY as usize) {
        return false;
    }
    let mut keys = [0u8; KEY_MAX / 8 + 1];
    let n = unsafe {
        libc::ioctl(
            file.as_raw_fd(),
            eviocgbit(EV_KEY as u32, keys.len()),
            keys.as_mut_ptr(),
        )
    };
    n >= 0 && has_bit(&keys, KEY_ENTER as usize)
}

pub struct Keyboards {
    files: Vec<File>,
}

impl Keyboards {
    /// No keyboard at all (no display).
    pub fn none() -> Keyboards {
        Keyboards { files: Vec::new() }
    }

    /// Opens every keyboard under /dev/input, non-blocking. None is not an
    /// error: the screen still shows; it just cannot be driven.
    pub fn open() -> Result<Keyboards> {
        let mut files = Vec::new();
        if let Ok(dir) = std::fs::read_dir("/dev/input") {
            let mut paths: Vec<_> = dir
                .filter_map(|e| e.ok().map(|e| e.path()))
                .filter(|p| {
                    p.file_name()
                        .and_then(|n| n.to_str())
                        .is_some_and(|n| n.starts_with("event"))
                })
                .collect();
            paths.sort();
            for path in paths {
                let Ok(file) = std::fs::OpenOptions::new()
                    .read(true)
                    .custom_flags(libc::O_NONBLOCK)
                    .open(&path)
                else {
                    continue;
                };
                if is_keyboard(&file) {
                    tracing::info!("keyboard: {}", path.display());
                    files.push(file);
                }
            }
        }
        if files.is_empty() {
            tracing::warn!("no keyboard under /dev/input: the screen shows, but no key reaches it");
        }
        Ok(Keyboards { files })
    }

    /// The keys pressed since the last poll, in order.
    pub fn poll(&mut self) -> Vec<Key> {
        let mut keys = Vec::new();
        let mut buf = [0u8; 24 * 32];
        for file in &mut self.files {
            loop {
                let n = match file.read(&mut buf) {
                    Ok(0) => break,
                    Ok(n) => n,
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
                    Err(_) => break,
                };
                for event in buf[..n].chunks_exact(24) {
                    // struct input_event { timeval (16 bytes); u16 type; u16 code; i32 value }
                    let kind = u16::from_ne_bytes([event[16], event[17]]);
                    let code = u16::from_ne_bytes([event[18], event[19]]);
                    let value = i32::from_ne_bytes([event[20], event[21], event[22], event[23]]);
                    if kind != EV_KEY || value != 1 {
                        continue; // not a key press (a release, a repeat, a sync)
                    }
                    let key = match code {
                        KEY_UP => Key::Up,
                        KEY_DOWN => Key::Down,
                        KEY_ENTER | KEY_KPENTER => Key::Enter,
                        KEY_ESC => Key::Escape,
                        _ => continue,
                    };
                    keys.push(key);
                }
            }
        }
        keys
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_ioctl_numbers_are_the_kernel_s() {
        // EVIOCGBIT(0, 4) and EVIOCGBIT(EV_KEY, 96), as <linux/input.h> computes them
        assert_eq!(eviocgbit(0, 4), 0x8004_4520);
        assert_eq!(eviocgbit(1, 96), 0x8060_4521);
        assert!(has_bit(&[0b0000_0010], 1));
        assert!(!has_bit(&[0b0000_0010], 0));
        assert!(!has_bit(&[], 9));
    }
}
