//! Input device abstraction for VirtIO input via evdev
//!
//! This module provides access to keyboard and mouse events
//! from Linux input devices (/dev/input/eventX).

use crate::error::{BarkError, Result};
use std::collections::VecDeque;
use std::fs::{File, OpenOptions};
use std::io::Read;
use std::os::unix::io::AsRawFd;
use std::path::Path;

/// Linux input event structure
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
struct LinuxInputEvent {
    tv_sec: i64,
    tv_usec: i64,
    event_type: u16,
    code: u16,
    value: i32,
}

// Event types
const EV_SYN: u16 = 0x00;
const EV_KEY: u16 = 0x01;
const EV_REL: u16 = 0x02;
const EV_ABS: u16 = 0x03;

// Relative axes
const REL_X: u16 = 0x00;
const REL_Y: u16 = 0x01;
const REL_WHEEL: u16 = 0x08;

// Absolute axes
const ABS_X: u16 = 0x00;
const ABS_Y: u16 = 0x01;

/// Input device (keyboard, mouse, touchpad)
pub struct InputDevice {
    files: Vec<File>,
    event_queue: VecDeque<InputEvent>,
    mouse_x: i32,
    mouse_y: i32,
    keys_pressed: Vec<KeyCode>,
}

impl InputDevice {
    /// Open the default input device(s)
    pub fn open_default() -> Result<Self> {
        let mut files = Vec::new();

        // Try to open common input devices
        for i in 0..10 {
            let path = format!("/dev/input/event{}", i);
            if let Ok(file) = OpenOptions::new().read(true).open(&path) {
                // Set non-blocking
                let fd = file.as_raw_fd();
                unsafe {
                    let flags = libc::fcntl(fd, libc::F_GETFL);
                    libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK);
                }
                files.push(file);
            }
        }

        if files.is_empty() {
            return Err(BarkError::DeviceNotFound("No input devices found".into()));
        }

        Ok(Self {
            files,
            event_queue: VecDeque::new(),
            mouse_x: 0,
            mouse_y: 0,
            keys_pressed: Vec::new(),
        })
    }

    /// Open a specific input device
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let file = OpenOptions::new()
            .read(true)
            .open(path.as_ref())
            .map_err(|e| BarkError::Input(format!("Failed to open input device: {}", e)))?;

        // Set non-blocking
        let fd = file.as_raw_fd();
        unsafe {
            let flags = libc::fcntl(fd, libc::F_GETFL);
            libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK);
        }

        Ok(Self {
            files: vec![file],
            event_queue: VecDeque::new(),
            mouse_x: 0,
            mouse_y: 0,
            keys_pressed: Vec::new(),
        })
    }

    /// Create a dummy input device (for testing)
    pub fn dummy() -> Self {
        Self {
            files: Vec::new(),
            event_queue: VecDeque::new(),
            mouse_x: 0,
            mouse_y: 0,
            keys_pressed: Vec::new(),
        }
    }

    /// Poll for input events (non-blocking)
    pub fn poll(&mut self) -> Vec<InputEvent> {
        let mut raw_events = Vec::new();
        let mut buffer = [0u8; std::mem::size_of::<LinuxInputEvent>()];

        // First, collect all raw events from all files
        for file in &mut self.files {
            loop {
                match file.read_exact(&mut buffer) {
                    Ok(()) => {
                        let raw_event: LinuxInputEvent =
                            unsafe { std::ptr::read(buffer.as_ptr() as *const _) };
                        raw_events.push(raw_event);
                    }
                    Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                        break;
                    }
                    Err(_) => {
                        break;
                    }
                }
            }
        }

        // Now translate raw events (can borrow self mutably now)
        let mut events = Vec::new();
        for raw_event in raw_events {
            if let Some(event) = self.translate_event(raw_event) {
                events.push(event);
            }
        }

        // Also return any queued events
        while let Some(event) = self.event_queue.pop_front() {
            events.push(event);
        }

        events
    }

    /// Translate Linux input event to our InputEvent
    fn translate_event(&mut self, raw: LinuxInputEvent) -> Option<InputEvent> {
        match raw.event_type {
            EV_KEY => {
                let key = KeyCode::from_linux(raw.code);
                match raw.value {
                    0 => {
                        // Key released
                        self.keys_pressed.retain(|&k| k != key);
                        Some(InputEvent::KeyUp(key))
                    }
                    1 => {
                        // Key pressed
                        if !self.keys_pressed.contains(&key) {
                            self.keys_pressed.push(key);
                        }
                        Some(InputEvent::KeyDown(key))
                    }
                    2 => {
                        // Key repeat
                        Some(InputEvent::KeyRepeat(key))
                    }
                    _ => None,
                }
            }
            EV_REL => match raw.code {
                REL_X => {
                    self.mouse_x += raw.value;
                    Some(InputEvent::MouseMove {
                        x: self.mouse_x,
                        y: self.mouse_y,
                        dx: raw.value,
                        dy: 0,
                    })
                }
                REL_Y => {
                    self.mouse_y += raw.value;
                    Some(InputEvent::MouseMove {
                        x: self.mouse_x,
                        y: self.mouse_y,
                        dx: 0,
                        dy: raw.value,
                    })
                }
                REL_WHEEL => Some(InputEvent::MouseScroll { delta: raw.value }),
                _ => None,
            },
            EV_ABS => match raw.code {
                ABS_X => {
                    self.mouse_x = raw.value;
                    Some(InputEvent::MouseMove {
                        x: self.mouse_x,
                        y: self.mouse_y,
                        dx: 0,
                        dy: 0,
                    })
                }
                ABS_Y => {
                    self.mouse_y = raw.value;
                    Some(InputEvent::MouseMove {
                        x: self.mouse_x,
                        y: self.mouse_y,
                        dx: 0,
                        dy: 0,
                    })
                }
                _ => None,
            },
            _ => None,
        }
    }

    /// Get current mouse position
    pub fn mouse_position(&self) -> (i32, i32) {
        (self.mouse_x, self.mouse_y)
    }

    /// Set mouse position (for absolute positioning)
    pub fn set_mouse_position(&mut self, x: i32, y: i32) {
        self.mouse_x = x;
        self.mouse_y = y;
    }

    /// Check if a key is currently pressed
    pub fn is_key_pressed(&self, key: KeyCode) -> bool {
        self.keys_pressed.contains(&key)
    }

    /// Get all currently pressed keys
    pub fn pressed_keys(&self) -> &[KeyCode] {
        &self.keys_pressed
    }

    /// Inject a synthetic event (for testing)
    pub fn inject_event(&mut self, event: InputEvent) {
        self.event_queue.push_back(event);
    }
}

