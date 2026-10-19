//! The keyboard, straight from the kernel: every `/dev/input/event*` that
//! has an Enter key is read for its presses and repeats, turned into keys
//! (world.rs) by the US layout with Shift and Caps Lock, as a page on the
//! screen is typed into (ABNT2 and the dead keys are for a slice to
//! come). No library: an input event is 24 bytes on a 64-bit system, and
//! the two ioctls that tell a keyboard from a mouse are stable.

use crate::world::Key;
use anyhow::Result;
use std::fs::File;
use std::io::Read;
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;

const EV_KEY: u16 = 1;
const KEY_ESC: u16 = 1;
const KEY_BACKSPACE: u16 = 14;
const KEY_TAB: u16 = 15;
const KEY_ENTER: u16 = 28;
const KEY_LEFTCTRL: u16 = 29;
const KEY_LEFTSHIFT: u16 = 42;
const KEY_RIGHTSHIFT: u16 = 54;
const KEY_KPASTERISK: u16 = 55;
const KEY_SPACE: u16 = 57;
const KEY_CAPSLOCK: u16 = 58;
const KEY_F1: u16 = 59;
const KEY_F5: u16 = 63;
const KEY_KP7: u16 = 71;
const KEY_KPDOT: u16 = 83;
const KEY_102ND: u16 = 86;
const KEY_KPENTER: u16 = 96;
const KEY_RIGHTCTRL: u16 = 97;
const KEY_KPSLASH: u16 = 98;
const KEY_HOME: u16 = 102;
const KEY_UP: u16 = 103;
const KEY_PAGEUP: u16 = 104;
const KEY_LEFT: u16 = 105;
const KEY_RIGHT: u16 = 106;
const KEY_END: u16 = 107;
const KEY_DOWN: u16 = 108;
const KEY_PAGEDOWN: u16 = 109;
const KEY_DELETE: u16 = 111;
const KEY_MAX: usize = 0x2ff;

/// The printable keys of the US layout by scancode: the plain character
/// and the shifted one. Rows as on the keyboard: the number row (2-13),
/// QWERTY (16-27), ASDF (30-41), the backslash (43), ZXCV (44-53).
fn us(code: u16) -> Option<(char, char)> {
    Some(match code {
        2 => ('1', '!'),
        3 => ('2', '@'),
        4 => ('3', '#'),
        5 => ('4', '$'),
        6 => ('5', '%'),
        7 => ('6', '^'),
        8 => ('7', '&'),
        9 => ('8', '*'),
        10 => ('9', '('),
        11 => ('0', ')'),
        12 => ('-', '_'),
        13 => ('=', '+'),
        16 => ('q', 'Q'),
        17 => ('w', 'W'),
        18 => ('e', 'E'),
        19 => ('r', 'R'),
        20 => ('t', 'T'),
        21 => ('y', 'Y'),
        22 => ('u', 'U'),
        23 => ('i', 'I'),
        24 => ('o', 'O'),
        25 => ('p', 'P'),
        26 => ('[', '{'),
        27 => (']', '}'),
        30 => ('a', 'A'),
        31 => ('s', 'S'),
        32 => ('d', 'D'),
        33 => ('f', 'F'),
        34 => ('g', 'G'),
        35 => ('h', 'H'),
        36 => ('j', 'J'),
        37 => ('k', 'K'),
        38 => ('l', 'L'),
        39 => (';', ':'),
        40 => ('\'', '"'),
        41 => ('`', '~'),
        43 => ('\\', '|'),
        44 => ('z', 'Z'),
        45 => ('x', 'X'),
        46 => ('c', 'C'),
        47 => ('v', 'V'),
        48 => ('b', 'B'),
        49 => ('n', 'N'),
        50 => ('m', 'M'),
        51 => (',', '<'),
        52 => ('.', '>'),
        53 => ('/', '?'),
        KEY_KPASTERISK => ('*', '*'),
        KEY_102ND => ('<', '>'),
        KEY_KPSLASH => ('/', '/'),
        _ => return None,
    })
}

/// The keypad with Num Lock on (the console's default): digits, the dot
/// and the signs; 71-83 is the block 7 8 9 - 4 5 6 + 1 2 3 0 .
fn keypad(code: u16) -> Option<char> {
    const BLOCK: [char; 13] = [
        '7', '8', '9', '-', '4', '5', '6', '+', '1', '2', '3', '0', '.',
    ];
    if (KEY_KP7..=KEY_KPDOT).contains(&code) {
        Some(BLOCK[(code - KEY_KP7) as usize])
    } else {
        None
    }
}

/// The modifiers held, and Caps Lock.
#[derive(Default)]
struct Modifiers {
    shift: bool,
    ctrl: bool,
    caps: bool,
}

