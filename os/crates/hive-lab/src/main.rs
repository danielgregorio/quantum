//! hive-lab: the Hive in a box, driven one JSON line at a time.
//!
//! ```text
//! sudo target/debug/hive-lab            # reads requests on stdin
//! sudo target/debug/hive-lab --play tests/lab/nginx-crash.jsonl
//! ```
//!
//! Each line on stdin is a request, `{"op": ..., ...}`, and gets one line
//! back, `{"ok": true, ...}` or `{"ok": false, "error": ...}`:
//!
//! - `start` (`synapse`: true): hive-cortex, hive-synapse and the four roles.
//! - `inject` (`message`: a HiveMessage as JSON): what a nerve observed.
//!   Ready made: `crash` (`service`, `exit_code`, `restarts`, `logs`),
//!   `port_conflict` (`port`, `requested_by`, `held_by`), `disk_low`
//!   (`mount`, `percent`), `command` (`cmd`, `uid`).
//! - `ask` (`text`): grove asks a question. `not_found` (`command`,
//!   `package`): grove could not find a program. `anonymous` (`on`).
//! - `send` (`as`: nerve|actuator|shell|dashboard, `message`): anything.
//! - `approve` (`notification`, `suggestion`: the latest offered when left
//!   out; `as`: dashboard, or shell to see a user refused) and `dismiss`
//!   (`notification`): the dashboard's answers.
//! - `observe`: what every role received since the last look.
//! - `until` (`to`, `type`, `contains`, `excludes`, `timeout`: 5): waits for
//!   the first new message that matches; with `--play`, a miss fails the
//!   tape. `excludes` is text the message must not hold (exact case).
//! - `none` (`to`, `type`, `contains`, `within`: 1): nothing that matches
//!   arrives in that time (what must not happen: an action nobody approved).
//! - `log_until` (`daemon`, `contains`, `timeout`: 5): a daemon logs a line
//!   with that text.
//! - `tui` (`app`: dashboard|grove, `rows`: 30, `cols`: 100): the real
//!   program in a pseudo-terminal (grove as the lab's user, the dashboard
//!   as root). `view` (`app`): its screen as text. `keys` (`app`, `keys`:
//!   ["Down", "Enter", "text"...]): typing. `until_screen` (`app`,
//!   `contains`, `excludes`, `timeout`: 5): waits until the screen shows
//!   it (and not `excludes`).
//! - `log` (`daemon`: cortex|synapse, `lines`: 30).
//! - `end`.
//!
//! With `--record FILE`, every request is also appended to FILE: a session
//! becomes a tape that `--play` runs again as a test.

mod agent;

use anyhow::{bail, Context as _, Result};
use hive_common::messages::HiveMessage;
use hive_lab::{Event, Lab, Options, Role};
use serde_json::{json, Value};
use std::io::Write as _;
use std::path::PathBuf;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};

