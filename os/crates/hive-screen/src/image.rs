//! Pictures in memory: `0xAARRGGBB` pixels, straight alpha, read from and
//! written to PNG.

use anyhow::{bail, Context as _, Result};
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Image {
    pub width: u32,
    pub height: u32,
    pub pixels: Vec<u32>,
}

impl Image {
    pub fn new(width: u32, height: u32) -> Image {
        Image {
            width,
            height,
            pixels: vec![0; (width * height) as usize],
        }
    }

    pub fn load(path: &Path) -> Result<Image> {
        let file =
            std::fs::File::open(path).with_context(|| format!("cannot open {}", path.display()))?;
        let decoder = png::Decoder::new(std::io::BufReader::new(file));
        let mut reader = decoder
            .read_info()
            .with_context(|| format!("{} is not a PNG", path.display()))?;
        let mut buf = vec![0; reader.output_buffer_size()];
        let info = reader
            .next_frame(&mut buf)
            .with_context(|| format!("cannot read {}", path.display()))?;
        let bytes = &buf[..info.buffer_size()];
        let (width, height) = (info.width, info.height);
        let mut pixels = Vec::with_capacity((width * height) as usize);
        let channels = match (info.color_type, info.bit_depth) {
            (png::ColorType::Rgba, png::BitDepth::Eight) => 4,
            (png::ColorType::Rgb, png::BitDepth::Eight) => 3,
            (png::ColorType::GrayscaleAlpha, png::BitDepth::Eight) => 2,
            (png::ColorType::Grayscale, png::BitDepth::Eight) => 1,
            (kind, depth) => bail!(
                "{} is a {:?} {:?} PNG; the screen reads 8-bit ones",
                path.display(),
                kind,
                depth
            ),
        };
        for px in bytes.chunks_exact(channels) {
            let (r, g, b, a) = match channels {
                4 => (px[0], px[1], px[2], px[3]),
                3 => (px[0], px[1], px[2], 255),
                2 => (px[0], px[0], px[0], px[1]),
                _ => (px[0], px[0], px[0], 255),
            };
            pixels.push(argb(a, r, g, b));
        }
        Ok(Image {
            width,
            height,
            pixels,
        })
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        let file = std::fs::File::create(path)
            .with_context(|| format!("cannot write {}", path.display()))?;
        let mut encoder = png::Encoder::new(std::io::BufWriter::new(file), self.width, self.height);
        encoder.set_color(png::ColorType::Rgba);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder.write_header()?;
        let mut bytes = Vec::with_capacity(self.pixels.len() * 4);
        for &p in &self.pixels {
            bytes.extend_from_slice(&[red(p), green(p), blue(p), alpha(p)]);
        }
        writer.write_image_data(&bytes)?;
        Ok(())
    }

    pub fn get(&self, x: u32, y: u32) -> u32 {
        self.pixels[(y * self.width + x) as usize]
    }

    /// How many pixels differ between two pictures of the same size, or
    /// None when the sizes differ.
    pub fn differences(&self, other: &Image) -> Option<usize> {
        (self.width == other.width && self.height == other.height).then(|| {
            self.pixels
                .iter()
                .zip(&other.pixels)
                .filter(|(a, b)| a != b)
                .count()
        })
    }
}

pub fn argb(a: u8, r: u8, g: u8, b: u8) -> u32 {
    (a as u32) << 24 | (r as u32) << 16 | (g as u32) << 8 | b as u32
}

pub fn alpha(p: u32) -> u8 {
    (p >> 24) as u8
}
pub fn red(p: u32) -> u8 {
    (p >> 16) as u8
}
pub fn green(p: u32) -> u8 {
    (p >> 8) as u8
}
pub fn blue(p: u32) -> u8 {
    p as u8
}

/// `#rrggbb` or `#rgb` (as the compiler writes them) to an opaque pixel.
pub fn parse_color(text: &str) -> Option<u32> {
    let hex = text.strip_prefix('#')?;
    let digits: Vec<u8> = hex
        .chars()
        .map(|c| c.to_digit(16).map(|d| d as u8))
        .collect::<Option<_>>()?;
    match digits.len() {
        3 => Some(argb(255, digits[0] * 17, digits[1] * 17, digits[2] * 17)),
        6 => Some(argb(
            255,
            digits[0] * 16 + digits[1],
            digits[2] * 16 + digits[3],
            digits[4] * 16 + digits[5],
        )),
        _ => None,
    }
}

/// `src` over `dst`, straight alpha, with `src`'s alpha scaled by `factor`
/// (0 to 255).
pub fn over(src: u32, dst: u32, factor: u32) -> u32 {
    let a = (alpha(src) as u32 * factor + 127) / 255;
    if a == 0 {
        return dst;
    }
    if a >= 255 {
        return src | 0xFF00_0000;
    }
    let mix = |s: u8, d: u8| ((s as u32 * a + d as u32 * (255 - a) + 127) / 255) as u8;
    let da = alpha(dst) as u32;
    let out_a = (a + da * (255 - a) / 255).min(255) as u8;
    argb(
        out_a,
        mix(red(src), red(dst)),
        mix(green(src), green(dst)),
        mix(blue(src), blue(dst)),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn colours_parse_and_blend() {
        assert_eq!(parse_color("#ffd34d"), Some(0xFFFFD34D));
        assert_eq!(parse_color("#fff"), Some(0xFFFFFFFF));
        assert_eq!(parse_color("red"), None);
        assert_eq!(over(0x80FF0000, 0xFF000000, 255), 0xFF800000);
        assert_eq!(over(0xFFFF0000, 0xFF0000FF, 0), 0xFF0000FF);
        assert_eq!(over(0xFFFF0000, 0xFF0000FF, 255), 0xFFFF0000);
    }

    #[test]
    fn a_png_round_trips() {
        let dir = tempfile::tempdir().unwrap();
        let mut im = Image::new(3, 2);
        im.pixels[0] = 0xFF123456;
        im.pixels[5] = 0x80FFFFFF;
        im.save(&dir.path().join("a.png")).unwrap();
        let back = Image::load(&dir.path().join("a.png")).unwrap();
        assert_eq!(back, im);
        assert_eq!(back.differences(&Image::new(3, 2)), Some(2));
        assert_eq!(back.differences(&Image::new(2, 2)), None);
    }
}