impl Modifiers {
    /// A press (1), a repeat (2) or a release (0) of a key: the key it
    /// means now, if any. Returns the key for presses and repeats; a
    /// repeat of Enter, Escape, Tab and the function keys is not a
    /// second press.
    fn key(&mut self, code: u16, value: i32) -> Option<Key> {
        let pressed = value != 0;
        match code {
            KEY_LEFTSHIFT | KEY_RIGHTSHIFT => {
                self.shift = pressed;
                return None;
            }
            KEY_LEFTCTRL | KEY_RIGHTCTRL => {
                self.ctrl = pressed;
                return None;
            }
            KEY_CAPSLOCK => {
                if value == 1 {
                    self.caps = !self.caps;
                }
                return None;
            }
            _ => {}
        }
        if !pressed {
            return None;
        }
        let repeat = value == 2;
        let key = match code {
            KEY_UP => Key::Up,
            KEY_DOWN => Key::Down,
            KEY_LEFT => Key::Left,
            KEY_RIGHT => Key::Right,
            KEY_HOME => Key::Home,
            KEY_END => Key::End,
            KEY_PAGEUP => Key::PageUp,
            KEY_PAGEDOWN => Key::PageDown,
            KEY_BACKSPACE => Key::Backspace,
            KEY_DELETE => Key::Delete,
            KEY_SPACE => Key::Space,
            KEY_ENTER | KEY_KPENTER if !repeat => Key::Enter,
            KEY_ESC if !repeat => Key::Escape,
            KEY_TAB if !repeat => {
                if self.shift {
                    Key::ShiftTab
                } else {
                    Key::Tab
                }
            }
            KEY_F1 if !repeat => Key::F1,
            KEY_F5 if !repeat => Key::F5,
            KEY_ENTER | KEY_KPENTER | KEY_ESC | KEY_TAB | KEY_F1 | KEY_F5 => return None,
            _ => {
                if self.ctrl {
                    return match us(code) {
                        Some(('u', _)) => Some(Key::CtrlU),
                        _ => None,
                    };
                }
                if let Some(c) = keypad(code) {
                    return Some(Key::Char(c));
                }
                let (plain, shifted) = us(code)?;
                let letter = plain.is_ascii_alphabetic();
                let upper = if letter {
                    self.shift != self.caps
                } else {
                    self.shift
                };
                Key::Char(if upper { shifted } else { plain })
            }
        };
        Some(key)
    }
}

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
    modifiers: Modifiers,
}

impl Keyboards {
    /// No keyboard at all (no display).
    pub fn none() -> Keyboards {
        Keyboards {
            files: Vec::new(),
            modifiers: Modifiers::default(),
        }
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
        Ok(Keyboards {
            files,
            modifiers: Modifiers::default(),
        })
    }

    /// The keys pressed (or held, repeating) since the last poll, in order.
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
                    if kind != EV_KEY {
                        continue; // a sync, a LED
                    }
                    if let Some(key) = self.modifiers.key(code, value) {
                        keys.push(key);
                    }
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

    #[test]
    fn the_layout_gives_characters_with_shift_and_caps_and_the_keys_by_name() {
        let mut m = Modifiers::default();
        assert_eq!(m.key(30, 1), Some(Key::Char('a')));
        assert_eq!(m.key(30, 2), Some(Key::Char('a'))); // held: repeats
        assert_eq!(m.key(30, 0), None);
        m.key(KEY_LEFTSHIFT, 1);
        assert_eq!(m.key(30, 1), Some(Key::Char('A')));
        assert_eq!(m.key(2, 1), Some(Key::Char('!')));
        assert_eq!(m.key(KEY_TAB, 1), Some(Key::ShiftTab));
        m.key(KEY_LEFTSHIFT, 0);
        m.key(KEY_CAPSLOCK, 1);
        m.key(KEY_CAPSLOCK, 0);
        assert_eq!(m.key(30, 1), Some(Key::Char('A'))); // caps: letters only
        assert_eq!(m.key(2, 1), Some(Key::Char('1')));
        m.key(KEY_RIGHTSHIFT, 1);
        assert_eq!(m.key(30, 1), Some(Key::Char('a'))); // caps and shift undo each other
        m.key(KEY_RIGHTSHIFT, 0);
        m.key(KEY_CAPSLOCK, 1);
        assert_eq!(m.key(KEY_TAB, 1), Some(Key::Tab));
        assert_eq!(m.key(KEY_ENTER, 1), Some(Key::Enter));
        assert_eq!(m.key(KEY_ENTER, 2), None); // Enter held is one Enter
        assert_eq!(m.key(KEY_KPENTER, 1), Some(Key::Enter));
        assert_eq!(m.key(KEY_ESC, 1), Some(Key::Escape));
        assert_eq!(m.key(KEY_BACKSPACE, 2), Some(Key::Backspace));
        assert_eq!(m.key(KEY_F5, 1), Some(Key::F5));
        assert_eq!(m.key(KEY_F1, 1), Some(Key::F1));
        assert_eq!(m.key(KEY_SPACE, 1), Some(Key::Space));
        assert_eq!(m.key(KEY_KP7, 1), Some(Key::Char('7')));
        assert_eq!(m.key(KEY_KPDOT, 1), Some(Key::Char('.')));
        assert_eq!(m.key(KEY_PAGEDOWN, 1), Some(Key::PageDown));
        m.key(KEY_LEFTCTRL, 1);
        assert_eq!(m.key(22, 1), Some(Key::CtrlU));
        assert_eq!(m.key(30, 1), None); // Ctrl+A is nobody's
        m.key(KEY_LEFTCTRL, 0);
        assert_eq!(m.key(22, 1), Some(Key::Char('u')));
        assert_eq!(m.key(0x2ff_u16, 1), None);
    }
}
