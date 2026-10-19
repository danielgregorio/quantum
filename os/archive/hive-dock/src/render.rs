//! Dock rendering using tiny-skia.

use anyhow::Result;
use fontdue::{Font, FontSettings};
use tiny_skia::{Color, FillRule, Paint, PathBuilder, Pixmap, Rect, Transform};

use crate::apps::AppInfo;

/// Colors for the dock (dark theme matching DruidOS design)
mod colors {
    use tiny_skia::Color;

    pub fn bg_surface() -> Color {
        Color::from_rgba8(26, 26, 26, 230) // #1A1A1A with alpha
    }

    pub fn border() -> Color {
        Color::from_rgba8(51, 51, 51, 255) // #333333
    }

    pub fn icon_bg() -> Color {
        Color::from_rgba8(38, 38, 38, 255) // #262626
    }

    pub fn icon_bg_hover() -> Color {
        Color::from_rgba8(51, 51, 51, 255) // #333333
    }

    pub fn running_indicator() -> Color {
        Color::from_rgba8(123, 92, 255, 255) // Accent #7B5CFF
    }

    pub fn text_secondary() -> Color {
        Color::from_rgba8(160, 160, 160, 255) // #A0A0A0
    }
}

/// Dock renderer
pub struct DockRenderer {
    pixmap: Pixmap,
    width: u32,
    height: u32,
    icon_size: u32,
    font: Option<Font>,
}

impl DockRenderer {
    /// Create a new renderer
    pub fn new(width: u32, height: u32, icon_size: u32) -> Self {
        let pixmap = Pixmap::new(width, height)
            .expect("Failed to create pixmap");

        // Try to load system font
        let font = Self::load_font();

        Self {
            pixmap,
            width,
            height,
            icon_size,
            font,
        }
    }

    /// Load a font for text rendering
    fn load_font() -> Option<Font> {
        // Try common font paths
        let font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ];

        for path in &font_paths {
            if let Ok(font_data) = std::fs::read(path) {
                if let Ok(font) = Font::from_bytes(font_data, FontSettings::default()) {
                    return Some(font);
                }
            }
        }

