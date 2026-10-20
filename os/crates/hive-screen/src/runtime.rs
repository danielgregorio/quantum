//! The screen running: the world, the Hive's messages turned into its
//! events and offers, keys turned into approvals, a page brought by
//! `quantum pixel` and its events sent back, a tick at a time.

use crate::hive::Hive;
use crate::pixel::PixelSocket;
use crate::world::{Key, Outgoing, World};
use anyhow::{bail, Context as _, Result};
use hive_common::messages::{HiveMessage, Severity};
use serde_json::Value;
use std::sync::mpsc::TryRecvError;

pub struct Runtime {
    pub world: World,
    pub hive: Option<Hive>,
    pub pixel: Option<PixelSocket>,
    /// What the daemon knows of itself and the world does not: whether
    /// the level is pinned, the keyboard's layout, what a frame costs
    /// (main.rs keeps it current).
    pub about: Value,
    /// The last `status` the page's runtime was told, so it hears of a
    /// change once.
    status_sent: Option<Value>,
}

impl Runtime {
    pub fn new(world: World, hive: Option<Hive>, pixel: Option<PixelSocket>) -> Runtime {
        Runtime {
            world,
            hive,
            pixel,
            about: serde_json::json!({"pinned": false, "keyboard": "us", "frame_ms": 0.0}),
            status_sent: None,
        }
    }

    /// What the screen says of itself to the page's runtime: the level,
    /// the cores, whether pages move, the keyboard, what a frame costs.
    /// Sent when the runtime connects and whenever any of it changes.
    pub fn status(&self) -> Value {
        let mut status = serde_json::json!({
            "event": "status",
            "level": self.world.level(),
            "level_name": crate::level::LEVELS[self.world.level()].name,
            "cores": self.world.facts().cores,
            "motion": self.world.motion_on(),
            "scene": [self.world.scene.width, self.world.scene.height],
        });
        if let (Some(into), Some(from)) = (status.as_object_mut(), self.about.as_object()) {
            for (k, v) in from {
                into.insert(k.clone(), v.clone());
            }
        }
        status
    }

    fn tell_status(&mut self) {
        if !self.pixel.as_ref().is_some_and(|p| p.connected()) {
            self.status_sent = None;
            return;
        }
        let status = self.status();
        if self.status_sent.as_ref() != Some(&status) {
            if let Some(socket) = &mut self.pixel {
                socket.send(&status);
            }
            self.status_sent = Some(status);
        }
    }

    /// One tick: what the Hive and the pixel socket sent meanwhile, the
    /// world's tick, then the window's events to the socket.
    pub fn step(&mut self) -> Result<()> {
        if let Some(socket) = &mut self.pixel {
            for req in socket.poll() {
                if let Err(e) = self.pixel_request(&req) {
                    tracing::warn!("pixel socket: {:#}", e);
                    if let Some(socket) = &mut self.pixel {
                        socket.send(&serde_json::json!({"error": format!("{:#}", e)}));
                    }
                }
            }
        }
        loop {
            let next = match &self.hive {
                Some(h) => h.incoming.try_recv(),
                None => Err(TryRecvError::Empty),
            };
            match next {
                Ok(msg) => self.incoming(msg)?,
                Err(TryRecvError::Empty) => break,
                Err(TryRecvError::Disconnected) => {
                    bail!("the Hive went away: hive-cortex closed the connection")
                }
            }
        }
        self.world.tick();
        self.tell_status();
        self.flush_pixel();
        Ok(())
    }

    /// A request of the pixel socket (or of the play driver): `show` a
    /// page, `close` it.
    pub fn pixel_request(&mut self, req: &Value) -> Result<()> {
        match req.get("op").and_then(Value::as_str) {
            Some("show") => {
                let page = req.get("page").context("show needs page")?;
                if !page.is_object() {
                    bail!("show: page is not an object");
                }
                let title = page.get("title").and_then(Value::as_str).unwrap_or("");
                tracing::info!("page: {}", title);
                self.world.show(page);
            }
            Some("close") => {
                tracing::info!("page closed by its runtime");
                self.world.close_window();
            }
            Some(other) => bail!("no such op: {}", other),
            None => bail!("a request needs op"),
        }
        Ok(())
    }

