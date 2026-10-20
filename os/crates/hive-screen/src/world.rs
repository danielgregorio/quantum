//! The scene alive: sprites with their animations and tweens, the effects,
//! the offers an administrator approves, the notices and what the Hive
//! says, advanced a tick at a time (60 a second) and drawn on a canvas.
//!
//! The world knows nothing of sockets or displays: the Hive's messages
//! come in as events and offers, keys come in as keys, and what it wants
//! sent back comes out as [`Outgoing`]. That is what makes it the same
//! on the console, in the lab and in a test.

use crate::canvas::{Band, Canvas};
use crate::ease::{interpolate, Ease, Trans};
use crate::image::{argb, Image};
use crate::level::{self, LEVELS};
use crate::particles::Emitter;
use crate::scene::{Action, Align, Node, Property, Scene, Side};
use crate::window::{bevel_out, Rect, Window, BLACK, DARK, HONEY, LIGHT, MID, SHADOW, TEXT};
use hive_common::actions::Action as HiveAction;
use hive_common::events::{fill, Fields};
use serde_json::{json, Value};
use std::collections::VecDeque;
use uuid::Uuid;

pub const TICK_RATE: f32 = 60.0;

#[derive(Debug, Clone)]
struct Anim {
    name: String,
    frames: Vec<u32>,
    fps: f32,
    looping: bool,
    index: usize,
    acc: f32,
    done: bool,
}

#[derive(Debug, Clone)]
pub struct Sprite {
    pub name: Option<String>,
    pub sheet: usize,
    pub frame: u32,
    pub x: f32,
    pub y: f32,
    pub visible: bool,
    pub scale: f32,
    pub alpha: f32,
    anim: Option<Anim>,
}

#[derive(Debug, Clone)]
struct Tween {
    sprite: usize,
    property: Property,
    from: f32,
    to: f32,
    ticks: u32,
    t: u32,
    trans: Trans,
    ease: Ease,
    repeat: i32,
    yoyo: bool,
}

/// What became of an offer the administrator approved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome {
    /// Nothing to run: the offer carried no action.
    NoAction,
    /// Sent to the Hive; waiting for the actuator's answer.
    Sent,
    Succeeded,
    Failed,
}

#[derive(Debug, Clone)]
pub struct Offer {
    pub notification: Uuid,
    pub suggestion: u32,
    pub title: String,
    pub action: Option<HiveAction>,
    pub dangerous: bool,
    /// A dangerous offer asks for Enter twice; this is after the first.
    pub armed: bool,
    pub outcome: Option<Outcome>,
}

/// What the world asks to be sent to the Hive.
#[derive(Debug, Clone, PartialEq)]
pub enum Outgoing {
    Approve {
        notification: Uuid,
        suggestion: u32,
        confirmed: bool,
    },
    Dismiss {
        notification: Uuid,
    },
}

/// A key, as the keyboard (input.rs), the play driver and a test name
/// it. The scene takes Up, Down, Enter and Escape; a page on the screen
/// (window.rs) takes them all.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Key {
    Up,
    Down,
    Left,
    Right,
    Enter,
    Escape,
    Tab,
    ShiftTab,
    Home,
    End,
    Backspace,
    Delete,
    Space,
    PageUp,
    PageDown,
    F1,
    F5,
    CtrlU,
    /// A printable character, as the keyboard's layout and its shift
    /// give it.
    Char(char),
}

impl Key {
    /// A key by name: `up`, `down`, `left`, `right`, `enter`, `escape`,
    /// `tab`, `shift-tab`, `home`, `end`, `backspace`, `delete`, `space`,
    /// `pgup`, `pgdn`, `f1`, `f5`, `ctrl-u`, or one character.
    pub fn parse(name: &str) -> Option<Key> {
        let lower = name.to_ascii_lowercase();
        Some(match lower.as_str() {
            "up" => Key::Up,
            "down" => Key::Down,
            "left" => Key::Left,
            "right" => Key::Right,
            "enter" | "return" => Key::Enter,
            "escape" | "esc" => Key::Escape,
            "tab" => Key::Tab,
            "shift-tab" | "shift+tab" | "backtab" => Key::ShiftTab,
            "home" => Key::Home,
            "end" => Key::End,
            "backspace" => Key::Backspace,
            "delete" | "del" => Key::Delete,
            "space" => Key::Space,
            "pgup" | "pageup" => Key::PageUp,
            "pgdn" | "pagedown" => Key::PageDown,
            "f1" => Key::F1,
            "f5" => Key::F5,
            "ctrl-u" | "ctrl+u" => Key::CtrlU,
            _ => {
                let mut chars = name.chars();
                match (chars.next(), chars.next()) {
                    (Some(c), None) if !c.is_control() => Key::Char(c),
                    _ => return None,
                }
            }
        })
    }

    /// The name `parse` takes back.
    pub fn name(&self) -> String {
        match self {
            Key::Char(c) => c.to_string(),
            Key::ShiftTab => "shift-tab".into(),
            Key::PageUp => "pgup".into(),
            Key::PageDown => "pgdn".into(),
            Key::CtrlU => "ctrl-u".into(),
            other => format!("{:?}", other).to_lowercase(),
        }
    }
}

/// Where the toast (`qs:say`) sits when the scene has no bar at the
/// bottom: a strip at the bottom of the scene.
const TOAST_HEIGHT: u32 = 12;

/// The bars of the scene (`qs:bar`), in the look of a window manager: the
/// one at the top is 14 pixels (a light line, the bar, a rule), the one at
/// the bottom 12 (a rule and the bar); the texts sit 4 pixels in from the
/// edges.
const BAR_TOP_H: u32 = 14;
const BAR_BOTTOM_H: u32 = 12;
const BAR_IN: i32 = 4;
const BAR_BG: u32 = 0xFF12_1224;
const BAR_LINE: u32 = 0xFF34_345A;

