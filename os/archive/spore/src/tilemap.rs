//! Tilemap rendering for 2D games and UIs
//!
//! Efficient rendering of large tile-based backgrounds and levels.

use crate::canvas::Canvas;
use crate::color::Color;
use crate::sprite::SpriteSheet;

/// A single tile in a tilemap
#[derive(Debug, Clone, Copy, Default)]
pub struct Tile {
    /// Tile index in the tileset (0 = empty/transparent)
    pub id: u16,
    /// Flags for flipping and rotation
    pub flags: TileFlags,
}

impl Tile {
    /// Create a new tile
    pub const fn new(id: u16) -> Self {
        Self {
            id,
            flags: TileFlags::NONE,
        }
    }

    /// Create an empty tile
    pub const fn empty() -> Self {
        Self::new(0)
    }

    /// Create a tile with flags
    pub const fn with_flags(id: u16, flags: TileFlags) -> Self {
        Self { id, flags }
    }

    /// Check if this tile is empty
    pub const fn is_empty(&self) -> bool {
        self.id == 0
    }
}

/// Flags for tile rendering
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct TileFlags(u8);

impl TileFlags {
    pub const NONE: Self = Self(0);
    pub const FLIP_H: Self = Self(1);
    pub const FLIP_V: Self = Self(2);
    pub const FLIP_HV: Self = Self(3);

    pub fn flip_horizontal(self) -> bool {
        (self.0 & 1) != 0
    }

    pub fn flip_vertical(self) -> bool {
        (self.0 & 2) != 0
    }
}

/// A 2D tilemap
pub struct Tilemap {
    /// Map width in tiles
    pub width: u32,
    /// Map height in tiles
    pub height: u32,
    /// Tile data
    tiles: Vec<Tile>,
    /// Tile width in pixels
    pub tile_width: u32,
    /// Tile height in pixels
    pub tile_height: u32,
}

impl Tilemap {
    /// Create a new tilemap
    pub fn new(width: u32, height: u32, tile_width: u32, tile_height: u32) -> Self {
        Self {
            width,
            height,
            tiles: vec![Tile::empty(); (width * height) as usize],
            tile_width,
            tile_height,
        }
    }

    /// Get the total number of tiles
    pub fn tile_count(&self) -> usize {
        self.tiles.len()
    }

    /// Get the map size in pixels
    pub fn pixel_size(&self) -> (u32, u32) {
        (self.width * self.tile_width, self.height * self.tile_height)
    }

    /// Get a tile at the given position
    pub fn get(&self, x: u32, y: u32) -> Tile {
        if x < self.width && y < self.height {
            self.tiles[(y * self.width + x) as usize]
        } else {
            Tile::empty()
        }
    }

    /// Set a tile at the given position
    pub fn set(&mut self, x: u32, y: u32, tile: Tile) {
        if x < self.width && y < self.height {
            self.tiles[(y * self.width + x) as usize] = tile;
        }
    }

    /// Fill a rectangular region with a tile
    pub fn fill_rect(&mut self, x: u32, y: u32, w: u32, h: u32, tile: Tile) {
        for ty in y..(y + h).min(self.height) {
            for tx in x..(x + w).min(self.width) {
                self.set(tx, ty, tile);
            }
        }
    }

    /// Clear the entire tilemap
    pub fn clear(&mut self) {
        self.tiles.fill(Tile::empty());
    }

    /// Draw the tilemap to a canvas
    pub fn draw(&self, canvas: &mut Canvas, tileset: &SpriteSheet, offset_x: i32, offset_y: i32) {
        // Calculate visible tile range
        let start_tx = ((-offset_x).max(0) / self.tile_width as i32) as u32;
        let start_ty = ((-offset_y).max(0) / self.tile_height as i32) as u32;
        let end_tx = ((canvas.width as i32 - offset_x) / self.tile_width as i32 + 1) as u32;
        let end_ty = ((canvas.height as i32 - offset_y) / self.tile_height as i32 + 1) as u32;

        let end_tx = end_tx.min(self.width);
        let end_ty = end_ty.min(self.height);

        for ty in start_ty..end_ty {
            for tx in start_tx..end_tx {
                let tile = self.get(tx, ty);
                if !tile.is_empty() {
                    let px = offset_x + (tx * self.tile_width) as i32;
                    let py = offset_y + (ty * self.tile_height) as i32;

                    // TODO: Handle tile flags (flip)
                    tileset.draw(canvas, tile.id as u32 - 1, px, py);
                }
            }
        }
    }

