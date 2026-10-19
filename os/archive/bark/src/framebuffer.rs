//! Framebuffer abstraction for VirtIO GPU / Linux fbdev
//!
//! This module provides access to the display framebuffer,
//! allowing SPORE to write pixels directly to the screen.
//!
//! Supports:
//! - Linux framebuffer device (/dev/fb0)
//! - VirtIO GPU (via DRM - future)
//! - Memory-mapped pixel buffer

use crate::error::{BarkError, Result};
use memmap2::MmapMut;
use std::fs::{File, OpenOptions};
use std::os::unix::io::AsRawFd;
use std::path::Path;

/// Framebuffer info from FBIOGET_VSCREENINFO
#[repr(C)]
#[derive(Debug, Clone, Default)]
pub struct FbVarScreenInfo {
    pub xres: u32,
    pub yres: u32,
    pub xres_virtual: u32,
    pub yres_virtual: u32,
    pub xoffset: u32,
    pub yoffset: u32,
    pub bits_per_pixel: u32,
    pub grayscale: u32,
    // RGB bitfield info
    pub red_offset: u32,
    pub red_length: u32,
    pub red_msb_right: u32,
    pub green_offset: u32,
    pub green_length: u32,
    pub green_msb_right: u32,
    pub blue_offset: u32,
    pub blue_length: u32,
    pub blue_msb_right: u32,
    pub transp_offset: u32,
    pub transp_length: u32,
    pub transp_msb_right: u32,
    pub nonstd: u32,
    pub activate: u32,
    pub height: u32,
    pub width: u32,
    pub accel_flags: u32,
    // Timing (not used)
    pub pixclock: u32,
    pub left_margin: u32,
    pub right_margin: u32,
    pub upper_margin: u32,
    pub lower_margin: u32,
    pub hsync_len: u32,
    pub vsync_len: u32,
    pub sync: u32,
    pub vmode: u32,
    pub rotate: u32,
    pub colorspace: u32,
    pub reserved: [u32; 4],
}

/// Fixed screen info from FBIOGET_FSCREENINFO
#[repr(C)]
#[derive(Debug, Clone, Default)]
pub struct FbFixScreenInfo {
    pub id: [u8; 16],
    pub smem_start: usize,
    pub smem_len: u32,
    pub fb_type: u32,
    pub type_aux: u32,
    pub visual: u32,
    pub xpanstep: u16,
    pub ypanstep: u16,
    pub ywrapstep: u16,
    pub line_length: u32,
    pub mmio_start: usize,
    pub mmio_len: u32,
    pub accel: u32,
    pub capabilities: u16,
    pub reserved: [u16; 2],
}

// ioctl constants for framebuffer
// Use c_ulong for glibc x86_64 compatibility
const FBIOGET_VSCREENINFO: libc::c_ulong = 0x4600;
const FBIOGET_FSCREENINFO: libc::c_ulong = 0x4602;
#[allow(dead_code)]
const FBIOPAN_DISPLAY: libc::c_ulong = 0x4606;

/// Linux framebuffer device wrapper
pub struct Framebuffer {
    /// File handle to /dev/fbX
    file: File,
    /// Memory-mapped framebuffer
    mmap: MmapMut,
    /// Screen width in pixels
    pub width: u32,
    /// Screen height in pixels
    pub height: u32,
    /// Bits per pixel (usually 32)
    pub bpp: u32,
    /// Bytes per line (may include padding)
    pub stride: u32,
    /// Total size in bytes
    pub size: usize,
    /// Variable screen info
    var_info: FbVarScreenInfo,
    /// Fixed screen info
    fix_info: FbFixScreenInfo,
    /// Software backbuffer for double buffering
    backbuffer: Vec<u32>,
    /// Use double buffering
    double_buffer: bool,
}

impl Framebuffer {
    /// Open the default framebuffer device (/dev/fb0)
    pub fn open_default() -> Result<Self> {
        Self::open("/dev/fb0")
    }