/// A panel (`qs:offers` or `qs:notices` with a title): a bevelled frame
/// with a 3-px shadow, a title bar of 10 pixels with a rule under it,
/// and the rows 3 pixels in from the frame.
const PANEL_BG: u32 = 0xFF14_1430;
const PANEL_TOP: i32 = 13;
const PANEL_IN: i32 = 3;

/// What the bars say of the machine, which the daemon tells the world as
/// it runs. A test's world knows none of it, so its frames are the same
/// on every machine.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Facts {
    pub host: String,
    pub cores: usize,
    /// The time as HH:MM; none shows as `--:--`.
    pub clock: Option<String>,
}

impl Default for Facts {
    fn default() -> Facts {
        Facts {
            host: String::new(),
            cores: 1,
            clock: None,
        }
    }
}

/// `text` with every `{field}` replaced by what `field` gives for it; a
/// field it has nothing for stays as written.
fn fill_fields(text: &str, field: impl Fn(&str) -> Option<String>) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(open) = rest.find('{') {
        out.push_str(&rest[..open]);
        let after = &rest[open + 1..];
        match after.find('}') {
            Some(close) if !after[..close].contains('{') => {
                let name = &after[..close];
                match field(name) {
                    Some(value) => out.push_str(&value),
                    None => {
                        out.push('{');
                        out.push_str(name);
                        out.push('}');
                    }
                }
                rest = &after[close + 1..];
            }
            _ => {
                out.push('{');
                rest = after;
            }
        }
    }
    out.push_str(rest);
    out
}

/// How dark the scene goes under a page: black at this alpha.
const DIM_ALPHA: u8 = 0x78;

/// An ordered dither, 4 by 4: the pixel-art way to show one picture
/// through another, with no alpha.
const BAYER: [[u8; 4]; 4] = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];

/// A transition of the page on the screen: what the window manager of
/// 2008 did in 3D, in pixel art, in ticks. Jelly: the window opens
/// growing from 60% with an overshoot. Lamp: closed, it bends and is
/// sucked into the bottom left corner, where its button on the bar will
/// be. Curtain: a page shown again after an action replaces the one
/// before through the dither, line by line.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MotionKind {
    Jelly,
    Lamp,
    Curtain,
}

impl MotionKind {
    fn ticks(self) -> u32 {
        match self {
            MotionKind::Jelly => 12,
            MotionKind::Lamp => 14,
            MotionKind::Curtain => 8,
        }
    }

    fn name(self) -> &'static str {
        match self {
            MotionKind::Jelly => "jelly",
            MotionKind::Lamp => "lamp",
            MotionKind::Curtain => "curtain",
        }
    }
}

struct Motion {
    kind: MotionKind,
    t: u32,
    /// The picture of the page as it was (the lamp's, the curtain's old
    /// one), and its frame.
    old: Option<(Image, Rect)>,
}

/// An emitter the scene keeps going, from the presentation level it names.
struct Ambient {
    level: u32,
    emitter: Emitter,
}

pub struct World {
    pub scene: Scene,
    pub sprites: Vec<Sprite>,
    tweens: Vec<Tween>,
    emitters: Vec<Ambient>,
    bursts: Vec<Emitter>,
    pub offers: Vec<Offer>,
    pub focus: usize,
    pub notices: VecDeque<String>,
    toast: Option<(String, u32)>,
    pub tick: u64,
    seeds: u32,
    /// What happened since the last look: for a test and the lab.
    pub events: Vec<Value>,
    /// Whether the picture changed since the last draw.
    dirty: bool,
    /// The presentation level it plays at (level.rs).
    level: usize,
    /// A page on the screen (`quantum pixel`), over the scene.
    window: Option<Window>,
    /// The transition the page is in, if any.
    motion: Option<Motion>,
    /// Whether pages move at all (`HIVE_SCREEN_MOTION=off` says no).
    motion_on: bool,
    /// What the page's runtime is to hear: the window's events, until
    /// the socket takes them.
    pixel_out: Vec<Value>,
    /// What the bars say of the machine.
    facts: Facts,
}

impl World {
    pub fn new(scene: Scene) -> World {
        let mut sprites = Vec::new();
        let mut emitters = Vec::new();
        let mut seeds = 1u32;
        for node in &scene.nodes {
            match node {
                Node::Sprite {
                    name,
                    sheet,
                    frame,
                    x,
                    y,
                    animation,
                    hidden,
                } => {
                    let mut sprite = Sprite {
                        name: name.clone(),
                        sheet: *sheet,
                        frame: *frame,
                        x: *x as f32,
                        y: *y as f32,
                        visible: !hidden,
                        scale: 1.0,
                        alpha: 1.0,
                        anim: None,
                    };
                    if let Some(a) = animation {
                        let def = &scene.sheets[*sheet].animations[a];
                        sprite.anim = Some(Anim {
                            name: a.clone(),
                            frames: def.frames.clone(),
                            fps: def.fps,
                            looping: def.looping,
                            index: 0,
                            acc: 0.0,
                            done: false,
                        });
                        sprite.frame = def.frames[0];
                    }
                    sprites.push(sprite);
                }
                Node::Emitter {
                    particles,
                    x,
                    y,
                    width,
                    level,
                } => {
                    seeds += 1;
                    emitters.push(Ambient {
                        level: *level,
                        emitter: Emitter::new(
                            scene.particles[particles].clone(),
                            *x as f32,
                            *y as f32,
                            *width as f32,
                            seeds,
                        ),
                    });
                }
                _ => {}
            }
        }
        World {
            scene,
            sprites,
            tweens: Vec::new(),
            emitters,
            bursts: Vec::new(),
            offers: Vec::new(),
            focus: 0,
            notices: VecDeque::new(),
            toast: None,
            tick: 0,
            seeds,
            events: Vec::new(),
            dirty: true,
            level: level::DEFAULT,
            window: None,
            motion: None,
            motion_on: true,
            pixel_out: Vec::new(),
            facts: Facts::default(),
        }
    }

