//! Additional primitive drawing operations
//!
//! Extends Canvas with more drawing primitives like rounded rectangles,
//! triangles, and gradient fills.

use crate::canvas::Canvas;
use crate::color::Color;

/// Extension trait for additional primitive drawing
pub trait PrimitivesExt {
    /// Draw a rounded rectangle
    fn fill_rounded_rect(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        radius: u32,
        color: Color,
    );

    /// Draw a rounded rectangle outline
    fn draw_rounded_rect(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        radius: u32,
        color: Color,
    );

    /// Fill a triangle
    fn fill_triangle(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, x2: i32, y2: i32, color: Color);

    /// Fill a rectangle with a vertical gradient
    fn fill_gradient_v(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        color_top: Color,
        color_bottom: Color,
    );

    /// Fill a rectangle with a horizontal gradient
    fn fill_gradient_h(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        color_left: Color,
        color_right: Color,
    );
}

impl PrimitivesExt for Canvas {
    fn fill_rounded_rect(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        radius: u32,
        color: Color,
    ) {
        let r = radius.min(width / 2).min(height / 2) as i32;
        let w = width as i32;
        let h = height as i32;

        // Center rectangle
        self.fill_rect(x + r, y, width - 2 * radius, height, color);
        // Left rectangle
        self.fill_rect(x, y + r, radius, height - 2 * radius, color);
        // Right rectangle
        self.fill_rect(x + w - r, y + r, radius, height - 2 * radius, color);

        // Four corners
        fill_quarter_circle(self, x + r, y + r, r, 2, color); // Top-left
        fill_quarter_circle(self, x + w - r - 1, y + r, r, 1, color); // Top-right
        fill_quarter_circle(self, x + r, y + h - r - 1, r, 3, color); // Bottom-left
        fill_quarter_circle(self, x + w - r - 1, y + h - r - 1, r, 0, color); // Bottom-right
    }

    fn draw_rounded_rect(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        radius: u32,
        color: Color,
    ) {
        let r = radius.min(width / 2).min(height / 2) as i32;
        let w = width as i32;
        let h = height as i32;

        // Top edge
        self.draw_hline(x + r, y, width - 2 * radius, color);
        // Bottom edge
        self.draw_hline(x + r, y + h - 1, width - 2 * radius, color);
        // Left edge
        self.draw_vline(x, y + r, height - 2 * radius, color);
        // Right edge
        self.draw_vline(x + w - 1, y + r, height - 2 * radius, color);

        // Four corner arcs
        draw_quarter_circle(self, x + r, y + r, r, 2, color);
        draw_quarter_circle(self, x + w - r - 1, y + r, r, 1, color);
        draw_quarter_circle(self, x + r, y + h - r - 1, r, 3, color);
        draw_quarter_circle(self, x + w - r - 1, y + h - r - 1, r, 0, color);
    }

    fn fill_triangle(
        &mut self,
        x0: i32,
        y0: i32,
        x1: i32,
        y1: i32,
        x2: i32,
        y2: i32,
        color: Color,
    ) {
        // Sort vertices by y-coordinate
        let (mut v0, mut v1, mut v2) = ((x0, y0), (x1, y1), (x2, y2));
        if v0.1 > v1.1 {
            std::mem::swap(&mut v0, &mut v1);
        }
        if v0.1 > v2.1 {
            std::mem::swap(&mut v0, &mut v2);
        }
        if v1.1 > v2.1 {
            std::mem::swap(&mut v1, &mut v2);
        }

        // Flat bottom triangle
        if v1.1 == v2.1 {
            fill_flat_bottom_triangle(self, v0, v1, v2, color);
        }
        // Flat top triangle
        else if v0.1 == v1.1 {
            fill_flat_top_triangle(self, v0, v1, v2, color);
        }
        // Split into flat bottom + flat top
        else {
            let alpha = (v1.1 - v0.1) as f32 / (v2.1 - v0.1) as f32;
            let v3 = ((v0.0 as f32 + alpha * (v2.0 - v0.0) as f32) as i32, v1.1);
            fill_flat_bottom_triangle(self, v0, v1, v3, color);
            fill_flat_top_triangle(self, v1, v3, v2, color);
        }
    }

    fn fill_gradient_v(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        color_top: Color,
        color_bottom: Color,
    ) {
        for row in 0..height as i32 {
            let t = row as f32 / (height - 1).max(1) as f32;
            let color = color_top.lerp(color_bottom, t);
            self.draw_hline(x, y + row, width, color);
        }
    }

    fn fill_gradient_h(
        &mut self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        color_left: Color,
        color_right: Color,
    ) {
        for col in 0..width as i32 {
            let t = col as f32 / (width - 1).max(1) as f32;
            let color = color_left.lerp(color_right, t);
            self.draw_vline(x + col, y, height, color);
        }
    }
}