    /// The window's events, to the page's runtime.
    fn flush_pixel(&mut self) {
        let events = self.world.take_pixel_events();
        if let Some(socket) = &mut self.pixel {
            for e in &events {
                socket.send(e);
            }
        }
    }

    /// A message of the Hive: a notice becomes the event it is about (and
    /// an `offer`, with a row per suggestion, when it carries any); the
    /// actuator's answer becomes `done`.
    pub fn incoming(&mut self, msg: HiveMessage) -> Result<()> {
        match msg {
            HiveMessage::Notification {
                id,
                title,
                body,
                severity,
                actions,
                kind,
                mut fields,
                ..
            } => {
                fields.insert("title".into(), title.clone());
                fields.insert("body".into(), body);
                fields.insert("severity".into(), severity_name(severity).into());
                if actions.is_empty() {
                    let kind = kind.unwrap_or_else(|| "notice".to_string());
                    tracing::info!("event: {} ({})", kind, title);
                    self.world.event(&kind, &fields);
                } else {
                    // the Hive's own suggestions are an `offer`; a user's
                    // request comes as one too, under its own name
                    let count = actions.len();
                    for s in actions {
                        tracing::info!("offer: {}", s.title);
                        self.world.offer(id, s.id, s.title, s.action);
                    }
                    fields.insert("count".into(), count.to_string());
                    let kind = kind.unwrap_or_else(|| "offer".to_string());
                    tracing::info!("event: {} ({})", kind, title);
                    self.world.event(&kind, &fields);
                }
            }
            HiveMessage::ActionResponse {
                action,
                success,
                output,
                ..
            } => {
                if let Some(fields) = self.world.done(&action, success, output.as_deref()) {
                    self.world
                        .event(if success { "done" } else { "failed" }, &fields);
                }
            }
            _ => {}
        }
        Ok(())
    }

    /// A key, by name (up, down, left, right, enter, escape, tab,
    /// shift-tab, home, end, backspace, delete, space, pgup, pgdn, f1, f5,
    /// ctrl-u, or one character).
    pub fn key(&mut self, name: &str) -> Result<()> {
        let Some(key) = Key::parse(name) else {
            bail!(
                "no such key: {} (up, down, left, right, enter, escape, tab, shift-tab, home, end, backspace, delete, space, pgup, pgdn, f1, f5, ctrl-u, or one character)",
                name
            );
        };
        self.press(key)
    }

    /// Text typed, a character a key (a space is the Space key).
    pub fn type_text(&mut self, text: &str) -> Result<()> {
        for c in text.chars() {
            let key = match c {
                ' ' => Key::Space,
                '\n' => Key::Enter,
                '\t' => Key::Tab,
                c if c.is_control() => continue,
                c => Key::Char(c),
            };
            self.press(key)?;
        }
        Ok(())
    }

    /// A key.
    pub fn press(&mut self, key: Key) -> Result<()> {
        if let Some(out) = self.world.key(key) {
            let msg = match out {
                Outgoing::Approve {
                    notification,
                    suggestion,
                    confirmed,
                } => HiveMessage::UserAction {
                    notification_id: notification,
                    suggestion_id: suggestion,
                    confirmed,
                },
                Outgoing::Dismiss { notification } => HiveMessage::UserDismiss {
                    notification_id: notification,
                },
            };
            if let Some(h) = &mut self.hive {
                h.send(&msg)?;
            }
        }
        self.flush_pixel();
        Ok(())
    }
}

fn severity_name(s: Severity) -> &'static str {
    match s {
        Severity::Info => "info",
        Severity::Notice => "notice",
        Severity::Warning => "warning",
        Severity::Error => "error",
        Severity::Critical => "critical",
    }
}
