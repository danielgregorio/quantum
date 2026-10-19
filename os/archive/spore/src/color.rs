//! Color representation and manipulation
//!
//! Colors are stored as 32-bit ARGB values (0xAARRGGBB) for direct
//! compatibility with framebuffer pixel format.

/// A 32-bit ARGB color (0xAARRGGBB)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct Color(pub u32);

impl Color {
    /// Transparent black
    pub const TRANSPARENT: Color = Color(0x00000000);
    /// Fully opaque black
    pub const BLACK: Color = Color(0xFF000000);
    /// Fully opaque white
    pub const WHITE: Color = Color(0xFFFFFFFF);
    /// Fully opaque red
    pub const RED: Color = Color(0xFFFF0000);
    /// Fully opaque green
    pub const GREEN: Color = Color(0xFF00FF00);
    /// Fully opaque blue
    pub const BLUE: Color = Color(0xFF0000FF);
    /// Fully opaque yellow
    pub const YELLOW: Color = Color(0xFFFFFF00);
    /// Fully opaque cyan
    pub const CYAN: Color = Color(0xFF00FFFF);
    /// Fully opaque magenta
    pub const MAGENTA: Color = Color(0xFFFF00FF);

    /// Create a color from RGB components (fully opaque)
    #[inline]
    pub const fn rgb(r: u8, g: u8, b: u8) -> Self {
        Self(0xFF000000 | ((r as u32) << 16) | ((g as u32) << 8) | (b as u32))
    }

    /// Create a color from RGBA components
    #[inline]
    pub const fn rgba(r: u8, g: u8, b: u8, a: u8) -> Self {
        Self(((a as u32) << 24) | ((r as u32) << 16) | ((g as u32) << 8) | (b as u32))
    }

    /// Create a color from a raw ARGB value
    #[inline]
    pub const fn from_argb(argb: u32) -> Self {
        Self(argb)
    }

    /// Create a color from hex string (e.g., "#FF5500" or "FF5500")
    pub fn from_hex(hex: &str) -> Option<Self> {
        let hex = hex.trim_start_matches('#');
        let value = u32::from_str_radix(hex, 16).ok()?;

        Some(match hex.len() {
            6 => Self(0xFF000000 | value), // RGB
            8 => Self(value),              // ARGB
            3 => {
                // Short form RGB (e.g., "F50" -> "FF5500")
                let r = ((value >> 8) & 0xF) as u8;
                let g = ((value >> 4) & 0xF) as u8;
                let b = (value & 0xF) as u8;
                Self::rgb(r << 4 | r, g << 4 | g, b << 4 | b)
            }
            _ => return None,
        })
    }

    /// Get the raw ARGB value
    #[inline]
    pub const fn to_argb(self) -> u32 {
        self.0
    }

    /// Get the alpha component (0-255)
    #[inline]
    pub const fn alpha(self) -> u8 {
        ((self.0 >> 24) & 0xFF) as u8
    }

    /// Get the red component (0-255)
    #[inline]
    pub const fn red(self) -> u8 {
        ((self.0 >> 16) & 0xFF) as u8
    }

    /// Get the green component (0-255)
    #[inline]
    pub const fn green(self) -> u8 {
        ((self.0 >> 8) & 0xFF) as u8
    }

    /// Get the blue component (0-255)
    #[inline]
    pub const fn blue(self) -> u8 {
        (self.0 & 0xFF) as u8
    }

    /// Create a new color with modified alpha
    #[inline]
    pub const fn with_alpha(self, alpha: u8) -> Self {
        Self((self.0 & 0x00FFFFFF) | ((alpha as u32) << 24))
    }

    /// Check if the color is fully transparent
    #[inline]
    pub const fn is_transparent(self) -> bool {
        self.alpha() == 0
    }

    /// Check if the color is fully opaque
    #[inline]
    pub const fn is_opaque(self) -> bool {
        self.alpha() == 255
    }

    /// Blend this color over another (alpha compositing)
    ///
    /// Uses standard "over" operation: result = src * alpha + dst * (1 - alpha)
    #[inline]
    pub fn blend_over(self, dst: Color) -> Color {
        let src_a = self.alpha() as u32;

        if src_a == 255 {
            return self; // Fully opaque, no blending needed
        }
        if src_a == 0 {
            return dst; // Fully transparent, keep destination
        }

        let inv_a = 255 - src_a;

        let r = ((self.red() as u32 * src_a + dst.red() as u32 * inv_a) / 255) as u8;
        let g = ((self.green() as u32 * src_a + dst.green() as u32 * inv_a) / 255) as u8;
        let b = ((self.blue() as u32 * src_a + dst.blue() as u32 * inv_a) / 255) as u8;
        let a = (src_a + (dst.alpha() as u32 * inv_a) / 255) as u8;

        Color::rgba(r, g, b, a)
    }