    // ---------------------------------------------------------------- the facts

    /// What the bars say of the machine: the daemon tells it as it runs.
    pub fn set_facts(&mut self, facts: Facts) {
        if facts != self.facts {
            self.facts = facts;
            self.dirty = true;
        }
    }

    /// A field of the screen's own, as a bar shows it (schema.py's
    /// BAR_FIELDS): none for a name that is not one.
    fn field(&self, name: &str) -> Option<String> {
        Some(match name {
            "clock" => self
                .facts
                .clock
                .clone()
                .unwrap_or_else(|| "--:--".to_string()),
            "level" => LEVELS[self.level].name.to_string(),
            "cores" => self.facts.cores.to_string(),
            "host" => self.facts.host.clone(),
            "offers" => self
                .offers
                .iter()
                .filter(|o| o.outcome.is_none())
                .count()
                .to_string(),
            _ => return None,
        })
    }

    /// A bar's text with its fields filled in.
    fn bar_text(&self, text: &Option<String>) -> String {
        match text {
            Some(t) => fill_fields(t, |name| self.field(name)),
            None => String::new(),
        }
    }

    // ---------------------------------------------------------------- the level

    /// The presentation level it plays at (level.rs).
    pub fn level(&self) -> usize {
        self.level
    }

    /// Whether particles play at this level.
    pub fn effects(&self) -> bool {
        LEVELS[self.level].effects
    }

    /// Plays at another level: the picture changes, what happens does
    /// not. Without effects the bursts going are dropped, and an emitter
    /// plays only from the level it names.
    pub fn set_level(&mut self, level: usize) {
        let level = level.min(LEVELS.len() - 1);
        if level == self.level {
            return;
        }
        self.level = level;
        if !self.effects() {
            self.bursts.clear();
        }
        // a page on the screen flows again into the canvas the level gives it
        let (w, h) = self.page_canvas();
        if let Some(window) = &mut self.window {
            window.resize(w, h);
        }
        self.dirty = true;
    }

    /// The canvas a page is drawn on at this level, in pixels: the scene,
    /// or twice it at the fine level.
    pub fn page_canvas(&self) -> (u32, u32) {
        let scale = LEVELS[self.level].scale.max(1);
        (self.scene.width * scale, self.scene.height * scale)
    }

    /// The picture is to be drawn again whatever moved: the display came
    /// back from another terminal.
    pub fn touch(&mut self) {
        self.dirty = true;
    }

    /// Whether an emitter of the scene plays at this level.
    fn plays(&self, ambient: &Ambient) -> bool {
        self.effects() && ambient.level as usize <= self.level
    }

    /// Whether the picture changed since the last call: a display draws
    /// only then, so a scene at rest costs nothing.
    pub fn take_dirty(&mut self) -> bool {
        std::mem::replace(&mut self.dirty, false)
    }

    fn sprite_named(&self, name: &str) -> Option<usize> {
        self.sprites
            .iter()
            .position(|s| s.name.as_deref() == Some(name))
    }

    // ---------------------------------------------------------------- events

    /// An event of the Hive: the rule on it runs, action by action. An
    /// action whose `{field}` the event does not provide, or whose target
    /// no sprite is named, is left out, as the rules leave out an offer
    /// they cannot fill in.
    pub fn event(&mut self, kind: &str, fields: &Fields) {
        self.events
            .push(json!({"kind": "event", "event": kind, "fields": fields}));
        self.dirty = true;
        let Some(rule) = self.scene.rule(kind) else {
            return;
        };
        let actions = rule.actions.clone();
        for action in &actions {
            self.apply(action, fields);
        }
    }

    fn apply(&mut self, action: &Action, fields: &Fields) {
        match action {
            Action::Animate { target, name } => {
                let Some(i) = self.target(target, fields) else {
                    return;
                };
                let sheet = &self.scene.sheets[self.sprites[i].sheet];
                let Some(def) = sheet.animations.get(name) else {
                    return;
                };
                self.sprites[i].frame = def.frames[0];
                self.sprites[i].anim = Some(Anim {
                    name: name.clone(),
                    frames: def.frames.clone(),
                    fps: def.fps,
                    looping: def.looping,
                    index: 0,
                    acc: 0.0,
                    done: false,
                });
            }
            Action::Frame { target, frame } => {
                if let Some(i) = self.target(target, fields) {
                    let frames = self.scene.sheets[self.sprites[i].sheet].frames;
                    if *frame < frames {
                        self.sprites[i].frame = *frame;
                        self.sprites[i].anim = None;
                    }
                }
            }
            Action::Show { target, visible } => {
                if let Some(i) = self.target(target, fields) {
                    self.sprites[i].visible = *visible;
                }
            }
            Action::Tween {
                target,
                property,
                to,
                from,
                seconds,
                trans,
                ease,
                repeat,
                yoyo,
            } => {
                let Some(i) = self.target(target, fields) else {
                    return;
                };
                let now = self.read(i, *property);
                self.tweens
                    .retain(|t| !(t.sprite == i && t.property == *property));
                self.tweens.push(Tween {
                    sprite: i,
                    property: *property,
                    from: from.unwrap_or(now),
                    to: *to,
                    ticks: ((seconds * TICK_RATE).round() as u32).max(1),
                    t: 0,
                    trans: *trans,
                    ease: *ease,
                    repeat: *repeat,
                    yoyo: *yoyo,
                });
            }
            Action::Emit {
                particles,
                at,
                dx,
                dy,
            } => {
                if !self.effects() {
                    return;
                }
                let Some(i) = self.target(at, fields) else {
                    return;
                };
                let (x, y) = (
                    self.sprites[i].x + *dx as f32,
                    self.sprites[i].y + *dy as f32,
                );
                self.seeds += 1;
                self.bursts.push(Emitter::new(
                    self.scene.particles[particles].clone(),
                    x,
                    y,
                    0.0,
                    self.seeds,
                ));
            }
            Action::Say { text, seconds } => {
                if let Some(line) = fill(text, fields) {
                    self.say(line, *seconds);
                }
            }
        }
    }