#[tokio::main]
async fn main() -> Result<()> {
    if std::env::var_os("HIVE_LAB_AGENT").is_some() {
        return agent::run().await;
    }
    let mut args = std::env::args().skip(1);
    let (mut play, mut record, mut bin_dir) = (None, None, None);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--play" => play = args.next().map(PathBuf::from),
            "--record" => record = args.next().map(PathBuf::from),
            "--bin-dir" => bin_dir = args.next().map(PathBuf::from),
            "-h" | "--help" => {
                println!("hive-lab [--bin-dir DIR] [--record FILE] [--play FILE]  (requests on stdin, one JSON per line)");
                return Ok(());
            }
            other => bail!("unknown argument {}", other),
        }
    }
    let exe = std::env::current_exe()?;
    let bin_dir = bin_dir.unwrap_or_else(|| exe.parent().map(PathBuf::from).unwrap_or_default());
    let mut driver = Driver {
        lab: None,
        bin_dir,
        exe,
    };

    let mut lines: Box<dyn Iterator<Item = String>> = match &play {
        Some(tape) => Box::new(
            std::fs::read_to_string(tape)
                .with_context(|| format!("cannot read {}", tape.display()))?
                .lines()
                .map(str::to_string)
                .collect::<Vec<_>>()
                .into_iter(),
        ),
        None => Box::new(std::iter::empty()),
    };
    let mut stdin = BufReader::new(tokio::io::stdin()).lines();
    let mut failed = false;
    loop {
        let line = if play.is_some() {
            match lines.next() {
                Some(l) => l,
                None => break,
            }
        } else {
            match stdin.next_line().await? {
                Some(l) => l,
                None => break,
            }
        };
        if line.trim().is_empty() || line.trim_start().starts_with("//") {
            continue;
        }
        let reply = match serde_json::from_str::<Value>(&line) {
            Ok(req) => {
                if let Some(path) = &record {
                    let mut f = std::fs::OpenOptions::new()
                        .create(true)
                        .append(true)
                        .open(path)?;
                    writeln!(f, "{}", line.trim())?;
                }
                let id = req.get("id").cloned();
                let mut reply = match driver.handle(&req).await {
                    Ok(v) => v,
                    Err(e) => json!({"ok": false, "error": format!("{:#}", e)}),
                };
                if let (Some(id), Value::Object(map)) = (id, &mut reply) {
                    map.insert("id".into(), id);
                }
                reply
            }
            Err(e) => json!({"ok": false, "error": format!("not JSON: {}", e)}),
        };
        failed |= reply.get("ok") == Some(&Value::Bool(false));
        println!("{}", reply);
        if play.is_some() && failed {
            break;
        }
    }
    if let Some(lab) = driver.lab.take() {
        lab.end().await;
    }
    if play.is_some() && failed {
        std::process::exit(1);
    }
    Ok(())
}

struct Driver {
    lab: Option<Lab>,
    bin_dir: PathBuf,
    exe: PathBuf,
}

impl Driver {
    fn lab(&mut self) -> Result<&mut Lab> {
        self.lab
            .as_mut()
            .context("no lab yet: send {\"op\": \"start\"} first")
    }

