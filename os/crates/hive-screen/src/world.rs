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
use crate::level::{self, LEVELS};
use crate::particles::Emitter;
use crate::scene::{Action, Align, Node, Property, Scene};
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Key {
    Up,
    Down,
    Enter,
    Escape,
}

impl Key {
    pub fn parse(name: &str) -> Option<Key> {
        Some(match name.to_ascii_lowercase().as_str() {
            "up" => Key::Up,
            "down" => Key::Down,
            "enter" | "return" => Key::Enter,
            "escape" | "esc" => Key::Escape,
            _ => return None,
        })
    }
}

/// Where the toast (`qs:say`) sits: a strip at the bottom of the scene.
const TOAST_HEIGHT: u32 = 12;

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
        self.dirty = true;
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

    /// A key from the administrator: moves the focus, approves, dismisses.
    pub fn key(&mut self, key: Key) -> Option<Outgoing> {
        self.dirty = true;
        self.events
            .push(json!({"kind": "key", "key": format!("{:?}", key).to_lowercase()}));
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
    }

    // ---------------------------------------------------------------- the picture

    /// The picture, drawn in `threads` bands at once (in this thread when
    /// there is one): the same picture whatever the count.
    pub fn render(&self, canvas: &mut Canvas, threads: usize) {
        if threads <= 1 {
            self.draw(&mut canvas.band());
            return;
        }
        let mut bands = canvas.bands(threads);
        std::thread::scope(|s| {
            for band in &mut bands {
                s.spawn(move || self.draw(band));
            }
        });
    }

    /// One band of the picture: every node in order, clipped to its rows.
    pub fn draw(&self, canvas: &mut Band) {
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
                } => self.draw_offers(canvas, *x, *y, *width, *rows, *color, *focus),
                Node::Notices {
                    x,
                    y,
                    width,
                    rows,
                    color,
                } => {
                    let fit = font.fit(*width);
                    let shown = self
                        .notices
                        .iter()
                        .rev()
                        .take(*rows as usize)
                        .collect::<Vec<_>>();
                    for (n, line) in shown.iter().rev().enumerate() {
                        let text: String = line.chars().take(fit).collect();
                        canvas.text(font, &text, *x, y + (n as u32 * font.cell.1) as i32, *color);
                    }
                }
            }
        }
        for b in &self.bursts {
            b.draw(canvas);
        }
        if let Some((line, _)) = &self.toast {
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
        })
    }

    /// The events since the last take, cleared.
    pub fn take_events(&mut self) -> Vec<Value> {
        std::mem::take(&mut self.events)
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
