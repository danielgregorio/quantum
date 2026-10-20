//! A page on the screen: the view tree a page's runtime sends (`quantum
//! pixel`, over the pixel socket, or a test over the play protocol), laid
//! out in cells of the font, drawn over the scene as a window (a frame
//! with a bevel, a shadow, a title bar with the Esc key, a status bar
//! with the keys that apply, as tall as its content), driven by the
//! keyboard alone, and answered with events: `click`, `submit` (with the
//! form's fields), `change` (a search field, after a pause), `navigate`,
//! `close`.
//!
//! Four rules: everything that reacts has the focus in turn, in document
//! order, and the focus shows (a honey mark); few keys, the console's own
//! (Tab and Shift+Tab between elements, the arrows inside one, Enter acts,
//! Space marks, Esc closes); the last line says the keys that apply to
//! what has the focus; Esc closes the innermost thing, and with nothing
//! open, the page.

use crate::canvas::{Band, Font};
use crate::world::Key;
use serde_json::{json, Map, Value};

/// The frame around the content, in pixels: the outer line, the bevel and
/// the padding on each side; the title bar and the status bar with their
/// lines above and below.
const SIDE: i32 = 4;
const TITLE_H: i32 = 12;
const STATUS_H: i32 = 12;
/// What the bars and lines take of the window's height: the outer lines
/// (2), the title bar and its line (13), the status bar and its line
/// (13), the padding above and below the content (2) and one more row
/// of breathing room (1).
const CHROME_H: i32 = 31;
const MIN_ROWS: usize = 4;
/// The console's `sm` breakpoint, in columns (UI-3): below it an `hbox`
/// that says `stack_below` stacks. At the scene's size the page has 53
/// columns, a phone's width; at the fine level, drawn on the canvas of two
/// pixels to the scene's one, it has 106.
const SM_COLS: usize = 80;

// The look of a window manager in pixel art: a 1-px bevel (light above and
// left, dark below and right) on what is raised, the reverse on what is
// sunken, a 3-px shadow, the scene dimmed under the window.
const BG: u32 = 0xFF12_1228;
const TITLE_BG: u32 = 0xFFFF_D34D;
const TITLE_BG2: u32 = 0xFFD9_AA2E;
const TITLE_DARK: u32 = 0xFF8A_6A10;
const LIGHT: u32 = 0xFF4A_4A7A;
const MID: u32 = 0xFF2A_2A48;
const DARK: u32 = 0xFF0B_0B16;
const BLACK: u32 = 0xFF05_050C;
const ZEBRA: u32 = 0xFF16_1630;
const OK_LIGHT: u32 = 0xFF2F_6F3F;
const OK_DARK: u32 = 0xFF10_3018;
const ERR_LIGHT: u32 = 0xFF8A_3A3A;
const ERR_DARK: u32 = 0xFF30_1010;
const SHADOW: u32 = 0x8000_0000;
const DIM: u32 = 0x7800_0000;
const INK: u32 = 0xFF1A_1A2E;
const TEXT: u32 = 0xFFFF_FFFF;
const MUTED: u32 = 0xFF8A_8AA0;
const HONEY: u32 = 0xFFFF_D34D;
const LINK: u32 = 0xFF8A_D4FF;
const FIELD_BG: u32 = 0xFF0B_0B16;
const ROW_BG: u32 = 0xFF2A_2A48;
const DANGER_BG: u32 = 0xFFB0_3030;
const OK_BG: u32 = 0xFF1F_4D2A;
const OK_TEXT: u32 = 0xFFBF_E8C8;
const ERR_BG: u32 = 0xFF5A_1F1F;
const ERR_TEXT: u32 = 0xFFFF_C0C0;
const LINE: u32 = 0xFF50_5078;

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
pub struct Rect {
    pub x: usize,
    pub y: usize,
    pub w: usize,
    pub h: usize,
}

#[derive(Default, Clone)]
struct Node {
    id: u64,
    kind: String,
    props: Map<String, Value>,
    event: Option<Value>,
    children: Vec<usize>,
    parent: Option<usize>,
    /// A table's columns, and its rows of cells (each cell a list of nodes).
    columns: Vec<Value>,
    rows: Vec<Vec<Vec<usize>>>,
    // what the keyboard changes
    value: String,
    cursor: usize,
    checked: bool,
    choice: usize,
    tab: usize,
    /// A table's active row (-1: the header) and the action in it.
    row: isize,
    col: usize,
    // laid out
    rect: Rect,
    lines: Vec<String>,
}

pub struct Window {
    pub title: String,
    pub flash: Option<(String, bool)>,
    /// Cells across and down of the content: what fits in the window on
    /// this canvas (49 by up to 13 at the scene's size; 100 by up to 29 at
    /// the fine level). The window is as tall as its content, up to the
    /// canvas.
    pub cols: usize,
    pub rows: usize,
    /// The canvas it is drawn on, in pixels.
    canvas: (u32, u32),
    /// The window's frame on the canvas, in pixels.
    pub frame: Rect,
    /// Where the content's cell (0, 0) is drawn, in pixels.
    ox: i32,
    oy: i32,
    nodes: Vec<Node>,
    focusables: Vec<usize>,
    focus: usize,
    scroll: usize,
    content_height: usize,
    events: Vec<Value>,
    /// A search field typed into: the change event is due at this tick.
    search_due: Option<(u64, usize)>,
    /// Laying out the cells of a table: what reacts in them is reached
    /// through the table (its row and column), not by Tab.
    in_table: bool,
    /// How many pages were shown: a test waits for the next.
    pub shown: u64,
}

fn text_of(v: Option<&Value>) -> String {
    match v {
        Some(Value::String(s)) => s.clone(),
        Some(Value::Null) | None => String::new(),
        Some(other) => other.to_string(),
    }
}

fn truthy(v: Option<&Value>) -> bool {
    match v {
        Some(Value::Bool(b)) => *b,
        Some(Value::String(s)) => matches!(
            s.trim().to_ascii_lowercase().as_str(),
            "true" | "1" | "on" | "yes" | "checked"
        ),
        Some(Value::Number(n)) => n.as_f64().unwrap_or(0.0) != 0.0,
        _ => false,
    }
}

/// Words wrapped into lines of at most `width` characters.
fn wrap(text: &str, width: usize) -> Vec<String> {
    let width = width.max(1);
    let mut lines = Vec::new();
    for paragraph in text.split('\n') {
        let mut line = String::new();
        for word in paragraph.split_whitespace() {
            let w = word.chars().count();
            let l = line.chars().count();
            if l > 0 && l + 1 + w > width {
                lines.push(std::mem::take(&mut line));
            }
            if w > width {
                // a word longer than the line is cut
                let mut chunk = String::new();
                for ch in word.chars() {
                    if chunk.chars().count() == width {
                        lines.push(std::mem::take(&mut chunk));
                    }
                    chunk.push(ch);
                }
                line = chunk;
                continue;
            }
            if !line.is_empty() {
                line.push(' ');
            }
            line.push_str(word);
        }
        lines.push(line);
    }
    if lines.is_empty() {
        lines.push(String::new());
    }
    lines
}

fn cut(text: &str, width: usize) -> String {
    text.chars().take(width).collect()
}

impl Window {
    /// A page as `quantum pixel` sends it (its title, flash and view
    /// tree), laid out for a canvas of `width` by `height` pixels.
    pub fn new(page: &Value, width: u32, height: u32) -> Window {
        let mut w = Window {
            title: text_of(page.get("title")),
            cols: 12,
            rows: MIN_ROWS,
            canvas: (width.max(120), height.max(80)),
            frame: Rect::default(),
            ox: 0,
            oy: 0,
            flash: page
                .get("flash")
                .and_then(Value::as_str)
                .filter(|s| !s.is_empty())
                .map(|s| {
                    (
                        s.to_string(),
                        page.get("flashType").and_then(Value::as_str) == Some("error"),
                    )
                }),
            nodes: Vec::new(),
            focusables: Vec::new(),
            focus: 0,
            scroll: 0,
            content_height: 0,
            events: Vec::new(),
            search_due: None,
            in_table: false,
            shown: 1,
        };
        let root = Value::Object(Map::new());
        w.add(&root, None);
        w.nodes[0].kind = "page".into();
        let view = page
            .get("view")
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default();
        for v in &view {
            let n = w.add(v, Some(0));
            w.nodes[0].children.push(n);
        }
        w.layout();
        w.focus_first();
        w
    }