    /// Open a specific framebuffer device
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref();

        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(path)
            .map_err(|e| {
                if e.kind() == std::io::ErrorKind::PermissionDenied {
                    BarkError::PermissionDenied(format!("Cannot open {}: {}", path.display(), e))
                } else if e.kind() == std::io::ErrorKind::NotFound {
                    BarkError::DeviceNotFound(format!("Framebuffer not found: {}", path.display()))
                } else {
                    BarkError::Io(e)
                }
            })?;

        let fd = file.as_raw_fd();

        // Get variable screen info
        let mut var_info = FbVarScreenInfo::default();
        unsafe {
            if libc::ioctl(fd, FBIOGET_VSCREENINFO, &mut var_info) < 0 {
                return Err(BarkError::Framebuffer(
                    "Failed to get variable screen info".into(),
                ));
            }
        }

        // Get fixed screen info
        let mut fix_info = FbFixScreenInfo::default();
        unsafe {
            if libc::ioctl(fd, FBIOGET_FSCREENINFO, &mut fix_info) < 0 {
                return Err(BarkError::Framebuffer(
                    "Failed to get fixed screen info".into(),
                ));
            }
        }

        let width = var_info.xres;
        let height = var_info.yres;
        let bpp = var_info.bits_per_pixel;
        let stride = fix_info.line_length;
        let size = fix_info.smem_len as usize;

        // Memory map the framebuffer with explicit size
        // Using map_mut(&file) doesn't work for device files - need explicit size
        let mmap = unsafe {
            memmap2::MmapOptions::new()
                .len(size)
                .map_mut(&file)
                .map_err(|e| BarkError::MmapFailed(format!("Failed to mmap framebuffer: {}", e)))?
        };

        // Create backbuffer for double buffering
        let backbuffer = vec![0u32; (width * height) as usize];

