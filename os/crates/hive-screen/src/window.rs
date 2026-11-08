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
//!
//! The tags with a state of their own (UI-21) keep it here, from the view
//! the page was shown with until it is shown again: an open modal is a box
//! over the page that has the keyboard; a toast is drawn over the page for
//! its `duration` (counted in ticks); an accordion's folds open and close
//! on their headers, the first open; a tooltip's tip shows while it has the
//! focus; a dropdown's button opens its options; a carousel shows one
//! slide, a stepper one step, with their controls; a calendar, a date field
//! shown as a month, moves its cursor with the arrows and its month with
//! PgUp and PgDn, and Enter picks the day, which its form sends.

use crate::canvas::{Band, Font};
use crate::world::{Key, TICK_RATE};
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
/// UI-21: the rows of the modal shown over the page are counted from here,
/// so that its content is laid out as the page's is and drawn in a box of
/// its own over it (`row_y`).
const OVERLAY: usize = 1 << 20;
/// The page under a modal, dimmed.
const DIM: u32 = 0xA000_0000;

// The look of a window manager in pixel art: a 1-px bevel (light above and
// left, dark below and right) on what is raised, the reverse on what is
// sunken, a 3-px shadow, the scene dimmed under the window.
const BG: u32 = 0xFF12_1228;
const TITLE_BG: u32 = 0xFFFF_D34D;
const TITLE_BG2: u32 = 0xFFD9_AA2E;
const TITLE_DARK: u32 = 0xFF8A_6A10;
pub(crate) const LIGHT: u32 = 0xFF4A_4A7A;
pub(crate) const MID: u32 = 0xFF2A_2A48;
pub(crate) const DARK: u32 = 0xFF0B_0B16;
pub(crate) const BLACK: u32 = 0xFF05_050C;
const ZEBRA: u32 = 0xFF16_1630;
const OK_LIGHT: u32 = 0xFF2F_6F3F;
const OK_DARK: u32 = 0xFF10_3018;
const ERR_LIGHT: u32 = 0xFF8A_3A3A;
const ERR_DARK: u32 = 0xFF30_1010;
pub(crate) const SHADOW: u32 = 0x8000_0000;
const INK: u32 = 0xFF1A_1A2E;
pub(crate) const TEXT: u32 = 0xFFFF_FFFF;
const MUTED: u32 = 0xFF8A_8AA0;
pub(crate) const HONEY: u32 = 0xFFFF_D34D;
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
    /// A chart's bars (UI-21): {label, shown, percent, color}.
    bars: Vec<Value>,
    // what the keyboard changes
    value: String,
    cursor: usize,
    checked: bool,
    choice: usize,
    /// A tabpanel's open tab; a carousel's slide, a stepper's step (UI-21).
    tab: usize,
    /// UI-21: what a tag with a state of its own keeps: a fold, a dropdown
    /// or a modal open, a toast still shown.
    open: bool,
    /// A toast's ticks left (0: it stays until dismissed); a carousel's
    /// ticks since its slide moved (`auto_play`).
    ticks: u64,
    /// A stepper's Back and Next: buttons of the screen's own, outside the
    /// view tree.
    controls: Vec<usize>,
    /// A table's active row (-1: the header) and the action in it.
    row: isize,
    col: usize,
    /// UI-21: a calendar's cursor, in days from 1970-01-01; the month it is
    /// in is the month shown. Its `value` is the day picked (YYYY-MM-DD).
    day: i64,
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
    /// UI-21: the modal shown over the page, which has the keyboard while
    /// it is open; the rows of its box; the focusables that are its own.
    overlay: Option<usize>,
    overlay_rows: usize,
    overlay_focus: (usize, usize),
    /// The toasts laid out, drawn over the page.
    toasts: Vec<usize>,
}

fn text_of(v: Option<&Value>) -> String {
    match v {
        Some(Value::String(s)) => s.clone(),
        Some(Value::Null) | None => String::new(),
        Some(other) => other.to_string(),
    }
}

/// A number in the view: a JSON number, or a text that reads as one.
fn number(v: Option<&Value>) -> Option<f64> {
    match v {
        Some(Value::Number(n)) => n.as_f64(),
        Some(Value::String(s)) => s.trim().parse().ok(),
        _ => None,
    }
}

