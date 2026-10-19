//! Sprite handling for 2D graphics
//!
//! Sprites are rectangular images that can be drawn to a Canvas.
//! Supports transparency, scaling, and sprite sheets.

use crate::canvas::Canvas;
use crate::color::Color;

/// A 2D sprite image
#[derive(Clone)]
pub struct Sprite {
    /// Width in pixels
    pub width: u32,
    /// Height in pixels
    pub height: u32,
    /// Pixel data (ARGB format)
    pixels: Vec<u32>,
}

impl Sprite {
    /// Create a new sprite with the given dimensions
    pub fn new(width: u32, height: u32) -> Self {
        Self {
            width,
            height,
            pixels: vec![0; (width * height) as usize],
        }
    }

    /// Create a sprite from raw pixel data
    pub fn from_pixels(width: u32, height: u32, pixels: Vec<u32>) -> Self {
        assert_eq!(pixels.len(), (width * height) as usize);
        Self {
            width,
            height,
            pixels,
        }
    }

    /// Create a sprite filled with a solid color
    pub fn solid(width: u32, height: u32, color: Color) -> Self {
        Self {
            width,
            height,
            pixels: vec![color.to_argb(); (width * height) as usize],
        }
    }

    /// Get the pixel data
    pub fn pixels(&self) -> &[u32] {
        &self.pixels
    }

    /// Get mutable pixel data
    pub fn pixels_mut(&mut self) -> &mut [u32] {
        &mut self.pixels
    }

    /// Set a pixel
    pub fn set_pixel(&mut self, x: u32, y: u32, color: Color) {
        if x < self.width && y < self.height {
            let idx = (y * self.width + x) as usize;
            self.pixels[idx] = color.to_argb();
        }
    }

    /// Get a pixel
    pub fn get_pixel(&self, x: u32, y: u32) -> Color {
        if x < self.width && y < self.height {
            let idx = (y * self.width + x) as usize;
            Color::from(self.pixels[idx])
        } else {
            Color::TRANSPARENT
        }
    }

    /// Draw the sprite to a canvas
    pub fn draw(&self, canvas: &mut Canvas, x: i32, y: i32) {
        canvas.blit_raw(&self.pixels, self.width, self.height, x, y);
    }

    /// Draw the sprite with a tint color
    pub fn draw_tinted(&self, canvas: &mut Canvas, x: i32, y: i32, tint: Color) {
        let x0 = x.max(0);
        let y0 = y.max(0);
        let x1 = (x + self.width as i32).min(canvas.width as i32);
        let y1 = (y + self.height as i32).min(canvas.height as i32);

        if x0 >= x1 || y0 >= y1 {
            return;
        }

        let src_off_x = if x < 0 { (-x) as u32 } else { 0 };
        let src_off_y = if y < 0 { (-y) as u32 } else { 0 };

        for dy in 0..(y1 - y0) as u32 {
            for dx in 0..(x1 - x0) as u32 {
                let src_idx = ((src_off_y + dy) * self.width + src_off_x + dx) as usize;
                let src_color = Color::from(self.pixels[src_idx]);

                if !src_color.is_transparent() {
                    let tinted = src_color.multiply(tint);
                    canvas.set_pixel(x0 + dx as i32, y0 + dy as i32, tinted);
                }
            }
        }
    }

    /// Draw the sprite scaled
    pub fn draw_scaled(&self, canvas: &mut Canvas, x: i32, y: i32, scale_x: f32, scale_y: f32) {
        let scaled_w = (self.width as f32 * scale_x) as i32;
        let scaled_h = (self.height as f32 * scale_y) as i32;

        if scaled_w <= 0 || scaled_h <= 0 {
            return;
        }

        for dy in 0..scaled_h {
            for dx in 0..scaled_w {
                let src_x = (dx as f32 / scale_x) as u32;
                let src_y = (dy as f32 / scale_y) as u32;

                let src_x = src_x.min(self.width - 1);
                let src_y = src_y.min(self.height - 1);

                let color = self.get_pixel(src_x, src_y);
                if !color.is_transparent() {
                    canvas.set_pixel(x + dx, y + dy, color);
                }
            }
        }
    }

    /// Flip the sprite horizontally
    pub fn flip_horizontal(&mut self) {
        for y in 0..self.height {
            for x in 0..self.width / 2 {
                let left = (y * self.width + x) as usize;
                let right = (y * self.width + self.width - 1 - x) as usize;
                self.pixels.swap(left, right);
            }
        }
    }

    /// Flip the sprite vertically
    pub fn flip_vertical(&mut self) {
        for y in 0..self.height / 2 {
            let top_row = (y * self.width) as usize;
            let bottom_row = ((self.height - 1 - y) * self.width) as usize;
            for x in 0..self.width as usize {
                self.pixels.swap(top_row + x, bottom_row + x);
            }
        }
    }

    /// Create a rotated copy (90 degrees clockwise)
    pub fn rotate_90_cw(&self) -> Sprite {
        let mut rotated = Sprite::new(self.height, self.width);
        for y in 0..self.height {
            for x in 0..self.width {
                let new_x = self.height - 1 - y;
                let new_y = x;
                rotated.set_pixel(new_x, new_y, self.get_pixel(x, y));
            }
        }
        rotated
    }
}

/// A sprite sheet containing multiple sprites in a grid
pub struct SpriteSheet {
    /// The full sheet image
    sheet: Sprite,
    /// Width of each cell
    cell_width: u32,
    /// Height of each cell
    cell_height: u32,
    /// Number of columns
    columns: u32,
    /// Number of rows
    rows: u32,
}