        Ok(Self {
            file,
            mmap,
            width,
            height,
            bpp,
            stride,
            size,
            var_info,
            fix_info,
            backbuffer,
            double_buffer: true,
        })
    }

    /// Create a virtual framebuffer (for testing without hardware)
    pub fn virtual_fb(width: u32, height: u32) -> Self {
        let size = (width * height * 4) as usize;
        let backbuffer = vec![0u32; (width * height) as usize];

        // Create a dummy mmap using anonymous memory
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .open("/dev/zero")
            .expect("Failed to open /dev/zero");

        let mmap = MmapMut::map_anon(size).expect("Failed to create anonymous mmap");

        Self {
            file,
            mmap,
            width,
            height,
            bpp: 32,
            stride: width * 4,
            size,
            var_info: FbVarScreenInfo::default(),
            fix_info: FbFixScreenInfo::default(),
            backbuffer,
            double_buffer: true,
        }
    }

    /// Enable or disable double buffering
    pub fn set_double_buffer(&mut self, enabled: bool) {
        self.double_buffer = enabled;
    }

    /// Get the pixel buffer (backbuffer if double buffering, direct mmap otherwise)
    pub fn pixels(&self) -> &[u32] {
        if self.double_buffer {
            &self.backbuffer
        } else {
            // Interpret mmap as u32 slice
            unsafe {
                std::slice::from_raw_parts(
                    self.mmap.as_ptr() as *const u32,
                    (self.width * self.height) as usize,
                )
            }
        }
    }

    /// Get mutable pixel buffer
    pub fn pixels_mut(&mut self) -> &mut [u32] {
        if self.double_buffer {
            &mut self.backbuffer
        } else {
            unsafe {
                std::slice::from_raw_parts_mut(
                    self.mmap.as_mut_ptr() as *mut u32,
                    (self.width * self.height) as usize,
                )
            }
        }
    }

    /// Set a single pixel (ARGB format: 0xAARRGGBB)
    #[inline(always)]
    pub fn set_pixel(&mut self, x: u32, y: u32, color: u32) {
        if x < self.width && y < self.height {
            let idx = (y * self.width + x) as usize;
            if self.double_buffer {
                self.backbuffer[idx] = color;
            } else {
                let offset = (y * self.stride + x * (self.bpp / 8)) as usize;
                if offset + 4 <= self.mmap.len() {
                    self.mmap[offset..offset + 4].copy_from_slice(&color.to_ne_bytes());
                }
            }
        }
    }

    /// Get a single pixel
    #[inline(always)]
    pub fn get_pixel(&self, x: u32, y: u32) -> u32 {
        if x < self.width && y < self.height {
            let idx = (y * self.width + x) as usize;
            if self.double_buffer {
                self.backbuffer[idx]
            } else {
                let offset = (y * self.stride + x * (self.bpp / 8)) as usize;
                if offset + 4 <= self.mmap.len() {
                    u32::from_ne_bytes([
                        self.mmap[offset],
                        self.mmap[offset + 1],
                        self.mmap[offset + 2],
                        self.mmap[offset + 3],
                    ])
                } else {
                    0
                }
            }
        } else {
            0
        }
    }

    /// Clear the entire framebuffer to a color
    pub fn clear(&mut self, color: u32) {
        if self.double_buffer {
            self.backbuffer.fill(color);
        } else {
            let pixels = unsafe {
                std::slice::from_raw_parts_mut(
                    self.mmap.as_mut_ptr() as *mut u32,
                    (self.width * self.height) as usize,
                )
            };
            pixels.fill(color);
        }
    }

    /// Flush backbuffer to display (only if double buffering)
    pub fn flush(&mut self) {
        if self.double_buffer {
            let bytes_per_pixel = (self.bpp / 8) as usize;

            // Handle different bit depths
            match self.bpp {
                32 => {
                    // 32bpp: direct copy possible if no stride padding
                    if self.stride == self.width * 4 {
                        let src = unsafe {
                            std::slice::from_raw_parts(
                                self.backbuffer.as_ptr() as *const u8,
                                self.backbuffer.len() * 4,
                            )
                        };
                        let len = src.len().min(self.mmap.len());
                        self.mmap[..len].copy_from_slice(&src[..len]);
                    } else {
                        // Handle stride (row padding)
                        for y in 0..self.height {
                            let src_offset = (y * self.width) as usize;
                            let dst_offset = (y * self.stride) as usize;
                            let row_bytes = (self.width * 4) as usize;

                            let src = unsafe {
                                std::slice::from_raw_parts(
                                    self.backbuffer.as_ptr().add(src_offset) as *const u8,
                                    row_bytes,
                                )
                            };
                            if dst_offset + row_bytes <= self.mmap.len() {
                                self.mmap[dst_offset..dst_offset + row_bytes].copy_from_slice(src);
                            }
                        }
                    }
                }
                24 => {
                    // 24bpp: convert each u32 pixel to 3 bytes (BGR format for Linux fbdev)
                    for y in 0..self.height {
                        let src_row_start = (y * self.width) as usize;
                        let dst_row_start = (y * self.stride) as usize;

                        for x in 0..self.width as usize {
                            let pixel = self.backbuffer[src_row_start + x];
                            let dst_offset = dst_row_start + x * 3;

                            if dst_offset + 3 <= self.mmap.len() {
                                // Extract RGB from ARGB and write as BGR (Linux fbdev order)
                                let r = ((pixel >> 16) & 0xFF) as u8;
                                let g = ((pixel >> 8) & 0xFF) as u8;
                                let b = (pixel & 0xFF) as u8;

                                self.mmap[dst_offset] = b;
                                self.mmap[dst_offset + 1] = g;
                                self.mmap[dst_offset + 2] = r;
                            }
                        }
                    }
                }
                16 => {
                    // 16bpp: convert to RGB565
                    for y in 0..self.height {
                        let src_row_start = (y * self.width) as usize;
                        let dst_row_start = (y * self.stride) as usize;

                        for x in 0..self.width as usize {
                            let pixel = self.backbuffer[src_row_start + x];
                            let dst_offset = dst_row_start + x * 2;

                            if dst_offset + 2 <= self.mmap.len() {
                                let r = ((pixel >> 16) & 0xFF) as u16;
                                let g = ((pixel >> 8) & 0xFF) as u16;
                                let b = (pixel & 0xFF) as u16;

                                // RGB565: RRRRRGGGGGGBBBBB
                                let rgb565: u16 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
                                self.mmap[dst_offset..dst_offset + 2]
                                    .copy_from_slice(&rgb565.to_le_bytes());
                            }
                        }
                    }
                }
                _ => {
                    // Unsupported bit depth, do nothing
                }
            }
        }

        // Sync memory
        let _ = self.mmap.flush();
    }

    /// Copy a buffer of pixels to the framebuffer
    ///
    /// This is the main function SPORE uses to send rendered frames.
    pub fn copy_buffer(&mut self, buffer: &[u32]) {
        let len = buffer.len().min((self.width * self.height) as usize);
        if self.double_buffer {
            self.backbuffer[..len].copy_from_slice(&buffer[..len]);
        } else {
            let pixels = unsafe {
                std::slice::from_raw_parts_mut(
                    self.mmap.as_mut_ptr() as *mut u32,
                    (self.width * self.height) as usize,
                )
            };
            pixels[..len].copy_from_slice(&buffer[..len]);
        }
    }

    /// Get raw pointer to backbuffer (for SPORE)
    pub fn as_ptr(&self) -> *const u32 {
        if self.double_buffer {
            self.backbuffer.as_ptr()
        } else {
            self.mmap.as_ptr() as *const u32
        }
    }

    /// Get mutable raw pointer to backbuffer
    pub fn as_mut_ptr(&mut self) -> *mut u32 {
        if self.double_buffer {
            self.backbuffer.as_mut_ptr()
        } else {
            self.mmap.as_mut_ptr() as *mut u32
        }
    }

    /// Get framebuffer info
    pub fn info(&self) -> FramebufferInfo {
        FramebufferInfo {
            width: self.width,
            height: self.height,
            bpp: self.bpp,
            stride: self.stride,
            size: self.size,
        }
    }
}