    async fn handle(&mut self, req: &Value) -> Result<Value> {
        let op = req
            .get("op")
            .and_then(Value::as_str)
            .context("a request needs op")?;
        let s = |k: &str| req.get(k).and_then(Value::as_str);
        let n = |k: &str| req.get(k).and_then(Value::as_f64);
        match op {
            "start" => {
                if let Some(old) = self.lab.take() {
                    old.end().await;
                }
                let synapse = req.get("synapse").and_then(Value::as_bool).unwrap_or(true);
                let lab = Lab::start(Options {
                    bin_dir: self.bin_dir.clone(),
                    agent_exe: self.exe.clone(),
                    synapse,
                })
                .await?;
                let dir = lab.dir().display().to_string();
                self.lab = Some(lab);
                Ok(
                    json!({"ok": true, "dir": dir, "roles": ["nerve", "actuator", "shell", "dashboard"], "synapse": synapse}),
                )
            }
            "inject" => {
                let msg: HiveMessage = serde_json::from_value(
                    req.get("message")
                        .cloned()
                        .context("inject needs message")?,
                )?;
                self.send(Role::Nerve, msg).await
            }
            "crash" => {
                let logs: Vec<String> = req
                    .get("logs")
                    .and_then(Value::as_array)
                    .map(|a| {
                        a.iter()
                            .filter_map(|v| v.as_str().map(str::to_string))
                            .collect()
                    })
                    .unwrap_or_default();
                let logs: Vec<&str> = logs.iter().map(String::as_str).collect();
                let msg = hive_lab::service_crash(
                    s("service").context("crash needs service")?,
                    n("exit_code").unwrap_or(1.0) as i32,
                    n("restarts").unwrap_or(3.0) as u32,
                    &logs,
                );
                self.send(Role::Nerve, msg).await
            }
            "port_conflict" => {
                let msg = hive_lab::port_conflict(
                    n("port").context("port_conflict needs port")? as u16,
                    s("requested_by").unwrap_or("app"),
                    s("held_by").unwrap_or("nginx"),
                );
                self.send(Role::Nerve, msg).await
            }
            "disk_low" => {
                self.send(
                    Role::Nerve,
                    hive_lab::disk_low(
                        s("mount").unwrap_or("/"),
                        n("percent").unwrap_or(95.0) as f32,
                    ),
                )
                .await
            }
            "command" => {
                let msg = hive_lab::command_observed(
                    s("cmd").context("command needs cmd")?,
                    n("uid").unwrap_or(61010.0) as u32,
                );
                self.send(Role::Nerve, msg).await
            }
            "ask" => {
                self.send(
                    Role::Shell,
                    hive_lab::user_query(s("text").context("ask needs text")?),
                )
                .await
            }
            "not_found" => {
                let msg = HiveMessage::CommandNotFound {
                    command: s("command").context("not_found needs command")?.to_string(),
                    package: s("package")
                        .or(s("command"))
                        .unwrap_or_default()
                        .to_string(),
                };
                self.send(Role::Shell, msg).await
            }
            "anonymous" => {
                self.send(
                    Role::Shell,
                    hive_lab::anonymous(req.get("on").and_then(Value::as_bool).unwrap_or(true)),
                )
                .await
            }
            "send" => {
                let role = Role::parse(s("as").context("send needs as")?)
                    .context("as: nerve, actuator, shell or dashboard")?;
                let msg: HiveMessage = serde_json::from_value(
                    req.get("message").cloned().context("send needs message")?,
                )?;
                self.send(role, msg).await
            }
            "approve" | "dismiss" => {
                let lab = self.lab()?;
                let (notification, suggestion) = match s("notification") {
                    Some(id) => (
                        id.parse::<uuid::Uuid>()?,
                        n("suggestion").unwrap_or(1.0) as u32,
                    ),
                    None => latest_offer(&lab.all_events())
                        .context("no notification with suggestions has reached the dashboard")?,
                };
                let suggestion = n("suggestion").map(|v| v as u32).unwrap_or(suggestion);
                let msg = if op == "approve" {
                    HiveMessage::UserAction {
                        notification_id: notification,
                        suggestion_id: suggestion,
                        confirmed: true,
                    }
                } else {
                    HiveMessage::UserDismiss {
                        notification_id: notification,
                    }
                };
                let role = match s("as") {
                    Some(r) => Role::parse(r).context("as: dashboard or shell")?,
                    None => Role::Dashboard,
                };
                self.send(role, msg).await
            }
            "observe" => {
                let events = self.lab()?.take_new();
                Ok(json!({"ok": true, "events": events}))
            }
            "until" => {
                let matches = matcher(req)?;
                let timeout = Duration::from_secs_f64(n("timeout").unwrap_or(5.0));
                match self.lab()?.until(matches, timeout).await {
                    Ok((event, before)) => {
                        Ok(json!({"ok": true, "event": event, "before": before}))
                    }
                    Err(e) => {
                        let lab = self.lab()?;
                        Ok(
                            json!({"ok": false, "error": format!("until {}: {}", req, e), "seen": lab.all_events().len(), "cortex": lab.log("cortex", 15)}),
                        )
                    }
                }
            }
            "none" => {
                let matches = matcher(req)?;
                let within = Duration::from_secs_f64(n("within").unwrap_or(1.0));
                match self.lab()?.until(matches, within).await {
                    Ok((event, _)) => Ok(
                        json!({"ok": false, "error": format!("none {}: it arrived", req), "event": event}),
                    ),
                    Err(_) => Ok(json!({"ok": true})),
                }
            }
            "log_until" => {
                let daemon = s("daemon").unwrap_or("cortex").to_string();
                let text = s("contains")
                    .context("log_until needs contains")?
                    .to_string();
                let timeout = Duration::from_secs_f64(n("timeout").unwrap_or(5.0));
                let lab = self.lab()?;
                let deadline = std::time::Instant::now() + timeout;
                loop {
                    if let Some(line) = lab.log(&daemon, 10_000).lines().find(|l| l.contains(&text))
                    {
                        return Ok(json!({"ok": true, "line": line}));
                    }
                    if std::time::Instant::now() > deadline {
                        return Ok(
                            json!({"ok": false, "error": format!("{} never logged {:?}", daemon, text), "log": lab.log(&daemon, 15)}),
                        );
                    }
                    tokio::time::sleep(Duration::from_millis(25)).await;
                }
            }
            "tui" => {
                let app = s("app")
                    .context("tui needs app: dashboard or grove")?
                    .to_string();
                let rows = n("rows").unwrap_or(30.0) as u16;
                let cols = n("cols").unwrap_or(100.0) as u16;
                self.lab()?.start_tui(&app, rows, cols).await?;
                Ok(json!({"ok": true, "app": app, "rows": rows, "cols": cols}))
            }
            "view" => {
                let screen = self.lab()?.screen(s("app").context("view needs app")?)?;
                Ok(json!({"ok": true, "screen": screen.text, "cursor": screen.cursor}))
            }
            "keys" => {
                let app = s("app").context("keys needs app")?.to_string();
                let mut keys: Vec<String> = req
                    .get("keys")
                    .and_then(Value::as_array)
                    .map(|a| {
                        a.iter()
                            .filter_map(|v| v.as_str().map(str::to_string))
                            .collect()
                    })
                    .unwrap_or_default();
                if let Some(text) = s("text") {
                    keys.push(text.to_string());
                }
                self.lab()?.keys(&app, &keys)?;
                Ok(json!({"ok": true, "typed": keys.len()}))
            }
            "until_screen" => {
                let app = s("app").context("until_screen needs app")?.to_string();
                let text = s("contains")
                    .context("until_screen needs contains")?
                    .to_string();
                let timeout = Duration::from_secs_f64(n("timeout").unwrap_or(5.0));
                match self
                    .lab()?
                    .until_screen(&app, &text, s("excludes"), timeout)
                    .await
                {
                    Ok(screen) => Ok(json!({"ok": true, "screen": screen.text})),
                    Err(e) => Ok(json!({"ok": false, "error": format!("{:#}", e)})),
                }
            }
            "log" => {
                let daemon = s("daemon").unwrap_or("cortex").to_string();
                let lines = n("lines").unwrap_or(30.0) as usize;
                Ok(json!({"ok": true, "log": self.lab()?.log(&daemon, lines)}))
            }
            "end" => {
                if let Some(lab) = self.lab.take() {
                    lab.end().await;
                }
                Ok(json!({"ok": true}))
            }
            other => bail!("unknown op {:?}", other),
        }
    }

