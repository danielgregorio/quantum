//! The keyboard, straight from the kernel: every `/dev/input/event*` that
//! has an Enter key is read for its presses and repeats, turned into keys
//! (world.rs) by the machine's layout (US, or ABNT2 with its dead accents
//! composed with the letter after them) with Shift, Caps Lock and AltGr,
//! as a page on the screen is typed into. No library: an input event is
//! 24 bytes on a 64-bit system, and the two ioctls that tell a keyboard
//! from a mouse are stable.

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
const KEY_RO: u16 = 89;
const KEY_KPENTER: u16 = 96;
const KEY_RIGHTCTRL: u16 = 97;
const KEY_RIGHTALT: u16 = 100;
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
const KEY_KPCOMMA: u16 = 121;
const KEY_MAX: usize = 0x2ff;

/// The keyboard's layout: which character a key gives. Read from the
/// system (`XKBLAYOUT` in /etc/default/keyboard), or `HIVE_SCREEN_KEYBOARD`
/// (`us`, `br`) in the unit's environment.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Layout {
    Us,
    /// The Brazilian keyboard: `ç` on its own key, the accents as dead
    /// keys (`´` `` ` `` on the key right of P, `~` `^` right of Ç, `¨`
    /// on Shift+6) composed with the vowel that follows.
    Abnt2,
}

impl Layout {
    pub fn parse(name: &str) -> Option<Layout> {
        match name.trim().trim_matches('"').to_ascii_lowercase().as_str() {
            "us" | "en" => Some(Layout::Us),
            "br" | "abnt2" | "br-abnt2" | "pt-br" => Some(Layout::Abnt2),
            _ => None,
        }
    }

    /// The machine's layout: the environment first, then the keyboard the
    /// Hive applied (`set-keyboard`, approved on this screen: a file under
    /// its settings), then the system's keyboard file; US when none says.
    pub fn detect() -> Layout {
        if let Ok(name) = std::env::var("HIVE_SCREEN_KEYBOARD") {
            if let Some(layout) = Layout::parse(&name) {
                return layout;
            }
            tracing::warn!(
                "HIVE_SCREEN_KEYBOARD={}: not a layout I know (us, br)",
                name
            );
        }
        let settings = std::env::var_os("HIVE_SETTINGS_DIR")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| std::path::PathBuf::from("/var/lib/hive/settings"));
        if let Ok(text) = std::fs::read_to_string(settings.join("keyboard")) {
            if let Some(layout) = Layout::from_setting(&text) {
                return layout;
            }
        }
        Layout::from_keyboard_file(
            &std::fs::read_to_string("/etc/default/keyboard").unwrap_or_default(),
        )
    }

    /// `br abnt2` in the Hive's keyboard setting: the first word is the
    /// layout; None when the file says nothing the screen reads.
    pub fn from_setting(text: &str) -> Option<Layout> {
        Layout::parse(text.split_whitespace().next()?)
    }

    /// `XKBLAYOUT="br"` in the file's text (the first layout, when it
    /// lists several).
    pub fn from_keyboard_file(text: &str) -> Layout {
        for line in text.lines() {
            let line = line.trim();
            if let Some(value) = line.strip_prefix("XKBLAYOUT=") {
                let first = value.trim_matches('"').split(',').next().unwrap_or("");
                return Layout::parse(first).unwrap_or(Layout::Us);
            }
        }
        Layout::Us
    }

    pub fn name(&self) -> &'static str {
        match self {
            Layout::Us => "us",
            Layout::Abnt2 => "br (ABNT2)",
        }
    }
}

/// What a key gives: a character, or a dead accent that waits for the
/// letter after it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Given {
    Char(char),
    Dead(char),
}

use Given::{Char as C, Dead as D};

