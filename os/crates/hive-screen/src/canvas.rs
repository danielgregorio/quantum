//! The picture of a tick: the scene's pixels, drawn in order, that a
//! display scales up or a test saves.

use crate::image::{alpha, argb, blue, green, over, red, Image};

pub struct Canvas {
    pub image: Image,
}

/// The screen's font: a sheet of cells, one per printable ASCII character
/// (cells 0-94) and one per Latin-1 character (95-190), white on
/// transparent, as quantum/runtime/screen/font.py draws it.
pub struct Font {
    pub image: Image,
    pub cell: (u32, u32),
    columns: u32,
}

impl Font {
    pub fn new(image: Image, cell: (u32, u32)) -> Font {
        let columns = image.width / cell.0.max(1);
        Font {
            image,
            cell,
            columns,
        }
    }

    /// The cell of a character; a character the font lacks is the box
    /// (Latin-1's 0x80, which the compiler draws as one).
    fn cell_of(&self, ch: char) -> u32 {
        let cp = ch as u32;
        match cp {
            0x20..=0x7E => cp - 0x20,
            0xA0..=0xFF => 95 + cp - 0xA0,
            _ => 95 + (0xA4 - 0xA0), // the box the compiler draws for a sign it has no glyph for
        }
    }

    pub fn width_of(&self, text: &str) -> u32 {
        text.chars().count() as u32 * self.cell.0
    }

    /// How many characters fit in `width` pixels.
    pub fn fit(&self, width: u32) -> usize {
        (width / self.cell.0.max(1)) as usize
    }
}

impl Canvas {
    pub fn new(width: u32, height: u32) -> Canvas {
        Canvas {
            image: Image::new(width, height),
        }
    }

    pub fn clear(&mut self, color: u32) {
        self.image.pixels.fill(color);
    }

    pub fn fill_rect(&mut self, x: i32, y: i32, w: u32, h: u32, color: u32) {
        let (cw, ch) = (self.image.width as i32, self.image.height as i32);
        let x0 = x.max(0);
        let y0 = y.max(0);
        let x1 = (x + w as i32).min(cw);
        let y1 = (y + h as i32).min(ch);
        if x0 >= x1 || y0 >= y1 {
            return;
        }
        let factor = 255;
        for py in y0..y1 {
            let row = py as usize * self.image.width as usize;
            for px in x0..x1 {
                let i = row + px as usize;
                self.image.pixels[i] = over(color, self.image.pixels[i], factor);
            }
        }
    }

    /// One cell of a sheet at (x, y), `alpha` 0 to 1, `scale` about its
    /// centre, nearest neighbour.
    #[allow(clippy::too_many_arguments)]
    pub fn blit(
        &mut self,
        sheet: &Image,
        sx: u32,
        sy: u32,
        sw: u32,
        sh: u32,
        x: f32,
        y: f32,
        alpha_factor: f32,
        scale: f32,
    ) {
        if alpha_factor <= 0.0 || scale <= 0.0 {
            return;
        }
        let factor = (alpha_factor.clamp(0.0, 1.0) * 255.0).round() as u32;
        let dw = (sw as f32 * scale).round().max(1.0) as i32;
        let dh = (sh as f32 * scale).round().max(1.0) as i32;
        // scaled about the centre of the frame
        let dx = (x + sw as f32 / 2.0 - dw as f32 / 2.0).round() as i32;
        let dy = (y + sh as f32 / 2.0 - dh as f32 / 2.0).round() as i32;
        let (cw, ch) = (self.image.width as i32, self.image.height as i32);
        let x0 = dx.max(0);
        let y0 = dy.max(0);
        let x1 = (dx + dw).min(cw);
        let y1 = (dy + dh).min(ch);
        if x0 >= x1 || y0 >= y1 {
            return;
        }
        for py in y0..y1 {
            let v = ((py - dy) as u32 * sh / dh as u32).min(sh - 1);
            let row = py as usize * self.image.width as usize;
            for px in x0..x1 {
                let u = ((px - dx) as u32 * sw / dw as u32).min(sw - 1);
                let src = sheet.get(sx + u, sy + v);
                if alpha(src) == 0 {
                    continue;
                }
                let i = row + px as usize;
                self.image.pixels[i] = over(src, self.image.pixels[i], factor);
            }
        }
    }