    fn add(&mut self, v: &Value, parent: Option<usize>) -> usize {
        let n = self.nodes.len();
        let props = v
            .get("props")
            .and_then(Value::as_object)
            .cloned()
            .unwrap_or_default();
        let kind = text_of(v.get("type"));
        let mut node = Node {
            id: v.get("id").and_then(Value::as_u64).unwrap_or(0),
            kind: kind.clone(),
            event: v.get("event").cloned().filter(|e| !e.is_null()),
            parent,
            columns: v
                .get("columns")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default(),
            ..Node::default()
        };
        node.value = text_of(props.get("value"));
        node.cursor = node.value.chars().count();
        node.checked = truthy(props.get("checked"));
        node.props = props;
        self.nodes.push(node);
        for child in v
            .get("children")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            let c = self.add(child, Some(n));
            self.nodes[n].children.push(c);
        }
        let mut rows = Vec::new();
        for row in v
            .get("rows")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            let mut cells = Vec::new();
            for cell in row.as_array().into_iter().flatten() {
                let mut nodes = Vec::new();
                for item in cell.as_array().into_iter().flatten() {
                    nodes.push(self.add(item, Some(n)));
                }
                cells.push(nodes);
            }
            rows.push(cells);
        }
        self.nodes[n].rows = rows;
        if matches!(kind.as_str(), "radio" | "select") {
            let chosen = self.nodes[n].value.clone();
            let options = self.options(n);
            self.nodes[n].choice = options.iter().position(|(_, v)| *v == chosen).unwrap_or(0);
        }
        if kind == "table" && self.nodes[n].rows.is_empty() {
            self.nodes[n].row = -1;
        }
        n
    }

    /// A radio's or a select's options: (label, value).
    fn options(&self, n: usize) -> Vec<(String, String)> {
        let node = &self.nodes[n];
        let mut out: Vec<(String, String)> = text_of(node.props.get("options"))
            .split(',')
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(|s| (s.to_string(), s.to_string()))
            .collect();
        for &c in &node.children {
            let child = &self.nodes[c];
            if child.kind == "option" {
                let value = text_of(child.props.get("value"));
                let label = text_of(child.props.get("label"));
                out.push((
                    if label.is_empty() {
                        value.clone()
                    } else {
                        label
                    },
                    value,
                ));
            }
        }
        out
    }

    // ---------------------------------------------------------------- layout

    /// The canvas changed size (the level changed): the page flows again
    /// into the new cells, the focus stays where it was.
    pub fn resize(&mut self, width: u32, height: u32) {
        self.canvas = (width.max(120), height.max(80));
        self.layout();
        self.reveal();
    }

    /// The margin around the window: 8 px at the scene's size, scaled
    /// with the canvas.
    fn margin(&self) -> i32 {
        (self.canvas.0 as i32 / 40).max(4)
    }

    /// The content flows into the columns the canvas gives; then the
    /// window takes the height the content needs, up to the canvas, and
    /// sits in the middle.
    fn layout(&mut self) {
        let (cw, ch) = (6usize, 10usize);
        let margin = self.margin() as usize;
        let width = (self.canvas.0 as usize).saturating_sub(2 * margin);
        self.cols = (width.saturating_sub(2 * SIDE as usize) / cw).max(12);
        self.focusables.clear();
        let h = self.place(0, 0, 0, self.cols);
        self.content_height = h;
        let max_rows = ((self.canvas.1 as usize).saturating_sub(2 * margin + CHROME_H as usize)
            / ch)
            .max(MIN_ROWS);
        self.rows = (h + self.content_top()).clamp(MIN_ROWS, max_rows);
        let height = self.rows * ch + CHROME_H as usize;
        let y = (self.canvas.1 as usize).saturating_sub(height) / 2;
        self.frame = Rect {
            x: margin,
            y,
            w: width,
            h: height,
        };
        self.ox = (margin + SIDE as usize) as i32;
        self.oy = y as i32 + 1 + TITLE_H + 1 + 1;
        let rows = self.content_rows();
        if self.scroll + rows > h.max(rows) {
            self.scroll = h.max(rows) - rows;
        }
    }

    /// The first row of the content: under the flash when there is one.
    fn content_top(&self) -> usize {
        usize::from(self.flash.is_some())
    }

    /// The rows of content the window shows at once.
    fn content_rows(&self) -> usize {
        self.rows.saturating_sub(self.content_top()).max(1)
    }

    fn is_focusable(kind: &str, props: &Map<String, Value>) -> bool {
        match kind {
            "input" => text_of(props.get("input_type")) != "file",
            "checkbox" | "switch" | "radio" | "select" | "button" | "link" | "table"
            | "tabpanel" => true,
            _ => false,
        }
    }

    fn gap_rows(props: &Map<String, Value>) -> usize {
        match text_of(props.get("gap")).as_str() {
            "md" | "lg" | "xl" => 1,
            _ => 0,
        }
    }

    /// The width an element takes beside others, at most `w`.
    fn natural_width(&self, n: usize, w: usize) -> usize {
        let node = &self.nodes[n];
        let p = &node.props;
        let text = text_of(p.get("text"));
        let width = match node.kind.as_str() {
            "text" | "footer" | "stream" => text.chars().count(),
            "badge" => text.chars().count() + 2,
            "link" => text.chars().count().max(1),
            "button" => text.chars().count() + 4,
            "input" => {
                let px = text_of(p.get("width")).parse::<usize>().unwrap_or(0) / 6;
                if px > 0 {
                    px.max(6)
                } else {
                    24
                }
            }
            "checkbox" | "switch" => 4 + text_of(p.get("label")).chars().count(),
            "select" => {
                4 + self
                    .options(n)
                    .iter()
                    .map(|(l, _)| l.chars().count())
                    .max()
                    .unwrap_or(0)
            }
            "radio" => self
                .options(n)
                .iter()
                .map(|(l, _)| l.chars().count() + 5)
                .sum::<usize>()
                .max(1),
            "spacer" => 1,
            "image" => text_of(p.get("alt")).chars().count() + 2,
            _ => w,
        };
        width.min(w).max(1)
    }

    /// Lays `n` out at (x, y) in `w` cells; its height in rows.
    fn place(&mut self, n: usize, x: usize, y: usize, w: usize) -> usize {
        let kind = self.nodes[n].kind.clone();
        let props = self.nodes[n].props.clone();
        let children = self.nodes[n].children.clone();
        if !self.in_table && Self::is_focusable(&kind, &props) {
            self.focusables.push(n);
        }
        let h = match kind.as_str() {
            "page" => self.stack(&children, x + 1, y, w.saturating_sub(2), 0),
            "window" | "vbox" | "scrollbox" | "form" | "cardbody" | "cardfooter" | "tab"
            | "list" | "item" => self.stack(&children, x, y, w, Self::gap_rows(&props)),
            "section" | "header" | "cardheader" | "formitem" => {
                let title = text_of(
                    props
                        .get("title")
                        .or(props.get("label"))
                        .or(props.get("text")),
                );
                let has = !title.trim().is_empty();
                self.nodes[n].lines = vec![cut(&title, w)];
                let below = self.stack(&children, x, y + usize::from(has), w, 0);
                usize::from(has) + below
            }
            "panel" | "card" => {
                let inner = self.stack(&children, x + 1, y + 1, w.saturating_sub(2), 0);
                self.nodes[n].lines = vec![cut(&text_of(props.get("title")), w.saturating_sub(4))];
                inner + 2
            }
            "hbox" => {
                let stack = text_of(props.get("stack_below"));
                if !stack.is_empty() && self.cols < SM_COLS {
                    self.stack(&children, x, y, w, Self::gap_rows(&props))
                } else {
                    self.flow(&children, x, y, w)
                }
            }
            "grid" => self.stack(&children, x, y, w, 0),
            "tabpanel" => {
                let tabs: Vec<usize> = children
                    .iter()
                    .copied()
                    .filter(|&c| self.nodes[c].kind == "tab")
                    .collect();
                let active = self.nodes[n].tab.min(tabs.len().saturating_sub(1));
                self.nodes[n].tab = active;
                let mut h = 1;
                for (i, &t) in tabs.iter().enumerate() {
                    if i == active {
                        h += self.place(t, x, y + 1, w);
                    } else {
                        self.nodes[t].rect = Rect::default();
                    }
                }
                h
            }
            "table" => self.place_table(n, x, y, w),
            "text" | "alert" | "stream" | "footer" => {
                let mut text = text_of(props.get("text"));
                if kind == "alert" {
                    let title = text_of(props.get("title"));
                    if !title.is_empty() {
                        text = format!("{}: {}", title, text);
                    }
                }
                let lines = wrap(&text, w);
                let h = lines.len();
                self.nodes[n].lines = lines;
                h
            }
            "input" => {
                let rows = text_of(props.get("rows"))
                    .parse::<usize>()
                    .unwrap_or(1)
                    .max(1);
                let error = text_of(props.get("error"));
                let mut h = rows;
                if !error.is_empty() {
                    self.nodes[n].lines = wrap(&error, w);
                    h += self.nodes[n].lines.len();
                }
                h
            }
            _ => {
                let error = text_of(props.get("error"));
                if !error.is_empty() {
                    self.nodes[n].lines = wrap(&error, w);
                    1 + self.nodes[n].lines.len()
                } else {
                    1
                }
            }
        };
        self.nodes[n].rect = Rect { x, y, w, h };
        h
    }

    fn stack(&mut self, children: &[usize], x: usize, y: usize, w: usize, gap: usize) -> usize {
        let mut cy = y;
        for (i, &c) in children.iter().enumerate() {
            if i > 0 {
                cy += gap;
            }
            cy += self.place(c, x, cy, w);
        }
        cy - y
    }

    /// Children side by side, wrapping to the next line when they do not
    /// fit; on one line, `grow` children share what is left.
    fn flow(&mut self, children: &[usize], x: usize, y: usize, w: usize) -> usize {
        let widths: Vec<usize> = children.iter().map(|&c| self.natural_width(c, w)).collect();
        let total: usize = widths.iter().sum::<usize>() + children.len().saturating_sub(1);
        let mut widths = widths;
        if total <= w {
            let growing: Vec<usize> = children
                .iter()
                .enumerate()
                .filter(|(_, &c)| truthy(self.nodes[c].props.get("grow")))
                .map(|(i, _)| i)
                .collect();
            if !growing.is_empty() {
                let extra = (w - total) / growing.len();
                for i in growing {
                    widths[i] += extra;
                }
            }
        }
        let (mut cx, mut cy, mut line_h) = (x, y, 0usize);
        for (i, &c) in children.iter().enumerate() {
            let cw = widths[i].min(w);
            if cx > x && cx + cw > x + w {
                cx = x;
                cy += line_h.max(1);
                line_h = 0;
            }
            let h = self.place(c, cx, cy, cw);
            line_h = line_h.max(h);
            cx += cw + 1;
        }
        cy + line_h.max(1) - y
    }

    fn place_table(&mut self, n: usize, x: usize, y: usize, w: usize) -> usize {
        let columns = self.nodes[n].columns.clone();
        let rows = self.nodes[n].rows.clone();
        let count = columns.len().max(1);
        // natural widths: the label, or the widest cell
        let mut widths: Vec<usize> = columns
            .iter()
            .enumerate()
            .map(|(i, c)| {
                let label = text_of(c.get("label")).chars().count();
                let widest = rows
                    .iter()
                    .filter_map(|r| r.get(i))
                    .map(|cell| {
                        cell.iter()
                            .map(|&m| self.natural_width(m, w))
                            .sum::<usize>()
                    })
                    .max()
                    .unwrap_or(0);
                label.max(widest).max(1)
            })
            .collect();
        let gaps = count.saturating_sub(1);
        let mut total: usize = widths.iter().sum::<usize>() + gaps;
        while total > w {
            // shrink the widest until it fits
            let (i, _) = widths.iter().enumerate().max_by_key(|(_, &v)| v).unwrap();
            if widths[i] <= 3 {
                break;
            }
            widths[i] -= 1;
            total -= 1;
        }
        // header
        let mut cy = y + 1;
        self.in_table = true;
        for row in &rows {
            let mut cx = x;
            let mut row_h = 1;
            for (i, cell) in row.iter().enumerate() {
                let cw = widths.get(i).copied().unwrap_or(1);
                let mut ccx = cx;
                for &m in cell {
                    let mw = self.natural_width(m, cw).min(cw);
                    let h = self.place(m, ccx, cy, mw);
                    row_h = row_h.max(h);
                    ccx += mw + 1;
                }
                cx += cw + 1;
            }
            cy += row_h;
        }
        self.in_table = false;
        self.nodes[n].lines = widths.iter().map(|w| w.to_string()).collect();
        cy - y
    }

    // ---------------------------------------------------------------- focus

    fn focus_first(&mut self) {
        self.focus = 0;
        // the first field, else the first focusable
        if let Some(i) = self.focusables.iter().position(|&n| {
            matches!(
                self.nodes[n].kind.as_str(),
                "input" | "checkbox" | "switch" | "radio" | "select"
            )
        }) {
            self.focus = i;
        }
        // a field the action refused gets the focus (UI-9)
        if let Some(i) = self
            .focusables
            .iter()
            .position(|&n| !text_of(self.nodes[n].props.get("error")).is_empty())
        {
            self.focus = i;
        }
        self.reveal();
    }

    fn focused(&self) -> Option<usize> {
        self.focusables.get(self.focus).copied()
    }

    /// What the element with the focus is: its kind and the name it
    /// binds or the text it shows. The page shown again after an action
    /// has the same elements, numbered otherwise when a flash or an error
    /// came in; this finds the one it was on.
    pub fn focused_identity(&self) -> Option<(String, String)> {
        self.focused()
            .map(|n| (self.nodes[n].kind.clone(), self.identity(n)))
    }

    fn identity(&self, n: usize) -> String {
        let p = &self.nodes[n].props;
        text_of(
            p.get("bind")
                .or(p.get("text"))
                .or(p.get("label"))
                .or(p.get("to"))
                .or(p.get("ui_id")),
        )
    }

    /// Puts the focus on the element of that kind and identity, when the
    /// page has one; whether it did. A field the action refused keeps
    /// the focus the layout gave it (UI-9).
    pub fn focus_on(&mut self, kind: &str, identity: &str) -> bool {
        if self
            .focused()
            .is_some_and(|n| !text_of(self.nodes[n].props.get("error")).is_empty())
        {
            return false;
        }
        match self
            .focusables
            .iter()
            .position(|&n| self.nodes[n].kind == kind && self.identity(n) == identity)
        {
            Some(i) => {
                self.focus = i;
                self.reveal();
                true
            }
            None => false,
        }
    }

    /// Scrolls so that the focused element is in view.
    fn reveal(&mut self) {
        let Some(n) = self.focused() else {
            return;
        };
        let r = self.nodes[n].rect;
        let (top, bottom) = (r.y, r.y + r.h.max(1));
        let rows = self.content_rows();
        // in view, with a row of what is around it when there is room
        if top < self.scroll + 1 {
            self.scroll = top.saturating_sub(1);
        } else if bottom + 1 > self.scroll + rows {
            self.scroll = (bottom + 1).saturating_sub(rows);
        }
        self.scroll = self.scroll.min(self.content_height.saturating_sub(rows));
    }

    /// Whether that key (Up, Down, Home or End) is the page's to move the
    /// focus with: what has the focus does nothing with it. A button, a
    /// link, a box or a tab bar take none of them; a one-line field takes
    /// Home and End for its cursor and leaves Up and Down; a radio, a
    /// select, a table and a text area take them all.
    fn vertical_key_is_free(&self, key: Key) -> bool {
        match self.focused() {
            None => true,
            Some(n) => match self.nodes[n].kind.as_str() {
                "button" | "link" | "checkbox" | "switch" | "tabpanel" => true,
                "input" => {
                    matches!(key, Key::Up | Key::Down)
                        && text_of(self.nodes[n].props.get("rows")).is_empty()
                }
                _ => false,
            },
        }
    }

    /// Up and Down go to the element before and after (no wrap: a list
    /// ends), Home and End to the first and the last; with nothing to
    /// focus, they scroll.
    fn move_vertically(&mut self, key: Key) -> bool {
        let count = self.focusables.len();
        if count == 0 {
            let rows = self.content_rows();
            let max = self.content_height.saturating_sub(rows);
            self.scroll = match key {
                Key::Up => self.scroll.saturating_sub(1),
                Key::Down => (self.scroll + 1).min(max),
                Key::Home => 0,
                _ => max,
            };
            return true;
        }
        self.focus = match key {
            Key::Up => self.focus.saturating_sub(1),
            Key::Down => (self.focus + 1).min(count - 1),
            Key::Home => 0,
            _ => count - 1,
        };
        self.reveal();
        true
    }

    /// The form an element belongs to, if any.
    fn form_of(&self, n: usize) -> Option<usize> {
        let mut cur = self.nodes[n].parent;
        while let Some(p) = cur {
            if self.nodes[p].kind == "form" {
                return Some(p);
            }
            cur = self.nodes[p].parent;
        }
        None
    }

    /// What a browser would post for the form: a checked box `on`, an
    /// unchecked one nothing, the chosen option's value, the field's text.
    fn form_fields(&self, form: usize, fields: &mut Map<String, Value>) {
        let mut stack = vec![form];
        while let Some(n) = stack.pop() {
            let node = &self.nodes[n];
            let bind = text_of(node.props.get("bind"));
            match node.kind.as_str() {
                "input" if !bind.is_empty() && text_of(node.props.get("input_type")) != "file" => {
                    fields.insert(bind, Value::String(node.value.clone()));
                }
                "checkbox" | "switch" if !bind.is_empty() => {
                    if node.checked {
                        fields.insert(bind, Value::String("on".into()));
                    }
                }
                "radio" | "select" if !bind.is_empty() => {
                    if let Some((_, v)) = self.options(n).get(node.choice) {
                        fields.insert(bind, Value::String(v.clone()));
                    }
                }
                _ => {}
            }
            for &c in node.children.iter().rev() {
                stack.push(c);
            }
            for row in &node.rows {
                for cell in row {
                    stack.extend(cell.iter().copied());
                }
            }
        }
    }

    fn submit(&mut self, form: usize) {
        let node = &self.nodes[form];
        let event = node.event.clone().unwrap_or(Value::Null);
        let action = text_of(event.get("action"));
        let mut fields = event
            .get("fields")
            .and_then(Value::as_object)
            .cloned()
            .unwrap_or_default();
        self.form_fields(form, &mut fields);
        let id = node.id;
        self.events
            .push(json!({"event": "submit", "id": id, "action": action, "fields": fields}));
    }

    /// Enter on a button: its own action, or the form it submits.
    fn activate(&mut self, n: usize) {
        let node = self.nodes[n].clone();
        match node.kind.as_str() {
            "link" => {
                let to = text_of(node.props.get("to"));
                self.events
                    .push(json!({"event": "navigate", "id": node.id, "to": to}));
            }
            "button" => {
                if let Some(event) = &node.event {
                    let action = text_of(event.get("action"));
                    let fields = event.get("fields").cloned().unwrap_or(json!({}));
                    self.events
                        .push(json!({"event": "click", "id": node.id, "action": action, "fields": fields}));
                } else if let Some(form) = self.form_of(n) {
                    self.submit(form);
                }
            }
            _ => {}
        }
    }

    /// The buttons and links in a table's active row, in order.
    fn row_actions(&self, table: usize) -> Vec<usize> {
        let node = &self.nodes[table];
        if node.row < 0 {
            return Vec::new();
        }
        self.actions_of_row(table, node.row as usize)
    }

    /// The buttons and links in one row of a table, in order.
    fn actions_of_row(&self, table: usize, r: usize) -> Vec<usize> {
        let node = &self.nodes[table];
        let Some(row) = node.rows.get(r) else {
            return Vec::new();
        };
        let mut out = Vec::new();
        for cell in row {
            let mut stack: Vec<usize> = cell.iter().rev().copied().collect();
            while let Some(m) = stack.pop() {
                if matches!(self.nodes[m].kind.as_str(), "button" | "link") {
                    out.push(m);
                }
                for &c in self.nodes[m].children.iter().rev() {
                    stack.push(c);
                }
            }
        }
        out
    }

    fn sortable_columns(&self, table: usize) -> Vec<usize> {
        self.nodes[table]
            .columns
            .iter()
            .enumerate()
            .filter(|(_, c)| c.get("to").and_then(Value::as_str).is_some())
            .map(|(i, _)| i)
            .collect()
    }

    // ---------------------------------------------------------------- keys

    /// A key, at `tick`; whether the picture changed.
    pub fn key(&mut self, key: Key, tick: u64) -> bool {
        match key {
            Key::Tab => {
                if !self.focusables.is_empty() {
                    self.focus = (self.focus + 1) % self.focusables.len();
                    self.reveal();
                }
                return true;
            }
            Key::ShiftTab => {
                if !self.focusables.is_empty() {
                    self.focus = (self.focus + self.focusables.len() - 1) % self.focusables.len();
                    self.reveal();
                }
                return true;
            }
            Key::Escape => {
                self.events.push(json!({"event": "close"}));
                return true;
            }
            Key::F5 => {
                self.events.push(json!({"event": "reload"}));
                return true;
            }
            Key::PageDown => {
                let rows = self.content_rows();
                let max = self.content_height.saturating_sub(rows);
                self.scroll = (self.scroll + rows).min(max);
                return true;
            }
            Key::PageUp => {
                self.scroll = self.scroll.saturating_sub(self.content_rows());
                return true;
            }
            Key::Up | Key::Down | Key::Home | Key::End if self.vertical_key_is_free(key) => {
                return self.move_vertically(key);
            }
            _ => {}
        }
        let Some(n) = self.focused() else {
            return false;
        };
        let kind = self.nodes[n].kind.clone();
        match kind.as_str() {
            "input" => self.key_in_field(n, key, tick),
            "checkbox" | "switch" => match key {
                Key::Space => {
                    self.nodes[n].checked = !self.nodes[n].checked;
                    true
                }
                Key::Enter => {
                    if let Some(form) = self.form_of(n) {
                        self.submit(form);
                    }
                    true
                }
                _ => false,
            },
            "radio" | "select" => {
                let count = self.options(n).len();
                match key {
                    Key::Left | Key::Up if count > 0 => {
                        self.nodes[n].choice = (self.nodes[n].choice + count - 1) % count;
                        true
                    }
                    Key::Right | Key::Down if count > 0 => {
                        self.nodes[n].choice = (self.nodes[n].choice + 1) % count;
                        true
                    }
                    Key::Enter => {
                        if let Some(form) = self.form_of(n) {
                            self.submit(form);
                        }
                        true
                    }
                    _ => false,
                }
            }
            "button" | "link" => match key {
                Key::Enter | Key::Space => {
                    self.activate(n);
                    true
                }
                _ => false,
            },
            "table" => self.key_in_table(n, key),
            "tabpanel" => {
                let tabs = self.nodes[n]
                    .children
                    .iter()
                    .filter(|&&c| self.nodes[c].kind == "tab")
                    .count();
                match key {
                    Key::Left if tabs > 0 => {
                        self.nodes[n].tab = (self.nodes[n].tab + tabs - 1) % tabs;
                        self.layout();
                        self.refocus(n);
                        true
                    }
                    Key::Right if tabs > 0 => {
                        self.nodes[n].tab = (self.nodes[n].tab + 1) % tabs;
                        self.layout();
                        self.refocus(n);
                        true
                    }
                    _ => false,
                }
            }
            _ => false,
        }
    }

    /// After a layout, the focus stays on `n`.
    fn refocus(&mut self, n: usize) {
        if let Some(i) = self.focusables.iter().position(|&m| m == n) {
            self.focus = i;
        }
        self.reveal();
    }

    fn key_in_field(&mut self, n: usize, key: Key, tick: u64) -> bool {
        let area = !text_of(self.nodes[n].props.get("rows")).is_empty();
        let number = text_of(self.nodes[n].props.get("input_type")) == "number";
        let mut chars: Vec<char> = self.nodes[n].value.chars().collect();
        let mut cursor = self.nodes[n].cursor.min(chars.len());
        let mut changed = false;
        match key {
            Key::Char(c) => {
                if number && !c.is_ascii_digit() && c != '-' && c != '.' {
                    return false;
                }
                chars.insert(cursor, c);
                cursor += 1;
                changed = true;
            }
            Key::Space => {
                chars.insert(cursor, ' ');
                cursor += 1;
                changed = true;
            }
            Key::Backspace => {
                if cursor > 0 {
                    chars.remove(cursor - 1);
                    cursor -= 1;
                    changed = true;
                }
            }
            Key::Delete => {
                if cursor < chars.len() {
                    chars.remove(cursor);
                    changed = true;
                }
            }
            Key::Left => cursor = cursor.saturating_sub(1),
            Key::Right => cursor = (cursor + 1).min(chars.len()),
            Key::Home => cursor = 0,
            Key::End => cursor = chars.len(),
            Key::CtrlU => {
                chars.clear();
                cursor = 0;
                changed = true;
            }
            Key::Enter => {
                if area {
                    chars.insert(cursor, '\n');
                    cursor += 1;
                    changed = true;
                } else if let Some(form) = self.form_of(n) {
                    self.submit(form);
                    return true;
                }
            }
            _ => return false,
        }
        self.nodes[n].value = chars.into_iter().collect();
        self.nodes[n].cursor = cursor;
        if changed && truthy(self.nodes[n].props.get("search")) {
            // UI-12: search as you type, after a pause
            let delay = text_of(self.nodes[n].props.get("delay"))
                .parse::<u64>()
                .unwrap_or(300);
            self.search_due = Some((tick + delay * 60 / 1000, n));
        }
        true
    }

    fn key_in_table(&mut self, n: usize, key: Key) -> bool {
        let rows = self.nodes[n].rows.len() as isize;
        let sortable = self.sortable_columns(n);
        let node = &self.nodes[n];
        let (row, col) = (node.row, node.col);
        match key {
            Key::Up => {
                let min = if sortable.is_empty() { 0 } else { -1 };
                if row > min {
                    self.nodes[n].row = row - 1;
                    self.nodes[n].col = 0;
                }
                true
            }
            Key::Down => {
                if row + 1 < rows {
                    self.nodes[n].row = row + 1;
                    self.nodes[n].col = 0;
                }
                true
            }
            Key::Left | Key::Right => {
                let count = if row < 0 {
                    sortable.len()
                } else {
                    self.row_actions(n).len()
                };
                if count > 0 {
                    self.nodes[n].col = if key == Key::Left {
                        (col + count - 1) % count
                    } else {
                        (col + 1) % count
                    };
                }
                true
            }
            Key::Enter => {
                if row < 0 {
                    if let Some(&i) = sortable.get(col) {
                        let to = text_of(self.nodes[n].columns[i].get("to"));
                        let id = self.nodes[n].id;
                        self.events
                            .push(json!({"event": "navigate", "id": id, "to": to}));
                    }
                } else if let Some(&m) = self.row_actions(n).get(col) {
                    self.activate(m);
                }
                true
            }
            _ => false,
        }
    }

    /// A tick: a search due sends its change. Whether the picture changed
    /// (the cursor blinks).
    pub fn tick(&mut self, tick: u64) -> bool {
        if let Some((due, n)) = self.search_due {
            if tick >= due {
                self.search_due = None;
                let node = &self.nodes[n];
                self.events.push(json!({
                    "event": "change", "id": node.id,
                    "bind": text_of(node.props.get("bind")), "value": node.value}));
            }
        }
        tick % 30 == 0
            && self
                .focused()
                .is_some_and(|n| self.nodes[n].kind == "input")
    }

    /// The events since the last take.
    pub fn take_events(&mut self) -> Vec<Value> {
        std::mem::take(&mut self.events)
    }

    // ---------------------------------------------------------------- what it shows

    /// The keys that apply to what has the focus.
    pub fn help(&self) -> String {
        let Some(n) = self.focused() else {
            return "Tab move · Esc fecha".into();
        };
        match self.nodes[n].kind.as_str() {
            "input" => "digite · setas · Enter envia · Esc fecha".into(),
            "checkbox" | "switch" => "Espaço marca · Enter envia · Tab move".into(),
            "radio" | "select" => "setas escolhem · Enter envia · Tab move".into(),
            "button" => "Enter aciona · Tab move · Esc fecha".into(),
            "link" => "Enter abre · Tab move · Esc fecha".into(),
            "table" => "setas: linha, ação · Enter aciona · Tab sai".into(),
            "tabpanel" => "setas trocam a aba · Tab entra · Esc fecha".into(),
            _ => "Tab move · Enter escolhe · Esc fecha".into(),
        }
    }

    /// Every text the page shows, in order: for a test.
    pub fn texts(&self) -> Vec<String> {
        let mut out = Vec::new();
        if let Some((flash, _)) = &self.flash {
            out.push(flash.clone());
        }
        self.collect_texts(0, &mut out);
        out
    }

    fn collect_texts(&self, n: usize, out: &mut Vec<String>) {
        let node = &self.nodes[n];
        let p = &node.props;
        match node.kind.as_str() {
            "text" | "badge" | "link" | "button" | "footer" | "stream" | "alert" => {
                let t = text_of(p.get("text"));
                if !t.is_empty() {
                    out.push(t);
                }
                if node.kind == "alert" {
                    let t = text_of(p.get("title"));
                    if !t.is_empty() {
                        out.push(t);
                    }
                }
            }
            "section" | "header" | "cardheader" | "panel" | "card" | "formitem" | "tab" => {
                let t = text_of(p.get("title").or(p.get("label")).or(p.get("text")));
                if !t.is_empty() {
                    out.push(t);
                }
            }
            "checkbox" | "switch" => out.push(text_of(p.get("label"))),
            "radio" | "select" => out.extend(self.options(n).into_iter().map(|(l, _)| l)),
            "image" => out.push(format!("[{}]", text_of(p.get("alt")))),
            "table" => {
                for c in &node.columns {
                    let label = text_of(c.get("label"));
                    if !label.is_empty() {
                        out.push(label);
                    }
                }
            }
            _ => {}
        }
        let error = text_of(p.get("error"));
        if !error.is_empty() {
            out.push(error);
        }
        if node.kind == "tabpanel" {
            // the closed tabs' content is not shown
            let active = node.tab;
            for (i, &c) in node
                .children
                .iter()
                .filter(|&&c| self.nodes[c].kind == "tab")
                .enumerate()
            {
                out.push(text_of(self.nodes[c].props.get("title")));
                if i == active {
                    for &g in &self.nodes[c].children {
                        self.collect_texts(g, out);
                    }
                }
            }
            return;
        }
        for &c in &node.children {
            self.collect_texts(c, out);
        }
        for row in &node.rows {
            for cell in row {
                for &m in cell {
                    self.collect_texts(m, out);
                }
            }
        }
    }

    /// The page as data: the title, the flash, the focusable elements in
    /// order with their state, the texts, the help line.
    pub fn observe(&self) -> Value {
        let items: Vec<Value> = self
            .focusables
            .iter()
            .enumerate()
            .map(|(i, &n)| {
                let node = &self.nodes[n];
                let p = &node.props;
                let mut v = json!({
                    "id": node.id, "kind": node.kind, "focus": i == self.focus,
                    "bind": p.get("bind").cloned().unwrap_or(Value::Null),
                    "label": p.get("label").or(p.get("text")).or(p.get("title")).cloned().unwrap_or(Value::Null),
                });
                match node.kind.as_str() {
                    "input" => {
                        v["value"] = json!(node.value);
                        v["cursor"] = json!(node.cursor);
                    }
                    "checkbox" | "switch" => v["checked"] = json!(node.checked),
                    "radio" | "select" => {
                        let options = self.options(n);
                        v["value"] = json!(options.get(node.choice).map(|(_, v)| v.clone()).unwrap_or_default());
                        v["options"] = json!(options.iter().map(|(_, v)| v.clone()).collect::<Vec<_>>());
                    }
                    "table" => {
                        v["row"] = json!(node.row);
                        v["col"] = json!(node.col);
                        v["actions"] = json!(self
                            .row_actions(n)
                            .iter()
                            .map(|&m| text_of(self.nodes[m].props.get("text")))
                            .collect::<Vec<_>>());
                        // every row's actions, for a driver looking for a button by its text
                        v["rows"] = json!((0..node.rows.len())
                            .map(|r| self
                                .actions_of_row(n, r)
                                .iter()
                                .map(|&m| text_of(self.nodes[m].props.get("text")))
                                .collect::<Vec<_>>())
                            .collect::<Vec<_>>());
                    }
                    "tabpanel" => v["tab"] = json!(node.tab),
                    "link" => v["to"] = json!(text_of(p.get("to"))),
                    _ => {}
                }
                if let Some(e) = p.get("error") {
                    v["error"] = e.clone();
                }
                v
            })
            .collect();
        let progress: Vec<Value> = self
            .nodes
            .iter()
            .filter(|n| n.kind == "progress")
            .map(|n| {
                json!({"id": n.props.get("ui_id").cloned().unwrap_or(Value::Null),
                             "value": text_of(n.props.get("value")).parse::<f64>().unwrap_or(0.0)})
            })
            .collect();
        json!({
            "title": self.title,
            "flash": self.flash.as_ref().map(|(f, _)| f.clone()),
            "shown": self.shown,
            "cols": self.cols,
            "rows": self.rows,
            "frame": {"x": self.frame.x, "y": self.frame.y, "w": self.frame.w, "h": self.frame.h},
            "focus": self.focus,
            "items": items,
            "texts": self.texts(),
            "progress": progress,
            "help": self.help(),
            "scroll": self.scroll,
            "height": self.content_height,
        })
    }

    // ---------------------------------------------------------------- drawing

    /// The page over the scene, as a window: the scene dimmed, a shadow,
    /// a frame with a bevel, the title bar with the Esc key, the flash,
    /// the content from the scroll, a scrollbar when it is longer than
    /// the window, the status bar with the keys that apply. Drawn in the
    /// band's own pixels (at the fine level the canvas has twice the
    /// scene's, and the page twice the cells), so the font is never a
    /// block.
    pub fn draw(&self, b: &mut Band, font: &Font, tick: u64) {
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let f = self.frame;
        let (x, y, w, h) = (f.x as i32, f.y as i32, f.w as u32, f.h as u32);
        b.fill_rect(0, 0, self.canvas.0, self.canvas.1, DIM);
        b.fill_rect(x + 3, y + 3, w, h, SHADOW);
        bevel_out(b, x, y, w, h, BG, LIGHT, BLACK);
        // the title bar: honey in two tones, the title in ink, the Esc key
        b.fill_rect(x + 1, y + 1, w - 2, 6, TITLE_BG);
        b.fill_rect(x + 1, y + 7, w - 2, (TITLE_H - 6) as u32, TITLE_BG2);
        b.fill_rect(x + 1, y + 1 + TITLE_H, w - 2, 1, DARK);
        b.text(
            font,
            &cut(&self.title, self.cols.saturating_sub(6)),
            x + 5,
            y + 2,
            INK,
        );
        let kx = x + w as i32 - 26;
        bevel_out(b, kx, y + 2, 23, 9, TITLE_BG2, TITLE_BG, TITLE_DARK);
        b.text(font, "Esc", kx + 2, y + 1, INK);
        // the flash: what the action said, in the first row of the content
        if let Some((flash, error)) = &self.flash {
            let fy = self.oy;
            let (bg, light, dark, color) = if *error {
                (ERR_BG, ERR_LIGHT, ERR_DARK, ERR_TEXT)
            } else {
                (OK_BG, OK_LIGHT, OK_DARK, OK_TEXT)
            };
            let fw = self.cols as u32 * cw as u32 + 2;
            bevel_out(b, self.ox - 1, fy, fw, ch as u32, bg, light, dark);
            b.text(
                font,
                &cut(flash, self.cols.saturating_sub(1)),
                self.ox + 2,
                fy,
                color,
            );
        }
        // the content, by rows
        let focused = self.focused();
        let blink = (tick / 30) % 2 == 0;
        self.draw_node(0, b, font, focused, blink);
        // the scrollbar, sunken, with a raised thumb, inside the frame
        let content_rows = self.content_rows();
        if self.content_height > content_rows {
            let sx = x + w as i32 - 6;
            let y0 = self.oy + self.content_top() as i32 * ch;
            let track = content_rows as i32 * ch;
            bevel_in(b, sx, y0, 4, track as u32, DARK, LIGHT, BLACK);
            let thumb = ((track as f32 * content_rows as f32 / self.content_height as f32).round()
                as i32)
                .clamp(ch, track);
            let room = (self.content_height - content_rows) as f32;
            let at = y0 + ((track - thumb) as f32 * self.scroll as f32 / room).round() as i32;
            bevel_out(b, sx, at, 4, thumb as u32, MID, LIGHT, BLACK);
        }
        // the status bar: the keys that apply, raised
        let sy = y + h as i32 - 1 - STATUS_H;
        b.fill_rect(x + 1, sy - 1, w - 2, 1, LIGHT);
        b.fill_rect(x + 1, sy, w - 2, STATUS_H as u32, MID);
        b.text(font, &cut(&self.help(), self.cols), x + 5, sy + 1, TEXT);
    }

    /// A row of the content on the screen, or None when scrolled out.
    fn row_y(&self, row: usize, ch: i32) -> Option<i32> {
        if row < self.scroll || row - self.scroll >= self.content_rows() {
            return None;
        }
        Some(self.oy + (self.content_top() + row - self.scroll) as i32 * ch)
    }

    #[allow(clippy::too_many_lines)]
    fn draw_node(&self, n: usize, b: &mut Band, font: &Font, focused: Option<usize>, blink: bool) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let r = node.rect;
        let p = &node.props;
        let is_focus = focused == Some(n);
        let x = self.ox + r.x as i32 * cw;
        let kind = node.kind.as_str();
        match kind {
            "page" | "window" | "vbox" | "scrollbox" | "form" | "cardbody" | "cardfooter"
            | "tab" | "list" | "item" | "hbox" | "grid" => {}
            "section" | "header" | "cardheader" | "formitem" => {
                if let (Some(line), Some(y)) = (node.lines.first(), self.row_y(r.y, ch)) {
                    if !line.trim().is_empty() {
                        b.text(
                            font,
                            line,
                            x,
                            y + 1,
                            if kind == "formitem" { MUTED } else { HONEY },
                        );
                    }
                }
            }
            "panel" | "card" => {
                // a frame with a bevel, a line a cell in, the title on it
                let (x0, x1) = (x, self.ox + (r.x + r.w) as i32 * cw);
                if let Some(y) = self.row_y(r.y, ch) {
                    b.fill_rect(x0, y + ch / 2, (x1 - x0) as u32, 1, LIGHT);
                    if let Some(title) = node.lines.first() {
                        if !title.is_empty() {
                            let tw = font.width_of(title) as i32 + 2 * cw;
                            b.fill_rect(x0 + cw, y, tw as u32, ch as u32, BG);
                            b.text(font, title, x0 + 2 * cw, y + 1, HONEY);
                        }
                    }
                }
                if let Some(y) = self.row_y(r.y + r.h - 1, ch) {
                    b.fill_rect(x0, y + ch / 2, (x1 - x0) as u32, 1, BLACK);
                }
                for row in r.y..r.y + r.h {
                    if let Some(y) = self.row_y(row, ch) {
                        b.fill_rect(x0, y, 1, ch as u32, LIGHT);
                        b.fill_rect(x1 - 1, y, 1, ch as u32, BLACK);
                    }
                }
            }
            "text" | "footer" | "stream" | "alert" => {
                let (bg, color) = match kind {
                    "alert" => {
                        if matches!(text_of(p.get("variant")).as_str(), "danger" | "error") {
                            (Some((ERR_BG, ERR_LIGHT, ERR_DARK)), ERR_TEXT)
                        } else {
                            (Some((OK_BG, OK_LIGHT, OK_DARK)), OK_TEXT)
                        }
                    }
                    "footer" => (None, MUTED),
                    _ => (
                        None,
                        if text_of(p.get("weight")) == "bold" {
                            HONEY
                        } else {
                            TEXT
                        },
                    ),
                };
                for (i, line) in node.lines.iter().enumerate() {
                    if let Some(y) = self.row_y(r.y + i, ch) {
                        if let Some((fill, light, dark)) = bg {
                            let wpx = r.w as u32 * cw as u32;
                            b.fill_rect(x, y, wpx, ch as u32, fill);
                            if i == 0 {
                                b.fill_rect(x, y, wpx, 1, light);
                            }
                            if i + 1 == node.lines.len() {
                                b.fill_rect(x, y + ch - 1, wpx, 1, dark);
                            }
                            b.fill_rect(x, y, 1, ch as u32, light);
                            b.fill_rect(x + wpx as i32 - 1, y, 1, ch as u32, dark);
                        }
                        b.text(font, line, x + i32::from(bg.is_some()) * 2, y + 1, color);
                    }
                }
            }
            "badge" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let t = cut(&text_of(p.get("text")), r.w.saturating_sub(2));
                    let (bg, light, dark, color) = match text_of(p.get("variant")).as_str() {
                        "success" => (OK_BG, OK_LIGHT, OK_DARK, OK_TEXT),
                        "danger" | "error" => (ERR_BG, ERR_LIGHT, ERR_DARK, ERR_TEXT),
                        "warning" | "primary" => (TITLE_BG2, TITLE_BG, TITLE_DARK, INK),
                        _ => (MID, LIGHT, BLACK, TEXT),
                    };
                    let wpx = font.width_of(&t) + 2 * font.cell.0;
                    bevel_out(b, x, y, wpx, ch as u32, bg, light, dark);
                    b.text(font, &t, x + cw, y, color);
                }
            }
            "link" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let t = cut(&text_of(p.get("text")), r.w);
                    let color = if is_focus { HONEY } else { LINK };
                    b.text(font, &t, x, y + 1, color);
                }
            }
            "image" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    b.text(
                        font,
                        &cut(&format!("[{}]", text_of(p.get("alt"))), r.w),
                        x,
                        y + 1,
                        MUTED,
                    );
                }
            }
            "rule" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let wpx = r.w as u32 * cw as u32;
                    b.fill_rect(x, y + ch / 2 - 1, wpx, 1, BLACK);
                    b.fill_rect(x, y + ch / 2, wpx, 1, LIGHT);
                }
            }
            "spacer" => {}
            "progress" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let max = text_of(p.get("max"))
                        .parse::<f32>()
                        .unwrap_or(100.0)
                        .max(1.0);
                    let value = text_of(p.get("value"))
                        .parse::<f32>()
                        .unwrap_or(0.0)
                        .clamp(0.0, max);
                    let w = (r.w.min(20) as i32 * cw) as u32;
                    bevel_in(b, x, y + 1, w, (ch - 2) as u32, FIELD_BG, LIGHT, BLACK);
                    let filled = ((w - 2) as f32 * value / max) as u32;
                    if filled > 0 {
                        b.fill_rect(x + 1, y + 2, filled, (ch - 4) as u32, HONEY);
                    }
                }
            }
            "button" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let t = cut(&text_of(p.get("text")), r.w.saturating_sub(4));
                    let variant = text_of(p.get("variant"));
                    let (bg, light, dark, color) = if is_focus {
                        (MID, HONEY, HONEY, HONEY)
                    } else if variant == "primary" {
                        (MID, LIGHT, BLACK, HONEY)
                    } else if variant == "danger" {
                        (DANGER_BG, ERR_LIGHT, ERR_DARK, TEXT)
                    } else {
                        (MID, LIGHT, BLACK, TEXT)
                    };
                    let w = font.width_of(&t) + 4 * font.cell.0;
                    bevel_out(b, x, y, w, ch as u32, bg, light, dark);
                    b.text(font, &t, x + 2 * cw, y, color);
                }
            }
            "input" => {
                let rows = text_of(p.get("rows")).parse::<usize>().unwrap_or(1).max(1);
                let password = text_of(p.get("input_type")) == "password";
                let shown: String = if password {
                    node.value.chars().map(|_| '*').collect()
                } else {
                    node.value.clone()
                };
                let lines: Vec<String> = if rows > 1 {
                    shown.split('\n').map(str::to_string).collect()
                } else {
                    vec![shown]
                };
                // the cursor's line and column, for an area
                let mut before = node.cursor;
                let (mut cl, mut cc) = (0usize, before);
                for (i, l) in lines.iter().enumerate() {
                    let len = l.chars().count();
                    if before <= len {
                        cl = i;
                        cc = before;
                        break;
                    }
                    before -= len + 1;
                }
                let inner = r.w.saturating_sub(2).max(1);
                let wpx = r.w as u32 * cw as u32;
                // the field, sunken: one box for every row of an area
                let (light, dark) = if is_focus {
                    (HONEY, HONEY)
                } else {
                    (LIGHT, BLACK)
                };
                let (first, last) = (self.row_y(r.y, ch), self.row_y(r.y + rows - 1, ch));
                if let (Some(top), Some(bottom)) = (first, last) {
                    let hpx = (bottom + ch - top) as u32;
                    bevel_in(b, x, top, wpx, hpx, FIELD_BG, light, dark);
                }
                for i in 0..rows {
                    let Some(y) = self.row_y(r.y + i, ch) else {
                        continue;
                    };
                    let line = lines.get(i).cloned().unwrap_or_default();
                    // scroll the line so the cursor is in view
                    let start = if i == cl && cc > inner.saturating_sub(1) {
                        cc + 1 - inner
                    } else {
                        0
                    };
                    let visible: String = line.chars().skip(start).take(inner).collect();
                    if line.is_empty() && i == 0 && !is_focus {
                        b.text(
                            font,
                            &cut(&text_of(p.get("placeholder")), inner),
                            x + cw,
                            y,
                            MUTED,
                        );
                    } else {
                        b.text(font, &visible, x + cw, y, TEXT);
                    }
                    if is_focus && i == cl && blink {
                        let cx = x + cw + (cc - start) as i32 * cw;
                        b.fill_rect(cx, y + 1, cw as u32, (ch - 2) as u32, HONEY);
                        if let Some(under) = line.chars().nth(cc) {
                            b.text(font, &under.to_string(), cx, y, INK);
                        }
                    }
                }
                for (i, line) in node.lines.iter().enumerate() {
                    if let Some(y) = self.row_y(r.y + rows + i, ch) {
                        b.text(font, line, x, y + 1, ERR_TEXT);
                    }
                }
            }
            "checkbox" | "switch" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let (light, dark) = if is_focus {
                        (HONEY, HONEY)
                    } else {
                        (LIGHT, BLACK)
                    };
                    if kind == "switch" {
                        // a track with a knob at the left (off) or the right (on)
                        bevel_in(b, x, y + 1, 14, 8, FIELD_BG, light, dark);
                        let kx = if node.checked { x + 7 } else { x + 1 };
                        if node.checked {
                            bevel_out(b, kx, y + 2, 6, 6, HONEY, TITLE_BG, TITLE_DARK);
                        } else {
                            bevel_out(b, kx, y + 2, 6, 6, MID, LIGHT, BLACK);
                        }
                    } else {
                        bevel_in(b, x, y + 1, 8, 8, FIELD_BG, light, dark);
                        if node.checked {
                            check_mark(b, x, y + 1, HONEY);
                        }
                    }
                    b.text(
                        font,
                        &cut(&text_of(p.get("label")), r.w.saturating_sub(4)),
                        x + 3 * cw,
                        y + 1,
                        TEXT,
                    );
                }
                self.draw_error(node, b, font, 1);
            }
            "radio" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let mut cx = x;
                    for (i, (label, _)) in self.options(n).iter().enumerate() {
                        let chosen = i == node.choice;
                        let (light, dark) = if is_focus && chosen {
                            (HONEY, HONEY)
                        } else {
                            (LIGHT, BLACK)
                        };
                        bevel_in(b, cx, y + 1, 8, 8, FIELD_BG, light, dark);
                        if chosen {
                            b.fill_rect(cx + 2, y + 3, 4, 4, HONEY);
                        }
                        b.text(font, label, cx + 2 * cw, y + 1, TEXT);
                        cx += (label.chars().count() as i32 + 5) * cw;
                    }
                }
                self.draw_error(node, b, font, 1);
            }
            "select" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let options = self.options(n);
                    let label = options
                        .get(node.choice)
                        .map(|(l, _)| l.clone())
                        .unwrap_or_default();
                    let (light, dark, color) = if is_focus {
                        (HONEY, HONEY, HONEY)
                    } else {
                        (LIGHT, BLACK, TEXT)
                    };
                    let shown = cut(&label, r.w.saturating_sub(4));
                    let wpx = font.width_of(&shown) + 4 * font.cell.0;
                    bevel_out(b, x, y, wpx, ch as u32, MID, light, dark);
                    b.text(font, &shown, x + cw / 2 + 1, y, color);
                    // the arrow: three rows, five, three and one pixel wide
                    let ax = x + wpx as i32 - 9;
                    for (i, w) in [5u32, 3, 1].iter().enumerate() {
                        b.fill_rect(ax + i as i32, y + 3 + i as i32, *w, 1, HONEY);
                    }
                }
                self.draw_error(node, b, font, 1);
            }
            "tabpanel" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let mut cx = x;
                    for (i, &c) in node
                        .children
                        .iter()
                        .filter(|&&c| self.nodes[c].kind == "tab")
                        .enumerate()
                    {
                        let title = text_of(self.nodes[c].props.get("title"));
                        let title = if title.is_empty() {
                            (i + 1).to_string()
                        } else {
                            title
                        };
                        let active = i == node.tab;
                        let width = font.width_of(&title) + 2 * cw as u32;
                        if active {
                            let (bg, light, dark) = if is_focus {
                                (TITLE_BG2, TITLE_BG, TITLE_DARK)
                            } else {
                                (MID, LIGHT, BLACK)
                            };
                            bevel_out(b, cx, y, width, ch as u32, bg, light, dark);
                        }
                        let color = if active && is_focus {
                            INK
                        } else if active {
                            TEXT
                        } else {
                            MUTED
                        };
                        b.text(font, &title, cx + cw, y, color);
                        cx += (title.chars().count() as i32 + 3) * cw;
                    }
                    // the bar's floor
                    b.fill_rect(x, y + ch - 1, r.w as u32 * cw as u32, 1, LIGHT);
                }
            }
            "table" => {
                let widths: Vec<usize> =
                    node.lines.iter().map(|w| w.parse().unwrap_or(1)).collect();
                if let Some(y) = self.row_y(r.y, ch) {
                    let mut cx = x;
                    let sortable = self.sortable_columns(n);
                    for (i, c) in node.columns.iter().enumerate() {
                        let w = widths.get(i).copied().unwrap_or(1);
                        let label = cut(&text_of(c.get("label")), w);
                        let on = is_focus && node.row < 0 && sortable.get(node.col) == Some(&i);
                        b.text(font, &label, cx, y, if on { HONEY } else { MUTED });
                        if on {
                            b.fill_rect(cx, y + ch - 2, font.width_of(&label), 1, HONEY);
                        }
                        cx += (w as i32 + 1) * cw;
                    }
                    // the rule under the header
                    b.fill_rect(x, y + ch - 1, r.w as u32 * cw as u32, 1, LINE);
                }
                // the rows: every other one shaded, the active one lit
                let active_row = if is_focus && node.row >= 0 {
                    node.row as usize
                } else {
                    usize::MAX
                };
                for (ri, row) in node.rows.iter().enumerate() {
                    let top = row
                        .iter()
                        .flatten()
                        .map(|&m| self.nodes[m].rect.y)
                        .min()
                        .unwrap_or(r.y + 1);
                    let height = row
                        .iter()
                        .flatten()
                        .map(|&m| self.nodes[m].rect.y + self.nodes[m].rect.h)
                        .max()
                        .unwrap_or(top + 1)
                        - top;
                    let bg = if ri == active_row {
                        Some(ROW_BG)
                    } else if ri % 2 == 1 {
                        Some(ZEBRA)
                    } else {
                        None
                    };
                    if let Some(bg) = bg {
                        for i in 0..height.max(1) {
                            if let Some(y) = self.row_y(top + i, ch) {
                                let wpx = r.w as u32 * cw as u32 + 2;
                                b.fill_rect(x - 1, y, wpx, ch as u32, bg);
                            }
                        }
                    }
                }
                let active_action = if is_focus && node.row >= 0 {
                    self.row_actions(n).get(node.col).copied()
                } else {
                    None
                };
                for row in &node.rows {
                    for cell in row {
                        for &m in cell {
                            self.draw_node(m, b, font, active_action, blink);
                        }
                    }
                }
                return;
            }
            _ => {
                if let Some(y) = self.row_y(r.y, ch) {
                    b.text(
                        font,
                        &cut(&format!("[ui:{} não é desenhado na tela]", kind), r.w),
                        x,
                        y + 1,
                        MUTED,
                    );
                }
            }
        }
        for &c in &node.children {
            if kind == "tabpanel"
                && self.nodes[c].kind == "tab"
                && self.nodes[c].rect == Rect::default()
            {
                continue;
            }
            self.draw_node(c, b, font, focused, blink);
        }
    }

    fn draw_error(&self, node: &Node, b: &mut Band, font: &Font, from: usize) {
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        for (i, line) in node.lines.iter().enumerate() {
            if let Some(y) = self.row_y(node.rect.y + from + i, ch) {
                b.text(
                    font,
                    line,
                    self.ox + node.rect.x as i32 * cw,
                    y + 1,
                    ERR_TEXT,
                );
            }
        }
    }
}