    /// Draw the tilemap with a tint color
    pub fn draw_tinted(
        &self,
        canvas: &mut Canvas,
        tileset: &SpriteSheet,
        offset_x: i32,
        offset_y: i32,
        tint: Color,
    ) {
        let start_tx = ((-offset_x).max(0) / self.tile_width as i32) as u32;
        let start_ty = ((-offset_y).max(0) / self.tile_height as i32) as u32;
        let end_tx = ((canvas.width as i32 - offset_x) / self.tile_width as i32 + 1) as u32;
        let end_ty = ((canvas.height as i32 - offset_y) / self.tile_height as i32 + 1) as u32;

        let end_tx = end_tx.min(self.width);
        let end_ty = end_ty.min(self.height);

        for ty in start_ty..end_ty {
            for tx in start_tx..end_tx {
                let tile = self.get(tx, ty);
                if !tile.is_empty() {
                    let px = offset_x + (tx * self.tile_width) as i32;
                    let py = offset_y + (ty * self.tile_height) as i32;

                    let sprite = tileset.get_sprite(tile.id as u32 - 1);
                    sprite.draw_tinted(canvas, px, py, tint);
                }
            }
        }
    }

    /// Get tile at pixel position
    pub fn tile_at_pixel(&self, px: i32, py: i32) -> Option<(u32, u32, Tile)> {
        if px < 0 || py < 0 {
            return None;
        }

        let tx = px as u32 / self.tile_width;
        let ty = py as u32 / self.tile_height;

        if tx < self.width && ty < self.height {
            Some((tx, ty, self.get(tx, ty)))
        } else {
            None
        }
    }

    /// Convert pixel position to tile position
    pub fn pixel_to_tile(&self, px: i32, py: i32) -> (i32, i32) {
        (
            px.div_euclid(self.tile_width as i32),
            py.div_euclid(self.tile_height as i32),
        )
    }

    /// Convert tile position to pixel position (top-left of tile)
    pub fn tile_to_pixel(&self, tx: u32, ty: u32) -> (i32, i32) {
        (
            (tx * self.tile_width) as i32,
            (ty * self.tile_height) as i32,
        )
    }
}

/// Multi-layer tilemap for parallax backgrounds
pub struct LayeredTilemap {
    layers: Vec<(Tilemap, f32, f32)>, // (tilemap, scroll_factor_x, scroll_factor_y)
}

impl LayeredTilemap {
    /// Create a new layered tilemap
    pub fn new() -> Self {
        Self { layers: Vec::new() }
    }

    /// Add a layer with scroll factors (1.0 = normal, 0.5 = half speed for parallax)
    pub fn add_layer(&mut self, tilemap: Tilemap, scroll_x: f32, scroll_y: f32) {
        self.layers.push((tilemap, scroll_x, scroll_y));
    }

    /// Get number of layers
    pub fn layer_count(&self) -> usize {
        self.layers.len()
    }

    /// Get a layer
    pub fn layer(&self, index: usize) -> Option<&Tilemap> {
        self.layers.get(index).map(|(t, _, _)| t)
    }

    /// Get a mutable layer
    pub fn layer_mut(&mut self, index: usize) -> Option<&mut Tilemap> {
        self.layers.get_mut(index).map(|(t, _, _)| t)
    }

    /// Draw all layers with camera offset
    pub fn draw(&self, canvas: &mut Canvas, tileset: &SpriteSheet, camera_x: i32, camera_y: i32) {
        for (tilemap, scroll_x, scroll_y) in &self.layers {
            let offset_x = -(camera_x as f32 * scroll_x) as i32;
            let offset_y = -(camera_y as f32 * scroll_y) as i32;
            tilemap.draw(canvas, tileset, offset_x, offset_y);
        }
    }
}

impl Default for LayeredTilemap {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tilemap_creation() {
        let tilemap = Tilemap::new(10, 10, 16, 16);
        assert_eq!(tilemap.width, 10);
        assert_eq!(tilemap.height, 10);
        assert_eq!(tilemap.tile_count(), 100);
    }

    #[test]
    fn test_tilemap_get_set() {
        let mut tilemap = Tilemap::new(10, 10, 16, 16);
        tilemap.set(5, 5, Tile::new(42));
        assert_eq!(tilemap.get(5, 5).id, 42);
        assert!(tilemap.get(0, 0).is_empty());
    }

    #[test]
    fn test_tile_at_pixel() {
        let mut tilemap = Tilemap::new(10, 10, 16, 16);
        tilemap.set(1, 1, Tile::new(1));

        let result = tilemap.tile_at_pixel(20, 20);
        assert!(result.is_some());
        let (tx, ty, tile) = result.unwrap();
        assert_eq!(tx, 1);
        assert_eq!(ty, 1);
        assert_eq!(tile.id, 1);
    }
}