    fn target(&self, target: &str, fields: &Fields) -> Option<usize> {
        let name = fill(target, fields)?;
        self.sprite_named(&name)
    }

    pub fn say(&mut self, line: String, seconds: f32) {
        self.notices.push_back(line.clone());
        while self.notices.len() > 50 {
            self.notices.pop_front();
        }
        self.events.push(json!({"kind": "say", "text": line}));
        self.toast = Some((line, ((seconds * TICK_RATE).round() as u32).max(1)));
    }

    fn read(&self, i: usize, property: Property) -> f32 {
        let s = &self.sprites[i];
        match property {
            Property::X => s.x,
            Property::Y => s.y,
            Property::Scale => s.scale,
            Property::Alpha => s.alpha,
        }
    }

    fn write(&mut self, i: usize, property: Property, v: f32) {
        let s = &mut self.sprites[i];
        match property {
            Property::X => s.x = v,
            Property::Y => s.y = v,
            Property::Scale => s.scale = v,
            Property::Alpha => s.alpha = v,
        }
    }

    // ---------------------------------------------------------------- offers

    /// The Hive offered something: one row an administrator may approve.
    pub fn offer(
        &mut self,
        notification: Uuid,
        suggestion: u32,
        title: String,
        action: Option<HiveAction>,
    ) {
        let dangerous = action.as_ref().is_some_and(|a| a.is_dangerous());
        self.offers.push(Offer {
            notification,
            suggestion,
            title: title.clone(),
            action,
            dangerous,
            armed: false,
            outcome: None,
        });
        self.events.push(json!({"kind": "offer", "title": title}));
        self.dirty = true;
    }

    /// The actuator answered: the offer it was about is done, or failed.
    /// Returns the event's fields when a row matched.
    pub fn done(
        &mut self,
        action: &HiveAction,
        success: bool,
        output: Option<&str>,
    ) -> Option<Fields> {
        let i = self
            .offers
            .iter()
            .position(|o| o.outcome == Some(Outcome::Sent) && o.action.as_ref() == Some(action))?;
        self.offers[i].outcome = Some(if success {
            Outcome::Succeeded
        } else {
            Outcome::Failed
        });
        self.dirty = true;
        let mut fields = action_fields(action);
        fields.insert("output".into(), output.unwrap_or("").to_string());
        Some(fields)
    }

    /// A key from the administrator: with a page open, the page's (the
    /// keyboard is its alone); on the scene, it moves the focus, approves,
    /// dismisses.
    pub fn key(&mut self, key: Key) -> Option<Outgoing> {
        self.dirty = true;
        self.events.push(json!({"kind": "key", "key": key.name()}));
        if let Some(w) = &mut self.window {
            w.key(key, self.tick);
            self.drain_window();
            return None;
        }
        match key {
            Key::Up => {
                self.focus = self.focus.saturating_sub(1);
                self.disarm_others();
                None
            }
            Key::Down => {
                if self.focus + 1 < self.offers.len() {
                    self.focus += 1;
                }
                self.disarm_others();
                None
            }
            Key::Enter => {
                let i = self.focus;
                let offer = self.offers.get_mut(i)?;
                if offer.outcome.is_some() {
                    return None;
                }
                if offer.dangerous && !offer.armed {
                    offer.armed = true;
                    return None;
                }
                offer.armed = false;
                offer.outcome = Some(if offer.action.is_some() {
                    Outcome::Sent
                } else {
                    Outcome::NoAction
                });
                self.events
                    .push(json!({"kind": "approve", "title": offer.title}));
                Some(Outgoing::Approve {
                    notification: offer.notification,
                    suggestion: offer.suggestion,
                    confirmed: true,
                })
            }
            Key::Escape => {
                if self.offers.is_empty() {
                    return None;
                }
                let offer = self.offers.remove(self.focus.min(self.offers.len() - 1));
                if self.focus >= self.offers.len() {
                    self.focus = self.offers.len().saturating_sub(1);
                }
                self.events
                    .push(json!({"kind": "dismiss", "title": offer.title}));
                // the rows of one notification go together: dismissing one
                // dismisses the notification, as on the dashboard
                self.offers.retain(|o| o.notification != offer.notification);
                if self.focus >= self.offers.len() {
                    self.focus = self.offers.len().saturating_sub(1);
                }
                Some(Outgoing::Dismiss {
                    notification: offer.notification,
                })
            }
            _ => None,
        }
    }

    fn disarm_others(&mut self) {
        let focus = self.focus;
        for (i, o) in self.offers.iter_mut().enumerate() {
            if i != focus {
                o.armed = false;
            }
        }
    }

    // ---------------------------------------------------------------- a page on the screen

    /// A page to show over the scene, as `quantum pixel` sends it (title,
    /// flash, view tree). The same page shown again (after an action)
    /// keeps the focus on the element it was on, when the new page has it.
    pub fn show(&mut self, page: &Value) {
        let (w, h) = self.page_canvas();
        let mut window = Window::new(page, w, h);
        let old = self.page_image();
        if let Some(old) = &self.window {
            window.shown = old.shown + 1;
            if let Some((kind, identity)) = old.focused_identity() {
                window.focus_on(&kind, &identity);
            }
        }
        self.events
            .push(json!({"kind": "show", "title": window.title, "shown": window.shown}));
        self.window = Some(window);
        if self.moves() {
            self.motion = Some(match old {
                Some(old) => Motion {
                    kind: MotionKind::Curtain,
                    t: 0,
                    old: Some(old),
                },
                None => Motion {
                    kind: MotionKind::Jelly,
                    t: 0,
                    old: None,
                },
            });
        }
        self.dirty = true;
    }

