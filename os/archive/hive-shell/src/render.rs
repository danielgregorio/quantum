//! Software rendering for overlay content.

use anyhow::Result;
use hive_common::messages::Suggestion;
use tiny_skia::{Color, FillRule, Paint, PathBuilder, Pixmap, Transform};

/// Software renderer for overlay content
pub struct Renderer {
    pixmap: Pixmap,
    width: u32,
    height: u32,
}

impl Renderer {
    /// Create a new renderer with given dimensions
    pub fn new(width: u32, height: u32) -> Self {
        let pixmap = Pixmap::new(width, height).expect("Failed to create pixmap");
        Self {
            pixmap,
            width,
            height,
        }
    }

    /// Render suggestions to the buffer
    pub fn render_suggestions(&mut self, suggestions: &[&Suggestion]) -> Result<()> {
        // Clear with transparent background
        self.pixmap.fill(Color::from_rgba8(0, 0, 0, 0));

        if suggestions.is_empty() {
            return Ok(());
        }

        // Calculate dimensions
        let padding = 16.0;
        let card_height = 80.0;
        let card_spacing = 8.0;
        let card_width = self.width as f32 - padding * 2.0;

        let mut y = padding;

        for suggestion in suggestions.iter().take(5) {
            // Draw card background with rounded corners
            self.draw_rounded_rect(
                padding,
                y,
                card_width,
                card_height,
                12.0,
                Color::from_rgba8(26, 26, 26, 230), // Semi-transparent dark
            );

            // Draw accent line on the left
            let accent_color = self.confidence_color(suggestion.confidence);
            self.draw_rounded_rect(
                padding,
                y,
                4.0,
                card_height,
                2.0,
                accent_color,
            );

            // Note: Text rendering would require fontdue integration
            // For now, we just draw the background cards

            y += card_height + card_spacing;
        }

        Ok(())
    }

    /// Get color based on confidence level
    fn confidence_color(&self, confidence: f32) -> Color {
        if confidence >= 0.8 {
            Color::from_rgba8(74, 222, 128, 255) // Green - success
        } else if confidence >= 0.5 {
            Color::from_rgba8(251, 191, 36, 255) // Yellow - warning
        } else {
            Color::from_rgba8(96, 165, 250, 255) // Blue - info
        }
    }

    /// Draw a rounded rectangle
    fn draw_rounded_rect(
        &mut self,
        x: f32,
        y: f32,
        width: f32,
        height: f32,
        radius: f32,
        color: Color,
    ) {
        let mut pb = PathBuilder::new();

        // Start from top-left corner (after radius)
        pb.move_to(x + radius, y);

        // Top edge
        pb.line_to(x + width - radius, y);
        // Top-right corner
        pb.quad_to(x + width, y, x + width, y + radius);

        // Right edge
        pb.line_to(x + width, y + height - radius);
        // Bottom-right corner
        pb.quad_to(x + width, y + height, x + width - radius, y + height);

        // Bottom edge
        pb.line_to(x + radius, y + height);
        // Bottom-left corner
        pb.quad_to(x, y + height, x, y + height - radius);

        // Left edge
        pb.line_to(x, y + radius);
        // Top-left corner
        pb.quad_to(x, y, x + radius, y);

        pb.close();

        if let Some(path) = pb.finish() {
            let mut paint = Paint::default();
            paint.set_color(color);
            paint.anti_alias = true;

            self.pixmap.fill_path(
                &path,
                &paint,
                FillRule::Winding,
                Transform::identity(),
                None,
            );
        }
    }

    /// Get the raw pixel buffer
    pub fn pixels(&self) -> &[u8] {
        self.pixmap.data()
    }

    /// Resize the renderer
    pub fn resize(&mut self, width: u32, height: u32) {
        if width != self.width || height != self.height {
            if let Some(new_pixmap) = Pixmap::new(width, height) {
                self.pixmap = new_pixmap;
                self.width = width;
                self.height = height;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_renderer_creation() {
        let renderer = Renderer::new(400, 300);
        assert_eq!(renderer.width, 400);
        assert_eq!(renderer.height, 300);
    }

    #[test]
    fn test_render_empty_suggestions() {
        let mut renderer = Renderer::new(400, 300);
        let result = renderer.render_suggestions(&[]);
        assert!(result.is_ok());
    }

    #[test]
    fn test_confidence_colors() {
        let renderer = Renderer::new(100, 100);

        // High confidence = green (74/255, 222/255)
        let high = renderer.confidence_color(0.9);
        assert!((high.red() - 74.0 / 255.0).abs() < 0.01);
        assert!((high.green() - 222.0 / 255.0).abs() < 0.01);

        // Medium confidence = yellow (251/255, 191/255)
        let medium = renderer.confidence_color(0.6);
        assert!((medium.red() - 251.0 / 255.0).abs() < 0.01);
        assert!((medium.green() - 191.0 / 255.0).abs() < 0.01);

        // Low confidence = blue (96/255, 165/255)
        let low = renderer.confidence_color(0.3);
        assert!((low.red() - 96.0 / 255.0).abs() < 0.01);
        assert!((low.green() - 165.0 / 255.0).abs() < 0.01);
    }
}