impl SpriteSheet {
    /// Create a sprite sheet from a sprite
    pub fn new(sheet: Sprite, cell_width: u32, cell_height: u32) -> Self {
        let columns = sheet.width / cell_width;
        let rows = sheet.height / cell_height;
        Self {
            sheet,
            cell_width,
            cell_height,
            columns,
            rows,
        }
    }

    /// Get the number of sprites in the sheet
    pub fn count(&self) -> u32 {
        self.columns * self.rows
    }

    /// Get the cell dimensions
    pub fn cell_size(&self) -> (u32, u32) {
        (self.cell_width, self.cell_height)
    }

    /// Get the grid dimensions
    pub fn grid_size(&self) -> (u32, u32) {
        (self.columns, self.rows)
    }

    /// Extract a sprite at the given index
    pub fn get_sprite(&self, index: u32) -> Sprite {
        let col = index % self.columns;
        let row = index / self.columns;
        self.get_sprite_at(col, row)
    }

    /// Extract a sprite at the given grid position
    pub fn get_sprite_at(&self, col: u32, row: u32) -> Sprite {
        let src_x = col * self.cell_width;
        let src_y = row * self.cell_height;

        let mut sprite = Sprite::new(self.cell_width, self.cell_height);
        for y in 0..self.cell_height {
            for x in 0..self.cell_width {
                sprite.set_pixel(x, y, self.sheet.get_pixel(src_x + x, src_y + y));
            }
        }
        sprite
    }

    /// Draw a sprite from the sheet at the given index
    pub fn draw(&self, canvas: &mut Canvas, index: u32, x: i32, y: i32) {
        let col = index % self.columns;
        let row = index / self.columns;
        self.draw_at(canvas, col, row, x, y);
    }

    /// Draw a sprite from the sheet at the given grid position
    pub fn draw_at(&self, canvas: &mut Canvas, col: u32, row: u32, x: i32, y: i32) {
        let src_x = col * self.cell_width;
        let src_y = row * self.cell_height;

        // Calculate visible bounds
        let x0 = x.max(0);
        let y0 = y.max(0);
        let x1 = (x + self.cell_width as i32).min(canvas.width as i32);
        let y1 = (y + self.cell_height as i32).min(canvas.height as i32);

        if x0 >= x1 || y0 >= y1 {
            return;
        }

        let off_x = if x < 0 { (-x) as u32 } else { 0 };
        let off_y = if y < 0 { (-y) as u32 } else { 0 };

        for dy in 0..(y1 - y0) as u32 {
            for dx in 0..(x1 - x0) as u32 {
                let color = self.sheet.get_pixel(src_x + off_x + dx, src_y + off_y + dy);
                if !color.is_transparent() {
                    canvas.set_pixel(x0 + dx as i32, y0 + dy as i32, color);
                }
            }
        }
    }
}

/// Animation helper for sprite sheets
pub struct SpriteAnimation {
    /// Frames as indices into a sprite sheet
    frames: Vec<u32>,
    /// Frame duration in milliseconds
    frame_duration: u32,
    /// Current frame index
    current_frame: usize,
    /// Accumulated time
    elapsed: u32,
    /// Should the animation loop?
    looping: bool,
    /// Has the animation finished? (only relevant for non-looping)
    finished: bool,
}

impl SpriteAnimation {
    /// Create a new animation
    pub fn new(frames: Vec<u32>, frame_duration: u32, looping: bool) -> Self {
        Self {
            frames,
            frame_duration,
            current_frame: 0,
            elapsed: 0,
            looping,
            finished: false,
        }
    }

    /// Create a range-based animation (frames start..end)
    pub fn from_range(start: u32, end: u32, frame_duration: u32, looping: bool) -> Self {
        Self::new((start..end).collect(), frame_duration, looping)
    }

    /// Update the animation
    pub fn update(&mut self, delta_ms: u32) {
        if self.finished || self.frames.is_empty() {
            return;
        }

        self.elapsed += delta_ms;
        while self.elapsed >= self.frame_duration {
            self.elapsed -= self.frame_duration;
            self.current_frame += 1;

            if self.current_frame >= self.frames.len() {
                if self.looping {
                    self.current_frame = 0;
                } else {
                    self.current_frame = self.frames.len() - 1;
                    self.finished = true;
                }
            }
        }
    }

    /// Get the current frame index
    pub fn current_frame_index(&self) -> u32 {
        self.frames.get(self.current_frame).copied().unwrap_or(0)
    }

    /// Reset the animation
    pub fn reset(&mut self) {
        self.current_frame = 0;
        self.elapsed = 0;
        self.finished = false;
    }

    /// Check if the animation has finished (only for non-looping)
    pub fn is_finished(&self) -> bool {
        self.finished
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sprite_creation() {
        let sprite = Sprite::new(32, 32);
        assert_eq!(sprite.width, 32);
        assert_eq!(sprite.height, 32);
        assert_eq!(sprite.pixels().len(), 1024);
    }

    #[test]
    fn test_sprite_set_get_pixel() {
        let mut sprite = Sprite::new(10, 10);
        sprite.set_pixel(5, 5, Color::RED);
        assert_eq!(sprite.get_pixel(5, 5), Color::RED);
    }

    #[test]
    fn test_sprite_sheet() {
        let sheet = Sprite::solid(64, 64, Color::WHITE);
        let sprite_sheet = SpriteSheet::new(sheet, 16, 16);
        assert_eq!(sprite_sheet.count(), 16);
        assert_eq!(sprite_sheet.grid_size(), (4, 4));
    }

    #[test]
    fn test_animation() {
        let mut anim = SpriteAnimation::from_range(0, 4, 100, true);
        assert_eq!(anim.current_frame_index(), 0);

        anim.update(100);
        assert_eq!(anim.current_frame_index(), 1);

        anim.update(300);
        assert_eq!(anim.current_frame_index(), 0); // Wrapped around
    }
}
