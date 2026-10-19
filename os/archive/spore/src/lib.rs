//! # SPORE - Software-based Portable Rendering Engine
//!
//! SPORE is a CPU-based 2D rendering engine for DruidOS. It provides
//! efficient software rendering without requiring GPU acceleration,
//! making it ideal for virtual machine environments.
//!
//! ## Features
//!
//! - Software-based 2D rendering (no GPU required)
//! - Double-buffered framebuffer via Bark HAL
//! - Sprite blitting with transparency
//! - Primitive drawing (rectangles, lines, circles)
//! - Text rendering with bitmap fonts
//! - Tilemap support
//! - Simple particle system
//!
//! ## Example
//!
//! ```rust,no_run
//! use spore::{Canvas, Color};
//!
//! // Create a canvas
//! let mut canvas = Canvas::new(1280, 720);
//!
//! // Clear to dark background
//! canvas.clear(Color::rgb(20, 20, 30));
//!
//! // Draw a filled rectangle
//! canvas.fill_rect(100, 100, 200, 150, Color::rgb(255, 100, 50));
//!
//! // Get the pixel buffer to send to Bark
//! let pixels = canvas.pixels();
//! ```

pub mod canvas;
pub mod color;
pub mod particle;
pub mod primitives;
pub mod sprite;
pub mod text;
pub mod tilemap;

// Re-exports
pub use canvas::Canvas;
pub use color::Color;
pub use particle::{Particle, ParticleSystem};
pub use sprite::{Sprite, SpriteSheet};
pub use text::{BitmapFont, TextRenderer};
pub use tilemap::{Tile, Tilemap};

/// SPORE version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default screen width
pub const DEFAULT_WIDTH: u32 = 1280;

/// Default screen height
pub const DEFAULT_HEIGHT: u32 = 720;

/// Target FPS
pub const TARGET_FPS: u32 = 60;