    /// Multiply color by another (per-component)
    #[inline]
    pub fn multiply(self, other: Color) -> Color {
        let r = ((self.red() as u32 * other.red() as u32) / 255) as u8;
        let g = ((self.green() as u32 * other.green() as u32) / 255) as u8;
        let b = ((self.blue() as u32 * other.blue() as u32) / 255) as u8;
        let a = ((self.alpha() as u32 * other.alpha() as u32) / 255) as u8;
        Color::rgba(r, g, b, a)
    }

    /// Linearly interpolate between two colors
    #[inline]
    pub fn lerp(self, other: Color, t: f32) -> Color {
        let t = t.clamp(0.0, 1.0);
        let inv_t = 1.0 - t;

        let r = (self.red() as f32 * inv_t + other.red() as f32 * t) as u8;
        let g = (self.green() as f32 * inv_t + other.green() as f32 * t) as u8;
        let b = (self.blue() as f32 * inv_t + other.blue() as f32 * t) as u8;
        let a = (self.alpha() as f32 * inv_t + other.alpha() as f32 * t) as u8;

        Color::rgba(r, g, b, a)
    }

    /// Darken the color by a factor (0.0 = black, 1.0 = unchanged)
    #[inline]
    pub fn darken(self, factor: f32) -> Color {
        let factor = factor.clamp(0.0, 1.0);
        let r = (self.red() as f32 * factor) as u8;
        let g = (self.green() as f32 * factor) as u8;
        let b = (self.blue() as f32 * factor) as u8;
        Color::rgba(r, g, b, self.alpha())
    }

    /// Lighten the color by a factor (0.0 = unchanged, 1.0 = white)
    #[inline]
    pub fn lighten(self, factor: f32) -> Color {
        let factor = factor.clamp(0.0, 1.0);
        let r = self.red() as f32;
        let g = self.green() as f32;
        let b = self.blue() as f32;

        let r = (r + (255.0 - r) * factor) as u8;
        let g = (g + (255.0 - g) * factor) as u8;
        let b = (b + (255.0 - b) * factor) as u8;

        Color::rgba(r, g, b, self.alpha())
    }

    /// Convert to grayscale
    #[inline]
    pub fn to_grayscale(self) -> Color {
        // Use standard luminance weights
        let gray = (0.299 * self.red() as f32
            + 0.587 * self.green() as f32
            + 0.114 * self.blue() as f32) as u8;
        Color::rgba(gray, gray, gray, self.alpha())
    }
}

impl From<u32> for Color {
    fn from(argb: u32) -> Self {
        Color(argb)
    }
}

impl From<Color> for u32 {
    fn from(color: Color) -> Self {
        color.0
    }
}

impl From<(u8, u8, u8)> for Color {
    fn from((r, g, b): (u8, u8, u8)) -> Self {
        Color::rgb(r, g, b)
    }
}

impl From<(u8, u8, u8, u8)> for Color {
    fn from((r, g, b, a): (u8, u8, u8, u8)) -> Self {
        Color::rgba(r, g, b, a)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_color_components() {
        let color = Color::rgba(255, 128, 64, 200);
        assert_eq!(color.red(), 255);
        assert_eq!(color.green(), 128);
        assert_eq!(color.blue(), 64);
        assert_eq!(color.alpha(), 200);
    }

    #[test]
    fn test_color_from_hex() {
        assert_eq!(Color::from_hex("#FF0000"), Some(Color::RED));
        assert_eq!(Color::from_hex("00FF00"), Some(Color::GREEN));
        assert_eq!(Color::from_hex("F00"), Some(Color::RED));
    }

    #[test]
    fn test_color_blend() {
        let src = Color::rgba(255, 0, 0, 128); // 50% red
        let dst = Color::rgb(0, 0, 255); // Blue
        let result = src.blend_over(dst);

        // Should be roughly purple
        assert!(result.red() > 100);
        assert!(result.blue() > 100);
    }

    #[test]
    fn test_color_lerp() {
        let black = Color::BLACK;
        let white = Color::WHITE;

        let mid = black.lerp(white, 0.5);
        assert!(mid.red() > 100 && mid.red() < 150);
    }
}