    /// The page goes: the scene is whole again (after the lamp, when the
    /// page moves).
    pub fn close_window(&mut self) {
        let old = self.page_image();
        if self.window.take().is_some() {
            self.events.push(json!({"kind": "closed"}));
            self.motion = if self.moves() {
                Some(Motion {
                    kind: MotionKind::Lamp,
                    t: 0,
                    old,
                })
            } else {
                None
            };
            self.dirty = true;
        }
    }

    /// Whether pages move: never at the plain level (one core has no
    /// frames to spare), never when switched off.
    fn moves(&self) -> bool {
        self.motion_on && self.effects()
    }

    /// `HIVE_SCREEN_MOTION=off`: pages appear and go at once.
    pub fn set_motion(&mut self, on: bool) {
        self.motion_on = on;
        if !on {
            self.motion = None;
        }
    }

    /// The transition the page is in, as data: its kind and how far.
    pub fn motion(&self) -> Option<Value> {
        self.motion
            .as_ref()
            .map(|m| json!({"kind": m.kind.name(), "t": m.t, "ticks": m.kind.ticks()}))
    }

    /// The page drawn on a canvas of its own, transparent around it, with
    /// its frame: what the transitions bend, scale and mask.
    fn page_image(&self) -> Option<(Image, Rect)> {
        let w = self.window.as_ref()?;
        let (cw, ch) = self.page_canvas();
        let mut canvas = Canvas::new(cw, ch, 1);
        w.draw(&mut canvas.band(), &self.scene.font, self.tick);
        Some((canvas.image, w.frame))
    }

    /// The page on the screen, when one is.
    pub fn window(&self) -> Option<&Window> {
        self.window.as_ref()
    }

    /// The window's events go to the page's runtime and into the events a
    /// test sees; `close` (Esc) closes the window here, the runtime only
    /// hears of it.
    fn drain_window(&mut self) {
        let Some(w) = &mut self.window else {
            return;
        };
        let events = w.take_events();
        let mut close = false;
        for e in events {
            if e.get("event").and_then(Value::as_str) == Some("close") {
                close = true;
            }
            let mut seen = e.clone();
            seen["kind"] = json!("pixel");
            self.events.push(seen);
            self.pixel_out.push(e);
        }
        if close {
            self.close_window();
        }
    }

    /// The events the page's runtime is to hear, cleared.
    pub fn take_pixel_events(&mut self) -> Vec<Value> {
        std::mem::take(&mut self.pixel_out)
    }

    // ---------------------------------------------------------------- time

    /// One tick: animations, tweens, effects and the toast advance.
    pub fn tick(&mut self) {
        self.tick += 1;
        if !self.tweens.is_empty()
            || !self.bursts.is_empty()
            || self.emitters.iter().any(|a| self.plays(a))
        {
            self.dirty = true;
        }
        for sprite in &mut self.sprites {
            if let Some(anim) = &mut sprite.anim {
                if anim.done {
                    continue;
                }
                anim.acc += anim.fps / TICK_RATE;
                while anim.acc >= 1.0 {
                    anim.acc -= 1.0;
                    if anim.index + 1 < anim.frames.len() {
                        anim.index += 1;
                    } else if anim.looping {
                        anim.index = 0;
                    } else {
                        anim.done = true;
                        self.events
                            .push(json!({"kind": "animation-end", "sprite": sprite.name, "animation": anim.name}));
                        break;
                    }
                }
                if sprite.frame != anim.frames[anim.index] {
                    sprite.frame = anim.frames[anim.index];
                    self.dirty = true;
                }
            }
        }
        let mut finished = Vec::new();
        let mut writes = Vec::new();
        for (n, tw) in self.tweens.iter_mut().enumerate() {
            tw.t += 1;
            let v = interpolate(
                tw.from,
                tw.to - tw.from,
                tw.t as f32,
                tw.ticks as f32,
                tw.trans,
                tw.ease,
            );
            writes.push((tw.sprite, tw.property, v));
            if tw.t < tw.ticks {
                continue;
            }
            if tw.repeat == 0 {
                finished.push(n);
                continue;
            }
            if tw.repeat > 0 {
                tw.repeat -= 1;
            }
            tw.t = 0;
            if tw.yoyo {
                std::mem::swap(&mut tw.from, &mut tw.to);
            } else {
                writes.push((tw.sprite, tw.property, tw.from));
            }
        }
        for (i, p, v) in writes {
            self.write(i, p, v);
        }
        for n in finished.into_iter().rev() {
            let tw = self.tweens.remove(n);
            self.events
                .push(json!({"kind": "tween-end", "sprite": self.sprites[tw.sprite].name}));
        }
        let (effects, level) = (self.effects(), self.level as u32);
        for a in &mut self.emitters {
            if effects && a.level <= level {
                a.emitter.tick();
            }
        }
        for b in &mut self.bursts {
            b.tick();
        }
        self.bursts.retain(|b| !b.finished());
        if let Some((_, left)) = &mut self.toast {
            *left -= 1;
            if *left == 0 {
                self.toast = None;
                self.dirty = true;
            }
        }
        if let Some(w) = &mut self.window {
            if w.tick(self.tick) {
                self.dirty = true;
            }
            self.drain_window();
        }
        if let Some(m) = &mut self.motion {
            m.t += 1;
            self.dirty = true;
            if m.t >= m.kind.ticks() {
                self.motion = None;
            }
        }
    }

    // ---------------------------------------------------------------- the picture

    /// The picture, drawn in `threads` bands at once (in this thread when
    /// there is one): the same picture whatever the count.
    pub fn render(&self, canvas: &mut Canvas, threads: usize) {
        // the page, drawn once for every band
        let page = self.page_image();
        let page = page.as_ref();
        if threads <= 1 {
            self.draw(&mut canvas.band(), page);
            return;
        }
        let mut bands = canvas.bands(threads);
        std::thread::scope(|s| {
            for band in &mut bands {
                s.spawn(move || self.draw(band, page));
            }
        });
    }

