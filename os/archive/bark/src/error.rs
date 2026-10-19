//! Error types for Bark HAL

use std::io;
use thiserror::Error;

/// Result type for Bark operations
pub type Result<T> = std::result::Result<T, BarkError>;

/// Errors that can occur in Bark HAL
#[derive(Error, Debug)]
pub enum BarkError {
    /// I/O error from system calls
    #[error("I/O error: {0}")]
    Io(#[from] io::Error),

    /// Device not found
    #[error("Device not found: {0}")]
    DeviceNotFound(String),

    /// Device not supported
    #[error("Device not supported: {0}")]
    NotSupported(String),

    /// Invalid parameter
    #[error("Invalid parameter: {0}")]
    InvalidParameter(String),

    /// Memory mapping failed
    #[error("Memory mapping failed: {0}")]
    MmapFailed(String),

    /// Framebuffer error
    #[error("Framebuffer error: {0}")]
    Framebuffer(String),

    /// Input device error
    #[error("Input error: {0}")]
    Input(String),

    /// Permission denied
    #[error("Permission denied: {0}")]
    PermissionDenied(String),
}

impl From<nix::Error> for BarkError {
    fn from(e: nix::Error) -> Self {
        BarkError::Io(io::Error::from_raw_os_error(e as i32))
    }
}