/// A yes or no the view may leave out: `default` when it does.
fn truthy_or(v: Option<&Value>, default: bool) -> bool {
    match v {
        None | Some(Value::Null) => default,
        some => truthy(some),
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

/// The kinds of a page's view the screen draws (UI_PARITY.md); any other
/// says `[ui:kind is not drawn on the screen]` in its place, its content left
/// out (UI-7). An option is its select's, or a menu's drawn as a link.
const DRAWN: &[&str] = &[
    "page",
    "window",
    "vbox",
    "scrollbox",
    "form",
    "cardbody",
    "cardfooter",
    "tab",
    "list",
    "item",
    "hbox",
    "grid",
    "section",
    "header",
    "cardheader",
    "formitem",
    "panel",
    "card",
    "text",
    "footer",
    "stream",
    "alert",
    "badge",
    "link",
    "image",
    "rule",
    "spacer",
    "progress",
    "button",
    "input",
    "checkbox",
    "switch",
    "radio",
    "select",
    "option",
    "tabpanel",
    "table",
    "column",
    "avatar",
    "chart",
    "skeleton",
    "loading",
    "treeitem",
    // UI-21: the tags with a state of their own
    "accordion",
    "modal",
    "toast",
    "tooltip",
    "dropdown",
    "carousel",
    "stepper",
    "step",
    "calendar",
];

fn not_drawn(kind: &str) -> Option<String> {
    (!DRAWN.contains(&kind)).then(|| format!("[ui:{} is not drawn on the screen]", kind))
}

/// A tree's row's depth (UI-21).
fn depth_of(p: &Map<String, Value>) -> usize {
    p.get("depth").and_then(Value::as_u64).unwrap_or(0) as usize
}

/// A pie or a doughnut says each bar's share in percent; the others its value.
fn is_share(p: &Map<String, Value>) -> bool {
    matches!(text_of(p.get("chart_type")).as_str(), "pie" | "doughnut")
}

fn shown(bar: &Value, share: bool) -> String {
    if share {
        let percent = bar.get("percent").and_then(Value::as_f64).unwrap_or(0.0);
        if percent.fract() == 0.0 {
            format!("{}%", percent as i64)
        } else {
            format!("{:.1}%", percent)
        }
    } else {
        text_of(bar.get("shown"))
    }
}

/// A chart's colour: a design token's name in the window's palette, or the
/// page's own `#rrggbb`.
fn chart_color(name: &str) -> u32 {
    match name {
        "primary" | "info" => LINK,
        "success" => OK_TEXT,
        "warning" => HONEY,
        "danger" => DANGER_BG,
        "secondary" => MUTED,
        _ => name
            .strip_prefix('#')
            .filter(|h| h.len() == 6)
            .and_then(|h| u32::from_str_radix(h, 16).ok())
            .map(|rgb| 0xFF00_0000 | rgb)
            .unwrap_or(LINK),
    }
}

fn cut(text: &str, width: usize) -> String {
    text.chars().take(width).collect()
}

/// The text cut to `width` cells at a ` · ` between its parts, so a help
/// line loses whole hints, never half a word.
fn cut_at_separator(text: &str, width: usize) -> String {
    if text.chars().count() <= width {
        return text.to_string();
    }
    let head = cut(text, width);
    match head.rfind(" · ") {
        Some(at) => head[..at].to_string(),
        None => head,
    }
}

// ---------------------------------------------------------------- dates (UI-21)
//
// A calendar's days are counted from 1970-01-01 in the proleptic Gregorian
// calendar (H. Hinnant's days_from_civil and civil_from_days); a month is
// counted from January of the year 0.

const MONTHS: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];
const WEEKDAYS: [&str; 7] = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/// The days from 1970-01-01 to that date (`m` 1 to 12).
fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

/// The date `days` from 1970-01-01: (year, month 1 to 12, day).
fn civil_from_days(days: i64) -> (i64, i64, i64) {
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (yoe + era * 400 + i64::from(m <= 2), m, d)
}

/// The day of the week of a day, 0 = Sunday (1970-01-01 was a Thursday).
fn weekday(days: i64) -> i64 {
    (days + 4).rem_euclid(7)
}

/// The month a day is in.
fn month_of(days: i64) -> i64 {
    let (y, m, _) = civil_from_days(days);
    y * 12 + m - 1
}

/// The first day of a month.
fn month_start(month: i64) -> i64 {
    days_from_civil(month.div_euclid(12), month.rem_euclid(12) + 1, 1)
}

fn month_len(month: i64) -> i64 {
    month_start(month + 1) - month_start(month)
}

/// "November 2026": the month's name in English, then the year.
fn month_title(month: i64) -> String {
    format!(
        "{} {}",
        MONTHS[month.rem_euclid(12) as usize],
        month.div_euclid(12)
    )
}

/// A date as YYYY-MM-DD.
fn iso_date(days: i64) -> String {
    let (y, m, d) = civil_from_days(days);
    format!("{:04}-{:02}-{:02}", y, m, d)
}

/// A YYYY-MM-DD date that exists, in days.
fn parse_date(text: &str) -> Option<i64> {
    let mut parts = text.trim().splitn(3, '-');
    let y: i64 = parts.next()?.parse().ok()?;
    let m: i64 = parts.next()?.parse().ok()?;
    let d: i64 = parts.next()?.parse().ok()?;
    let month = y * 12 + m - 1;
    ((1..=12).contains(&m) && (1..=month_len(month)).contains(&d)).then(|| days_from_civil(y, m, d))
}

/// A YYYY-MM month.
fn parse_month(text: &str) -> Option<i64> {
    let (y, m) = text.trim().split_once('-')?;
    let (y, m): (i64, i64) = (y.parse().ok()?, m.parse().ok()?);
    (1..=12).contains(&m).then_some(y * 12 + m - 1)
}

/// The ISO week of a day: the week of its Thursday, counted from the week of
/// its year's first Thursday.
fn iso_week(days: i64) -> i64 {
    let thursday = days - (weekday(days) + 6) % 7 + 3;
    let (y, _, _) = civil_from_days(thursday);
    (thursday - days_from_civil(y, 1, 1)) / 7 + 1
}

/// Today, by the machine's clock: the month a calendar shows first when the
/// view does not say.
fn today() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| (d.as_secs() / 86_400) as i64)
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
            // a page that shows its flash itself (UI-16) gets no second line of it
            flash: page
                .get("flash")
                .and_then(Value::as_str)
                .filter(|s| !s.is_empty() && !truthy(page.get("flashShown")))
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
            overlay: None,
            overlay_rows: 0,
            overlay_focus: (0, 0),
            toasts: Vec::new(),
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
        // UI-21: a tag beyond the layout set that is a composition of it says
        // which kind it is drawn as
        let kind = Some(text_of(v.get("as")))
            .filter(|k| !k.is_empty())
            .unwrap_or_else(|| text_of(v.get("type")));
        let mut props = props;
        if let Some(Value::String(t)) = props.get("text") {
            // the font has ASCII and Latin-1: a pager's arrows and gap in signs it has
            let t = t.replace('‹', "<").replace('›', ">").replace('…', "...");
            props.insert("text".into(), Value::String(t));
        }
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
            bars: v
                .get("bars")
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
        if kind == "tabpanel" {
            // UI-17: the tab `open` names opens; else the first
            let wanted = text_of(self.nodes[n].props.get("open"));
            let wanted = wanted.trim();
            self.nodes[n].tab = self
                .tab_titles(n)
                .iter()
                .position(|t| !wanted.is_empty() && t.trim() == wanted)
                .unwrap_or(0);
        }
        self.start_state(n);
        n
    }

    /// UI-21: what a tag with a state of its own starts with, as the page
    /// is shown: an accordion's first fold open, a modal as `open` says, a
    /// toast shown for its `duration`, a carousel's and a stepper's
    /// `current`, a stepper's steps done before it and its Back and Next.
    fn start_state(&mut self, n: usize) {
        let kind = self.nodes[n].kind.clone();
        match kind.as_str() {
            "accordion" => {
                let first = self.nodes[n]
                    .children
                    .iter()
                    .copied()
                    .find(|&c| self.nodes[c].kind == "section");
                if let Some(first) = first {
                    self.nodes[first].open = true;
                }
            }
            "modal" => self.nodes[n].open = truthy(self.nodes[n].props.get("open")),
            "toast" => {
                let ms = number(self.nodes[n].props.get("duration")).unwrap_or(3000.0);
                self.nodes[n].open = true;
                self.nodes[n].ticks = if ms > 0.0 {
                    ((ms * TICK_RATE as f64 / 1000.0).round() as u64).max(1)
                } else {
                    0
                };
            }
            "carousel" | "stepper" => {
                let parts = self.moving_parts(n);
                let current = number(self.nodes[n].props.get("current"))
                    .unwrap_or(0.0)
                    .max(0.0) as usize;
                let current = current.min(parts.len().saturating_sub(1));
                self.nodes[n].tab = current;
                if kind == "stepper" {
                    // a step is done when it says so, else when it is behind the current one
                    for (i, &s) in parts.iter().enumerate() {
                        let said = self.nodes[s]
                            .props
                            .get("completed")
                            .filter(|v| !v.is_null());
                        self.nodes[s].checked = said.map_or(i < current, |v| truthy(Some(v)));
                    }
                    for (text, step) in [("Back", -1), ("Next", 1)] {
                        let c = self.nodes.len();
                        let mut props = Map::new();
                        props.insert("text".into(), json!(text));
                        props.insert("moves".into(), json!(step));
                        self.nodes.push(Node {
                            kind: "button".into(),
                            props,
                            parent: Some(n),
                            ..Node::default()
                        });
                        self.nodes[n].controls.push(c);
                    }
                }
            }
            "calendar" => {
                // the month the view says (the value's, else today's); the cursor
                // on the day picked when it is in it, else on the month's first
                let p = &self.nodes[n].props;
                let picked = parse_date(&text_of(p.get("value")));
                let month = parse_month(&text_of(p.get("month")))
                    .or(picked.map(month_of))
                    .unwrap_or_else(|| month_of(today()));
                let node = &mut self.nodes[n];
                node.value = picked.map(iso_date).unwrap_or_default();
                node.day = picked
                    .filter(|&d| month_of(d) == month)
                    .unwrap_or_else(|| month_start(month));
            }
            _ => {}
        }
    }

    /// UI-21: whether a calendar's day can be picked: not before `min`, not
    /// after `max`, not one of `disabled_dates`, not on one of
    /// `disabled_days` (0 = Sunday).
    fn pickable(&self, n: usize, day: i64) -> bool {
        let p = &self.nodes[n].props;
        let bound = |key: &str| parse_date(&text_of(p.get(key)));
        let list = |key: &str| p.get(key).and_then(Value::as_array).cloned();
        bound("min").map_or(true, |min| day >= min)
            && bound("max").map_or(true, |max| day <= max)
            && !list("disabled_dates")
                .unwrap_or_default()
                .iter()
                .any(|d| parse_date(&text_of(Some(d))) == Some(day))
            && !list("disabled_days")
                .unwrap_or_default()
                .iter()
                .any(|d| number(Some(d)).map(|w| (w as i64).rem_euclid(7)) == Some(weekday(day)))
    }

    /// A calendar's first day of the week (0 = Sunday), whether it shows the
    /// weeks' numbers, and the cells of its grid: a day takes two and one
    /// between (the week's number too, before the days).
    fn calendar_shape(&self, n: usize) -> (i64, bool, usize) {
        let p = &self.nodes[n].props;
        let first = number(p.get("first_day")).unwrap_or(0.0) as i64;
        let weeks = truthy(p.get("week_numbers"));
        (first.rem_euclid(7), weeks, 20 + if weeks { 3 } else { 0 })
    }

    /// The month a calendar shows, the column of its first day (from the
    /// first day of the week) and its rows of weeks.
    fn calendar_month(&self, n: usize) -> (i64, i64, usize) {
        let month = month_of(self.nodes[n].day);
        let (first_day, _, _) = self.calendar_shape(n);
        let lead = (weekday(month_start(month)) - first_day).rem_euclid(7);
        let weeks = (lead + month_len(month) + 6) / 7;
        (month, lead, weeks as usize)
    }

    /// A carousel's slides (each child is one), a stepper's steps.
    fn moving_parts(&self, n: usize) -> Vec<usize> {
        let node = &self.nodes[n];
        if node.kind == "stepper" {
            node.children
                .iter()
                .copied()
                .filter(|&c| self.nodes[c].kind == "step")
                .collect()
        } else {
            node.children.clone()
        }
    }

    /// Whether `n` is a fold: a section of an accordion (UI-21).
    fn is_fold(&self, n: usize) -> bool {
        let node = &self.nodes[n];
        node.kind == "section"
            && node
                .parent
                .is_some_and(|p| self.nodes[p].kind == "accordion")
    }

    /// The children that are shown, and laid out: a closed fold's, a
    /// closed dropdown's, a modal's that is not over the page and a
    /// toast's are not; a carousel shows its slide, a stepper its step and
    /// its Back and Next (UI-21).
    fn shown_children(&self, n: usize) -> Vec<usize> {
        let node = &self.nodes[n];
        match node.kind.as_str() {
            "section" if self.is_fold(n) && !node.open => Vec::new(),
            "modal" if self.overlay != Some(n) => Vec::new(),
            "dropdown" if !node.open => Vec::new(),
            "toast" => Vec::new(),
            "carousel" => node.children.get(node.tab).copied().into_iter().collect(),
            "stepper" => self
                .moving_parts(n)
                .get(node.tab)
                .copied()
                .into_iter()
                .chain(node.controls.iter().copied())
                .collect(),
            _ => node.children.clone(),
        }
    }

    /// The tooltip whose tip shows: the one that has the focus, or what
    /// has it inside (UI-21).
    fn tooltip_of_focus(&self) -> Option<usize> {
        let mut cur = self.focused();
        while let Some(n) = cur {
            if self.nodes[n].kind == "tooltip" {
                return Some(n);
            }
            cur = self.nodes[n].parent;
        }
        None
    }

    /// UI-21: what a calendar shows, as text: its title, the weekdays, a
    /// line a week (its number first when it shows them).
    fn calendar_texts(&self, n: usize) -> Vec<String> {
        let (first_day, numbered, _) = self.calendar_shape(n);
        let (month, lead, weeks) = self.calendar_month(n);
        let start = month_start(month);
        let mut out = vec![
            month_title(month),
            (0..7)
                .map(|i| WEEKDAYS[((first_day + i) % 7) as usize])
                .collect::<Vec<_>>()
                .join(" "),
        ];
        for week in 0..weeks as i64 {
            let mut line = String::new();
            if numbered {
                line.push_str(&format!("{:>2} ", iso_week(start - lead + 7 * week)));
            }
            let days: Vec<String> = (0..7)
                .map(|col| {
                    let d = 7 * week + col - lead + 1;
                    if (1..=month_len(month)).contains(&d) {
                        format!("{:>2}", d)
                    } else {
                        "  ".into()
                    }
                })
                .collect();
            line.push_str(&days.join(" "));
            out.push(line.trim().to_string());
        }
        out
    }

    /// What a tooltip holds, as text: the label a driver finds it by.
    fn content_text(&self, n: usize) -> String {
        let mut texts = Vec::new();
        for &c in &self.nodes[n].children {
            self.collect_texts(c, &mut texts);
        }
        texts.join(" ")
    }

    /// A tabpanel's tab titles, in order.
    fn tab_titles(&self, n: usize) -> Vec<String> {
        self.nodes[n]
            .children
            .iter()
            .filter(|&&c| self.nodes[c].kind == "tab")
            .map(|&c| text_of(self.nodes[c].props.get("title")))
            .collect()
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
        self.toasts.clear();
        self.overlay = None;
        self.overlay_rows = 0;
        let h = self.place(0, 0, 0, self.cols);
        self.content_height = h;
        if self.overlay.is_some() {
            // UI-21: an open modal has the keyboard
            let (from, to) = self.overlay_focus;
            self.focusables = self.focusables[from..to].to_vec();
        }
        let max_rows = ((self.canvas.1 as usize).saturating_sub(2 * margin + CHROME_H as usize)
            / ch)
            .max(MIN_ROWS);
        self.rows = (h.max(self.overlay_rows) + self.content_top()).clamp(MIN_ROWS, max_rows);
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
            | "tabpanel" | "calendar" => true,
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
            "rule" if truthy(p.get("vertical")) => 1,
            "avatar" => text_of(p.get("initials")).chars().count() + 4,
            "loading" => text.chars().count() + 4,
            "treeitem" => 3 * depth_of(p) + text.chars().count(),
            // UI-21: a dropdown is its button, and its menu when open; a
            // tooltip what it holds; a modal and a toast are over the page
            "dropdown" => {
                let options = if node.open {
                    node.children
                        .iter()
                        .map(|&c| self.natural_width(c, w) + 2)
                        .max()
                        .unwrap_or(0)
                } else {
                    0
                };
                (self.dropdown_label(n).chars().count() + 4).max(options)
            }
            "tooltip" => self.content_width(n, w),
            "modal" | "toast" => 1,
            "calendar" => self.calendar_shape(n).2,
            _ => w,
        };
        width.min(w).max(1)
    }

    /// The widest of what `n` holds, beside others, at most `w`.
    fn content_width(&self, n: usize, w: usize) -> usize {
        self.nodes[n]
            .children
            .iter()
            .map(|&c| self.natural_width(c, w))
            .max()
            .unwrap_or(1)
            .min(w)
    }

    fn dropdown_label(&self, n: usize) -> String {
        let label = text_of(self.nodes[n].props.get("label"));
        if label.is_empty() {
            "Menu".into()
        } else {
            label
        }
    }

    /// What reacts among the tags with a state of their own (UI-21): a
    /// fold's header, a dropdown's button, a carousel, a dismissible toast
    /// (a modal's close control and a tooltip are placed with their own).
    fn reacts(&self, n: usize) -> bool {
        let node = &self.nodes[n];
        match node.kind.as_str() {
            "dropdown" | "carousel" => true,
            "section" => self.is_fold(n),
            "toast" => node.open && truthy_or(node.props.get("dismissible"), true),
            _ => false,
        }
    }

    /// Lays `n` out at (x, y) in `w` cells; its height in rows.
    fn place(&mut self, n: usize, x: usize, y: usize, w: usize) -> usize {
        let kind = self.nodes[n].kind.clone();
        let props = self.nodes[n].props.clone();
        let children = self.nodes[n].children.clone();
        let goes = kind == "treeitem"
            && (self.nodes[n].event.is_some() || !text_of(props.get("to")).is_empty());
        if !self.in_table && (Self::is_focusable(&kind, &props) || goes || self.reacts(n)) {
            self.focusables.push(n);
        }
        let h = match kind.as_str() {
            "page" => self.stack(&children, x + 1, y, w.saturating_sub(2), 0),
            // UI-21: the tags with a state of their own
            "accordion" | "step" => self.stack(&children, x, y, w, 0),
            "section" if self.is_fold(n) => {
                // a header that opens and closes the fold; its content under it when open
                self.nodes[n].lines = vec![cut(&text_of(props.get("title")), w.saturating_sub(3))];
                if self.nodes[n].open {
                    1 + self.stack(&children, x + 2, y + 1, w.saturating_sub(2), 0)
                } else {
                    1
                }
            }
            "modal" => {
                if self.nodes[n].open && self.overlay.is_none() {
                    self.place_modal(n);
                    return 0;
                }
                0
            }
            "toast" => {
                if self.nodes[n].open {
                    self.place_toast(n);
                }
                0
            }
            "tooltip" => {
                let before = self.focusables.len();
                let h = self.stack(&children, x, y, w, 0);
                if self.focusables.len() == before && !self.in_table {
                    // nothing inside reacts: the tooltip takes the focus itself
                    self.focusables.push(n);
                }
                h
            }
            "dropdown" => {
                if self.nodes[n].open {
                    1 + self.stack(&children, x + 1, y + 1, w.saturating_sub(2), 0)
                } else {
                    1
                }
            }
            "carousel" => {
                // the slide shown, then its controls: the arrows and where it is
                let slide = children.get(self.nodes[n].tab).copied();
                1 + slide.map_or(0, |s| self.place(s, x, y, w))
            }
            "stepper" => self.place_stepper(n, x, y, w),
            "calendar" => {
                // its title with the month's keys, the weekdays, a row a week,
                // then an error the action gave it (UI-9)
                let error = text_of(props.get("error"));
                self.nodes[n].lines = if error.is_empty() {
                    Vec::new()
                } else {
                    wrap(&error, w)
                };
                2 + self.calendar_month(n).2 + self.nodes[n].lines.len()
            }
            "item" if props.contains_key("marker") => {
                // an ordered list's number before the item (UI-21)
                let m = text_of(props.get("marker")).chars().count() + 1;
                self.stack(&children, x + m, y, w.saturating_sub(m), 0)
            }
            "window" | "vbox" | "scrollbox" | "form" | "cardbody" | "cardfooter" | "tab"
            | "list" | "item" => self.stack(&children, x, y, w, Self::gap_rows(&props)),
            "chart" => {
                usize::from(!text_of(props.get("title")).is_empty())
                    + self.nodes[n].bars.len().max(1)
            }
            "skeleton" => match text_of(props.get("variant")).as_str() {
                "circle" => 1,
                "text" | "" => text_of(props.get("lines"))
                    .parse::<usize>()
                    .unwrap_or(1)
                    .max(1),
                _ => 3,
            },
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
                // a quote is drawn after a bar (UI-21)
                let lines = wrap(
                    &text,
                    w.saturating_sub(if truthy(props.get("quote")) { 2 } else { 0 }),
                );
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
        let height = cy + line_h.max(1) - y;
        for &c in children {
            // a dividedbox's divider goes down as far as its panes (UI-21)
            if self.nodes[c].kind == "rule" && truthy(self.nodes[c].props.get("vertical")) {
                self.nodes[c].rect.h = height - (self.nodes[c].rect.y - y);
            }
        }
        height
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

    /// UI-21: an open modal is laid out in a box of its own over the page,
    /// in the window's middle columns (a dialog's width at most), from the
    /// rows of the overlay: a title bar (its close control in it, first in
    /// the focus when it is `closable`), its content, a row below.
    fn place_modal(&mut self, n: usize) {
        let children = self.nodes[n].children.clone();
        let w = self.cols.saturating_sub(6).clamp(12, 64).min(self.cols);
        let x = (self.cols - w) / 2;
        self.overlay = Some(n);
        let from = self.focusables.len();
        if truthy_or(self.nodes[n].props.get("closable"), true) {
            self.focusables.push(n);
        }
        let inner = self.stack(&children, x + 1, OVERLAY + 1, w.saturating_sub(2), 0);
        self.overlay_focus = (from, self.focusables.len());
        self.overlay_rows = inner + 2;
        self.nodes[n].rect = Rect {
            x,
            y: OVERLAY,
            w,
            h: inner + 2,
        };
    }

    /// UI-21: a toast takes no room in the page: its title and its message
    /// (wrapped to a small box) are drawn over it, where `position` says.
    fn place_toast(&mut self, n: usize) {
        let p = &self.nodes[n].props;
        let (title, message) = (text_of(p.get("title")), text_of(p.get("message")));
        let close = if truthy_or(p.get("dismissible"), true) {
            2
        } else {
            0
        };
        let room = self.cols.saturating_sub(4).clamp(8, 36) - close;
        let mut lines = Vec::new();
        if !title.is_empty() {
            lines.push(cut(&title, room));
        }
        if !message.is_empty() {
            lines.extend(wrap(&message, room));
        }
        self.nodes[n].lines = lines;
        self.toasts.push(n);
    }

    /// UI-21: a stepper is its steps' titles in a row (one a row when
    /// `vertical`), the current step's description, error and whether it
    /// is optional, its content, and Back and Next on a row of their own.
    fn place_stepper(&mut self, n: usize, x: usize, y: usize, w: usize) -> usize {
        let steps = self.moving_parts(n);
        let current = self.nodes[n].tab.min(steps.len().saturating_sub(1));
        self.nodes[n].tab = current;
        let header = self.step_places(n, w);
        let mut cy = y + header.iter().map(|&(row, _)| row + 1).max().unwrap_or(0);
        if let Some(&s) = steps.get(current) {
            cy += self.step_notes(s, w).len();
            cy += self.place(s, x, cy, w);
        }
        let mut cx = x;
        // Back is muted on the first step, where it goes nowhere
        let controls = self.nodes[n].controls.clone();
        if let Some(&back) = controls.first() {
            let variant = if current == 0 { "muted" } else { "" };
            self.nodes[back]
                .props
                .insert("variant".into(), json!(variant));
        }
        if let Some(&next) = controls.get(1) {
            self.nodes[next]
                .props
                .insert("variant".into(), json!("primary"));
        }
        for c in controls {
            let width = self.natural_width(c, w);
            self.place(c, cx, cy, width);
            cx += width + 1;
        }
        cy + 1 - y
    }

    /// Where each step's title is in a stepper's header: (row, column).
    /// A step takes its number's box, a cell, its title; a line of two
    /// cells goes to the next, a cell on each side.
    fn step_places(&self, n: usize, w: usize) -> Vec<(usize, usize)> {
        let vertical = text_of(self.nodes[n].props.get("orientation")) == "vertical";
        let (mut row, mut col) = (0, 0);
        let mut out = Vec::new();
        for (i, s) in self.moving_parts(n).into_iter().enumerate() {
            let width = 3 + text_of(self.nodes[s].props.get("title")).chars().count();
            if i > 0 && (vertical || col + width > w) {
                row += 1;
                col = 0;
            }
            out.push((row, col));
            col += width + 4;
        }
        out
    }

    /// What the current step says under the header: its description, its
    /// error, and that it is optional; each with whether it is the error.
    fn step_notes(&self, s: usize, w: usize) -> Vec<(String, bool)> {
        let p = &self.nodes[s].props;
        let mut out: Vec<(String, bool)> = Vec::new();
        for (key, error) in [("description", false), ("error", true)] {
            let t = text_of(p.get(key));
            if !t.trim().is_empty() {
                out.extend(wrap(&t, w).into_iter().map(|l| (l, error)));
            }
        }
        if truthy(p.get("optional")) {
            out.push(("Optional".into(), false));
        }
        out
    }

    // ---------------------------------------------------------------- focus

    fn focus_first(&mut self) {
        // the first field, else the first focusable that stays (a toast goes, UI-21)
        self.focus = self
            .focusables
            .iter()
            .position(|&n| self.nodes[n].kind != "toast")
            .unwrap_or(0);
        if let Some(i) = self.focusables.iter().position(|&n| {
            matches!(
                self.nodes[n].kind.as_str(),
                "input" | "checkbox" | "switch" | "radio" | "select" | "calendar"
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
                .or(p.get("title"))
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
        if r.y >= OVERLAY || self.nodes[n].kind == "toast" {
            return; // over the page: always in view (UI-21)
        }
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
                "button" | "link" | "treeitem" | "checkbox" | "switch" | "tabpanel" | "section"
                | "modal" | "toast" | "tooltip" | "dropdown" | "carousel" => true,
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
                // UI-21: a calendar is a date field: the day picked, or nothing picked
                "calendar" if !bind.is_empty() => {
                    fields.insert(bind, Value::String(node.value.clone()));
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
            "link" | "treeitem" if node.event.is_some() => {
                // UI-21: a menu's option, a tree's row: a link that posts its action
                let event = node.event.clone().unwrap_or(json!({}));
                let action = text_of(event.get("action"));
                let fields = event.get("fields").cloned().unwrap_or(json!({}));
                self.events.push(
                    json!({"event": "click", "id": node.id, "action": action, "fields": fields}),
                );
            }
            "link" | "treeitem" => {
                let to = text_of(node.props.get("to"));
                self.events
                    .push(json!({"event": "navigate", "id": node.id, "to": to}));
            }
            "button" if node.props.contains_key("moves") => {
                // UI-21: a stepper's Back and Next move it, here
                if let Some(stepper) = node.parent {
                    let forward = number(node.props.get("moves")).unwrap_or(0.0) > 0.0;
                    self.move_stepper(stepper, forward);
                }
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
                // Esc closes the innermost thing open (UI-21), and with nothing open, the page
                if !self.close_innermost() {
                    self.events.push(json!({"event": "close"}));
                }
                return true;
            }
            Key::F5 => {
                self.events.push(json!({"event": "reload"}));
                return true;
            }
            // a calendar with the focus takes PgUp and PgDn for its months (UI-21)
            Key::PageDown | Key::PageUp
                if self
                    .focused()
                    .is_some_and(|n| self.nodes[n].kind == "calendar") => {}
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
            "button" | "link" | "treeitem" => match key {
                Key::Enter | Key::Space => {
                    self.activate(n);
                    // an option of a dropdown: the menu shuts on it
                    if let Some(d) = self.nodes[n]
                        .parent
                        .filter(|&d| self.nodes[d].kind == "dropdown" && self.nodes[d].open)
                    {
                        self.nodes[d].open = false;
                        self.relayout();
                        self.refocus(d);
                    }
                    true
                }
                _ => false,
            },
            // UI-21: a fold's header and a dropdown's button open and close
            "section" | "dropdown" => match key {
                Key::Enter | Key::Space => {
                    self.nodes[n].open = !self.nodes[n].open;
                    self.relayout();
                    true
                }
                _ => false,
            },
            "carousel" => match key {
                Key::Left | Key::Right => {
                    self.move_carousel(n, key == Key::Right);
                    self.relayout();
                    true
                }
                _ => false,
            },
            "modal" => match key {
                Key::Enter | Key::Space => {
                    self.close_modal(n);
                    true
                }
                _ => false,
            },
            "toast" => match key {
                Key::Enter | Key::Space => {
                    self.nodes[n].open = false;
                    self.relayout();
                    true
                }
                _ => false,
            },
            "table" => self.key_in_table(n, key),
            "calendar" => self.key_in_calendar(n, key),
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

    /// The page flows again after something opened, closed or moved
    /// (UI-21): the focus stays on what had it, or, when that is gone (a
    /// toast), on what came after it.
    fn relayout(&mut self) {
        let before = self.focused();
        let index = self.focus;
        self.layout();
        self.focus = match before.and_then(|n| self.focusables.iter().position(|&m| m == n)) {
            Some(i) => i,
            None => index.min(self.focusables.len().saturating_sub(1)),
        };
        self.reveal();
    }

    /// Esc on what is open (UI-21): the dropdown the focus is in, then the
    /// modal over the page (when it can be closed), then any dropdown open.
    /// Whether something closed.
    fn close_innermost(&mut self) -> bool {
        let mut cur = self.focused();
        while let Some(n) = cur {
            if self.nodes[n].kind == "dropdown" && self.nodes[n].open {
                self.nodes[n].open = false;
                self.relayout();
                self.refocus(n);
                return true;
            }
            cur = self.nodes[n].parent;
        }
        if let Some(m) = self.overlay {
            if truthy_or(self.nodes[m].props.get("closable"), true) {
                self.close_modal(m);
                return true;
            }
        }
        let open: Vec<usize> = (0..self.nodes.len())
            .filter(|&n| self.nodes[n].kind == "dropdown" && self.nodes[n].open)
            .collect();
        for &d in &open {
            self.nodes[d].open = false;
        }
        if !open.is_empty() {
            self.relayout();
        }
        !open.is_empty()
    }

    /// A modal closed: its content is not shown until the page is shown
    /// again, and the page has the keyboard back (UI-21).
    fn close_modal(&mut self, m: usize) {
        self.nodes[m].open = false;
        self.layout();
        self.focus_first();
    }

    /// The carousel's next slide or the one before, round when it loops
    /// (the page is to flow again).
    fn move_carousel(&mut self, n: usize, forward: bool) {
        let count = self.moving_parts(n).len();
        let current = self.nodes[n].tab;
        let loops = truthy_or(self.nodes[n].props.get("loop"), true);
        let next = if forward {
            if current + 1 < count {
                current + 1
            } else if loops {
                0
            } else {
                current
            }
        } else if current > 0 {
            current - 1
        } else if loops {
            count.saturating_sub(1)
        } else {
            current
        };
        self.nodes[n].tab = next;
        self.nodes[n].ticks = 0;
    }

    /// Next: this step done, the one after shown; Back: the one before.
    fn move_stepper(&mut self, n: usize, forward: bool) {
        let steps = self.moving_parts(n);
        let current = self.nodes[n].tab;
        if forward {
            if let Some(&s) = steps.get(current) {
                self.nodes[s].checked = true;
            }
            if current + 1 < steps.len() {
                self.nodes[n].tab = current + 1;
            }
        } else {
            self.nodes[n].tab = current.saturating_sub(1);
        }
        self.relayout();
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

    /// UI-21: a calendar's keys. The arrows move its cursor a day or a week,
    /// into the month before or after when they go past its ends; Home and
    /// End to its first and last day; PgUp and PgDn show the month before
    /// and after (the cursor on the same day, or the month's last); Enter or
    /// Space picks the day under the cursor, when it can be picked: the
    /// calendar's value, which its form sends under `bind`.
    fn key_in_calendar(&mut self, n: usize, key: Key) -> bool {
        let day = self.nodes[n].day;
        let month = month_of(day);
        let into = |m: i64| month_start(m) + (day - month_start(month)).min(month_len(m) - 1);
        let to = match key {
            Key::Left => day - 1,
            Key::Right => day + 1,
            Key::Up => day - 7,
            Key::Down => day + 7,
            Key::Home => month_start(month),
            Key::End => month_start(month) + month_len(month) - 1,
            Key::PageUp => into(month - 1),
            Key::PageDown => into(month + 1),
            Key::Enter | Key::Space => {
                if self.pickable(n, day) {
                    self.nodes[n].value = iso_date(day);
                }
                return true;
            }
            _ => return false,
        };
        self.nodes[n].day = to;
        if month_of(to) != month {
            // another month: its weeks may be more or fewer
            self.relayout();
        }
        true
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
        if self.tick_states() {
            return true;
        }
        tick % 30 == 0
            && self
                .focused()
                .is_some_and(|n| self.nodes[n].kind == "input")
    }

    /// UI-21: a toast goes when its duration has passed; a carousel that
    /// plays by itself moves every `interval` (not while it has the focus).
    /// Whether the page changed.
    fn tick_states(&mut self) -> bool {
        let focused = self.focused();
        let mut changed = false;
        for n in 0..self.nodes.len() {
            let node = &mut self.nodes[n];
            match node.kind.as_str() {
                "toast" if node.open && node.ticks > 0 => {
                    node.ticks -= 1;
                    if node.ticks == 0 {
                        node.open = false;
                        changed = true;
                    }
                }
                "carousel" if truthy(node.props.get("auto_play")) && focused != Some(n) => {
                    let ms = number(node.props.get("interval")).unwrap_or(5000.0);
                    let every = ((ms * TICK_RATE as f64 / 1000.0).round() as u64).max(1);
                    node.ticks += 1;
                    if node.ticks >= every {
                        self.move_carousel(n, true);
                        changed = true;
                    }
                }
                _ => {}
            }
        }
        if changed {
            self.relayout();
        }
        changed
    }

    /// The events since the last take.
    pub fn take_events(&mut self) -> Vec<Value> {
        std::mem::take(&mut self.events)
    }

    // ---------------------------------------------------------------- what it shows

    /// The keys that apply to what has the focus.
    pub fn help(&self) -> String {
        let Some(n) = self.focused() else {
            return "Tab moves · Esc closes".into();
        };
        match self.nodes[n].kind.as_str() {
            "input" => "type · arrows · Enter sends · Esc closes".into(),
            "checkbox" | "switch" => "Space marks · Enter sends · Tab moves".into(),
            "radio" | "select" => "arrows choose · Enter sends · Tab moves".into(),
            "button" => "Enter presses · Tab moves · Esc closes".into(),
            "link" => "Enter opens · Tab moves · Esc closes".into(),
            "table" => "arrows: row, action · Enter presses · Tab leaves".into(),
            "tabpanel" => "arrows change the tab · Tab enters · Esc closes".into(),
            // UI-21
            "section" if self.nodes[n].open => "Enter folds · Tab moves · Esc closes".into(),
            "section" => "Enter unfolds · Tab moves · Esc closes".into(),
            "dropdown" if self.nodes[n].open => "Down: the options · Enter or Esc shuts".into(),
            "dropdown" => "Enter opens · Tab moves · Esc closes".into(),
            "carousel" => "arrows change the slide · Tab moves · Esc closes".into(),
            "modal" => "Enter or Esc closes it · Tab moves".into(),
            "toast" => "Enter dismisses · Tab moves · Esc closes".into(),
            "tooltip" => "Tab moves · Esc closes".into(),
            "calendar" => "arrows: day · PgUp PgDn: month · Enter picks · Tab moves".into(),
            _ => "Tab moves · Enter chooses · Esc closes".into(),
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
        if let Some(message) = not_drawn(&node.kind) {
            out.push(message);
            return;
        }
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
            "treeitem" | "loading" => out.push(text_of(p.get("text"))),
            "avatar" => out.push(text_of(p.get("initials"))),
            "chart" => {
                let title = text_of(p.get("title"));
                if !title.is_empty() {
                    out.push(title);
                }
                let share = is_share(p);
                for bar in &node.bars {
                    out.push(text_of(bar.get("label")));
                    out.push(shown(bar, share));
                }
            }
            "radio" | "select" => out.extend(self.options(n).into_iter().map(|(l, _)| l)),
            // UI-21: what shows of a tag with a state of its own, as it is now
            "modal" if self.overlay == Some(n) => {
                let t = text_of(p.get("title"));
                if !t.is_empty() {
                    out.push(t);
                }
            }
            "toast" if node.open => out.extend(node.lines.iter().cloned()),
            "tooltip" if self.tooltip_of_focus() == Some(n) => out.push(text_of(p.get("text"))),
            "dropdown" => out.push(self.dropdown_label(n)),
            "carousel" => out.push(format!(
                "{}/{}",
                node.tab + 1,
                self.moving_parts(n).len().max(1)
            )),
            "stepper" => {
                let steps = self.moving_parts(n);
                for &s in &steps {
                    out.push(text_of(self.nodes[s].props.get("title")));
                }
                if let Some(&s) = steps.get(node.tab) {
                    out.extend(
                        self.step_notes(s, node.rect.w.max(1))
                            .into_iter()
                            .map(|(l, _)| l),
                    );
                }
            }
            "image" => out.push(format!("[{}]", text_of(p.get("alt")))),
            "calendar" => out.extend(self.calendar_texts(n)),
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
        for c in self.shown_children(n) {
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
                    "tabpanel" => {
                        v["tab"] = json!(node.tab);
                        v["tabs"] = json!(self.tab_titles(n));
                    }
                    "link" => v["to"] = json!(text_of(p.get("to"))),
                    // UI-21: what a driver needs of a tag with a state of its own
                    "section" | "dropdown" | "modal" | "toast" => v["open"] = json!(node.open),
                    "tooltip" => {
                        v["label"] = json!(self.content_text(n));
                        v["tip"] = json!(text_of(p.get("text")));
                    }
                    "carousel" => {
                        v["slide"] = json!(node.tab);
                        v["slides"] = json!(self.moving_parts(n).len());
                    }
                    "button" if p.contains_key("moves") => {
                        let stepper = node.parent.unwrap_or(0);
                        v["moves"] = json!("stepper");
                        v["step"] = json!(self.nodes[stepper].tab);
                        v["steps"] = json!(self.moving_parts(stepper).len());
                    }
                    "calendar" => {
                        // the month shown (YYYY-MM), the day picked, the cursor's day
                        let month = month_of(node.day);
                        v["value"] = json!(node.value);
                        v["month"] = json!(format!(
                            "{:04}-{:02}",
                            month.div_euclid(12),
                            month.rem_euclid(12) + 1
                        ));
                        v["title"] = json!(month_title(month));
                        v["cursor"] = json!(iso_date(node.day));
                    }
                    _ => {}
                }
                if node.kind == "toast" && v["label"].is_null() {
                    v["label"] = json!(text_of(p.get("message")));
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

    /// The page as a window (the world dims the scene under it): a shadow,
    /// a frame with a bevel, the title bar with the Esc key, the flash,
    /// the content from the scroll, a scrollbar when it is longer than
    /// the window, the status bar with the keys that apply. Drawn in the
    /// band's own pixels (at the fine level the canvas has twice the
    /// scene's, and the page twice the cells), so the font is never a
    /// block.
    pub fn draw(&self, b: &mut Band, font: &Font, tick: u64, offers: usize) {
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let f = self.frame;
        let (x, y, w, h) = (f.x as i32, f.y as i32, f.w as u32, f.h as u32);
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
        // UI-21: over the content, the modal open, the toasts, the tip of
        // what has the focus
        if let Some(m) = self.overlay {
            self.draw_modal(m, b, font, focused, blink);
        }
        self.draw_toasts(b, font, focused);
        self.draw_tip(b, font);
        // the status bar: the keys that apply, raised; at its right, the
        // offers that wait for F1
        let sy = y + h as i32 - 1 - STATUS_H;
        b.fill_rect(x + 1, sy - 1, w - 2, 1, LIGHT);
        b.fill_rect(x + 1, sy, w - 2, STATUS_H as u32, MID);
        let mut help_cols = self.cols;
        if offers > 0 {
            let tag = offers_tag(offers);
            let tw = font.width_of(&tag) as i32;
            b.text(font, &tag, x + w as i32 - 5 - tw, sy + 1, HONEY);
            help_cols = self.cols.saturating_sub(tag.chars().count() + 2);
        }
        b.text(
            font,
            &cut_at_separator(&self.help(), help_cols),
            x + 5,
            sy + 1,
            TEXT,
        );
    }

    /// A row of the content on the screen, or None when scrolled out.
    fn row_y(&self, row: usize, ch: i32) -> Option<i32> {
        if row >= OVERLAY {
            // UI-21: the modal's rows, in its box in the middle of the content
            let (at, rows) = (row - OVERLAY, self.content_rows());
            if at >= rows {
                return None;
            }
            let top = rows.saturating_sub(self.overlay_rows) / 2;
            return Some(self.oy + (self.content_top() + top + at) as i32 * ch);
        }
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
            "item" if p.contains_key("marker") => {
                if let Some(y) = self.row_y(r.y, ch) {
                    b.text(font, &text_of(p.get("marker")), x, y + 1, MUTED);
                }
            }
            "page" | "window" | "vbox" | "scrollbox" | "form" | "cardbody" | "cardfooter"
            | "tab" | "list" | "item" | "hbox" | "grid" | "accordion" | "step" => {}
            // UI-21: the tags with a state of their own
            "section" if self.is_fold(n) => self.draw_fold(n, b, font, is_focus),
            "modal" | "toast" => return, // over the page, after it
            "tooltip" => {
                for c in self.shown_children(n) {
                    self.draw_node(c, b, font, focused, blink);
                }
                if is_focus {
                    // what has no box of its own takes a dotted frame for the focus, over it
                    let wpx = self.content_width(n, r.w) as i32 * cw;
                    let rows: Vec<i32> = (r.y..r.y + r.h.max(1))
                        .filter_map(|row| self.row_y(row, ch))
                        .collect();
                    if let (Some(&top), Some(&bottom)) = (rows.first(), rows.last()) {
                        dotted(b, x - 2, top, wpx + 4, bottom + ch - top, HONEY);
                    }
                }
                return;
            }
            "dropdown" => self.draw_dropdown(n, b, font, focused, is_focus),
            "carousel" => self.draw_carousel(n, b, font, is_focus),
            "stepper" => self.draw_stepper(n, b, font),
            "calendar" => {
                self.draw_calendar(n, b, font, is_focus);
                let below = 2 + self.calendar_month(n).2;
                self.draw_error(node, b, font, below);
            }
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
                    _ if truthy(p.get("muted")) || truthy(p.get("quote")) => (None, MUTED),
                    _ => (
                        None,
                        if text_of(p.get("weight")) == "bold" || p.contains_key("heading") {
                            HONEY
                        } else {
                            TEXT
                        },
                    ),
                };
                let quote = truthy(p.get("quote"));
                let code = truthy(p.get("code"));
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
                        if code {
                            // UI-21: code on a sunken ground
                            b.fill_rect(x, y, r.w as u32 * cw as u32, ch as u32, FIELD_BG);
                        }
                        if quote {
                            b.fill_rect(x + cw / 2, y, 2, ch as u32, LINE);
                        }
                        let left = x + i32::from(bg.is_some()) * 2 + if quote { 2 * cw } else { 0 };
                        b.text(font, line, left, y + 1, color);
                    }
                }
            }
            "avatar" | "chart" | "skeleton" | "loading" | "treeitem" => {
                self.draw_more(n, b, font, is_focus);
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
            "rule" if truthy(p.get("vertical")) => {
                for row in r.y..r.y + r.h.max(1) {
                    if let Some(y) = self.row_y(row, ch) {
                        b.fill_rect(x + cw / 2 - 1, y, 1, ch as u32, BLACK);
                        b.fill_rect(x + cw / 2, y, 1, ch as u32, LIGHT);
                    }
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
                    } else if variant == "muted" {
                        // a stepper's Back on its first step (UI-21)
                        (MID, LIGHT, BLACK, MUTED)
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
                if let Some(message) = not_drawn(kind) {
                    if let Some(y) = self.row_y(r.y, ch) {
                        b.text(font, &cut(&message, r.w), x, y + 1, MUTED);
                    }
                    return; // its content was not laid out
                }
            }
        }
        for c in self.shown_children(n) {
            if kind == "tabpanel"
                && self.nodes[c].kind == "tab"
                && self.nodes[c].rect == Rect::default()
            {
                continue;
            }
            self.draw_node(c, b, font, focused, blink);
        }
    }

    /// UI-21: a fold's header, raised across the fold, an arrow that says
    /// whether it is open, its title.
    fn draw_fold(&self, n: usize, b: &mut Band, font: &Font, is_focus: bool) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let r = node.rect;
        let Some(y) = self.row_y(r.y, ch) else {
            return;
        };
        let x = self.ox + r.x as i32 * cw;
        let (light, dark, color) = if is_focus {
            (HONEY, HONEY, HONEY)
        } else {
            (LIGHT, BLACK, TEXT)
        };
        bevel_out(b, x, y, r.w as u32 * cw as u32, ch as u32, MID, light, dark);
        if node.open {
            arrow(b, x + 4, y + 4, Toward::Down, HONEY);
        } else {
            arrow(b, x + 5, y + 3, Toward::Right, HONEY);
        }
        if let Some(title) = node.lines.first() {
            b.text(font, title, x + 2 * cw, y, color);
        }
    }

    /// UI-21: a dropdown's button (its label and an arrow, down when shut,
    /// up when open), and its menu under it when open: a raised box, the
    /// option with the focus on a dark strip.
    fn draw_dropdown(
        &self,
        n: usize,
        b: &mut Band,
        font: &Font,
        focused: Option<usize>,
        is_focus: bool,
    ) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let r = node.rect;
        let x = self.ox + r.x as i32 * cw;
        let label = cut(&self.dropdown_label(n), r.w.saturating_sub(4));
        let bw = font.width_of(&label) + 4 * font.cell.0;
        if let Some(y) = self.row_y(r.y, ch) {
            let (light, dark, color) = if is_focus {
                (HONEY, HONEY, HONEY)
            } else {
                (LIGHT, BLACK, TEXT)
            };
            bevel_out(b, x, y, bw, ch as u32, MID, light, dark);
            b.text(font, &label, x + cw / 2 + 1, y, color);
            let to = if node.open { Toward::Up } else { Toward::Down };
            arrow(b, x + bw as i32 - 9, y + 3, to, HONEY);
        }
        if !node.open || r.h < 2 {
            return;
        }
        let mw = (self.natural_width(n, r.w) as i32 * cw).max(bw as i32);
        let (first, last) = (r.y + 1, r.y + r.h - 1);
        for row in first..=last {
            let Some(y) = self.row_y(row, ch) else {
                continue;
            };
            b.fill_rect(x, y, mw as u32, ch as u32, MID);
            b.fill_rect(x, y, 1, ch as u32, LIGHT);
            b.fill_rect(x + mw - 1, y, 1, ch as u32, BLACK);
            if row == last {
                b.fill_rect(x, y + ch - 1, mw as u32, 1, BLACK);
            }
        }
        for &c in &node.children {
            if focused == Some(c) {
                if let Some(y) = self.row_y(self.nodes[c].rect.y, ch) {
                    b.fill_rect(x + 1, y, (mw - 2) as u32, ch as u32, FIELD_BG);
                }
            }
        }
    }

    /// UI-21: a carousel's controls under its slide: the key before, where
    /// it is ("1/2"), the key after (muted at an end it does not go round),
    /// a dot a slide.
    fn draw_carousel(&self, n: usize, b: &mut Band, font: &Font, is_focus: bool) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let (r, p) = (node.rect, &node.props);
        let Some(y) = self.row_y(r.y + r.h.saturating_sub(1), ch) else {
            return;
        };
        let count = self.moving_parts(n).len().max(1);
        let current = node.tab;
        let loops = truthy_or(p.get("loop"), true);
        let (light, dark, color) = if is_focus {
            (HONEY, HONEY, HONEY)
        } else {
            (LIGHT, BLACK, TEXT)
        };
        let mut cx = self.ox + r.x as i32 * cw;
        let key = |b: &mut Band, cx: i32, to: Toward, goes: bool| {
            bevel_out(b, cx, y, 2 * cw as u32, ch as u32, MID, light, dark);
            let ink = if goes { color } else { MUTED };
            let (ax, ay) = (cx + cw - 2, y + 2);
            arrow(b, ax, ay, to, ink);
        };
        let arrows = truthy_or(p.get("show_arrows"), true);
        if arrows {
            key(b, cx, Toward::Left, loops || current > 0);
            cx += 3 * cw;
        }
        let at = format!("{}/{}", current + 1, count);
        b.text(font, &at, cx, y, color);
        cx += (at.chars().count() as i32 + 1) * cw;
        if arrows {
            key(b, cx, Toward::Right, loops || current + 1 < count);
            cx += 3 * cw;
        }
        if truthy_or(p.get("show_indicators"), true) && count > 1 {
            for i in 0..count {
                let dot = if i == current { HONEY } else { LIGHT };
                b.fill_rect(cx + i as i32 * 6, y + 3, 4, 4, dot);
            }
        }
    }

    /// UI-21: a stepper's header, a box a step with its number (a check
    /// when it is done; honey when it is the current one, red when it has
    /// an error), its title, a line to the next; then what the current
    /// step says.
    fn draw_stepper(&self, n: usize, b: &mut Band, font: &Font) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let r = node.rect;
        let x = self.ox + r.x as i32 * cw;
        let steps = self.moving_parts(n);
        let places = self.step_places(n, r.w);
        for (i, (&s, &(row, col))) in steps.iter().zip(places.iter()).enumerate() {
            let Some(y) = self.row_y(r.y + row, ch) else {
                continue;
            };
            let step = &self.nodes[s];
            let sx = x + col as i32 * cw;
            let current = i == node.tab;
            let error = !text_of(step.props.get("error")).trim().is_empty();
            let (bg, light, dark, ink) = if current {
                (TITLE_BG2, TITLE_BG, TITLE_DARK, INK)
            } else if error {
                (ERR_BG, ERR_LIGHT, ERR_DARK, ERR_TEXT)
            } else if step.checked {
                (OK_BG, OK_LIGHT, OK_DARK, OK_TEXT)
            } else {
                (MID, LIGHT, BLACK, MUTED)
            };
            bevel_out(b, sx, y, 2 * cw as u32, ch as u32, bg, light, dark);
            if step.checked && !current && !error {
                check_mark(b, sx + 2, y + 1, ink);
            } else {
                let number = (i + 1).to_string();
                let nw = font.width_of(&number) as i32;
                b.text(font, &number, sx + cw - nw / 2, y, ink);
            }
            let title = text_of(step.props.get("title"));
            let room = r.w.saturating_sub(col + 3);
            let color = if current {
                HONEY
            } else if error {
                ERR_TEXT
            } else if step.checked {
                TEXT
            } else {
                MUTED
            };
            b.text(font, &cut(&title, room), sx + 3 * cw, y, color);
            // the line to the next step, when it is on the same row
            let len = title.chars().count() as i32;
            if places.get(i + 1).is_some_and(|&(next, _)| next == row) {
                b.fill_rect(
                    sx + (3 + len) * cw + cw / 2,
                    y + ch / 2,
                    3 * cw as u32,
                    1,
                    LINE,
                );
            }
        }
        let below = places.iter().map(|&(row, _)| row + 1).max().unwrap_or(0);
        if let Some(&s) = steps.get(node.tab) {
            for (i, (line, error)) in self.step_notes(s, r.w).iter().enumerate() {
                if let Some(y) = self.row_y(r.y + below + i, ch) {
                    b.text(font, line, x, y + 1, if *error { ERR_TEXT } else { MUTED });
                }
            }
        }
    }

    /// UI-21: a calendar, a date field shown as a month: a row with the
    /// month's title between its keys (PgUp and PgDn, lit while it has the
    /// focus), the weekdays over a rule, a row a week with each day in its
    /// column (the week's number before them when it shows them). The day
    /// picked is a honey box; the cursor, while it has the focus, a honey
    /// frame (white around the day picked); a day that cannot be picked is
    /// dim. The days of the months around are left out, as `cal` does.
    fn draw_calendar(&self, n: usize, b: &mut Band, font: &Font, is_focus: bool) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let r = node.rect;
        let x = self.ox + r.x as i32 * cw;
        let (first_day, numbered, cells) = self.calendar_shape(n);
        let (month, lead, weeks) = self.calendar_month(n);
        let gx = x + if numbered { 3 * cw } else { 0 };
        // the title between the month's keys
        if let Some(y) = self.row_y(r.y, ch) {
            let (light, dark, ink) = if is_focus {
                (HONEY, HONEY, HONEY)
            } else {
                (LIGHT, BLACK, TEXT)
            };
            for (kx, to) in [
                (x, Toward::Left),
                (x + (cells as i32 - 2) * cw, Toward::Right),
            ] {
                bevel_out(b, kx, y, 2 * cw as u32, ch as u32, MID, light, dark);
                arrow(b, kx + cw - 2, y + 2, to, ink);
            }
            let title = month_title(month);
            let tx = x + (cells as i32 * cw - font.width_of(&title) as i32) / 2;
            b.text(font, &title, tx, y, HONEY);
        }
        // the weekdays, from the first day of the week, over a rule
        if let Some(y) = self.row_y(r.y + 1, ch) {
            for i in 0..7 {
                let name = WEEKDAYS[((first_day + i) % 7) as usize];
                b.text(font, name, gx + 3 * i as i32 * cw, y, MUTED);
            }
            let wpx = (cells as i32 * cw - if numbered { 3 * cw } else { 0 }) as u32;
            b.fill_rect(gx, y + ch - 1, wpx, 1, LINE);
        }
        let start = month_start(month);
        for week in 0..weeks as i64 {
            let Some(y) = self.row_y(r.y + 2 + week as usize, ch) else {
                continue;
            };
            if numbered {
                let number = format!("{:>2}", iso_week(start - lead + 7 * week));
                b.text(font, &number, x, y, MUTED);
            }
            for col in 0..7 {
                let d = 7 * week + col - lead;
                if d < 0 || d >= month_len(month) {
                    continue;
                }
                let day = start + d;
                let dx = gx + 3 * col as i32 * cw;
                let picked = parse_date(&node.value) == Some(day);
                let cursor = is_focus && node.day == day;
                let pickable = self.pickable(n, day);
                let (bx, bw) = (dx - 2, 2 * cw as u32 + 4);
                let ink = match (picked, cursor) {
                    (true, true) => {
                        bevel_out(b, bx, y, bw, ch as u32, TITLE_BG, TEXT, TEXT);
                        INK
                    }
                    (true, false) => {
                        bevel_out(b, bx, y, bw, ch as u32, TITLE_BG2, TITLE_BG, TITLE_DARK);
                        INK
                    }
                    (false, true) => {
                        bevel_out(b, bx, y, bw, ch as u32, MID, HONEY, HONEY);
                        if pickable {
                            HONEY
                        } else {
                            LINE
                        }
                    }
                    (false, false) if pickable => TEXT,
                    (false, false) => LINE,
                };
                let text = (d + 1).to_string();
                let tx = dx + 2 * cw - font.width_of(&text) as i32;
                b.text(font, &text, tx, y, ink);
            }
        }
    }

    /// UI-21: the modal open, over the page dimmed under it: a frame with
    /// its shadow, a honey title bar with the title and the close control
    /// (an x on a key, lit when it has the focus), its content.
    fn draw_modal(&self, m: usize, b: &mut Band, font: &Font, focused: Option<usize>, blink: bool) {
        let node = &self.nodes[m];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let f = self.frame;
        b.fill_rect(
            f.x as i32 + 1,
            self.oy - 1,
            f.w as u32 - 2,
            (self.rows as i32 * ch + 2) as u32,
            DIM,
        );
        let Some(ty) = self.row_y(OVERLAY, ch) else {
            return;
        };
        let r = node.rect;
        let rows = self.overlay_rows.min(self.content_rows()) as i32;
        // the bar takes its row and the frame's 3 px above it, as a window's
        let (mx, my) = (self.ox + r.x as i32 * cw - 3, ty - 3);
        let (mw, mh) = (r.w as u32 * cw as u32 + 6, (rows * ch + 4) as u32);
        b.fill_rect(mx + 3, my + 3, mw, mh, SHADOW);
        bevel_out(b, mx, my, mw, mh, BG, LIGHT, BLACK);
        b.fill_rect(mx + 1, my + 1, mw - 2, 5, TITLE_BG);
        b.fill_rect(mx + 1, my + 6, mw - 2, 6, TITLE_BG2);
        b.fill_rect(mx + 1, my + 12, mw - 2, 1, DARK);
        let title = cut(&text_of(node.props.get("title")), r.w.saturating_sub(4));
        b.text(font, &title, mx + 4, my + 2, INK);
        if truthy_or(node.props.get("closable"), true) {
            let kx = mx + mw as i32 - 14;
            if focused == Some(m) {
                bevel_out(b, kx, my + 3, 11, 8, MID, HONEY, HONEY);
                cross(b, kx + 3, my + 4, HONEY);
            } else {
                bevel_out(b, kx, my + 3, 11, 8, TITLE_BG2, TITLE_BG, TITLE_DARK);
                cross(b, kx + 3, my + 4, INK);
            }
        }
        for c in self.shown_children(m) {
            self.draw_node(c, b, font, focused, blink);
        }
    }

    /// UI-21: the toasts shown, each a small raised box over the page in
    /// the corner `position` names (top right unless it says otherwise),
    /// one under the other: a stripe of its variant's colour, the title in
    /// it, the message, an x to dismiss it when it can be (lit when it has
    /// the focus).
    fn draw_toasts(&self, b: &mut Band, font: &Font, focused: Option<usize>) {
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let area = (
            self.oy + self.content_top() as i32 * ch,
            self.oy + (self.content_top() + self.content_rows()) as i32 * ch,
        );
        let mut used: Vec<(String, i32)> = Vec::new();
        for &n in &self.toasts {
            let node = &self.nodes[n];
            if !node.open || node.lines.is_empty() {
                continue;
            }
            let p = &node.props;
            let close = truthy_or(p.get("dismissible"), true);
            let cells = node
                .lines
                .iter()
                .map(|l| l.chars().count())
                .max()
                .unwrap_or(0)
                + 2
                + if close { 2 } else { 0 };
            let (w, h) = (cells as i32 * cw + 4, node.lines.len() as i32 * ch + 4);
            let position = text_of(p.get("position"));
            let x = if position.contains("left") {
                self.ox + 2
            } else if position.contains("center") {
                self.ox + (self.cols as i32 * cw - w) / 2
            } else {
                self.ox + self.cols as i32 * cw - w - 2
            };
            // the toasts of one corner one under the other (over the other, at the bottom)
            let offset = used
                .iter()
                .find(|(k, _)| *k == position)
                .map_or(0, |(_, o)| *o);
            let y = if position.contains("bottom") {
                area.1 - h - 2 - offset
            } else {
                area.0 + 2 + offset
            };
            match used.iter_mut().find(|(k, _)| *k == position) {
                Some(entry) => entry.1 += h + 2,
                None => used.push((position, h + 2)),
            }
            let is_focus = focused == Some(n);
            let (bg, accent, ink) = match text_of(p.get("variant")).as_str() {
                "success" => (OK_BG, OK_TEXT, OK_TEXT),
                "danger" | "error" => (ERR_BG, ERR_TEXT, ERR_TEXT),
                "warning" => (MID, HONEY, HONEY),
                _ => (MID, LINK, HONEY),
            };
            let (light, dark) = if is_focus {
                (HONEY, HONEY)
            } else {
                (LIGHT, BLACK)
            };
            b.fill_rect(x + 3, y + 3, w as u32, h as u32, SHADOW);
            bevel_out(b, x, y, w as u32, h as u32, bg, light, dark);
            b.fill_rect(x + 2, y + 2, 2, (h - 4) as u32, accent);
            let titled = !text_of(p.get("title")).is_empty();
            for (i, line) in node.lines.iter().enumerate() {
                let color = if i == 0 && titled { ink } else { TEXT };
                b.text(font, line, x + 2 + cw, y + 2 + i as i32 * ch, color);
            }
            if close {
                cross(
                    b,
                    x + w - cw - 3,
                    y + 4,
                    if is_focus { HONEY } else { MUTED },
                );
            }
        }
    }

    /// UI-21: the tip of the tooltip that has the focus, in a small honey
    /// box above what it is about (below when there is no room, or when
    /// `position` says so).
    fn draw_tip(&self, b: &mut Band, font: &Font) {
        let Some(t) = self.tooltip_of_focus() else {
            return;
        };
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let node = &self.nodes[t];
        let r = node.rect;
        let tip = cut(
            &text_of(node.props.get("text")),
            self.cols.saturating_sub(2),
        );
        if tip.is_empty() {
            return;
        }
        let above = (text_of(node.props.get("position")) != "bottom" && r.y > 0)
            .then(|| self.row_y(r.y - 1, ch))
            .flatten()
            .filter(|_| r.y != OVERLAY);
        let Some(y) = above.or_else(|| self.row_y(r.y + r.h.max(1), ch)) else {
            return;
        };
        let w = font.width_of(&tip) as i32 + 2 * cw;
        let right = self.ox + self.cols as i32 * cw;
        let x = (self.ox + r.x as i32 * cw).min(right - w).max(self.ox);
        b.fill_rect(x + 2, y + 2, w as u32, ch as u32, SHADOW);
        bevel_out(b, x, y, w as u32, ch as u32, TITLE_BG, TITLE_BG, TITLE_DARK);
        b.text(font, &tip, x + cw, y, INK);
    }

    /// UI-21: the kinds that are not a composition of the layout set, drawn
    /// with the window's palette; what the font has no sign for (a bar, a
    /// tree's lines, a status) is drawn in pixels.
    fn draw_more(&self, n: usize, b: &mut Band, font: &Font, is_focus: bool) {
        let node = &self.nodes[n];
        let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
        let (r, p) = (node.rect, &node.props);
        let x = self.ox + r.x as i32 * cw;
        match node.kind.as_str() {
            "avatar" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let t = format!("({})", text_of(p.get("initials")));
                    b.text(font, &t, x, y + 1, HONEY);
                    let status = match text_of(p.get("status")).as_str() {
                        "online" => Some(OK_TEXT),
                        "away" => Some(TITLE_BG2),
                        "busy" => Some(DANGER_BG),
                        "offline" => Some(MUTED),
                        _ => None,
                    };
                    if let Some(color) = status {
                        let at = x + font.width_of(&t) as i32 + cw / 2;
                        b.fill_rect(at, y + ch / 2 - 2, 4, 4, color);
                    }
                }
            }
            "chart" => {
                let mut row = r.y;
                let title = text_of(p.get("title"));
                if !title.is_empty() {
                    if let Some(y) = self.row_y(row, ch) {
                        b.text(font, &cut(&title, r.w), x, y + 1, HONEY);
                    }
                    row += 1;
                }
                let share = is_share(p);
                let names = node
                    .bars
                    .iter()
                    .map(|b| text_of(b.get("label")).chars().count())
                    .max()
                    .unwrap_or(0);
                let values = node
                    .bars
                    .iter()
                    .map(|b| shown(b, share).chars().count())
                    .max()
                    .unwrap_or(0);
                let room = r.w.saturating_sub(names + values + 2).max(4);
                for bar in &node.bars {
                    if let Some(y) = self.row_y(row, ch) {
                        b.text(
                            font,
                            &cut(&text_of(bar.get("label")), names),
                            x,
                            y + 1,
                            TEXT,
                        );
                        let percent = bar.get("percent").and_then(Value::as_f64).unwrap_or(0.0);
                        let length = (room as f64 * cw as f64 * percent / 100.0).round() as u32;
                        let left = x + (names as i32 + 1) * cw;
                        if length > 0 {
                            b.fill_rect(
                                left,
                                y + 2,
                                length,
                                (ch - 4).max(1) as u32,
                                chart_color(&text_of(bar.get("color"))),
                            );
                        }
                        b.text(
                            font,
                            &shown(bar, share),
                            left + length as i32 + cw,
                            y + 1,
                            MUTED,
                        );
                    }
                    row += 1;
                }
            }
            "skeleton" => {
                let variant = text_of(p.get("variant"));
                let full = r.w as u32 * cw as u32;
                for row in r.y..r.y + r.h {
                    if let Some(y) = self.row_y(row, ch) {
                        let w = match variant.as_str() {
                            "circle" => 2 * cw as u32,
                            "text" | "" if row + 1 == r.y + r.h && r.h > 1 => full * 3 / 5,
                            _ => full,
                        };
                        b.fill_rect(x, y + 2, w, (ch - 4).max(1) as u32, MID);
                    }
                }
            }
            "loading" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    b.text(font, "...", x, y + 1, HONEY);
                    b.text(
                        font,
                        &cut(&text_of(p.get("text")), r.w.saturating_sub(4)),
                        x + 4 * cw,
                        y + 1,
                        MUTED,
                    );
                }
            }
            "treeitem" => {
                if let Some(y) = self.row_y(r.y, ch) {
                    let depth = depth_of(p);
                    if depth > 0 {
                        // a line down for each level that goes on, then the branch to the row
                        let lines: Vec<bool> = p
                            .get("lines")
                            .and_then(Value::as_array)
                            .map(|a| a.iter().map(|v| truthy(Some(v))).collect())
                            .unwrap_or_default();
                        for (level, on) in lines.iter().enumerate() {
                            if *on {
                                b.fill_rect(
                                    x + level as i32 * 3 * cw + cw / 2,
                                    y,
                                    1,
                                    ch as u32,
                                    LINE,
                                );
                            }
                        }
                        let at = x + (depth as i32 - 1) * 3 * cw + cw / 2;
                        let last = truthy(p.get("last"));
                        b.fill_rect(
                            at,
                            y,
                            1,
                            if last { ch as u32 / 2 + 1 } else { ch as u32 },
                            LINE,
                        );
                        b.fill_rect(at, y + ch / 2, (2 * cw) as u32, 1, LINE);
                    }
                    let goes = node.event.is_some() || !text_of(p.get("to")).is_empty();
                    let color = if is_focus {
                        HONEY
                    } else if goes {
                        LINK
                    } else {
                        TEXT
                    };
                    let left = x + 3 * depth as i32 * cw;
                    let room = r.w.saturating_sub(3 * depth);
                    b.text(
                        font,
                        &cut(&text_of(p.get("text")), room),
                        left,
                        y + 1,
                        color,
                    );
                }
            }
            _ => {}
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

/// What the status bar says of the offers that wait, for F1.
pub(crate) fn offers_tag(offers: usize) -> String {
    if offers == 1 {
        "F1 · 1 offer".to_string()
    } else {
        format!("F1 · {} offers", offers)
    }
}

/// A row of a menu: its text, whether it has the focus, whether it is
/// done with (shown muted).
pub(crate) struct MenuRow {
    pub text: String,
    pub focused: bool,
    pub muted: bool,
}

/// The size of a menu of `cols` cells by `rows` rows, in pixels: the
/// frame around the content, as a window's.
pub(crate) fn menu_size(font: &Font, cols: usize, rows: usize) -> (u32, u32) {
    (
        cols as u32 * font.cell.0 + 10,
        rows as u32 * font.cell.1 + CHROME_H as u32,
    )
}

/// A menu in the look of the windows at (x, y): the frame with its shadow,
/// a honey title bar, one row a line (the one with the focus raised, in
/// honey; a muted one in grey), a status bar with the keys.
#[allow(clippy::too_many_arguments)]
pub(crate) fn draw_menu(
    b: &mut Band,
    font: &Font,
    x: i32,
    y: i32,
    cols: usize,
    title: &str,
    rows: &[MenuRow],
    help: &str,
) {
    let (cw, ch) = (font.cell.0 as i32, font.cell.1 as i32);
    let (w, h) = menu_size(font, cols, rows.len());
    b.fill_rect(x + 3, y + 3, w, h, SHADOW);
    bevel_out(b, x, y, w, h, BG, LIGHT, BLACK);
    b.fill_rect(x + 1, y + 1, w - 2, 6, TITLE_BG);
    b.fill_rect(x + 1, y + 7, w - 2, (TITLE_H - 6) as u32, TITLE_BG2);
    b.fill_rect(x + 1, y + 1 + TITLE_H, w - 2, 1, DARK);
    b.text(font, &cut(title, cols), x + 5, y + 2, INK);
    let (ox, oy) = (x + SIDE + 1, y + 1 + TITLE_H + 2);
    for (i, row) in rows.iter().enumerate() {
        let ry = oy + i as i32 * ch;
        let color = if row.focused {
            bevel_out(
                b,
                ox - 1,
                ry,
                cols as u32 * cw as u32 + 2,
                ch as u32,
                MID,
                LIGHT,
                BLACK,
            );
            HONEY
        } else if row.muted {
            MUTED
        } else {
            TEXT
        };
        b.text(font, &cut(&row.text, cols), ox + 1, ry, color);
    }
    let sy = y + h as i32 - 1 - STATUS_H;
    b.fill_rect(x + 1, sy - 1, w - 2, 1, LIGHT);
    b.fill_rect(x + 1, sy, w - 2, STATUS_H as u32, MID);
    b.text(font, &cut(help, cols), x + 5, sy + 1, TEXT);
}

/// A raised box: light above and left, dark below and right.
#[allow(clippy::too_many_arguments)]
pub(crate) fn bevel_out(
    b: &mut Band,
    x: i32,
    y: i32,
    w: u32,
    h: u32,
    fill: u32,
    light: u32,
    dark: u32,
) {
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

/// Where an arrow points.
#[derive(Clone, Copy)]
enum Toward {
    Up,
    Down,
    Left,
    Right,
}

/// A small arrow in three steps (5, 3 and 1 px), pointing `to`: 5 px
/// across and 3 down (3 across and 5 down when it points left or right),
/// its corner at (x, y). The font has no arrows (UI-21).
fn arrow(b: &mut Band, x: i32, y: i32, to: Toward, color: u32) {
    for i in 0..3 {
        let len = 5 - 2 * i as u32;
        match to {
            Toward::Down => b.fill_rect(x + i, y + i, len, 1, color),
            Toward::Up => b.fill_rect(x + i, y + 2 - i, len, 1, color),
            Toward::Right => b.fill_rect(x + i, y + i, 1, len, color),
            Toward::Left => b.fill_rect(x + 2 - i, y + i, 1, len, color),
        }
    }
}

/// An x of 5 by 5 px at (x, y): what closes.
fn cross(b: &mut Band, x: i32, y: i32, color: u32) {
    for i in 0..5 {
        b.fill_rect(x + i, y + i, 1, 1, color);
        b.fill_rect(x + 4 - i, y + i, 1, 1, color);
    }
}

/// A dotted frame, every other pixel: the focus of what has no box of its
/// own (a tooltip, UI-21).
fn dotted(b: &mut Band, x: i32, y: i32, w: i32, h: i32, color: u32) {
    for i in (0..w).step_by(2) {
        b.fill_rect(x + i, y, 1, 1, color);
        b.fill_rect(x + i, y + h - 1, 1, 1, color);
    }
    for j in (0..h).step_by(2) {
        b.fill_rect(x, y + j, 1, 1, color);
        b.fill_rect(x + w - 1, y + j, 1, 1, color);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_help_line_is_cut_between_its_hints() {
        let help = "type · arrows · Enter sends · Esc closes";
        assert_eq!(cut_at_separator(help, 60), help);
        assert_eq!(cut_at_separator(help, 33), "type · arrows · Enter sends");
        assert_eq!(cut_at_separator(help, 10), "type");
        assert_eq!(cut_at_separator(help, 3), "typ");
        assert_eq!(offers_tag(1), "F1 · 1 offer");
        assert_eq!(offers_tag(2), "F1 · 2 offers");
    }

    fn page() -> Value {
        json!({"title": "Tasks", "flash": "Created: call", "view": [
            {"id": 1, "type": "window", "props": {"title": "Tasks"}, "children": [
                {"id": 2, "type": "form", "props": {}, "event": {"action": "create", "fields": {"filter": "all"}}, "children": [
                    {"id": 3, "type": "input", "props": {"bind": "title", "placeholder": "What?"}},
                    {"id": 4, "type": "select", "props": {"bind": "priority", "options": "medium,high,low", "value": "high"}},
                    {"id": 5, "type": "checkbox", "props": {"bind": "urgent", "label": "Urgent", "checked": "true"}},
                    {"id": 6, "type": "button", "props": {"text": "Create", "variant": "primary"}}]},
                {"id": 7, "type": "button", "props": {"text": "Done"}, "event": {"action": "toggle", "fields": {"id": "3"}}},
                {"id": 8, "type": "link", "props": {"text": "Sheet", "to": "/sheet"}},
                {"id": 9, "type": "table", "props": {}, "children": [],
                 "columns": [{"label": "Name", "to": "/?sort=name"}, {"label": "Actions"}],
                 "rows": [[[{"id": 10, "type": "text", "props": {"text": "Ann"}}],
                           [{"id": 11, "type": "button", "props": {"text": "Remove"}, "event": {"action": "remove", "fields": {"id": "1"}}}]],
                          [[{"id": 12, "type": "text", "props": {"text": "Bea"}}],
                           [{"id": 13, "type": "button", "props": {"text": "Remove"}, "event": {"action": "remove", "fields": {"id": "2"}}}]]]}]}]})
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
        assert_eq!(obs["items"][0]["bind"], "title");
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
        assert!(w.help().contains("row"));
    }

    #[test]
    fn typing_edits_the_field_with_a_cursor_and_enter_submits_the_form() {
        let mut w = Window::new(&page(), 320, 180);
        for c in "lunch".chars() {
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
            "aunch ",
            "a at the start, l gone, a space at the end"
        );
        keys(&mut w, &[Key::CtrlU]);
        for c in "bread".chars() {
            w.key(Key::Char(c), 0);
        }
        // the select to low, the box off
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
        assert_eq!(events[0]["action"], "create");
        assert_eq!(events[0]["fields"]["title"], "bread");
        assert_eq!(events[0]["fields"]["priority"], "low");
        assert_eq!(
            events[0]["fields"]["filter"], "all",
            "the form's hidden fields"
        );
        assert!(
            events[0]["fields"].get("urgent").is_none(),
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
            "Done sends its row's field"
        );
        keys(&mut w, &[Key::Tab, Key::Enter]);
        assert_eq!(w.take_events()[0]["to"], "/sheet");
        keys(&mut w, &[Key::Tab, Key::Down, Key::Enter]);
        let e = w.take_events();
        assert_eq!(e[0]["event"], "click");
        assert_eq!(e[0]["fields"]["id"], "2", "the second row's Remove");
        keys(&mut w, &[Key::Up, Key::Up, Key::Enter]);
        assert_eq!(
            w.take_events()[0]["to"],
            "/?sort=name",
            "the header's sortable column"
        );
        keys(&mut w, &[Key::Escape]);
        assert_eq!(w.take_events()[0]["event"], "close");
    }

    #[test]
    fn a_search_field_says_its_change_after_a_pause() {
        let page = json!({"title": "Search", "view": [{"id": 1, "type": "input", "props": {"bind": "q", "search": true, "delay": 300}}]});
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

    #[test]
    fn open_names_the_tab_that_opens() {
        // UI-17: the tab `open` names; a value that names none opens the first
        let tabs = |open: &str| {
            json!({"title": "T", "view": [{"type": "tabpanel", "props": {"open": open}, "children": [
                {"type": "tab", "props": {"title": "First"}, "children": [{"type": "text", "props": {"text": "one"}}]},
                {"type": "tab", "props": {"title": "Second"}, "children": [{"type": "text", "props": {"text": "two"}}]}]}]})
        };
        let w = Window::new(&tabs("Second"), 320, 180);
        assert!(w.texts().contains(&"two".to_string()));
        let panel = w.observe()["items"][0].clone();
        assert_eq!(
            (panel["tab"].clone(), panel["tabs"].clone()),
            (json!(1), json!(["First", "Second"]))
        );
        assert!(Window::new(&tabs("Ninth"), 320, 180)
            .texts()
            .contains(&"one".to_string()));
    }

    /// UI-21: the tags with a state of their own, as the view sends them
    /// (tests/apps/showcase/components/state.q).
    fn state() -> Value {
        json!({"title": "State", "view": [{"type": "window", "props": {"title": "State"}, "children": [
            {"type": "modal", "props": {"title": "Welcome", "open": true, "closable": true}, "children": [
                {"type": "text", "props": {"text": "Read this first"}}]},
            {"type": "toast", "props": {"title": "Saved", "message": "All changes kept", "duration": 1500,
                                        "dismissible": true, "position": "top-right"}},
            {"type": "accordion", "props": {}, "children": [
                {"type": "section", "props": {"title": "First fold"}, "children": [
                    {"type": "text", "props": {"text": "Inside the first"}}]},
                {"type": "section", "props": {"title": "Second fold"}, "children": [
                    {"type": "text", "props": {"text": "Inside the second"}}]}]},
            {"type": "tooltip", "props": {"text": "A tip for the badge"}, "children": [
                {"type": "badge", "props": {"text": "Hover me"}}]},
            {"type": "dropdown", "props": {"label": "Actions"}, "children": [
                {"type": "option", "as": "link", "props": {"text": "Copy"},
                 "event": {"action": "pick", "fields": {"value": "copy"}}},
                {"type": "option", "as": "link", "props": {"text": "Move"},
                 "event": {"action": "pick", "fields": {"value": "move"}}}]},
            {"type": "carousel", "props": {"current": 0, "loop": false}, "children": [
                {"type": "slide", "as": "vbox", "props": {}, "children": [
                    {"type": "text", "props": {"text": "Slide one"}}]},
                {"type": "slide", "as": "vbox", "props": {}, "children": [
                    {"type": "text", "props": {"text": "Slide two"}}]}]},
            {"type": "stepper", "props": {"current": 0}, "children": [
                {"type": "step", "props": {"title": "Account"}, "children": [
                    {"type": "text", "props": {"text": "Step one body"}}]},
                {"type": "step", "props": {"title": "Profile", "description": "Who you are"}, "children": [
                    {"type": "text", "props": {"text": "Step two body"}}]}]}]}]})
    }

    fn shows(w: &Window, text: &str) -> bool {
        w.texts().iter().any(|t| t.contains(text))
    }

    /// Tab until the element of that kind (and label, when given) has the focus.
    fn focus(w: &mut Window, kind: &str, label: &str) {
        for _ in 0..=w.focusables.len() {
            let item = w.observe()["items"][w.focus].clone();
            if item["kind"] == kind && (label.is_empty() || item["label"] == label) {
                return;
            }
            w.key(Key::Tab, 0);
        }
        panic!("no {} {:?} to focus", kind, label);
    }

    /// The state page with its modal closed.
    fn state_page() -> Window {
        let mut w = Window::new(&state(), 320, 180);
        w.key(Key::Enter, 0);
        w
    }

    #[test]
    fn an_open_modal_is_over_the_page_and_has_the_keyboard_until_it_closes() {
        let mut w = Window::new(&state(), 320, 180);
        assert!(shows(&w, "Welcome") && shows(&w, "Read this first"));
        let items = w.observe()["items"].clone();
        assert_eq!(
            items.as_array().unwrap().len(),
            1,
            "its close control alone"
        );
        assert_eq!(
            (items[0]["kind"].clone(), items[0]["label"].clone()),
            (json!("modal"), json!("Welcome"))
        );
        // Esc closes the modal before it would close the page
        w.key(Key::Escape, 0);
        assert!(w.take_events().is_empty());
        assert!(!shows(&w, "Read this first") && !shows(&w, "Welcome"));
        assert!(w.observe()["items"].as_array().unwrap().len() > 1);
        w.key(Key::Escape, 0);
        assert_eq!(w.take_events()[0]["event"], "close");
        // not closable: Esc is the page's
        let mut fixed = state();
        fixed["view"][0]["children"][0]["props"]["closable"] = json!(false);
        let mut w = Window::new(&fixed, 320, 180);
        assert!(w.observe()["items"].as_array().unwrap().is_empty());
        w.key(Key::Escape, 0);
        assert_eq!(w.take_events()[0]["event"], "close");
        // closed: nothing of it shows
        fixed["view"][0]["children"][0]["props"]["open"] = json!(false);
        assert!(!shows(&Window::new(&fixed, 320, 180), "Read this first"));
    }

    #[test]
    fn an_accordion_opens_its_first_fold_and_enter_opens_and_closes_the_others() {
        let mut w = state_page();
        assert!(shows(&w, "First fold") && shows(&w, "Inside the first"));
        assert!(shows(&w, "Second fold") && !shows(&w, "Inside the second"));
        focus(&mut w, "section", "Second fold");
        assert_eq!(w.observe()["items"][w.focus]["open"], false);
        w.key(Key::Enter, 0);
        assert!(shows(&w, "Inside the second"));
        assert_eq!(
            w.observe()["items"][w.focus]["label"],
            "Second fold",
            "the focus stays on the fold"
        );
        w.key(Key::Enter, 0);
        assert!(!shows(&w, "Inside the second"));
    }

    #[test]
    fn a_toast_goes_after_its_duration_or_when_dismissed() {
        let mut w = state_page();
        assert!(shows(&w, "Saved") && shows(&w, "All changes kept"));
        assert_ne!(
            w.observe()["items"][w.focus]["kind"],
            "toast",
            "the focus does not start on what goes"
        );
        for t in 1..90 {
            w.tick(t);
        }
        assert!(shows(&w, "All changes kept"), "1500 ms are 90 ticks");
        assert!(w.tick(90));
        assert!(!shows(&w, "All changes kept"));
        assert!(w.observe()["items"]
            .as_array()
            .unwrap()
            .iter()
            .all(|i| i["kind"] != "toast"));
        // dismissed: the focus goes to what came after it
        let mut w = state_page();
        focus(&mut w, "toast", "Saved");
        w.key(Key::Enter, 0);
        assert!(!shows(&w, "All changes kept"));
        assert_eq!(w.observe()["items"][w.focus]["label"], "First fold");
    }

    #[test]
    fn a_tooltip_says_its_tip_only_while_it_has_the_focus() {
        let mut w = state_page();
        assert!(shows(&w, "Hover me") && !shows(&w, "A tip for the badge"));
        focus(&mut w, "tooltip", "Hover me");
        assert_eq!(w.observe()["items"][w.focus]["tip"], "A tip for the badge");
        assert!(shows(&w, "A tip for the badge"));
        w.key(Key::Tab, 0);
        assert!(!shows(&w, "A tip for the badge"));
    }

    #[test]
    fn a_dropdown_opens_its_options_and_one_posts_its_action() {
        let mut w = state_page();
        assert!(shows(&w, "Actions") && !shows(&w, "Copy") && !shows(&w, "Move"));
        focus(&mut w, "dropdown", "Actions");
        w.key(Key::Enter, 0);
        assert!(shows(&w, "Copy") && shows(&w, "Move"));
        // Esc shuts the menu, not the page
        w.key(Key::Escape, 0);
        assert!(w.take_events().is_empty() && !shows(&w, "Move"));
        w.key(Key::Enter, 0);
        keys(&mut w, &[Key::Down, Key::Down, Key::Enter]);
        let events = w.take_events();
        assert_eq!(events[0]["event"], "click");
        assert_eq!(events[0]["action"], "pick");
        assert_eq!(events[0]["fields"]["value"], "move");
        assert!(!shows(&w, "Move"), "the menu shuts on its option");
        assert_eq!(w.observe()["items"][w.focus]["kind"], "dropdown");
    }

    #[test]
    fn a_carousel_shows_one_slide_and_a_stepper_one_step() {
        let mut w = state_page();
        assert!(shows(&w, "Slide one") && !shows(&w, "Slide two") && shows(&w, "1/2"));
        focus(&mut w, "carousel", "");
        w.key(Key::Right, 0);
        assert!(shows(&w, "Slide two") && !shows(&w, "Slide one") && shows(&w, "2/2"));
        w.key(Key::Right, 0);
        assert!(shows(&w, "Slide two"), "it does not go round without loop");
        w.key(Key::Left, 0);
        assert!(shows(&w, "Slide one"));
        // the stepper: the titles, the current step's content, Back and Next
        assert!(shows(&w, "Account") && shows(&w, "Profile") && shows(&w, "Step one body"));
        assert!(!shows(&w, "Step two body") && !shows(&w, "Who you are"));
        focus(&mut w, "button", "Next");
        assert_eq!(w.observe()["items"][w.focus]["moves"], "stepper");
        w.key(Key::Enter, 0);
        assert!(w.take_events().is_empty(), "Next moves the stepper here");
        assert!(shows(&w, "Step two body") && shows(&w, "Who you are"));
        assert!(!shows(&w, "Step one body"));
        let parts = w.moving_parts(w.nodes[w.focused().unwrap()].parent.unwrap());
        assert!(w.nodes[parts[0]].checked, "the step left behind is done");
        focus(&mut w, "button", "Back");
        w.key(Key::Enter, 0);
        assert!(shows(&w, "Step one body"));
    }

    #[test]
    fn a_carousel_that_plays_moves_every_interval() {
        let page = json!({"title": "C", "view": [{"type": "carousel",
            "props": {"auto_play": true, "interval": 1000}, "children": [
                {"type": "vbox", "props": {}, "children": [{"type": "text", "props": {"text": "one"}}]},
                {"type": "vbox", "props": {}, "children": [{"type": "text", "props": {"text": "two"}}]}]},
            {"type": "button", "props": {"text": "Elsewhere"}}]});
        let mut w = Window::new(&page, 320, 180);
        focus(&mut w, "button", "Elsewhere");
        for t in 1..60 {
            w.tick(t);
        }
        assert!(shows(&w, "one"));
        w.tick(60);
        assert!(shows(&w, "two"));
        for t in 61..=120 {
            w.tick(t);
        }
        assert!(shows(&w, "one"), "round again");
    }

    #[test]
    fn a_calendar_s_days_are_the_gregorian_calendar_s() {
        assert_eq!(days_from_civil(1970, 1, 1), 0);
        for days in -800_000..800_000 {
            let (y, m, d) = civil_from_days(days);
            assert_eq!(days_from_civil(y, m, d), days);
        }
        let day = |text: &str| parse_date(text).unwrap();
        assert_eq!(weekday(day("2026-11-01")), 0, "a Sunday");
        assert_eq!(weekday(day("2000-01-01")), 6, "a Saturday");
        assert_eq!(month_len(month_of(day("2024-02-10"))), 29);
        assert_eq!(month_len(month_of(day("2100-02-10"))), 28);
        assert_eq!(month_len(month_of(day("2000-02-10"))), 29);
        assert_eq!(parse_date("2026-02-29"), None);
        assert_eq!(parse_date("2026-13-01"), None);
        assert_eq!(iso_date(day("2026-12-24")), "2026-12-24");
        assert_eq!(
            parse_month("2026-11").map(month_title).unwrap(),
            "November 2026"
        );
        // ISO weeks, as Python's isocalendar() says them
        assert_eq!(iso_week(day("2026-10-26")), 44);
        assert_eq!(iso_week(day("2026-12-28")), 53);
        assert_eq!(iso_week(day("2027-01-03")), 53);
        assert_eq!(iso_week(day("2027-01-04")), 1);
        assert_eq!(iso_week(day("2024-12-30")), 1);
    }

    /// UI-21: a form with a calendar, as the view of
    /// tests/apps/showcase/components/state.q sends it.
    fn booking(props: Value) -> Window {
        let mut p = json!({"bind": "day", "value": "2026-11-15", "month": "2026-11", "min": "",
                           "max": "", "disabled_dates": [], "disabled_days": [], "first_day": 0,
                           "week_numbers": false});
        for (k, v) in props.as_object().unwrap() {
            p[k] = v.clone();
        }
        let page = json!({"title": "Book", "view": [{"type": "form", "props": {},
            "event": {"action": "book", "fields": {}}, "children": [
                {"type": "calendar", "props": p},
                {"type": "button", "props": {"text": "Book"}}]}]});
        Window::new(&page, 320, 180)
    }

    fn calendar(w: &Window) -> Value {
        w.observe()["items"][0].clone()
    }

    #[test]
    fn a_calendar_shows_a_month_moves_and_the_day_it_picks_goes_with_its_form() {
        let mut w = booking(json!({}));
        let c = calendar(&w);
        assert_eq!(
            (c["kind"].clone(), c["focus"].clone()),
            (json!("calendar"), json!(true))
        );
        assert_eq!(
            (c["month"].clone(), c["value"].clone(), c["cursor"].clone()),
            (json!("2026-11"), json!("2026-11-15"), json!("2026-11-15"))
        );
        assert!(shows(&w, "November 2026") && shows(&w, "Su Mo Tu We Th Fr Sa"));
        assert!(w.help().contains("PgUp PgDn: month"));
        // PgDn: the next month, the cursor on the same day
        w.key(Key::PageDown, 0);
        assert!(shows(&w, "December 2026") && !shows(&w, "November 2026"));
        assert_eq!(calendar(&w)["cursor"], "2026-12-15");
        // the arrows: a week, a day; Enter picks the day under the cursor
        keys(&mut w, &[Key::Down, Key::Right, Key::Right, Key::Enter]);
        assert_eq!(calendar(&w)["value"], "2026-12-24");
        keys(&mut w, &[Key::Tab, Key::Enter]);
        let events = w.take_events();
        assert_eq!(events[0]["event"], "submit");
        assert_eq!(events[0]["fields"]["day"], "2026-12-24");
        // past the month's ends the month moves with the cursor
        let mut w = booking(json!({"value": "2026-12-01", "month": "2026-12"}));
        w.key(Key::Left, 0);
        assert_eq!(calendar(&w)["month"], "2026-11");
        assert_eq!(calendar(&w)["cursor"], "2026-11-30");
        keys(&mut w, &[Key::Home, Key::Up]);
        assert_eq!(calendar(&w)["cursor"], "2026-10-25");
        // a month shorter than the cursor's day: its last
        let mut w = booking(json!({"value": "2027-01-31", "month": "2027-01"}));
        w.key(Key::PageDown, 0);
        assert_eq!(calendar(&w)["cursor"], "2027-02-28");
        keys(&mut w, &[Key::PageUp, Key::PageUp]);
        assert_eq!(calendar(&w)["cursor"], "2026-12-28");
        assert_eq!(calendar(&w)["value"], "2027-01-31", "moving picks nothing");
    }

    #[test]
    fn a_calendar_s_day_out_of_bounds_or_disabled_cannot_be_picked() {
        let mut w = booking(json!({"min": "2026-11-03", "max": "2026-11-27",
            "disabled_dates": ["2026-11-18"], "disabled_days": [0, 6], "value": "",
            "month": "2026-11"}));
        assert_eq!(
            calendar(&w)["cursor"],
            "2026-11-01",
            "nothing picked: the month's first"
        );
        let pick = |w: &mut Window, day: &str| {
            let n = w.focused().unwrap();
            w.nodes[n].day = parse_date(day).unwrap();
            w.key(Key::Enter, 0);
            calendar(w)["value"].as_str().unwrap().to_string()
        };
        assert_eq!(pick(&mut w, "2026-11-02"), "", "before min");
        assert_eq!(pick(&mut w, "2026-11-30"), "", "after max");
        assert_eq!(pick(&mut w, "2026-11-18"), "", "a date disabled");
        assert_eq!(pick(&mut w, "2026-11-21"), "", "a Saturday");
        assert_eq!(pick(&mut w, "2026-11-19"), "2026-11-19");
        // the week from Monday, with the weeks' numbers before the days
        let w = booking(json!({"first_day": 1, "week_numbers": true}));
        assert!(shows(&w, "Mo Tu We Th Fr Sa Su"));
        assert_eq!(
            w.texts()[2],
            "44                    1",
            "Sunday the 1st, last of week 44"
        );
        assert_eq!(w.texts()[3], "45  2  3  4  5  6  7  8");
        // outside the calendar, PgDn scrolls the page as before
        let mut w = booking(json!({}));
        w.key(Key::Tab, 0);
        w.key(Key::PageDown, 0);
        assert_eq!(calendar(&w)["month"], "2026-11");
    }

    #[test]
    fn a_flash_the_page_shows_gets_no_line_of_its_own() {
        // UI-16: the page's own alert says it; the window does not say it again
        let mut shown = page();
        shown["flashShown"] = json!(true);
        assert_eq!(
            Window::new(&shown, 320, 180).observe()["flash"],
            Value::Null
        );
        assert_eq!(
            Window::new(&page(), 320, 180).observe()["flash"],
            "Created: call"
        );
    }
}