/// Input event types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum InputEvent {
    /// Key pressed
    KeyDown(KeyCode),
    /// Key released
    KeyUp(KeyCode),
    /// Key held (auto-repeat)
    KeyRepeat(KeyCode),
    /// Mouse moved
    MouseMove { x: i32, y: i32, dx: i32, dy: i32 },
    /// Mouse button pressed
    MouseButtonDown(MouseButton),
    /// Mouse button released
    MouseButtonUp(MouseButton),
    /// Mouse wheel scrolled
    MouseScroll { delta: i32 },
}

/// Mouse buttons
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
    Button4,
    Button5,
}

/// Key codes (subset of Linux keycodes)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u16)]
pub enum KeyCode {
    Unknown = 0,
    Escape = 1,
    Key1 = 2,
    Key2 = 3,
    Key3 = 4,
    Key4 = 5,
    Key5 = 6,
    Key6 = 7,
    Key7 = 8,
    Key8 = 9,
    Key9 = 10,
    Key0 = 11,
    Minus = 12,
    Equal = 13,
    Backspace = 14,
    Tab = 15,
    Q = 16,
    W = 17,
    E = 18,
    R = 19,
    T = 20,
    Y = 21,
    U = 22,
    I = 23,
    O = 24,
    P = 25,
    LeftBracket = 26,
    RightBracket = 27,
    Enter = 28,
    LeftCtrl = 29,
    A = 30,
    S = 31,
    D = 32,
    F = 33,
    G = 34,
    H = 35,
    J = 36,
    K = 37,
    L = 38,
    Semicolon = 39,
    Apostrophe = 40,
    Grave = 41,
    LeftShift = 42,
    Backslash = 43,
    Z = 44,
    X = 45,
    C = 46,
    V = 47,
    B = 48,
    N = 49,
    M = 50,
    Comma = 51,
    Dot = 52,
    Slash = 53,
    RightShift = 54,
    KpAsterisk = 55,
    LeftAlt = 56,
    Space = 57,
    CapsLock = 58,
    F1 = 59,
    F2 = 60,
    F3 = 61,
    F4 = 62,
    F5 = 63,
    F6 = 64,
    F7 = 65,
    F8 = 66,
    F9 = 67,
    F10 = 68,
    NumLock = 69,
    ScrollLock = 70,
    Kp7 = 71,
    Kp8 = 72,
    Kp9 = 73,
    KpMinus = 74,
    Kp4 = 75,
    Kp5 = 76,
    Kp6 = 77,
    KpPlus = 78,
    Kp1 = 79,
    Kp2 = 80,
    Kp3 = 81,
    Kp0 = 82,
    KpDot = 83,
    F11 = 87,
    F12 = 88,
    KpEnter = 96,
    RightCtrl = 97,
    KpSlash = 98,
    RightAlt = 100,
    Home = 102,
    Up = 103,
    PageUp = 104,
    Left = 105,
    Right = 106,
    End = 107,
    Down = 108,
    PageDown = 109,
    Insert = 110,
    Delete = 111,
    LeftMeta = 125,
    RightMeta = 126,
    // Mouse buttons (Linux BTN_* codes)
    MouseLeft = 0x110,
    MouseRight = 0x111,
    MouseMiddle = 0x112,
}