/// Framebuffer information
#[derive(Debug, Clone, Copy)]
pub struct FramebufferInfo {
    pub width: u32,
    pub height: u32,
    pub bpp: u32,
    pub stride: u32,
    pub size: usize,
}

impl std::fmt::Display for FramebufferInfo {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}x{}@{}bpp (stride: {}, size: {})",
            self.width, self.height, self.bpp, self.stride, self.size
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_virtual_framebuffer() {
        let mut fb = Framebuffer::virtual_fb(320, 240);
        assert_eq!(fb.width, 320);
        assert_eq!(fb.height, 240);

        // Test set/get pixel
        fb.set_pixel(10, 20, 0xFFFF0000);
        assert_eq!(fb.get_pixel(10, 20), 0xFFFF0000);

        // Test clear
        fb.clear(0xFF00FF00);
        assert_eq!(fb.get_pixel(0, 0), 0xFF00FF00);
        assert_eq!(fb.get_pixel(100, 100), 0xFF00FF00);

        // Test bounds
        fb.set_pixel(1000, 1000, 0xFFFFFFFF); // Should not panic
        assert_eq!(fb.get_pixel(1000, 1000), 0); // Out of bounds returns 0
    }

    #[test]
    fn test_framebuffer_info() {
        let fb = Framebuffer::virtual_fb(1280, 720);
        let info = fb.info();
        assert_eq!(info.width, 1280);
        assert_eq!(info.height, 720);
        assert_eq!(info.bpp, 32);
    }
}