/// A raised box: light above and left, dark below and right.
#[allow(clippy::too_many_arguments)]
fn bevel_out(b: &mut Band, x: i32, y: i32, w: u32, h: u32, fill: u32, light: u32, dark: u32) {
    if w == 0 || h == 0 {
        return;
    }
    b.fill_rect(x, y, w, h, fill);
    b.fill_rect(x, y, w, 1, light);
    b.fill_rect(x, y, 1, h, light);
    b.fill_rect(x, y + h as i32 - 1, w, 1, dark);
    b.fill_rect(x + w as i32 - 1, y, 1, h, dark);
}

/// A sunken box (a field): dark above and left, light below and right.
#[allow(clippy::too_many_arguments)]
fn bevel_in(b: &mut Band, x: i32, y: i32, w: u32, h: u32, fill: u32, light: u32, dark: u32) {
    bevel_out(b, x, y, w, h, fill, dark, light);
}

/// A check mark in an 8-px box at (x, y).
fn check_mark(b: &mut Band, x: i32, y: i32, color: u32) {
    for (dx, dy) in [(2, 4), (3, 5), (4, 6), (5, 5), (6, 4), (7, 3)] {
        b.fill_rect(x + dx, y + dy, 1, 1, color);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn page() -> Value {
        json!({"title": "Tarefas", "flash": "Criada: ligar", "view": [
            {"id": 1, "type": "window", "props": {"title": "Tarefas"}, "children": [
                {"id": 2, "type": "form", "props": {}, "event": {"action": "criar", "fields": {"filtro": "todas"}}, "children": [
                    {"id": 3, "type": "input", "props": {"bind": "titulo", "placeholder": "O que?"}},
                    {"id": 4, "type": "select", "props": {"bind": "prioridade", "options": "media,alta,baixa", "value": "alta"}},
                    {"id": 5, "type": "checkbox", "props": {"bind": "urgente", "label": "Urgente", "checked": "true"}},
                    {"id": 6, "type": "button", "props": {"text": "Criar", "variant": "primary"}}]},
                {"id": 7, "type": "button", "props": {"text": "Concluir"}, "event": {"action": "alternar", "fields": {"id": "3"}}},
                {"id": 8, "type": "link", "props": {"text": "Planilha", "to": "/planilha"}},
                {"id": 9, "type": "table", "props": {}, "children": [],
                 "columns": [{"label": "Nome", "to": "/?sort=nome"}, {"label": "Ações"}],
                 "rows": [[[{"id": 10, "type": "text", "props": {"text": "Ana"}}],
                           [{"id": 11, "type": "button", "props": {"text": "Remover"}, "event": {"action": "remove", "fields": {"id": "1"}}}]],
                          [[{"id": 12, "type": "text", "props": {"text": "Bia"}}],
                           [{"id": 13, "type": "button", "props": {"text": "Remover"}, "event": {"action": "remove", "fields": {"id": "2"}}}]]]}]}]})
    }

    fn keys(w: &mut Window, keys: &[Key]) {
        for &k in keys {
            w.key(k, 0);
        }
    }

    #[test]
    fn the_focus_starts_on_the_first_field_and_tab_goes_round() {
        let mut w = Window::new(&page(), 320, 180);
        let obs = w.observe();
        assert_eq!(obs["items"][0]["bind"], "titulo");
        assert_eq!(obs["items"][0]["focus"], true);
        assert_eq!(
            obs["items"].as_array().unwrap().len(),
            7,
            "input, select, checkbox, button, button, link, table"
        );
        keys(
            &mut w,
            &[Key::Tab, Key::Tab, Key::Tab, Key::Tab, Key::Tab, Key::Tab],
        );
        assert_eq!(w.observe()["items"][6]["focus"], true, "the table");
        keys(&mut w, &[Key::Tab]);
        assert_eq!(w.observe()["items"][0]["focus"], true, "round again");
        keys(&mut w, &[Key::ShiftTab]);
        assert_eq!(w.observe()["items"][6]["focus"], true);
        assert!(w.help().contains("linha"));
    }

    #[test]
    fn typing_edits_the_field_with_a_cursor_and_enter_submits_the_form() {
        let mut w = Window::new(&page(), 320, 180);
        for c in "ligar".chars() {
            w.key(Key::Char(c), 0);
        }
        keys(
            &mut w,
            &[
                Key::Home,
                Key::Char('a'),
                Key::Right,
                Key::Backspace,
                Key::End,
                Key::Space,
                Key::Char('x'),
                Key::Delete,
                Key::Backspace,
            ],
        );
        assert_eq!(
            w.observe()["items"][0]["value"],
            "aigar ",
            "a at the start, l gone, a space at the end"
        );
        keys(&mut w, &[Key::CtrlU]);
        for c in "banco".chars() {
            w.key(Key::Char(c), 0);
        }
        // the select to baixa, the box off
        keys(
            &mut w,
            &[
                Key::Tab,
                Key::Right,
                Key::Tab,
                Key::Space,
                Key::ShiftTab,
                Key::ShiftTab,
                Key::Enter,
            ],
        );
        let events = w.take_events();
        assert_eq!(events.len(), 1);
        assert_eq!(events[0]["event"], "submit");
        assert_eq!(events[0]["action"], "criar");
        assert_eq!(events[0]["fields"]["titulo"], "banco");
        assert_eq!(events[0]["fields"]["prioridade"], "baixa");
        assert_eq!(
            events[0]["fields"]["filtro"], "todas",
            "the form's hidden fields"
        );
        assert!(
            events[0]["fields"].get("urgente").is_none(),
            "an unchecked box does not go"
        );
    }

    #[test]
    fn buttons_click_links_navigate_tables_act_by_row_and_esc_closes() {
        let mut w = Window::new(&page(), 320, 180);
        keys(
            &mut w,
            &[Key::Tab, Key::Tab, Key::Tab, Key::Tab, Key::Enter],
        );
        assert_eq!(
            w.take_events()[0]["fields"]["id"],
            "3",
            "Concluir sends its row's field"
        );
        keys(&mut w, &[Key::Tab, Key::Enter]);
        assert_eq!(w.take_events()[0]["to"], "/planilha");
        keys(&mut w, &[Key::Tab, Key::Down, Key::Enter]);
        let e = w.take_events();
        assert_eq!(e[0]["event"], "click");
        assert_eq!(e[0]["fields"]["id"], "2", "the second row's Remover");
        keys(&mut w, &[Key::Up, Key::Up, Key::Enter]);
        assert_eq!(
            w.take_events()[0]["to"],
            "/?sort=nome",
            "the header's sortable column"
        );
        keys(&mut w, &[Key::Escape]);
        assert_eq!(w.take_events()[0]["event"], "close");
    }

    #[test]
    fn a_search_field_says_its_change_after_a_pause() {
        let page = json!({"title": "Busca", "view": [{"id": 1, "type": "input", "props": {"bind": "q", "search": true, "delay": 300}}]});
        let mut w = Window::new(&page, 320, 180);
        w.key(Key::Char('b'), 10);
        assert!(w.take_events().is_empty());
        assert!(!w.tick(20));
        w.tick(10 + 18);
        assert_eq!(w.take_events()[0]["event"], "change");
        assert_eq!(w.observe()["items"][0]["value"], "b");
    }

    #[test]
    fn texts_are_the_page_s_and_a_closed_tab_s_are_not() {
        let page = json!({"title": "T", "view": [{"type": "tabpanel", "props": {}, "children": [
            {"type": "tab", "props": {"title": "First"}, "children": [{"type": "text", "props": {"text": "one"}}]},
            {"type": "tab", "props": {"title": "Second"}, "children": [{"type": "text", "props": {"text": "two"}}]}]}]});
        let mut w = Window::new(&page, 320, 180);
        let texts = w.texts();
        assert!(texts.contains(&"one".to_string()) && !texts.contains(&"two".to_string()));
        w.key(Key::Right, 0);
        let texts = w.texts();
        assert!(texts.contains(&"two".to_string()) && !texts.contains(&"one".to_string()));
        assert_eq!(wrap("a bb ccc dddd", 5), vec!["a bb", "ccc", "dddd"]);
        assert_eq!(wrap("abcdefgh", 3), vec!["abc", "def", "gh"]);
    }
}