    async fn send(&mut self, role: Role, msg: HiveMessage) -> Result<Value> {
        let kind = msg.type_name().to_string();
        self.lab()?.send(role, &msg).await?;
        Ok(json!({"ok": true, "sent": kind, "as": role}))
    }
}

/// What `until` and `none` look for: who received it (`to`), the message's
/// variant (`type`), a piece of its JSON (`contains`, any case) and a piece
/// it must not hold (`excludes`, exact case).
fn matcher(req: &Value) -> Result<impl Fn(&Event) -> bool> {
    let s = |k: &str| req.get(k).and_then(Value::as_str);
    let to = s("to")
        .map(|r| Role::parse(r).context("to: nerve, actuator, shell or dashboard"))
        .transpose()?;
    let kind = s("type").map(str::to_string);
    let contains = s("contains").map(str::to_lowercase);
    let excludes = s("excludes").map(str::to_string);
    Ok(move |e: &Event| {
        to.map_or(true, |r| e.to == r)
            && kind.as_ref().map_or(true, |k| &e.kind == k)
            && contains
                .as_ref()
                .map_or(true, |c| e.message.to_string().to_lowercase().contains(c))
            && excludes
                .as_ref()
                .map_or(true, |x| !e.message.to_string().contains(x.as_str()))
    })
}

/// The newest notification the dashboard received that offered something:
/// its id and its first suggestion's id.
fn latest_offer(events: &[Event]) -> Option<(uuid::Uuid, u32)> {
    events.iter().rev().find_map(|e| {
        if e.to != Role::Dashboard || e.kind != "Notification" {
            return None;
        }
        let n = &e.message["Notification"];
        let first = n["actions"].as_array()?.first()?;
        Some((
            n["id"].as_str()?.parse().ok()?,
            first["id"].as_u64()? as u32,
        ))
    })
}