    /// One band of the picture: every node in order, clipped to its rows;
    /// the page over it, in its transition if one runs.
    pub fn draw(&self, canvas: &mut Band, page: Option<&(Image, Rect)>) {
        canvas.clear(self.scene.background);
        let font = &self.scene.font;
        let mut sprite_index = 0;
        let mut emitter_index = 0;
        for node in &self.scene.nodes {
            match node {
                Node::Sprite { .. } => {
                    let s = &self.sprites[sprite_index];
                    sprite_index += 1;
                    if !s.visible {
                        continue;
                    }
                    let sheet = &self.scene.sheets[s.sheet];
                    let (sx, sy) = sheet.cell(s.frame);
                    canvas.blit(
                        &sheet.image,
                        sx,
                        sy,
                        sheet.tile.0,
                        sheet.tile.1,
                        s.x,
                        s.y,
                        s.alpha,
                        s.scale,
                    );
                }
                Node::Text {
                    value,
                    x,
                    y,
                    color,
                    align,
                } => {
                    let w = font.width_of(value) as i32;
                    let x = match align {
                        Align::Left => *x,
                        Align::Center => x - w / 2,
                        Align::Right => x - w,
                    };
                    canvas.text(font, value, x, *y, *color);
                }
                Node::Emitter { .. } => {
                    let a = &self.emitters[emitter_index];
                    emitter_index += 1;
                    if self.plays(a) {
                        a.emitter.draw(canvas);
                    }
                }
                Node::Offers {
                    x,
                    y,
                    width,
                    rows,
                    color,
                    focus,
                    title,
                } => {
                    let (x, y, width) = self.draw_panel(canvas, *x, *y, *width, *rows, title);
                    self.draw_offers(canvas, x, y, width, *rows, *color, *focus)
                }
                Node::Notices {
                    x,
                    y,
                    width,
                    rows,
                    color,
                    title,
                } => {
                    let (x, y, width) = self.draw_panel(canvas, *x, *y, *width, *rows, title);
                    let fit = font.fit(width);
                    let shown = self
                        .notices
                        .iter()
                        .rev()
                        .take(*rows as usize)
                        .collect::<Vec<_>>();
                    for (n, line) in shown.iter().rev().enumerate() {
                        let text: String = line.chars().take(fit).collect();
                        canvas.text(font, &text, x, y + (n as u32 * font.cell.1) as i32, *color);
                    }
                }
                Node::Bar {
                    side,
                    title,
                    left,
                    right,
                    color,
                    accent,
                } => self.draw_bar(
                    canvas,
                    *side,
                    title,
                    left,
                    right,
                    *color,
                    *accent,
                    page.is_none(),
                ),
            }
        }
        for b in &self.bursts {
            b.draw(canvas);
        }
        // in the canvas's own pixels: the page's font is never a block
        self.draw_page(&mut canvas.unscaled(), page);
        // what the Hive says: in the bar at the bottom, or on a strip of
        // its own; over a page, on the strip, so it is read through the page
        let in_bar = page.is_none() && self.has_bottom_bar();
        if let Some((line, _)) = self.toast.as_ref().filter(|_| !in_bar) {
            let h = TOAST_HEIGHT;
            let y = self.scene.height as i32 - h as i32;
            canvas.fill_rect(0, y, self.scene.width, h, 0xE0101018);
            let fit = font.fit(self.scene.width - 8);
            let text: String = line.chars().take(fit).collect();
            let w = font.width_of(&text) as i32;
            canvas.text(
                font,
                &text,
                (self.scene.width as i32 - w) / 2,
                y + 1,
                0xFFFFFFFF,
            );
        }
    }