/// Fill a quarter circle (for rounded corners)
fn fill_quarter_circle(canvas: &mut Canvas, cx: i32, cy: i32, r: i32, quadrant: u8, color: Color) {
    let mut x = r;
    let mut y = 0;
    let mut err = 1 - r;

    while x >= y {
        match quadrant {
            0 => {
                // Bottom-right
                canvas.draw_hline(cx, cy + y, (x + 1) as u32, color);
                canvas.draw_hline(cx, cy + x, (y + 1) as u32, color);
            }
            1 => {
                // Top-right
                canvas.draw_hline(cx, cy - y, (x + 1) as u32, color);
                canvas.draw_hline(cx, cy - x, (y + 1) as u32, color);
            }
            2 => {
                // Top-left
                canvas.draw_hline(cx - x, cy - y, (x + 1) as u32, color);
                canvas.draw_hline(cx - y, cy - x, (y + 1) as u32, color);
            }
            3 => {
                // Bottom-left
                canvas.draw_hline(cx - x, cy + y, (x + 1) as u32, color);
                canvas.draw_hline(cx - y, cy + x, (y + 1) as u32, color);
            }
            _ => {}
        }

        y += 1;
        if err < 0 {
            err += 2 * y + 1;
        } else {
            x -= 1;
            err += 2 * (y - x + 1);
        }
    }
}

/// Draw a quarter circle arc (for rounded rectangle outlines)
fn draw_quarter_circle(canvas: &mut Canvas, cx: i32, cy: i32, r: i32, quadrant: u8, color: Color) {
    let mut x = r;
    let mut y = 0;
    let mut err = 1 - r;

    while x >= y {
        match quadrant {
            0 => {
                canvas.set_pixel(cx + x, cy + y, color);
                canvas.set_pixel(cx + y, cy + x, color);
            }
            1 => {
                canvas.set_pixel(cx + x, cy - y, color);
                canvas.set_pixel(cx + y, cy - x, color);
            }
            2 => {
                canvas.set_pixel(cx - x, cy - y, color);
                canvas.set_pixel(cx - y, cy - x, color);
            }
            3 => {
                canvas.set_pixel(cx - x, cy + y, color);
                canvas.set_pixel(cx - y, cy + x, color);
            }
            _ => {}
        }

        y += 1;
        if err < 0 {
            err += 2 * y + 1;
        } else {
            x -= 1;
            err += 2 * (y - x + 1);
        }
    }
}

fn fill_flat_bottom_triangle(
    canvas: &mut Canvas,
    v0: (i32, i32),
    v1: (i32, i32),
    v2: (i32, i32),
    color: Color,
) {
    let inv_slope1 = (v1.0 - v0.0) as f32 / (v1.1 - v0.1).max(1) as f32;
    let inv_slope2 = (v2.0 - v0.0) as f32 / (v2.1 - v0.1).max(1) as f32;

    let mut cur_x1 = v0.0 as f32;
    let mut cur_x2 = v0.0 as f32;

    for y in v0.1..=v1.1 {
        let x_start = cur_x1.min(cur_x2) as i32;
        let x_end = cur_x1.max(cur_x2) as i32;
        canvas.draw_hline(x_start, y, (x_end - x_start + 1).max(1) as u32, color);
        cur_x1 += inv_slope1;
        cur_x2 += inv_slope2;
    }
}

fn fill_flat_top_triangle(
    canvas: &mut Canvas,
    v0: (i32, i32),
    v1: (i32, i32),
    v2: (i32, i32),
    color: Color,
) {
    let inv_slope1 = (v2.0 - v0.0) as f32 / (v2.1 - v0.1).max(1) as f32;
    let inv_slope2 = (v2.0 - v1.0) as f32 / (v2.1 - v1.1).max(1) as f32;

    let mut cur_x1 = v2.0 as f32;
    let mut cur_x2 = v2.0 as f32;

    for y in (v0.1..=v2.1).rev() {
        let x_start = cur_x1.min(cur_x2) as i32;
        let x_end = cur_x1.max(cur_x2) as i32;
        canvas.draw_hline(x_start, y, (x_end - x_start + 1).max(1) as u32, color);
        cur_x1 -= inv_slope1;
        cur_x2 -= inv_slope2;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rounded_rect() {
        let mut canvas = Canvas::new(100, 100);
        canvas.fill_rounded_rect(10, 10, 50, 30, 5, Color::RED);
        // Check center is filled
        assert_eq!(canvas.get_pixel(35, 25), Color::RED);
    }

    #[test]
    fn test_gradient() {
        let mut canvas = Canvas::new(100, 100);
        canvas.fill_gradient_v(0, 0, 100, 100, Color::WHITE, Color::BLACK);
        // Top should be lighter than bottom
        let top = canvas.get_pixel(50, 10);
        let bottom = canvas.get_pixel(50, 90);
        assert!(top.red() > bottom.red());
    }
}
