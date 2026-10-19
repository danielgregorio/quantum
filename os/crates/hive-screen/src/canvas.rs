//! The picture of a tick: the scene's pixels, drawn in order, that a
//! display scales up or a test saves. A canvas is drawn in bands of rows,
//! each on its own thread when the machine has the cores: every band
//! draws the same nodes clipped to its rows, so the picture is the same
//! with one band or eight. At the fine level the canvas has `scale`
//! pixels to the scene's one: positions keep their fractions, particles
//! their size, and the font's pixels become blocks.

use crate::image::{alpha, argb, blue, green, over, red, Image};

pub struct Canvas {
    pub image: Image,
    /// Canvas pixels per scene pixel: 1, or 2 at the fine level.
    pub scale: u32,
}

/// Rows `y0..y0+rows` of a canvas, to draw into: the whole canvas, or one
/// of the bands drawn at once. Coordinates are the scene's.
pub struct Band<'a> {
    pixels: &'a mut [u32],
    width: u32,
    y0: u32,
    rows: u32,
    scale: u32,
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
    /// A canvas for a scene of `width` by `height`, `scale` pixels to the
    /// scene's one.
    pub fn new(width: u32, height: u32, scale: u32) -> Canvas {
        let scale = scale.max(1);
        Canvas {
            image: Image::new(width * scale, height * scale),
            scale,
        }
    }

    /// The whole canvas as one band.
    pub fn band(&mut self) -> Band<'_> {
        let (width, rows, scale) = (self.image.width, self.image.height, self.scale);
        Band {
            pixels: &mut self.image.pixels,
            width,
            y0: 0,
            rows,
            scale,
        }
    }

    /// The canvas in `n` bands of rows, as equal as they come (fewer when
    /// it has fewer rows than that).
    pub fn bands(&mut self, n: usize) -> Vec<Band<'_>> {
        let (width, height, scale) = (self.image.width, self.image.height, self.scale);
        let n = n.clamp(1, height.max(1) as usize);
        let per = (height as usize).div_ceil(n).max(1);
        let mut out = Vec::with_capacity(n);
        let mut y0 = 0u32;
        for chunk in self.image.pixels.chunks_mut(per * width.max(1) as usize) {
            let rows = (chunk.len() / width.max(1) as usize) as u32;
            out.push(Band {
                pixels: chunk,
                width,
                y0,
                rows,
                scale,
            });
            y0 += rows;
        }
        out
    }
}