    /// The scene dimmed and the page over it: whole, or in its transition.
    fn draw_page(&self, b: &mut Band, page: Option<&(Image, Rect)>) {
        let (cw, ch) = self.page_canvas();
        let dim = |b: &mut Band, alpha: f32| {
            let a = (DIM_ALPHA as f32 * alpha.clamp(0.0, 1.0)).round() as u8;
            if a > 0 {
                b.fill_rect(0, 0, cw, ch, argb(a, 0, 0, 0));
            }
        };
        let Some(m) = &self.motion else {
            if let Some((img, _)) = page {
                dim(b, 1.0);
                b.blit(img, 0, 0, cw, ch, 0.0, 0.0, 1.0, 1.0);
            }
            return;
        };
        let (t, d) = (m.t as f32, m.kind.ticks() as f32);
        match m.kind {
            MotionKind::Jelly => {
                let Some((img, f)) = page else {
                    return;
                };
                let p = interpolate(0.0, 1.0, t, d, Trans::Quad, Ease::Out);
                dim(b, p);
                // the window and its shadow, scaled about the frame's centre
                let k = 0.6 + 0.4 * interpolate(0.0, 1.0, t, d, Trans::Back, Ease::Out);
                let (x, y, w, h) = (f.x as u32, f.y as u32, f.w as u32 + 3, f.h as u32 + 3);
                b.blit(img, x, y, w, h, x as f32, y as f32, 1.0, k.max(0.05));
            }
            MotionKind::Lamp => {
                let Some((img, f)) = &m.old else {
                    return;
                };
                let p = interpolate(0.0, 1.0, t, d, Trans::Quad, Ease::In);
                dim(b, 1.0 - p);
                lamp(b, img, *f, (f.x as f32 + 8.0, ch as f32 - 6.0), p);
            }
            MotionKind::Curtain => {
                dim(b, 1.0);
                if let Some((img, _)) = page {
                    b.blit(img, 0, 0, cw, ch, 0.0, 0.0, 1.0, 1.0);
                }
                // the old page stays where the dither has not reached
                if let Some((old, f)) = &m.old {
                    let level = (16.0 * t / d) as u8;
                    let (x0, y0) = (f.x as i32, f.y as i32);
                    let (x1, y1) = (x0 + f.w as i32 + 3, y0 + f.h as i32 + 3);
                    for y in y0.max(0)..y1.min(ch as i32) {
                        for x in x0.max(0)..x1.min(cw as i32) {
                            if BAYER[(y % 4) as usize][(x % 4) as usize] >= level {
                                let px = old.get(x as u32, y as u32);
                                if px >> 24 != 0 {
                                    b.fill_rect(x, y, 1, 1, px);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn has_bottom_bar(&self) -> bool {
        self.scene.nodes.iter().any(|n| {
            matches!(
                n,
                Node::Bar {
                    side: Side::Bottom,
                    ..
                }
            )
        })
    }

    /// A panel for rows, when it has a title: the frame, the shadow, the
    /// title bar. Gives where the rows go and how wide they may be; with
    /// no title, the rows go where the node says.
    fn draw_panel(
        &self,
        canvas: &mut Band,
        x: i32,
        y: i32,
        width: u32,
        rows: u32,
        title: &Option<String>,
    ) -> (i32, i32, u32) {
        let Some(title) = title else {
            return (x, y, width);
        };
        let font = &self.scene.font;
        let h = rows * font.cell.1 + PANEL_TOP as u32 + 2;
        canvas.fill_rect(x + 3, y + 3, width, h, SHADOW);
        bevel_out(canvas, x, y, width, h, PANEL_BG, LIGHT, BLACK);
        let inner = width.saturating_sub(2);
        canvas.fill_rect(x + 1, y + 1, inner, font.cell.1, MID);
        canvas.fill_rect(x + 1, y + 1 + font.cell.1 as i32, inner, 1, DARK);
        let fit = font.fit(inner.saturating_sub(6));
        let text: String = title.chars().take(fit).collect();
        canvas.text(font, &text, x + BAR_IN, y + 1, HONEY);
        (
            x + PANEL_IN,
            y + PANEL_TOP,
            width.saturating_sub(2 * PANEL_IN as u32),
        )
    }

    /// A bar across the scene: the title in the accent, the text after
    /// it, the text at the right; at the bottom, what the Hive says
    /// takes the left while it lasts (and no page is over the scene).
    #[allow(clippy::too_many_arguments)]
    fn draw_bar(
        &self,
        canvas: &mut Band,
        side: Side,
        title: &Option<String>,
        left: &Option<String>,
        right: &Option<String>,
        color: u32,
        accent: u32,
        bare: bool,
    ) {
        let font = &self.scene.font;
        let w = self.scene.width;
        let ty = match side {
            Side::Top => {
                canvas.fill_rect(0, 0, w, BAR_TOP_H, BAR_BG);
                canvas.fill_rect(0, 0, w, 1, LIGHT);
                canvas.fill_rect(0, BAR_TOP_H as i32 - 1, w, 1, BAR_LINE);
                2
            }
            Side::Bottom => {
                let y0 = self.scene.height as i32 - BAR_BOTTOM_H as i32;
                canvas.fill_rect(0, y0, w, BAR_BOTTOM_H, BAR_BG);
                canvas.fill_rect(0, y0, w, 1, BAR_LINE);
                y0 + 1
            }
        };
        let right = self.bar_text(right);
        let rw = font.width_of(&right);
        if rw > 0 {
            canvas.text(font, &right, w as i32 - BAR_IN - rw as i32, ty, color);
        }
        // the left: what the Hive says, or the title and the text after it
        let room = (w as i32 - 2 * BAR_IN - rw as i32 - if rw > 0 { font.cell.0 as i32 } else { 0 })
            .max(0) as u32;
        let said = self.toast.as_ref().filter(|_| side == Side::Bottom && bare);
        let mut x = BAR_IN;
        if let Some((line, _)) = said {
            let text: String = line.chars().take(font.fit(room)).collect();
            canvas.text(font, &text, x, ty, TEXT);
            return;
        }
        let title = self.bar_text(title);
        if !title.is_empty() {
            let text: String = title.chars().take(font.fit(room)).collect();
            canvas.text(font, &text, x, ty, accent);
            x += font.width_of(&text) as i32 + font.cell.0 as i32;
        }
        let left = self.bar_text(left);
        let room = (room as i32 - (x - BAR_IN)).max(0) as u32;
        if !left.is_empty() && room > 0 {
            let text: String = left.chars().take(font.fit(room)).collect();
            canvas.text(font, &text, x, ty, color);
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn draw_offers(
        &self,
        canvas: &mut Band,
        x: i32,
        y: i32,
        width: u32,
        rows: u32,
        color: u32,
        focus: u32,
    ) {
        let font = &self.scene.font;
        let fit = font.fit(width);
        let rows = rows as usize;
        let first = if self.focus >= rows {
            self.focus + 1 - rows
        } else {
            0
        };
        for (n, offer) in self.offers.iter().enumerate().skip(first).take(rows) {
            let focused = n == self.focus;
            let mark = if focused { ">" } else { " " };
            let suffix = match (&offer.outcome, offer.armed) {
                (Some(Outcome::Succeeded), _) => " ok",
                (Some(Outcome::Failed), _) => " failed",
                (Some(Outcome::Sent), _) => " ...",
                (Some(Outcome::NoAction), _) => " noted",
                (None, true) => " again?",
                (None, false) => "",
            };
            let line = format!("{}{}{}", mark, offer.title, suffix);
            let text: String = line.chars().take(fit).collect();
            canvas.text(
                font,
                &text,
                x,
                y + (n - first) as i32 * font.cell.1 as i32,
                if focused { focus } else { color },
            );
        }
    }

    // ---------------------------------------------------------------- what a test sees

    /// What the screen shows, as data: the sprites by name, the offers
    /// with their state, the notices, the toast.
    pub fn observe(&self) -> Value {
        let sprites: serde_json::Map<String, Value> = self
            .sprites
            .iter()
            .filter_map(|s| {
                s.name.as_ref().map(|name| {
                    (
                        name.clone(),
                        json!({
                            "frame": s.frame,
                            "x": s.x,
                            "y": s.y,
                            "visible": s.visible,
                            "scale": s.scale,
                            "alpha": s.alpha,
                            "animation": s.anim.as_ref().filter(|a| !a.done).map(|a| a.name.clone()),
                        }),
                    )
                })
            })
            .collect();
        let offers: Vec<Value> = self
            .offers
            .iter()
            .enumerate()
            .map(|(i, o)| {
                json!({
                    "title": o.title,
                    "focus": i == self.focus,
                    "dangerous": o.dangerous,
                    "armed": o.armed,
                    "outcome": o.outcome.as_ref().map(|x| format!("{:?}", x).to_lowercase()),
                })
            })
            .collect();
        json!({
            "tick": self.tick,
            "level": self.level,
            "level_name": LEVELS[self.level].name,
            "sprites": sprites,
            "offers": offers,
            "notices": self.notices.iter().collect::<Vec<_>>(),
            "toast": self.toast.as_ref().map(|(t, _)| t.clone()),
            "tweens": self.tweens.len(),
            "effects": self.bursts.len() + self.emitters.iter().filter(|a| self.plays(a)).count(),
            "window": self.window.as_ref().map(Window::observe),
            "motion": self.motion(),
            "bars": self.observe_bars(),
        })
    }

    /// The bars with their fields filled in, by side.
    fn observe_bars(&self) -> Value {
        let mut bars = serde_json::Map::new();
        for n in &self.scene.nodes {
            if let Node::Bar {
                side,
                title,
                left,
                right,
                ..
            } = n
            {
                let name = match side {
                    Side::Top => "top",
                    Side::Bottom => "bottom",
                };
                bars.insert(
                    name.to_string(),
                    json!({
                        "title": self.bar_text(title),
                        "left": self.bar_text(left),
                        "right": self.bar_text(right),
                    }),
                );
            }
        }
        Value::Object(bars)
    }

    /// The events since the last take, cleared.
    pub fn take_events(&mut self) -> Vec<Value> {
        std::mem::take(&mut self.events)
    }
}

/// The magic lamp: every column of the window's picture converges on
/// `target`, the far side bending first, so the window bends as it is
/// sucked in; `p` from 0 (whole) to 1 (gone).
fn lamp(b: &mut Band, img: &Image, f: Rect, target: (f32, f32), p: f32) {
    let (fx, fy) = (f.x as f32, f.y as f32);
    let (fw, fh) = (f.w as f32 + 3.0, f.h as f32 + 3.0);
    let (tx, ty) = target;
    for col in 0..fw as u32 {
        let s = 0.45 + 0.55 * (col as f32 / fw);
        let q = (p * (0.6 + s)).min(1.0);
        let nx = (tx + (fx + col as f32 - tx) * (1.0 - q)).round() as i32;
        let top = fy + (ty - fy) * q * q;
        let bottom = fy + fh + (ty - fy - fh) * q;
        let h = (bottom - top).round().max(1.0) as u32;
        for dy in 0..h {
            let sy = ((dy as f32 * fh / h as f32) as u32).min(f.h as u32 + 2);
            let px = img.get(f.x as u32 + col, f.y as u32 + sy);
            if px >> 24 != 0 {
                b.fill_rect(nx, top.round() as i32 + dy as i32, 1, 1, px);
            }
        }
    }
}

/// The `done` event's fields from the action that ran: its name in
/// kebab-case and, when it has one, the service or the package it was
/// about. Read off the action's own JSON, so every variant is covered
/// without naming it here.
pub fn action_fields(action: &HiveAction) -> Fields {
    let mut fields = Fields::new();
    if let Ok(Value::Object(map)) = serde_json::to_value(action) {
        if let Some((variant, inner)) = map.into_iter().next() {
            fields.insert("action".into(), kebab(&variant));
            if let Value::Object(params) = inner {
                let is_service = variant.ends_with("Service");
                for (k, v) in params {
                    if let Value::String(s) = v {
                        if k == "name" && is_service {
                            fields.insert("service".into(), s.clone());
                        }
                        if k == "package" || (k == "name" && variant.ends_with("Package")) {
                            fields.insert("package".into(), s.clone());
                        }
                    }
                }
            }
        }
    } else if let Ok(Value::String(variant)) = serde_json::to_value(action) {
        fields.insert("action".into(), kebab(&variant));
    }
    fields
}

fn kebab(variant: &str) -> String {
    let mut out = String::new();
    for (i, c) in variant.chars().enumerate() {
        if c.is_ascii_uppercase() {
            if i > 0 {
                out.push('-');
            }
            out.push(c.to_ascii_lowercase());
        } else {
            out.push(c);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_bars_fields_are_filled_in_and_the_rest_is_left_as_written() {
        let field = |name: &str| match name {
            "clock" => Some("14:32".to_string()),
            "cores" => Some("4".to_string()),
            _ => None,
        };
        assert_eq!(
            fill_fields("{cores} cores · {level} · {clock}", field),
            "4 cores · {level} · 14:32"
        );
        assert_eq!(fill_fields("plain", field), "plain");
        assert_eq!(fill_fields("{clock", field), "{clock");
        assert_eq!(fill_fields("a {{clock}", field), "a {14:32");
        assert_eq!(fill_fields("", field), "");
    }

    #[test]
    fn an_action_tells_its_name_and_its_service_or_package() {
        let f = action_fields(&HiveAction::RestartService {
            name: "nginx".into(),
        });
        assert_eq!(f.get("action").unwrap(), "restart-service");
        assert_eq!(f.get("service").unwrap(), "nginx");
        let f = action_fields(&HiveAction::InstallPackage {
            name: "htop".into(),
            assume_yes: true,
        });
        assert_eq!(f.get("action").unwrap(), "install-package");
        assert_eq!(f.get("package").unwrap(), "htop");
        let f = action_fields(&HiveAction::UpdatePackageLists);
        assert_eq!(f.get("action").unwrap(), "update-package-lists");
        assert!(!f.contains_key("service"));
    }
}