impl KeyCode {
    /// Convert Linux keycode to KeyCode
    pub fn from_linux(code: u16) -> Self {
        match code {
            1 => KeyCode::Escape,
            2 => KeyCode::Key1,
            3 => KeyCode::Key2,
            4 => KeyCode::Key3,
            5 => KeyCode::Key4,
            6 => KeyCode::Key5,
            7 => KeyCode::Key6,
            8 => KeyCode::Key7,
            9 => KeyCode::Key8,
            10 => KeyCode::Key9,
            11 => KeyCode::Key0,
            12 => KeyCode::Minus,
            13 => KeyCode::Equal,
            14 => KeyCode::Backspace,
            15 => KeyCode::Tab,
            16 => KeyCode::Q,
            17 => KeyCode::W,
            18 => KeyCode::E,
            19 => KeyCode::R,
            20 => KeyCode::T,
            21 => KeyCode::Y,
            22 => KeyCode::U,
            23 => KeyCode::I,
            24 => KeyCode::O,
            25 => KeyCode::P,
            26 => KeyCode::LeftBracket,
            27 => KeyCode::RightBracket,
            28 => KeyCode::Enter,
            29 => KeyCode::LeftCtrl,
            30 => KeyCode::A,
            31 => KeyCode::S,
            32 => KeyCode::D,
            33 => KeyCode::F,
            34 => KeyCode::G,
            35 => KeyCode::H,
            36 => KeyCode::J,
            37 => KeyCode::K,
            38 => KeyCode::L,
            39 => KeyCode::Semicolon,
            40 => KeyCode::Apostrophe,
            41 => KeyCode::Grave,
            42 => KeyCode::LeftShift,
            43 => KeyCode::Backslash,
            44 => KeyCode::Z,
            45 => KeyCode::X,
            46 => KeyCode::C,
            47 => KeyCode::V,
            48 => KeyCode::B,
            49 => KeyCode::N,
            50 => KeyCode::M,
            51 => KeyCode::Comma,
            52 => KeyCode::Dot,
            53 => KeyCode::Slash,
            54 => KeyCode::RightShift,
            57 => KeyCode::Space,
            58 => KeyCode::CapsLock,
            59 => KeyCode::F1,
            60 => KeyCode::F2,
            61 => KeyCode::F3,
            62 => KeyCode::F4,
            63 => KeyCode::F5,
            64 => KeyCode::F6,
            65 => KeyCode::F7,
            66 => KeyCode::F8,
            67 => KeyCode::F9,
            68 => KeyCode::F10,
            87 => KeyCode::F11,
            88 => KeyCode::F12,
            97 => KeyCode::RightCtrl,
            100 => KeyCode::RightAlt,
            102 => KeyCode::Home,
            103 => KeyCode::Up,
            104 => KeyCode::PageUp,
            105 => KeyCode::Left,
            106 => KeyCode::Right,
            107 => KeyCode::End,
            108 => KeyCode::Down,
            109 => KeyCode::PageDown,
            110 => KeyCode::Insert,
            111 => KeyCode::Delete,
            125 => KeyCode::LeftMeta,
            126 => KeyCode::RightMeta,
            0x110 => KeyCode::MouseLeft,
            0x111 => KeyCode::MouseRight,
            0x112 => KeyCode::MouseMiddle,
            _ => KeyCode::Unknown,
        }
    }