impl Band<'_> {
    pub fn clear(&mut self, color: u32) {
        self.pixels.fill(color);
    }

    /// One canvas pixel, `color` over what is there.
    #[inline]
    fn put(&mut self, px: i32, py: i32, color: u32, factor: u32) {
        let row = py - self.y0 as i32;
        if px < 0 || px >= self.width as i32 || row < 0 || row >= self.rows as i32 {
            return;
        }
        let i = row as usize * self.width as usize + px as usize;
        self.pixels[i] = over(color, self.pixels[i], factor);
    }

    /// A rectangle of the scene.
    pub fn fill_rect(&mut self, x: i32, y: i32, w: u32, h: u32, color: u32) {
        let s = self.scale as i32;
        self.fill_canvas_rect(x * s, y * s, w * self.scale, h * self.scale, color);
    }

    /// A rectangle at a fractional place and size (a particle), which the
    /// fine level puts on its own pixel.
    pub fn fill_rect_f(&mut self, x: f32, y: f32, w: f32, h: f32, color: u32) {
        let s = self.scale as f32;
        let cw = (w * s).round().max(1.0) as u32;
        let ch = (h * s).round().max(1.0) as u32;
        self.fill_canvas_rect(
            (x * s).round() as i32,
            (y * s).round() as i32,
            cw,
            ch,
            color,
        );
    }

    fn fill_canvas_rect(&mut self, x: i32, y: i32, w: u32, h: u32, color: u32) {
        let x0 = x.max(0);
        let x1 = (x + w as i32).min(self.width as i32);
        let y0 = y.max(self.y0 as i32);
        let y1 = (y + h as i32).min((self.y0 + self.rows) as i32);
        if x0 >= x1 || y0 >= y1 {
            return;
        }
        for py in y0..y1 {
            let row = (py - self.y0 as i32) as usize * self.width as usize;
            for px in x0..x1 {
                let i = row + px as usize;
                self.pixels[i] = over(color, self.pixels[i], 255);
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
        let s = self.scale as f32;
        let dw = (sw as f32 * scale * s).round().max(1.0) as i32;
        let dh = (sh as f32 * scale * s).round().max(1.0) as i32;
        // scaled about the centre of the frame
        let dx = ((x + sw as f32 / 2.0) * s - dw as f32 / 2.0).round() as i32;
        let dy = ((y + sh as f32 / 2.0) * s - dh as f32 / 2.0).round() as i32;
        let x0 = dx.max(0);
        let x1 = (dx + dw).min(self.width as i32);
        let y0 = dy.max(self.y0 as i32);
        let y1 = (dy + dh).min((self.y0 + self.rows) as i32);
        if x0 >= x1 || y0 >= y1 {
            return;
        }
        for py in y0..y1 {
            let v = ((py - dy) as u32 * sh / dh as u32).min(sh - 1);
            let row = (py - self.y0 as i32) as usize * self.width as usize;
            for px in x0..x1 {
                let u = ((px - dx) as u32 * sw / dw as u32).min(sw - 1);
                let src = sheet.get(sx + u, sy + v);
                if alpha(src) == 0 {
                    continue;
                }
                let i = row + px as usize;
                self.pixels[i] = over(src, self.pixels[i], factor);
            }
        }
    }

    /// A line of text in the font, tinted `color`, its top left at (x, y).
    pub fn text(&mut self, font: &Font, text: &str, x: i32, y: i32, color: u32) {
        let (cw, ch) = font.cell;
        let (r, g, b) = (red(color), green(color), blue(color));
        let s = self.scale as i32;
        let mut pen = x;
        for ch_ in text.chars() {
            let cell = font.cell_of(ch_);
            let sx = (cell % font.columns) * cw;
            let sy = (cell / font.columns) * ch;
            if sy + ch <= font.image.height {
                for v in 0..ch {
                    for u in 0..cw {
                        let a = alpha(font.image.get(sx + u, sy + v));
                        if a == 0 {
                            continue;
                        }
                        let (px, py) = ((pen + u as i32) * s, (y + v as i32) * s);
                        // a pixel of the font is a block at the fine level
                        for k in 0..s {
                            for j in 0..s {
                                self.put(px + j, py + k, argb(a, r, g, b), 255);
                            }
                        }
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
        let mut c = Canvas::new(4, 4, 1);
        let mut sheet = Image::new(2, 2);
        sheet.pixels = vec![0xFF0000FF, 0, 0, 0xFF0000FF];
        {
            let mut b = c.band();
            b.clear(0xFF000000);
            b.fill_rect(-2, -2, 4, 4, 0xFFFF0000); // only (0,0)-(1,1) land
            b.fill_rect(3, 3, 10, 10, 0xFF00FF00);
            b.blit(&sheet, 0, 0, 2, 2, 3.0, 0.0, 1.0, 1.0); // half off the right edge
        }
        assert_eq!(c.image.get(0, 0), 0xFFFF0000);
        assert_eq!(c.image.get(2, 2), 0xFF000000);
        assert_eq!(c.image.get(3, 3), 0xFF00FF00);
        assert_eq!(c.image.get(3, 0), 0xFF0000FF);
        assert_eq!(c.image.get(3, 1), 0xFF000000); // a transparent source pixel leaves the canvas alone
    }

    #[test]
    fn a_blit_scales_about_the_centre_and_fades() {
        let mut sheet = Image::new(2, 2);
        sheet.pixels = vec![0xFFFFFFFF; 4];
        let mut c = Canvas::new(8, 8, 1);
        {
            let mut b = c.band();
            b.clear(0xFF000000);
            b.blit(&sheet, 0, 0, 2, 2, 3.0, 3.0, 1.0, 2.0); // 4x4 centred on (4,4): (2,2)-(5,5)
        }
        assert_eq!(c.image.get(2, 2), 0xFFFFFFFF);
        assert_eq!(c.image.get(5, 5), 0xFFFFFFFF);
        assert_eq!(c.image.get(1, 1), 0xFF000000);
        assert_eq!(c.image.get(6, 6), 0xFF000000);
        let mut c = Canvas::new(2, 2, 1);
        {
            let mut b = c.band();
            b.clear(0xFF000000);
            b.blit(&sheet, 0, 0, 2, 2, 0.0, 0.0, 0.5, 1.0);
        }
        assert_eq!(c.image.get(0, 0), 0xFF808080);
    }

    #[test]
    fn text_is_tinted_and_advances_a_cell_a_character() {
        let f = font();
        let mut c = Canvas::new(6, 2, 1);
        {
            let mut b = c.band();
            b.clear(0xFF000000);
            b.text(&f, "  ", 0, 0, 0xFFFF0000); // two spaces: cell 0, solid in this test font
        }
        assert_eq!(c.image.get(0, 0), 0xFFFF0000);
        assert_eq!(c.image.get(3, 1), 0xFFFF0000);
        assert_eq!(c.image.get(4, 0), 0xFF000000);
        assert_eq!(f.width_of("abc"), 6);
        assert_eq!(f.fit(5), 2);
    }

    #[test]
    fn bands_draw_the_picture_the_whole_canvas_draws() {
        let f = font();
        let mut sheet = Image::new(2, 2);
        sheet.pixels = vec![0xFF0000FF, 0, 0x80FF00FF, 0xFF0000FF];
        let draw = |b: &mut Band<'_>| {
            b.clear(0xFF101010);
            b.fill_rect(1, 2, 10, 5, 0xFFFF0000);
            b.fill_rect_f(3.4, 7.6, 2.5, 2.5, 0x80FFFFFF);
            b.blit(&sheet, 0, 0, 2, 2, 5.0, 3.0, 0.7, 3.0);
            b.blit(&sheet, 0, 0, 2, 2, 11.5, 9.25, 1.0, 1.0);
            b.text(&f, "  ", 2, 9, 0xFF00FF00);
        };
        for scale in [1, 2] {
            let mut whole = Canvas::new(16, 12, scale);
            draw(&mut whole.band());
            for n in [2, 3, 5, 12, 40] {
                let mut c = Canvas::new(16, 12, scale);
                let bands = c.bands(n);
                assert!(!bands.is_empty() && bands.len() <= n);
                for mut b in bands {
                    draw(&mut b);
                }
                assert_eq!(
                    c.image.pixels, whole.image.pixels,
                    "{} bands at x{}",
                    n, scale
                );
            }
        }
    }

    #[test]
    fn the_fine_level_has_two_pixels_to_the_scene_s_one() {
        let f = font();
        let mut c = Canvas::new(4, 4, 2);
        {
            let mut b = c.band();
            b.clear(0xFF000000);
            b.fill_rect(1, 1, 1, 1, 0xFFFF0000);
            b.fill_rect_f(0.5, 0.0, 0.5, 0.5, 0xFF00FF00);
            b.text(&f, " ", 2, 2, 0xFF0000FF);
        }
        assert_eq!((c.image.width, c.image.height), (8, 8));
        assert_eq!(c.image.get(2, 2), 0xFFFF0000);
        assert_eq!(c.image.get(3, 3), 0xFFFF0000);
        assert_eq!(c.image.get(4, 4), 0xFF0000FF, "a font pixel is a 2x2 block");
        assert_eq!(c.image.get(7, 7), 0xFF0000FF);
        assert_eq!(
            c.image.get(1, 0),
            0xFF00FF00,
            "a half-pixel particle lands on its fine pixel"
        );
        assert_eq!(c.image.get(0, 0), 0xFF000000);
        assert_eq!(c.image.get(2, 0), 0xFF000000);
    }
}
