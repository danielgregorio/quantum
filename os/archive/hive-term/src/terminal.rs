//! Terminal state and grid management.

use vte::{Params, Perform};

/// A single cell in the terminal grid
#[derive(Debug, Clone, Default)]
pub struct Cell {
    /// Character in this cell
    pub c: char,
    /// Foreground color index
    pub fg: u8,
    /// Background color index
    pub bg: u8,
    /// Bold attribute
    pub bold: bool,
    /// Italic attribute
    pub italic: bool,
    /// Underline attribute
    pub underline: bool,
    /// Inverse attribute
    pub inverse: bool,
}

impl Cell {
    /// Create a new empty cell
    pub fn new() -> Self {
        Self {
            c: ' ',
            fg: 7,  // Default white
            bg: 0,  // Default black
            bold: false,
            italic: false,
            underline: false,
            inverse: false,
        }
    }

    /// Create a cell with a character
    pub fn with_char(c: char) -> Self {
        Self {
            c,
            ..Self::new()
        }
    }
}

/// Terminal grid
pub struct Grid {
    /// Grid cells
    cells: Vec<Vec<Cell>>,
    /// Number of columns
    cols: usize,
    /// Number of rows
    rows: usize,
}

impl Grid {
    /// Create a new grid
    pub fn new(cols: usize, rows: usize) -> Self {
        let cells = (0..rows)
            .map(|_| (0..cols).map(|_| Cell::new()).collect())
            .collect();

        Self { cells, cols, rows }
    }

    /// Get a cell at position
    pub fn get(&self, col: usize, row: usize) -> Option<&Cell> {
        self.cells.get(row).and_then(|r| r.get(col))
    }

    /// Get a mutable cell at position
    pub fn get_mut(&mut self, col: usize, row: usize) -> Option<&mut Cell> {
        self.cells.get_mut(row).and_then(|r| r.get_mut(col))
    }

    /// Set a cell at position
    pub fn set(&mut self, col: usize, row: usize, cell: Cell) {
        if let Some(c) = self.get_mut(col, row) {
            *c = cell;
        }
    }

    /// Clear the entire grid
    pub fn clear(&mut self) {
        for row in &mut self.cells {
            for cell in row {
                *cell = Cell::new();
            }
        }
    }

    /// Clear a row
    pub fn clear_row(&mut self, row: usize) {
        if let Some(r) = self.cells.get_mut(row) {
            for cell in r {
                *cell = Cell::new();
            }
        }
    }

    /// Scroll the grid up by n lines
    pub fn scroll_up(&mut self, n: usize) {
        for _ in 0..n {
            self.cells.remove(0);
            self.cells.push((0..self.cols).map(|_| Cell::new()).collect());
        }
    }

    /// Resize the grid
    pub fn resize(&mut self, cols: usize, rows: usize) {
        // Resize rows
        while self.cells.len() < rows {
            self.cells.push((0..cols).map(|_| Cell::new()).collect());
        }
        while self.cells.len() > rows {
            self.cells.pop();
        }

        // Resize columns
        for row in &mut self.cells {
            while row.len() < cols {
                row.push(Cell::new());
            }
            while row.len() > cols {
                row.pop();
            }
        }

        self.cols = cols;
        self.rows = rows;
    }

    /// Get dimensions
    pub fn size(&self) -> (usize, usize) {
        (self.cols, self.rows)
    }
}

/// Terminal state
pub struct Terminal {
    /// Grid of cells
    grid: Grid,
    /// Cursor column position
    cursor_col: usize,
    /// Cursor row position
    cursor_row: usize,
    /// Current foreground color
    fg: u8,
    /// Current background color
    bg: u8,
    /// Bold mode
    bold: bool,
    /// Italic mode
    italic: bool,
    /// Underline mode
    underline: bool,
    /// Inverse mode
    inverse: bool,
    /// Saved cursor position
    saved_cursor: Option<(usize, usize)>,
    /// Title
    title: String,
}

impl Terminal {
    /// Create a new terminal
    pub fn new(cols: usize, rows: usize) -> Self {
        Self {
            grid: Grid::new(cols, rows),
            cursor_col: 0,
            cursor_row: 0,
            fg: 7,
            bg: 0,
            bold: false,
            italic: false,
            underline: false,
            inverse: false,
            saved_cursor: None,
            title: String::new(),
        }
    }