    /// Convert to printable character (if applicable)
    pub fn to_char(&self, shift: bool) -> Option<char> {
        match (self, shift) {
            (KeyCode::A, false) => Some('a'),
            (KeyCode::A, true) => Some('A'),
            (KeyCode::B, false) => Some('b'),
            (KeyCode::B, true) => Some('B'),
            (KeyCode::C, false) => Some('c'),
            (KeyCode::C, true) => Some('C'),
            (KeyCode::D, false) => Some('d'),
            (KeyCode::D, true) => Some('D'),
            (KeyCode::E, false) => Some('e'),
            (KeyCode::E, true) => Some('E'),
            (KeyCode::F, false) => Some('f'),
            (KeyCode::F, true) => Some('F'),
            (KeyCode::G, false) => Some('g'),
            (KeyCode::G, true) => Some('G'),
            (KeyCode::H, false) => Some('h'),
            (KeyCode::H, true) => Some('H'),
            (KeyCode::I, false) => Some('i'),
            (KeyCode::I, true) => Some('I'),
            (KeyCode::J, false) => Some('j'),
            (KeyCode::J, true) => Some('J'),
            (KeyCode::K, false) => Some('k'),
            (KeyCode::K, true) => Some('K'),
            (KeyCode::L, false) => Some('l'),
            (KeyCode::L, true) => Some('L'),
            (KeyCode::M, false) => Some('m'),
            (KeyCode::M, true) => Some('M'),
            (KeyCode::N, false) => Some('n'),
            (KeyCode::N, true) => Some('N'),
            (KeyCode::O, false) => Some('o'),
            (KeyCode::O, true) => Some('O'),
            (KeyCode::P, false) => Some('p'),
            (KeyCode::P, true) => Some('P'),
            (KeyCode::Q, false) => Some('q'),
            (KeyCode::Q, true) => Some('Q'),
            (KeyCode::R, false) => Some('r'),
            (KeyCode::R, true) => Some('R'),
            (KeyCode::S, false) => Some('s'),
            (KeyCode::S, true) => Some('S'),
            (KeyCode::T, false) => Some('t'),
            (KeyCode::T, true) => Some('T'),
            (KeyCode::U, false) => Some('u'),
            (KeyCode::U, true) => Some('U'),
            (KeyCode::V, false) => Some('v'),
            (KeyCode::V, true) => Some('V'),
            (KeyCode::W, false) => Some('w'),
            (KeyCode::W, true) => Some('W'),
            (KeyCode::X, false) => Some('x'),
            (KeyCode::X, true) => Some('X'),
            (KeyCode::Y, false) => Some('y'),
            (KeyCode::Y, true) => Some('Y'),
            (KeyCode::Z, false) => Some('z'),
            (KeyCode::Z, true) => Some('Z'),
            (KeyCode::Key0, false) => Some('0'),
            (KeyCode::Key0, true) => Some(')'),
            (KeyCode::Key1, false) => Some('1'),
            (KeyCode::Key1, true) => Some('!'),
            (KeyCode::Key2, false) => Some('2'),
            (KeyCode::Key2, true) => Some('@'),
            (KeyCode::Key3, false) => Some('3'),
            (KeyCode::Key3, true) => Some('#'),
            (KeyCode::Key4, false) => Some('4'),
            (KeyCode::Key4, true) => Some('$'),
            (KeyCode::Key5, false) => Some('5'),
            (KeyCode::Key5, true) => Some('%'),
            (KeyCode::Key6, false) => Some('6'),
            (KeyCode::Key6, true) => Some('^'),
            (KeyCode::Key7, false) => Some('7'),
            (KeyCode::Key7, true) => Some('&'),
            (KeyCode::Key8, false) => Some('8'),
            (KeyCode::Key8, true) => Some('*'),
            (KeyCode::Key9, false) => Some('9'),
            (KeyCode::Key9, true) => Some('('),
            (KeyCode::Space, _) => Some(' '),
            (KeyCode::Enter, _) => Some('\n'),
            (KeyCode::Tab, _) => Some('\t'),
            (KeyCode::Minus, false) => Some('-'),
            (KeyCode::Minus, true) => Some('_'),
            (KeyCode::Equal, false) => Some('='),
            (KeyCode::Equal, true) => Some('+'),
            (KeyCode::LeftBracket, false) => Some('['),
            (KeyCode::LeftBracket, true) => Some('{'),
            (KeyCode::RightBracket, false) => Some(']'),
            (KeyCode::RightBracket, true) => Some('}'),
            (KeyCode::Semicolon, false) => Some(';'),
            (KeyCode::Semicolon, true) => Some(':'),
            (KeyCode::Apostrophe, false) => Some('\''),
            (KeyCode::Apostrophe, true) => Some('"'),
            (KeyCode::Comma, false) => Some(','),
            (KeyCode::Comma, true) => Some('<'),
            (KeyCode::Dot, false) => Some('.'),
            (KeyCode::Dot, true) => Some('>'),
            (KeyCode::Slash, false) => Some('/'),
            (KeyCode::Slash, true) => Some('?'),
            (KeyCode::Backslash, false) => Some('\\'),
            (KeyCode::Backslash, true) => Some('|'),
            (KeyCode::Grave, false) => Some('`'),
            (KeyCode::Grave, true) => Some('~'),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_keycode_to_char() {
        assert_eq!(KeyCode::A.to_char(false), Some('a'));
        assert_eq!(KeyCode::A.to_char(true), Some('A'));
        assert_eq!(KeyCode::Space.to_char(false), Some(' '));
        assert_eq!(KeyCode::Enter.to_char(false), Some('\n'));
    }

    #[test]
    fn test_dummy_input() {
        let mut input = InputDevice::dummy();
        input.inject_event(InputEvent::KeyDown(KeyCode::A));

        let events = input.poll();
        assert_eq!(events.len(), 1);
        assert_eq!(events[0], InputEvent::KeyDown(KeyCode::A));
    }
}
