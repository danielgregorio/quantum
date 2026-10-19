//! Canvas - The main rendering surface
//!
//! The Canvas is a software framebuffer that all rendering operations
//! draw to. It can be flushed to the hardware via Bark.

use crate::color::Color;

/// A 2D pixel buffer for software rendering
pub struct Canvas {
    /// Width in pixels
    pub width: u32,
    /// Height in pixels
    pub height: u32,
    /// Pixel data (ARGB format)
    pixels: Vec<u32>,
    /// Clip rectangle (x, y, width, height)
    clip: Option<(i32, i32, u32, u32)>,
}

impl Canvas {
    /// Create a new canvas with the specified dimensions
    pub fn new(width: u32, height: u32) -> Self {
        let pixels = vec![0xFF000000; (width * height) as usize];
        Self {
            width,
            height,
            pixels,
            clip: None,
        }
    }

    /// Create a canvas with default DruidOS resolution (1280x720)
    pub fn default_resolution() -> Self {
        Self::new(crate::DEFAULT_WIDTH, crate::DEFAULT_HEIGHT)
    }

    /// Get the pixel buffer as a slice
    #[inline]
    pub fn pixels(&self) -> &[u32] {
        &self.pixels
    }

    /// Get the pixel buffer as a mutable slice
    #[inline]
    pub fn pixels_mut(&mut self) -> &mut [u32] {
        &mut self.pixels
    }

    /// Get a raw pointer to the pixel data
    #[inline]
    pub fn as_ptr(&self) -> *const u32 {
        self.pixels.as_ptr()
    }

    /// Get a mutable raw pointer to the pixel data
    #[inline]
    pub fn as_mut_ptr(&mut self) -> *mut u32 {
        self.pixels.as_mut_ptr()
    }

    /// Get the total number of pixels
    #[inline]
    pub fn len(&self) -> usize {
        self.pixels.len()
    }

