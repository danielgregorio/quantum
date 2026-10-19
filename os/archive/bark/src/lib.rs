//! # Bark - DruidOS Hardware Abstraction Layer
//!
//! Bark provides thin abstractions over Linux device interfaces,
//! specifically optimized for VirtIO devices in virtual machines.
//!
//! ## Modules
//!
//! - [`framebuffer`] - VirtIO GPU / Linux framebuffer access
//! - [`input`] - VirtIO input (keyboard, mouse) via evdev
//! - [`time`] - Clock and timer functions
//! - [`console`] - Text I/O for serial console
//!
//! ## Example
//!
//! ```rust,no_run
//! use bark::Framebuffer;
//!
//! // Initialize framebuffer
//! let mut fb = Framebuffer::open("/dev/fb0").unwrap();
//!
//! // Clear to black
//! fb.clear(0x00000000);
//!
//! // Draw a red pixel
//! fb.set_pixel(100, 100, 0xFFFF0000);
//!
//! // Flush to display
//! fb.flush();
//! ```

pub mod console;
pub mod error;
pub mod framebuffer;
pub mod input;
pub mod time;

// Re-exports for convenience
pub use console::{Console, ConsoleColor};
pub use error::{BarkError, Result};
pub use framebuffer::Framebuffer;
pub use input::{InputDevice, InputEvent, KeyCode, MouseButton};
pub use time::{get_time_ms, get_time_us, sleep_ms, sleep_us, FrameTimer, Instant};

/// Bark version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Initialize Bark HAL
///
/// This should be called once at startup to initialize all subsystems.
pub fn init() -> Result<BarkContext> {
    BarkContext::new()
}

/// Main Bark context holding all device handles
pub struct BarkContext {
    pub framebuffer: Option<Framebuffer>,
    pub input: Option<InputDevice>,
    pub console: Console,
}

impl BarkContext {
    /// Create a new Bark context, auto-detecting available devices
    pub fn new() -> Result<Self> {
        // Try to open framebuffer (optional - might not be available)
        let framebuffer = Framebuffer::open_default().ok();

        // Try to open input device (optional)
        let input = InputDevice::open_default().ok();

        // Console - try real console first, fall back to stdio
        let console = Console::open_default().unwrap_or_else(|_| Console::stdio());

        Ok(Self {
            framebuffer,
            input,
            console,
        })
    }

    /// Check if graphical display is available
    pub fn has_display(&self) -> bool {
        self.framebuffer.is_some()
    }

    /// Check if input device is available
    pub fn has_input(&self) -> bool {
        self.input.is_some()
    }

    /// Get framebuffer, panics if not available
    pub fn fb(&mut self) -> &mut Framebuffer {
        self.framebuffer.as_mut().expect("No framebuffer available")
    }

    /// Get input device, panics if not available
    pub fn input(&mut self) -> &mut InputDevice {
        self.input.as_mut().expect("No input device available")
    }
}

impl Default for BarkContext {
    fn default() -> Self {
        Self::new().expect("Failed to initialize Bark")
    }
}