/// The printable keys by scancode: the plain and the shifted. Rows as on
/// the keyboard: the number row (2-13), QWERTY (16-27), ASDF (30-41), the
/// backslash (43), ZXCV (44-53), the key left of Z (86), the one left of
/// the right Shift (89, ABNT2's `/`).
fn key_of(layout: Layout, code: u16) -> Option<(Given, Given)> {
    let common = match code {
        2 => Some((C('1'), C('!'))),
        3 => Some((C('2'), C('@'))),
        4 => Some((C('3'), C('#'))),
        5 => Some((C('4'), C('$'))),
        6 => Some((C('5'), C('%'))),
        7 => Some((C('6'), C('^'))),
        8 => Some((C('7'), C('&'))),
        9 => Some((C('8'), C('*'))),
        10 => Some((C('9'), C('('))),
        11 => Some((C('0'), C(')'))),
        12 => Some((C('-'), C('_'))),
        13 => Some((C('='), C('+'))),
        16 => Some((C('q'), C('Q'))),
        17 => Some((C('w'), C('W'))),
        18 => Some((C('e'), C('E'))),
        19 => Some((C('r'), C('R'))),
        20 => Some((C('t'), C('T'))),
        21 => Some((C('y'), C('Y'))),
        22 => Some((C('u'), C('U'))),
        23 => Some((C('i'), C('I'))),
        24 => Some((C('o'), C('O'))),
        25 => Some((C('p'), C('P'))),
        26 => Some((C('['), C('{'))),
        27 => Some((C(']'), C('}'))),
        30 => Some((C('a'), C('A'))),
        31 => Some((C('s'), C('S'))),
        32 => Some((C('d'), C('D'))),
        33 => Some((C('f'), C('F'))),
        34 => Some((C('g'), C('G'))),
        35 => Some((C('h'), C('H'))),
        36 => Some((C('j'), C('J'))),
        37 => Some((C('k'), C('K'))),
        38 => Some((C('l'), C('L'))),
        39 => Some((C(';'), C(':'))),
        40 => Some((C('\''), C('"'))),
        41 => Some((C('`'), C('~'))),
        43 => Some((C('\\'), C('|'))),
        44 => Some((C('z'), C('Z'))),
        45 => Some((C('x'), C('X'))),
        46 => Some((C('c'), C('C'))),
        47 => Some((C('v'), C('V'))),
        48 => Some((C('b'), C('B'))),
        49 => Some((C('n'), C('N'))),
        50 => Some((C('m'), C('M'))),
        51 => Some((C(','), C('<'))),
        52 => Some((C('.'), C('>'))),
        53 => Some((C('/'), C('?'))),
        KEY_KPASTERISK => Some((C('*'), C('*'))),
        KEY_102ND => Some((C('<'), C('>'))),
        KEY_KPSLASH => Some((C('/'), C('/'))),
        _ => None,
    };
    if layout == Layout::Us {
        return common;
    }
    // ABNT2: the keys that differ
    match code {
        7 => Some((C('6'), D('\u{a8}'))),
        26 => Some((D('\u{b4}'), D('`'))),
        27 => Some((C('['), C('{'))),
        39 => Some((C('\u{e7}'), C('\u{c7}'))),
        40 => Some((D('~'), D('^'))),
        41 => Some((C('\''), C('"'))),
        43 => Some((C(']'), C('}'))),
        53 => Some((C(';'), C(':'))),
        KEY_102ND => Some((C('\\'), C('|'))),
        KEY_RO => Some((C('/'), C('?'))),
        KEY_KPCOMMA => Some((C(','), C(','))),
        _ => common,
    }
}

/// AltGr on ABNT2: the third character of a few keys.
fn altgr_of(layout: Layout, code: u16) -> Option<char> {
    if layout != Layout::Abnt2 {
        return None;
    }
    Some(match code {
        16 => '/',
        17 => '?',
        18 => '\u{b0}',
        3 => '\u{b2}',
        4 => '\u{b3}',
        27 => '\u{aa}',
        43 => '\u{ba}',
        _ => return None,
    })
}