    /// Get the grid
    pub fn grid(&self) -> &Grid {
        &self.grid
    }

    /// Get cursor position
    pub fn cursor(&self) -> (usize, usize) {
        (self.cursor_col, self.cursor_row)
    }

    /// Get title
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Process input bytes
    pub fn process(&mut self, bytes: &[u8]) {
        let mut parser = vte::Parser::new();
        for byte in bytes {
            parser.advance(self, *byte);
        }
    }

    /// Resize the terminal
    pub fn resize(&mut self, cols: usize, rows: usize) {
        self.grid.resize(cols, rows);
        // Clamp cursor
        self.cursor_col = self.cursor_col.min(cols.saturating_sub(1));
        self.cursor_row = self.cursor_row.min(rows.saturating_sub(1));
    }

    /// Put a character at current cursor position
    fn put_char(&mut self, c: char) {
        let (cols, rows) = self.grid.size();

        // Handle newline
        if c == '\n' {
            self.cursor_row += 1;
            if self.cursor_row >= rows {
                self.grid.scroll_up(1);
                self.cursor_row = rows - 1;
            }
            return;
        }

        // Handle carriage return
        if c == '\r' {
            self.cursor_col = 0;
            return;
        }

        // Handle backspace
        if c == '\x08' {
            self.cursor_col = self.cursor_col.saturating_sub(1);
            return;
        }

        // Handle tab
        if c == '\t' {
            let next_tab = (self.cursor_col / 8 + 1) * 8;
            self.cursor_col = next_tab.min(cols - 1);
            return;
        }

        // Put character
        let cell = Cell {
            c,
            fg: self.fg,
            bg: self.bg,
            bold: self.bold,
            italic: self.italic,
            underline: self.underline,
            inverse: self.inverse,
        };
        self.grid.set(self.cursor_col, self.cursor_row, cell);

        // Advance cursor
        self.cursor_col += 1;
        if self.cursor_col >= cols {
            self.cursor_col = 0;
            self.cursor_row += 1;
            if self.cursor_row >= rows {
                self.grid.scroll_up(1);
                self.cursor_row = rows - 1;
            }
        }
    }

    /// Reset attributes
    fn reset_attrs(&mut self) {
        self.fg = 7;
        self.bg = 0;
        self.bold = false;
        self.italic = false;
        self.underline = false;
        self.inverse = false;
    }
}

impl Perform for Terminal {
    fn print(&mut self, c: char) {
        self.put_char(c);
    }

    fn execute(&mut self, byte: u8) {
        match byte {
            0x07 => {} // Bell
            0x08 => self.put_char('\x08'), // Backspace
            0x09 => self.put_char('\t'),   // Tab
            0x0a | 0x0b | 0x0c => self.put_char('\n'), // LF, VT, FF
            0x0d => self.put_char('\r'),   // CR
            _ => {}
        }
    }