    /// Check if the canvas is empty
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.pixels.is_empty()
    }

    /// Set a clipping rectangle
    ///
    /// All drawing operations will be clipped to this rectangle.
    pub fn set_clip(&mut self, x: i32, y: i32, width: u32, height: u32) {
        self.clip = Some((x, y, width, height));
    }

    /// Clear the clipping rectangle
    pub fn clear_clip(&mut self) {
        self.clip = None;
    }

    /// Check if a point is within the clipping region (and canvas bounds)
    #[inline]
    fn is_visible(&self, x: i32, y: i32) -> bool {
        if x < 0 || y < 0 || x >= self.width as i32 || y >= self.height as i32 {
            return false;
        }

        if let Some((cx, cy, cw, ch)) = self.clip {
            x >= cx && y >= cy && x < cx + cw as i32 && y < cy + ch as i32
        } else {
            true
        }
    }

    /// Convert (x, y) to pixel index
    #[inline]
    fn pixel_index(&self, x: u32, y: u32) -> usize {
        (y * self.width + x) as usize
    }

    /// Clear the entire canvas to a color
    pub fn clear(&mut self, color: Color) {
        self.pixels.fill(color.to_argb());
    }

    /// Set a single pixel
    #[inline]
    pub fn set_pixel(&mut self, x: i32, y: i32, color: Color) {
        if self.is_visible(x, y) {
            let idx = self.pixel_index(x as u32, y as u32);
            if color.is_opaque() {
                self.pixels[idx] = color.to_argb();
            } else if !color.is_transparent() {
                let dst = Color::from(self.pixels[idx]);
                self.pixels[idx] = color.blend_over(dst).to_argb();
            }
        }
    }

    /// Get a single pixel
    #[inline]
    pub fn get_pixel(&self, x: i32, y: i32) -> Color {
        if x >= 0 && y >= 0 && x < self.width as i32 && y < self.height as i32 {
            let idx = self.pixel_index(x as u32, y as u32);
            Color::from(self.pixels[idx])
        } else {
            Color::TRANSPARENT
        }
    }

    /// Set a pixel without bounds checking (unsafe but fast)
    ///
    /// # Safety
    /// Caller must ensure x < width and y < height
    #[inline]
    pub unsafe fn set_pixel_unchecked(&mut self, x: u32, y: u32, color: u32) {
        let idx = self.pixel_index(x, y);
        *self.pixels.get_unchecked_mut(idx) = color;
    }

    /// Fill a rectangle with a solid color
    pub fn fill_rect(&mut self, x: i32, y: i32, width: u32, height: u32, color: Color) {
        // Calculate visible bounds
        let x0 = x.max(0) as u32;
        let y0 = y.max(0) as u32;
        let x1 = ((x + width as i32) as u32).min(self.width);
        let y1 = ((y + height as i32) as u32).min(self.height);

        if x0 >= x1 || y0 >= y1 {
            return;
        }

        let argb = color.to_argb();

        if color.is_opaque() {
            // Fast path for opaque colors
            for py in y0..y1 {
                let row_start = self.pixel_index(x0, py);
                let row_end = self.pixel_index(x1, py);
                self.pixels[row_start..row_end].fill(argb);
            }
        } else if !color.is_transparent() {
            // Alpha blending path
            for py in y0..y1 {
                for px in x0..x1 {
                    let idx = self.pixel_index(px, py);
                    let dst = Color::from(self.pixels[idx]);
                    self.pixels[idx] = color.blend_over(dst).to_argb();
                }
            }
        }
    }

    /// Draw a rectangle outline
    pub fn draw_rect(&mut self, x: i32, y: i32, width: u32, height: u32, color: Color) {
        let w = width as i32;
        let h = height as i32;

        // Top edge
        self.draw_hline(x, y, width, color);
        // Bottom edge
        self.draw_hline(x, y + h - 1, width, color);
        // Left edge
        self.draw_vline(x, y, height, color);
        // Right edge
        self.draw_vline(x + w - 1, y, height, color);
    }

    /// Draw a horizontal line
    pub fn draw_hline(&mut self, x: i32, y: i32, length: u32, color: Color) {
        if y < 0 || y >= self.height as i32 {
            return;
        }

        let x0 = x.max(0) as u32;
        let x1 = ((x + length as i32) as u32).min(self.width);

        if x0 >= x1 {
            return;
        }

        let argb = color.to_argb();
        let row_start = self.pixel_index(x0, y as u32);
        let row_end = self.pixel_index(x1, y as u32);

        if color.is_opaque() {
            self.pixels[row_start..row_end].fill(argb);
        } else if !color.is_transparent() {
            for idx in row_start..row_end {
                let dst = Color::from(self.pixels[idx]);
                self.pixels[idx] = color.blend_over(dst).to_argb();
            }
        }
    }

    /// Draw a vertical line
    pub fn draw_vline(&mut self, x: i32, y: i32, length: u32, color: Color) {
        if x < 0 || x >= self.width as i32 {
            return;
        }

        let y0 = y.max(0) as u32;
        let y1 = ((y + length as i32) as u32).min(self.height);

        if y0 >= y1 {
            return;
        }

        let argb = color.to_argb();
        let px = x as u32;

        if color.is_opaque() {
            for py in y0..y1 {
                let idx = self.pixel_index(px, py);
                self.pixels[idx] = argb;
            }
        } else if !color.is_transparent() {
            for py in y0..y1 {
                let idx = self.pixel_index(px, py);
                let dst = Color::from(self.pixels[idx]);
                self.pixels[idx] = color.blend_over(dst).to_argb();
            }
        }
    }

    /// Draw a line using Bresenham's algorithm
    pub fn draw_line(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, color: Color) {
        let dx = (x1 - x0).abs();
        let dy = -(y1 - y0).abs();
        let sx = if x0 < x1 { 1 } else { -1 };
        let sy = if y0 < y1 { 1 } else { -1 };
        let mut err = dx + dy;

        let mut x = x0;
        let mut y = y0;

        loop {
            self.set_pixel(x, y, color);

            if x == x1 && y == y1 {
                break;
            }

            let e2 = 2 * err;
            if e2 >= dy {
                if x == x1 {
                    break;
                }
                err += dy;
                x += sx;
            }
            if e2 <= dx {
                if y == y1 {
                    break;
                }
                err += dx;
                y += sy;
            }
        }
    }

    /// Fill a circle using midpoint algorithm
    pub fn fill_circle(&mut self, cx: i32, cy: i32, radius: u32, color: Color) {
        let r = radius as i32;
        let mut x = r;
        let mut y = 0;
        let mut err = 1 - r;

        while x >= y {
            // Fill horizontal spans for each octant
            self.draw_hline(cx - x, cy + y, (2 * x + 1) as u32, color);
            self.draw_hline(cx - x, cy - y, (2 * x + 1) as u32, color);
            self.draw_hline(cx - y, cy + x, (2 * y + 1) as u32, color);
            self.draw_hline(cx - y, cy - x, (2 * y + 1) as u32, color);

            y += 1;
            if err < 0 {
                err += 2 * y + 1;
            } else {
                x -= 1;
                err += 2 * (y - x + 1);
            }
        }
    }

    /// Draw a circle outline
    pub fn draw_circle(&mut self, cx: i32, cy: i32, radius: u32, color: Color) {
        let r = radius as i32;
        let mut x = r;
        let mut y = 0;
        let mut err = 1 - r;

        while x >= y {
            self.set_pixel(cx + x, cy + y, color);
            self.set_pixel(cx - x, cy + y, color);
            self.set_pixel(cx + x, cy - y, color);
            self.set_pixel(cx - x, cy - y, color);
            self.set_pixel(cx + y, cy + x, color);
            self.set_pixel(cx - y, cy + x, color);
            self.set_pixel(cx + y, cy - x, color);
            self.set_pixel(cx - y, cy - x, color);

            y += 1;
            if err < 0 {
                err += 2 * y + 1;
            } else {
                x -= 1;
                err += 2 * (y - x + 1);
            }
        }
    }

    /// Blit another canvas onto this one
    pub fn blit(&mut self, src: &Canvas, dst_x: i32, dst_y: i32) {
        self.blit_region(src, 0, 0, src.width, src.height, dst_x, dst_y);
    }

    /// Blit a region of another canvas onto this one
    pub fn blit_region(
        &mut self,
        src: &Canvas,
        src_x: u32,
        src_y: u32,
        src_width: u32,
        src_height: u32,
        dst_x: i32,
        dst_y: i32,
    ) {
        // Calculate visible bounds
        let x0 = dst_x.max(0);
        let y0 = dst_y.max(0);
        let x1 = (dst_x + src_width as i32).min(self.width as i32);
        let y1 = (dst_y + src_height as i32).min(self.height as i32);

        if x0 >= x1 || y0 >= y1 {
            return;
        }

        // Source offset adjustment for clipping
        let src_off_x = if dst_x < 0 { (-dst_x) as u32 } else { 0 };
        let src_off_y = if dst_y < 0 { (-dst_y) as u32 } else { 0 };

        for dy in 0..(y1 - y0) as u32 {
            let src_row = src_y + src_off_y + dy;
            let dst_row = y0 as u32 + dy;

            if src_row >= src.height || dst_row >= self.height {
                continue;
            }

            for dx in 0..(x1 - x0) as u32 {
                let src_col = src_x + src_off_x + dx;
                let dst_col = x0 as u32 + dx;

                if src_col >= src.width || dst_col >= self.width {
                    continue;
                }

                let src_idx = (src_row * src.width + src_col) as usize;
                let dst_idx = (dst_row * self.width + dst_col) as usize;

                let src_color = Color::from(src.pixels[src_idx]);

                if src_color.is_opaque() {
                    self.pixels[dst_idx] = src_color.to_argb();
                } else if !src_color.is_transparent() {
                    let dst_color = Color::from(self.pixels[dst_idx]);
                    self.pixels[dst_idx] = src_color.blend_over(dst_color).to_argb();
                }
            }
        }
    }

    /// Blit raw pixel data onto this canvas
    pub fn blit_raw(
        &mut self,
        src_pixels: &[u32],
        src_width: u32,
        src_height: u32,
        dst_x: i32,
        dst_y: i32,
    ) {
        let x0 = dst_x.max(0);
        let y0 = dst_y.max(0);
        let x1 = (dst_x + src_width as i32).min(self.width as i32);
        let y1 = (dst_y + src_height as i32).min(self.height as i32);

        if x0 >= x1 || y0 >= y1 {
            return;
        }

        let src_off_x = if dst_x < 0 { (-dst_x) as u32 } else { 0 };
        let src_off_y = if dst_y < 0 { (-dst_y) as u32 } else { 0 };

        for dy in 0..(y1 - y0) as u32 {
            let src_row = src_off_y + dy;
            let dst_row = y0 as u32 + dy;

            for dx in 0..(x1 - x0) as u32 {
                let src_col = src_off_x + dx;
                let dst_col = x0 as u32 + dx;

                let src_idx = (src_row * src_width + src_col) as usize;
                let dst_idx = (dst_row * self.width + dst_col) as usize;

                if src_idx < src_pixels.len() {
                    let src_color = Color::from(src_pixels[src_idx]);
                    if src_color.is_opaque() {
                        self.pixels[dst_idx] = src_color.to_argb();
                    } else if !src_color.is_transparent() {
                        let dst_color = Color::from(self.pixels[dst_idx]);
                        self.pixels[dst_idx] = src_color.blend_over(dst_color).to_argb();
                    }
                }
            }
        }
    }

    /// Copy the canvas to a Bark framebuffer
    pub fn flush_to_framebuffer(&self, fb: &mut bark::Framebuffer) {
        fb.copy_buffer(&self.pixels);
        fb.flush();
    }
}