    /// A line of text in the font, tinted `color`, its top left at (x, y).
    pub fn text(&mut self, font: &Font, text: &str, x: i32, y: i32, color: u32) {
        let (cw, ch) = font.cell;
        let (r, g, b) = (red(color), green(color), blue(color));
        let mut pen = x;
        for ch_ in text.chars() {
            let cell = font.cell_of(ch_);
            let sx = (cell % font.columns) * cw;
            let sy = (cell / font.columns) * ch;
            if sy + ch <= font.image.height {
                for v in 0..ch {
                    let py = y + v as i32;
                    if py < 0 || py >= self.image.height as i32 {
                        continue;
                    }
                    for u in 0..cw {
                        let px = pen + u as i32;
                        if px < 0 || px >= self.image.width as i32 {
                            continue;
                        }
                        let a = alpha(font.image.get(sx + u, sy + v));
                        if a == 0 {
                            continue;
                        }
                        let i = py as usize * self.image.width as usize + px as usize;
                        self.image.pixels[i] = over(argb(a, r, g, b), self.image.pixels[i], 255);
                    }
                }
            }
            pen += cw as i32;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn font() -> Font {
        // a 2-column, 2-row "font" of 2x2 cells: cell 0 is solid, the rest empty
        let mut im = Image::new(4, 4);
        im.pixels[0] = 0xFFFFFFFF;
        im.pixels[1] = 0xFFFFFFFF;
        im.pixels[4] = 0xFFFFFFFF;
        im.pixels[5] = 0xFFFFFFFF;
        Font::new(im, (2, 2))
    }

    #[test]
    fn rectangles_and_blits_clip_at_the_edges() {
        let mut c = Canvas::new(4, 4);
        c.clear(0xFF000000);
        c.fill_rect(-2, -2, 4, 4, 0xFFFF0000); // only (0,0)-(1,1) land
        assert_eq!(c.image.get(0, 0), 0xFFFF0000);
        assert_eq!(c.image.get(2, 2), 0xFF000000);
        c.fill_rect(3, 3, 10, 10, 0xFF00FF00);
        assert_eq!(c.image.get(3, 3), 0xFF00FF00);
        let mut sheet = Image::new(2, 2);
        sheet.pixels = vec![0xFF0000FF, 0, 0, 0xFF0000FF];
        c.blit(&sheet, 0, 0, 2, 2, 3.0, 0.0, 1.0, 1.0); // half off the right edge
        assert_eq!(c.image.get(3, 0), 0xFF0000FF);
        assert_eq!(c.image.get(3, 1), 0xFF000000); // a transparent source pixel leaves the canvas alone
    }

    #[test]
    fn a_blit_scales_about_the_centre_and_fades() {
        let mut c = Canvas::new(8, 8);
        c.clear(0xFF000000);
        let mut sheet = Image::new(2, 2);
        sheet.pixels = vec![0xFFFFFFFF; 4];
        c.blit(&sheet, 0, 0, 2, 2, 3.0, 3.0, 1.0, 2.0); // 4x4 centred on (4,4): (2,2)-(5,5)
        assert_eq!(c.image.get(2, 2), 0xFFFFFFFF);
        assert_eq!(c.image.get(5, 5), 0xFFFFFFFF);
        assert_eq!(c.image.get(1, 1), 0xFF000000);
        assert_eq!(c.image.get(6, 6), 0xFF000000);
        let mut c = Canvas::new(2, 2);
        c.clear(0xFF000000);
        c.blit(&sheet, 0, 0, 2, 2, 0.0, 0.0, 0.5, 1.0);
        assert_eq!(c.image.get(0, 0), 0xFF808080);
    }

    #[test]
    fn text_is_tinted_and_advances_a_cell_a_character() {
        let f = font();
        let mut c = Canvas::new(6, 2);
        c.clear(0xFF000000);
        c.text(&f, "  ", 0, 0, 0xFFFF0000); // two spaces: cell 0, solid in this test font
        assert_eq!(c.image.get(0, 0), 0xFFFF0000);
        assert_eq!(c.image.get(3, 1), 0xFFFF0000);
        assert_eq!(c.image.get(4, 0), 0xFF000000);
        assert_eq!(f.width_of("abc"), 6);
        assert_eq!(f.fit(5), 2);
    }
}