    fn csi_dispatch(&mut self, params: &Params, _intermediates: &[u8], _ignore: bool, action: char) {
        let params: Vec<u16> = params.iter().map(|p| p[0]).collect();

        match action {
            // Cursor movement
            'A' => { // Up
                let n = params.first().copied().unwrap_or(1) as usize;
                self.cursor_row = self.cursor_row.saturating_sub(n);
            }
            'B' => { // Down
                let n = params.first().copied().unwrap_or(1) as usize;
                let (_, rows) = self.grid.size();
                self.cursor_row = (self.cursor_row + n).min(rows - 1);
            }
            'C' => { // Forward
                let n = params.first().copied().unwrap_or(1) as usize;
                let (cols, _) = self.grid.size();
                self.cursor_col = (self.cursor_col + n).min(cols - 1);
            }
            'D' => { // Back
                let n = params.first().copied().unwrap_or(1) as usize;
                self.cursor_col = self.cursor_col.saturating_sub(n);
            }
            'H' | 'f' => { // Cursor position
                let row = params.first().copied().unwrap_or(1) as usize;
                let col = params.get(1).copied().unwrap_or(1) as usize;
                let (cols, rows) = self.grid.size();
                self.cursor_row = (row.saturating_sub(1)).min(rows - 1);
                self.cursor_col = (col.saturating_sub(1)).min(cols - 1);
            }
            'J' => { // Erase in display
                let mode = params.first().copied().unwrap_or(0);
                match mode {
                    0 => {} // Clear from cursor to end
                    1 => {} // Clear from start to cursor
                    2 | 3 => self.grid.clear(), // Clear all
                    _ => {}
                }
            }
            'K' => { // Erase in line
                let mode = params.first().copied().unwrap_or(0);
                let (cols, _) = self.grid.size();
                match mode {
                    0 => { // Clear from cursor to end
                        for col in self.cursor_col..cols {
                            self.grid.set(col, self.cursor_row, Cell::new());
                        }
                    }
                    1 => { // Clear from start to cursor
                        for col in 0..=self.cursor_col {
                            self.grid.set(col, self.cursor_row, Cell::new());
                        }
                    }
                    2 => { // Clear entire line
                        self.grid.clear_row(self.cursor_row);
                    }
                    _ => {}
                }
            }
            'm' => { // SGR (Select Graphic Rendition)
                if params.is_empty() {
                    self.reset_attrs();
                    return;
                }
                for &param in &params {
                    match param {
                        0 => self.reset_attrs(),
                        1 => self.bold = true,
                        3 => self.italic = true,
                        4 => self.underline = true,
                        7 => self.inverse = true,
                        22 => self.bold = false,
                        23 => self.italic = false,
                        24 => self.underline = false,
                        27 => self.inverse = false,
                        30..=37 => self.fg = (param - 30) as u8,
                        39 => self.fg = 7,
                        40..=47 => self.bg = (param - 40) as u8,
                        49 => self.bg = 0,
                        90..=97 => self.fg = (param - 90 + 8) as u8,
                        100..=107 => self.bg = (param - 100 + 8) as u8,
                        _ => {}
                    }
                }
            }
            's' => { // Save cursor
                self.saved_cursor = Some((self.cursor_col, self.cursor_row));
            }
            'u' => { // Restore cursor
                if let Some((col, row)) = self.saved_cursor {
                    self.cursor_col = col;
                    self.cursor_row = row;
                }
            }
            _ => {}
        }
    }

    fn osc_dispatch(&mut self, params: &[&[u8]], _bell_terminated: bool) {
        if let Some(&[0 | 2]) = params.first().map(|p| *p) {
            if let Some(title) = params.get(1) {
                self.title = String::from_utf8_lossy(title).to_string();
            }
        }
    }

    fn hook(&mut self, _params: &Params, _intermediates: &[u8], _ignore: bool, _action: char) {}
    fn put(&mut self, _byte: u8) {}
    fn unhook(&mut self) {}
    fn esc_dispatch(&mut self, _intermediates: &[u8], _ignore: bool, _byte: u8) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cell_default() {
        let cell = Cell::new();
        assert_eq!(cell.c, ' ');
        assert_eq!(cell.fg, 7);
        assert_eq!(cell.bg, 0);
    }

    #[test]
    fn test_grid_creation() {
        let grid = Grid::new(80, 24);
        assert_eq!(grid.size(), (80, 24));
    }

    #[test]
    fn test_terminal_cursor() {
        let mut term = Terminal::new(80, 24);
        assert_eq!(term.cursor(), (0, 0));

        term.process(b"Hello");
        assert_eq!(term.cursor(), (5, 0));
    }

    #[test]
    fn test_terminal_newline() {
        let mut term = Terminal::new(80, 24);
        // LF doesn't reset column, only CR does
        // "Line1" -> col 5, "\n" -> row 1, "Line2" -> col 10
        term.process(b"Line1\nLine2");
        assert_eq!(term.cursor(), (10, 1));
    }

    #[test]
    fn test_terminal_crlf() {
        let mut term = Terminal::new(80, 24);
        // CR+LF resets column and moves to next line
        term.process(b"Line1\r\nLine2");
        assert_eq!(term.cursor(), (5, 1));
    }
}