impl Default for Canvas {
    fn default() -> Self {
        Self::default_resolution()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_canvas_creation() {
        let canvas = Canvas::new(100, 100);
        assert_eq!(canvas.width, 100);
        assert_eq!(canvas.height, 100);
        assert_eq!(canvas.len(), 10000);
    }

    #[test]
    fn test_set_get_pixel() {
        let mut canvas = Canvas::new(100, 100);
        canvas.set_pixel(50, 50, Color::RED);
        assert_eq!(canvas.get_pixel(50, 50), Color::RED);
    }

    #[test]
    fn test_clear() {
        let mut canvas = Canvas::new(10, 10);
        canvas.clear(Color::BLUE);
        assert_eq!(canvas.get_pixel(5, 5), Color::BLUE);
    }

    #[test]
    fn test_fill_rect() {
        let mut canvas = Canvas::new(100, 100);
        canvas.fill_rect(10, 10, 20, 20, Color::GREEN);
        assert_eq!(canvas.get_pixel(15, 15), Color::GREEN);
        assert_eq!(canvas.get_pixel(5, 5), Color::BLACK);
    }

    #[test]
    fn test_bounds_checking() {
        let mut canvas = Canvas::new(100, 100);
        // These should not panic
        canvas.set_pixel(-10, -10, Color::RED);
        canvas.set_pixel(200, 200, Color::RED);
        assert_eq!(canvas.get_pixel(-10, -10), Color::TRANSPARENT);
    }
}
