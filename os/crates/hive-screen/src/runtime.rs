//! The screen running: the world, the Hive's messages turned into its
//! events and offers, keys turned into approvals, a tick at a time.

use crate::hive::Hive;
use crate::world::{Key, Outgoing, World};
use anyhow::{bail, Result};
use hive_common::messages::{HiveMessage, Severity};
use std::sync::mpsc::TryRecvError;

pub struct Runtime {
    pub world: World,
    pub hive: Option<Hive>,
}

impl Runtime {
    pub fn new(world: World, hive: Option<Hive>) -> Runtime {
        Runtime { world, hive }
    }

    /// One tick: what the Hive sent meanwhile, then the world's tick.
    pub fn step(&mut self) -> Result<()> {
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
        Ok(())
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
                    let count = actions.len();
                    for s in actions {
                        tracing::info!("offer: {}", s.title);
                        self.world.offer(id, s.id, s.title, s.action);
                    }
                    fields.insert("count".into(), count.to_string());
                    self.world.event("offer", &fields);
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

    /// A key, by name (up, down, enter, escape).
    pub fn key(&mut self, name: &str) -> Result<()> {
        let Some(key) = Key::parse(name) else {
            bail!("no such key: {} (up, down, enter, escape)", name);
        };
        self.press(key)
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