        None
    }

    /// Render the dock with pinned and running apps
    pub fn render_dock(
        &mut self,
        pinned_apps: &[&AppInfo],
        running_apps: &[&AppInfo],
    ) -> Result<()> {
        // Clear to transparent
        self.pixmap.fill(Color::TRANSPARENT);

        // Draw background with rounded corners
        self.draw_background()?;

        // Draw app icons
        let padding = 12u32;
        let spacing = 8u32;
        let mut x = padding;
        let y = (self.height - self.icon_size) / 2;

        // Draw pinned apps
        for app in pinned_apps {
            let is_running = running_apps.iter().any(|r| r.id == app.id);
            self.draw_app_icon(x, y, app, is_running, false)?;
            x += self.icon_size + spacing;
        }

        // Draw separator if there are both pinned and running-only apps
        let running_only: Vec<_> = running_apps
            .iter()
            .filter(|r| !pinned_apps.iter().any(|p| p.id == r.id))
            .collect();

        if !pinned_apps.is_empty() && !running_only.is_empty() {
            // Draw vertical separator
            self.draw_separator(x, padding, self.height - 2 * padding)?;
            x += spacing;
        }

        // Draw running-only apps
        for app in running_only {
            self.draw_app_icon(x, y, app, true, false)?;
            x += self.icon_size + spacing;
        }

        Ok(())
    }

    /// Draw the dock background
    fn draw_background(&mut self) -> Result<()> {
        let rect = Rect::from_xywh(0.0, 0.0, self.width as f32, self.height as f32)
            .ok_or_else(|| anyhow::anyhow!("Invalid rect"))?;

        // Draw rounded rectangle background
        let radius = 12.0;
        let path = self.rounded_rect_path(0.0, 0.0, self.width as f32, self.height as f32, radius);

        let mut paint = Paint::default();
        paint.set_color(colors::bg_surface());
        paint.anti_alias = true;

        self.pixmap.fill_path(
            &path,
            &paint,
            FillRule::Winding,
            Transform::identity(),
            None,
        );

        // Draw border
        paint.set_color(colors::border());
        // Border would be drawn with stroke in a full implementation

        Ok(())
    }

    /// Draw an application icon
    fn draw_app_icon(
        &mut self,
        x: u32,
        y: u32,
        app: &AppInfo,
        is_running: bool,
        is_hovered: bool,
    ) -> Result<()> {
        let size = self.icon_size as f32;

        // Draw icon background
        let bg_color = if is_hovered {
            colors::icon_bg_hover()
        } else {
            colors::icon_bg()
        };

        let path = self.rounded_rect_path(x as f32, y as f32, size, size, 8.0);

        let mut paint = Paint::default();
        paint.set_color(bg_color);
        paint.anti_alias = true;

        self.pixmap.fill_path(
            &path,
            &paint,
            FillRule::Winding,
            Transform::identity(),
            None,
        );

        // Draw placeholder for icon (first letter of app name)
        if let Some(ref font) = self.font {
            let first_char = app.name.chars().next().unwrap_or('?');
            let font_size = (size * 0.5) as f32;

            let (metrics, bitmap) = font.rasterize(first_char, font_size);

            // Center the glyph
            let glyph_x = x as i32 + (size as i32 - metrics.width as i32) / 2;
            let glyph_y = y as i32 + (size as i32 - metrics.height as i32) / 2;

            // Draw glyph pixels
            for gy in 0..metrics.height {
                for gx in 0..metrics.width {
                    let alpha = bitmap[gy * metrics.width + gx];
                    if alpha > 0 {
                        let px = (glyph_x + gx as i32) as u32;
                        let py = (glyph_y + gy as i32) as u32;

                        if px < self.width && py < self.height {
                            // Simple pixel plotting (in real impl would blend properly)
                            let color = Color::from_rgba8(255, 255, 255, alpha);
                            self.plot_pixel(px, py, color);
                        }
                    }
                }
            }
        }

        // Draw running indicator dot
        if is_running {
            let indicator_size = 6.0;
            let indicator_x = x as f32 + (size - indicator_size) / 2.0;
            let indicator_y = y as f32 + size + 2.0;

            // Simple circle for running indicator
            let mut path = PathBuilder::new();
            path.push_circle(
                indicator_x + indicator_size / 2.0,
                indicator_y + indicator_size / 2.0,
                indicator_size / 2.0,
            );

            if let Some(path) = path.finish() {
                paint.set_color(colors::running_indicator());
                self.pixmap.fill_path(
                    &path,
                    &paint,
                    FillRule::Winding,
                    Transform::identity(),
                    None,
                );
            }
        }

        Ok(())
    }

    /// Draw a separator line
    fn draw_separator(&mut self, x: u32, y_start: u32, height: u32) -> Result<()> {
        let mut paint = Paint::default();
        paint.set_color(colors::border());

        // Draw vertical line
        for y in y_start..(y_start + height) {
            self.plot_pixel(x, y, colors::border());
        }

        Ok(())
    }

    /// Create a rounded rectangle path
    fn rounded_rect_path(&self, x: f32, y: f32, w: f32, h: f32, r: f32) -> tiny_skia::Path {
        let mut pb = PathBuilder::new();

        // Start at top-left after corner
        pb.move_to(x + r, y);

        // Top edge and top-right corner
        pb.line_to(x + w - r, y);
        pb.quad_to(x + w, y, x + w, y + r);

        // Right edge and bottom-right corner
        pb.line_to(x + w, y + h - r);
        pb.quad_to(x + w, y + h, x + w - r, y + h);

        // Bottom edge and bottom-left corner
        pb.line_to(x + r, y + h);
        pb.quad_to(x, y + h, x, y + h - r);

        // Left edge and top-left corner
        pb.line_to(x, y + r);
        pb.quad_to(x, y, x + r, y);

        pb.close();

        pb.finish().unwrap_or_else(|| {
            // Fallback to simple rectangle
            let mut pb = PathBuilder::new();
            pb.push_rect(Rect::from_xywh(x, y, w, h).unwrap());
            pb.finish().unwrap()
        })
    }

    /// Plot a single pixel (simple alpha blend)
    fn plot_pixel(&mut self, x: u32, y: u32, color: Color) {
        if x >= self.width || y >= self.height {
            return;
        }

        let idx = (y * self.width + x) as usize * 4;
        let pixels = self.pixmap.data_mut();

        if idx + 3 < pixels.len() {
            let alpha = color.alpha();
            if alpha > 0.0 {
                // Simple alpha blend
                let inv_alpha = 1.0 - alpha;
                pixels[idx] = ((color.red() * alpha + pixels[idx] as f32 / 255.0 * inv_alpha) * 255.0) as u8;
                pixels[idx + 1] = ((color.green() * alpha + pixels[idx + 1] as f32 / 255.0 * inv_alpha) * 255.0) as u8;
                pixels[idx + 2] = ((color.blue() * alpha + pixels[idx + 2] as f32 / 255.0 * inv_alpha) * 255.0) as u8;
                pixels[idx + 3] = 255;
            }
        }
    }

    /// Get the raw pixel data
    pub fn pixels(&self) -> &[u8] {
        self.pixmap.data()
    }

    /// Resize the renderer
    pub fn resize(&mut self, width: u32, height: u32) {
        if let Some(new_pixmap) = Pixmap::new(width, height) {
            self.pixmap = new_pixmap;
            self.width = width;
            self.height = height;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_renderer_creation() {
        let renderer = DockRenderer::new(800, 72, 48);
        assert_eq!(renderer.width, 800);
        assert_eq!(renderer.height, 72);
        assert_eq!(renderer.icon_size, 48);
    }

    #[test]
    fn test_render_empty_dock() {
        let mut renderer = DockRenderer::new(800, 72, 48);
        let result = renderer.render_dock(&[], &[]);
        assert!(result.is_ok());
    }

    #[test]
    fn test_colors() {
        let bg = colors::bg_surface();
        assert!(bg.alpha() > 0.0);

        let accent = colors::running_indicator();
        // Accent purple has more blue than green
        assert!(accent.blue() > accent.green());
    }
}