/// A dead accent composed with the letter after it, as Latin-1 has them;
/// None when the two do not make a letter.
fn compose(dead: char, c: char) -> Option<char> {
    let table: &[(char, &str, &str)] = &[
        (
            '\u{b4}',
            "aeiouyAEIOUY",
            "\u{e1}\u{e9}\u{ed}\u{f3}\u{fa}\u{fd}\u{c1}\u{c9}\u{cd}\u{d3}\u{da}\u{dd}",
        ),
        (
            '`',
            "aeiouAEIOU",
            "\u{e0}\u{e8}\u{ec}\u{f2}\u{f9}\u{c0}\u{c8}\u{cc}\u{d2}\u{d9}",
        ),
        (
            '^',
            "aeiouAEIOU",
            "\u{e2}\u{ea}\u{ee}\u{f4}\u{fb}\u{c2}\u{ca}\u{ce}\u{d4}\u{db}",
        ),
        ('~', "anoANO", "\u{e3}\u{f1}\u{f5}\u{c3}\u{d1}\u{d5}"),
        (
            '\u{a8}',
            "aeiouyAEIOU",
            "\u{e4}\u{eb}\u{ef}\u{f6}\u{fc}\u{ff}\u{c4}\u{cb}\u{cf}\u{d6}\u{dc}",
        ),
    ];
    let (_, from, to) = table.iter().find(|(d, _, _)| *d == dead)?;
    let i = from.chars().position(|x| x == c)?;
    to.chars().nth(i)
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

/// The modifiers held, Caps Lock, a dead accent waiting, and the layout.
struct Modifiers {
    layout: Layout,
    shift: bool,
    ctrl: bool,
    altgr: bool,
    caps: bool,
    dead: Option<char>,
}

impl Modifiers {
    fn new(layout: Layout) -> Modifiers {
        Modifiers {
            layout,
            shift: false,
            ctrl: false,
            altgr: false,
            caps: false,
            dead: None,
        }
    }

    /// A press (1), a repeat (2) or a release (0) of a key: the keys it
    /// means now, pushed on `out` (none, one, or two: a dead accent that
    /// did not compose comes out before the character). A repeat of
    /// Enter, Escape, Tab and the function keys is not a second press.
    fn key(&mut self, code: u16, value: i32, out: &mut Vec<Key>) {
        let pressed = value != 0;
        match code {
            KEY_LEFTSHIFT | KEY_RIGHTSHIFT => {
                self.shift = pressed;
                return;
            }
            KEY_LEFTCTRL | KEY_RIGHTCTRL => {
                self.ctrl = pressed;
                return;
            }
            KEY_RIGHTALT => {
                self.altgr = pressed;
                return;
            }
            KEY_CAPSLOCK => {
                if value == 1 {
                    self.caps = !self.caps;
                }
                return;
            }
            _ => {}
        }
        if !pressed {
            return;
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
            KEY_SPACE => {
                // a dead accent then a space is the accent itself
                if let Some(d) = self.dead.take() {
                    out.push(Key::Char(d));
                    return;
                }
                Key::Space
            }
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
            KEY_ENTER | KEY_KPENTER | KEY_ESC | KEY_TAB | KEY_F1 | KEY_F5 => return,
            _ => {
                if self.ctrl {
                    if let Some((C('u'), _)) = key_of(self.layout, code) {
                        self.dead = None;
                        out.push(Key::CtrlU);
                    }
                    return;
                }
                if let Some(c) = keypad(code) {
                    self.give(C(c), out);
                    return;
                }
                if self.altgr {
                    if let Some(c) = altgr_of(self.layout, code) {
                        self.give(C(c), out);
                    }
                    return;
                }
                let Some((plain, shifted)) = key_of(self.layout, code) else {
                    return;
                };
                let letter = matches!(plain, C(c) if c.is_alphabetic());
                let upper = if letter {
                    self.shift != self.caps
                } else {
                    self.shift
                };
                self.give(if upper { shifted } else { plain }, out);
                return;
            }
        };
        // a key that is not a character ends a dead accent, which is lost
        self.dead = None;
        out.push(key);
    }

    /// A character, or a dead accent, through the accent waiting (if any).
    fn give(&mut self, given: Given, out: &mut Vec<Key>) {
        match (self.dead.take(), given) {
            (None, C(c)) => out.push(Key::Char(c)),
            (None, D(d)) => self.dead = Some(d),
            (Some(d), C(c)) => match compose(d, c) {
                Some(composed) => out.push(Key::Char(composed)),
                None => {
                    out.push(Key::Char(d));
                    out.push(Key::Char(c));
                }
            },
            // the same accent twice is the accent; another one, both
            (Some(d), D(e)) => {
                out.push(Key::Char(d));
                if d != e {
                    self.dead = Some(e);
                }
            }
        }
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
            modifiers: Modifiers::new(Layout::Us),
        }
    }

    /// Opens every keyboard under /dev/input, non-blocking, read by that
    /// layout. None is not an error: the screen still shows; it just
    /// cannot be driven.
    pub fn open(layout: Layout) -> Result<Keyboards> {
        tracing::info!("keyboard layout {}", layout.name());
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
            modifiers: Modifiers::new(layout),
        })
    }

    /// The layout the keys are read by.
    pub fn layout(&self) -> Layout {
        self.modifiers.layout
    }

    /// Reads the keys by another layout from now on (the system's keyboard
    /// changed under the daemon: `set-keyboard` approved on this screen).
    pub fn set_layout(&mut self, layout: Layout) {
        if layout != self.modifiers.layout {
            tracing::info!("keyboard layout {}", layout.name());
            self.modifiers = Modifiers::new(layout);
        }
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
                    self.modifiers.key(code, value, &mut keys);
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

    /// The keys a press (or a repeat, or a release) gives.
    fn press(m: &mut Modifiers, code: u16, value: i32) -> Vec<Key> {
        let mut out = Vec::new();
        m.key(code, value, &mut out);
        out
    }

    fn one(m: &mut Modifiers, code: u16, value: i32) -> Option<Key> {
        let out = press(m, code, value);
        assert!(out.len() <= 1, "{:?}", out);
        out.into_iter().next()
    }

    #[test]
    fn the_us_layout_gives_characters_with_shift_and_caps_and_the_keys_by_name() {
        let mut m = Modifiers::new(Layout::Us);
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('a')));
        assert_eq!(one(&mut m, 30, 2), Some(Key::Char('a'))); // held: repeats
        assert_eq!(one(&mut m, 30, 0), None);
        m.key(KEY_LEFTSHIFT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('A')));
        assert_eq!(one(&mut m, 2, 1), Some(Key::Char('!')));
        assert_eq!(one(&mut m, KEY_TAB, 1), Some(Key::ShiftTab));
        m.key(KEY_LEFTSHIFT, 0, &mut Vec::new());
        m.key(KEY_CAPSLOCK, 1, &mut Vec::new());
        m.key(KEY_CAPSLOCK, 0, &mut Vec::new());
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('A'))); // caps: letters only
        assert_eq!(one(&mut m, 2, 1), Some(Key::Char('1')));
        m.key(KEY_RIGHTSHIFT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('a'))); // caps and shift undo each other
        m.key(KEY_RIGHTSHIFT, 0, &mut Vec::new());
        m.key(KEY_CAPSLOCK, 1, &mut Vec::new());
        assert_eq!(one(&mut m, KEY_TAB, 1), Some(Key::Tab));
        assert_eq!(one(&mut m, KEY_ENTER, 1), Some(Key::Enter));
        assert_eq!(one(&mut m, KEY_ENTER, 2), None); // Enter held is one Enter
        assert_eq!(one(&mut m, KEY_KPENTER, 1), Some(Key::Enter));
        assert_eq!(one(&mut m, KEY_ESC, 1), Some(Key::Escape));
        assert_eq!(one(&mut m, KEY_BACKSPACE, 2), Some(Key::Backspace));
        assert_eq!(one(&mut m, KEY_F5, 1), Some(Key::F5));
        assert_eq!(one(&mut m, KEY_F1, 1), Some(Key::F1));
        assert_eq!(one(&mut m, KEY_SPACE, 1), Some(Key::Space));
        assert_eq!(one(&mut m, KEY_KP7, 1), Some(Key::Char('7')));
        assert_eq!(one(&mut m, KEY_KPDOT, 1), Some(Key::Char('.')));
        assert_eq!(one(&mut m, KEY_PAGEDOWN, 1), Some(Key::PageDown));
        // US: the accents are plain characters, nothing waits
        assert_eq!(one(&mut m, 40, 1), Some(Key::Char('\'')));
        assert_eq!(one(&mut m, 41, 1), Some(Key::Char('`')));
        m.key(KEY_LEFTCTRL, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 22, 1), Some(Key::CtrlU));
        assert_eq!(one(&mut m, 30, 1), None); // Ctrl+A is nobody's
        m.key(KEY_LEFTCTRL, 0, &mut Vec::new());
        assert_eq!(one(&mut m, 22, 1), Some(Key::Char('u')));
        assert_eq!(one(&mut m, 0x2ff_u16, 1), None);
    }

    #[test]
    fn abnt2_has_cedilla_and_composes_the_dead_accents_with_the_vowel_after() {
        let mut m = Modifiers::new(Layout::Abnt2);
        assert_eq!(one(&mut m, 39, 1), Some(Key::Char('ç')));
        m.key(KEY_LEFTSHIFT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 39, 1), Some(Key::Char('Ç')));
        m.key(KEY_LEFTSHIFT, 0, &mut Vec::new());
        // ~ then a: ã; the accent alone gives nothing yet
        assert_eq!(one(&mut m, 40, 1), None);
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('ã')));
        // ´ then e: é; Shift+´ is `, then a: à
        assert_eq!(one(&mut m, 26, 1), None);
        assert_eq!(one(&mut m, 18, 1), Some(Key::Char('é')));
        m.key(KEY_LEFTSHIFT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 26, 1), None);
        m.key(KEY_LEFTSHIFT, 0, &mut Vec::new());
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('à')));
        // Shift+~ is ^, then o: ô; Shift+6 is ¨, then u: ü
        m.key(KEY_LEFTSHIFT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 40, 1), None);
        m.key(KEY_LEFTSHIFT, 0, &mut Vec::new());
        assert_eq!(one(&mut m, 24, 1), Some(Key::Char('ô')));
        m.key(KEY_LEFTSHIFT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 7, 1), None);
        m.key(KEY_LEFTSHIFT, 0, &mut Vec::new());
        assert_eq!(one(&mut m, 22, 1), Some(Key::Char('ü')));
        // a capital through Caps Lock: ~ then A: Ã
        m.key(KEY_CAPSLOCK, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 40, 1), None);
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('Ã')));
        m.key(KEY_CAPSLOCK, 1, &mut Vec::new());
        // the accent then a space is the accent; then a letter it cannot take, both
        assert_eq!(one(&mut m, 40, 1), None);
        assert_eq!(one(&mut m, KEY_SPACE, 1), Some(Key::Char('~')));
        assert_eq!(one(&mut m, 40, 1), None);
        assert_eq!(press(&mut m, 45, 1), vec![Key::Char('~'), Key::Char('x')]);
        // the same accent twice is the accent; Enter forgets one waiting
        assert_eq!(one(&mut m, 40, 1), None);
        assert_eq!(one(&mut m, 40, 1), Some(Key::Char('~')));
        assert_eq!(one(&mut m, 26, 1), None);
        assert_eq!(one(&mut m, KEY_ENTER, 1), Some(Key::Enter));
        assert_eq!(one(&mut m, 30, 1), Some(Key::Char('a')));
        // the keys that moved: / on its own key, ; where / is on the US one, \ left of Z
        assert_eq!(one(&mut m, KEY_RO, 1), Some(Key::Char('/')));
        assert_eq!(one(&mut m, 53, 1), Some(Key::Char(';')));
        assert_eq!(one(&mut m, KEY_102ND, 1), Some(Key::Char('\\')));
        assert_eq!(one(&mut m, 41, 1), Some(Key::Char('\'')));
        assert_eq!(one(&mut m, 27, 1), Some(Key::Char('[')));
        assert_eq!(one(&mut m, 43, 1), Some(Key::Char(']')));
        // AltGr: ? on W, º on ]
        m.key(KEY_RIGHTALT, 1, &mut Vec::new());
        assert_eq!(one(&mut m, 17, 1), Some(Key::Char('?')));
        assert_eq!(one(&mut m, 43, 1), Some(Key::Char('º')));
        assert_eq!(one(&mut m, 30, 1), None);
        m.key(KEY_RIGHTALT, 0, &mut Vec::new());
    }

    #[test]
    fn the_hives_keyboard_setting_names_the_layout() {
        assert_eq!(Layout::from_setting("br abnt2\n"), Some(Layout::Abnt2));
        assert_eq!(Layout::from_setting("us"), Some(Layout::Us));
        assert_eq!(Layout::from_setting(""), None);
        assert_eq!(Layout::from_setting("fr"), None);
    }

    #[test]
    fn the_layout_is_read_from_the_system_s_keyboard_file() {
        assert_eq!(
            Layout::from_keyboard_file("XKBMODEL=\"abnt2\"\nXKBLAYOUT=\"br\"\n"),
            Layout::Abnt2
        );
        assert_eq!(Layout::from_keyboard_file("XKBLAYOUT=\"us\"\n"), Layout::Us);
        assert_eq!(
            Layout::from_keyboard_file("XKBLAYOUT=\"br,us\"\n"),
            Layout::Abnt2
        );
        assert_eq!(Layout::from_keyboard_file("XKBLAYOUT=\"de\"\n"), Layout::Us);
        assert_eq!(Layout::from_keyboard_file(""), Layout::Us);
        assert_eq!(Layout::parse("ABNT2"), Some(Layout::Abnt2));
        assert_eq!(Layout::parse("fr"), None);
    }
}
