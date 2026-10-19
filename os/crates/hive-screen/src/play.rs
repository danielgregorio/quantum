//! The screen driven from stdin, for the lab and the tests: one JSON
//! request a line, one JSON answer a line (prefixed `QPP `, as the games'
//! play driver answers). The screen stands still between requests.
//!
//! ```text
//! {"op":"observe"}                                   what it shows, as data
//! {"op":"act","tap":["down","enter"],"ticks":30}      keys, then so many ticks
//! {"op":"until","toast":"stopped","max_ticks":600}   ticks, in real time, until a condition holds
//! {"op":"until","offer":"Restart nginx"} / {"op":"until","event":"done"} / {"op":"until","sprite":"nginx","frame":0}
//! {"op":"until","notice":"stopped"}
//! {"op":"frame","path":"out.png"}                    the picture of now
//! {"op":"frame","expect":"ref.png"}                  compared with a reference, pixel for pixel
//! {"op":"frame","expect":"ref.png","bands":4}        drawn in that many bands at once, as the daemon does
//! {"op":"level","level":2}                           the presentation level to play at (0 plain, 1 effects, 2 fine)
//! {"op":"inject","message":{...}}                    a HiveMessage, as if the Hive sent it
//! {"op":"end"}
//! ```

use crate::canvas::Canvas;
use crate::image::Image;
use crate::runtime::Runtime;
use anyhow::{Context as _, Result};
use hive_common::messages::HiveMessage;
use serde_json::{json, Value};
use std::io::{BufRead, Write};
use std::time::{Duration, Instant};

pub fn run(runtime: &mut Runtime) -> Result<()> {
    let stdin = std::io::stdin();
    let mut out = std::io::stdout();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let answer = match serde_json::from_str::<Value>(&line) {
            Ok(req) => match handle(runtime, &req) {
                Ok(Some(v)) => v,
                Ok(None) => {
                    writeln!(
                        out,
                        "QPP {}",
                        json!({"ended": true, "tick": runtime.world.tick})
                    )?;
                    out.flush()?;
                    return Ok(());
                }
                Err(e) => json!({"error": format!("{:#}", e)}),
            },
            Err(e) => json!({"error": format!("not a request: {}", e)}),
        };
        writeln!(out, "QPP {}", answer)?;
        out.flush()?;
    }
    Ok(())
}

fn observation(runtime: &mut Runtime, stopped: &str) -> Value {
    let mut obs = runtime.world.observe();
    obs["stopped"] = json!(stopped);
    obs["events"] = Value::Array(runtime.world.take_events());
    obs
}

fn holds(runtime: &Runtime, req: &Value, events: &[Value]) -> bool {
    let world = &runtime.world;
    let s = |k: &str| req.get(k).and_then(Value::as_str);
    if let Some(text) = s("toast") {
        return world
            .observe()
            .get("toast")
            .and_then(Value::as_str)
            .is_some_and(|t| t.contains(text));
    }
    if let Some(text) = s("notice") {
        return world.notices.iter().any(|n| n.contains(text));
    }
    if let Some(text) = s("offer") {
        return world.offers.iter().any(|o| o.title.contains(text));
    }
    if let Some(kind) = s("event") {
        return events.iter().any(|e| {
            e.get("kind").and_then(Value::as_str) == Some(kind)
                || (e.get("kind").and_then(Value::as_str) == Some("event")
                    && e.get("event").and_then(Value::as_str) == Some(kind))
        });
    }
    if let Some(name) = s("sprite") {
        let frame = req.get("frame").and_then(Value::as_u64);
        return world.sprites.iter().any(|sp| {
            sp.name.as_deref() == Some(name) && frame.map_or(true, |f| sp.frame as u64 == f)
        });
    }
    if let Some(n) = req.get("offers").and_then(Value::as_u64) {
        return world.offers.len() as u64 >= n;
    }
    false
}

fn handle(runtime: &mut Runtime, req: &Value) -> Result<Option<Value>> {
    let op = req
        .get("op")
        .and_then(Value::as_str)
        .context("a request needs op")?;
    match op {
        "observe" => Ok(Some(observation(runtime, "now"))),
        "act" => {
            let keys: Vec<String> = req
                .get("tap")
                .and_then(Value::as_array)
                .map(|a| {
                    a.iter()
                        .filter_map(|v| v.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default();
            for key in keys {
                runtime.key(&key)?;
            }
            let ticks = req.get("ticks").and_then(Value::as_u64).unwrap_or(1);
            for _ in 0..ticks {
                runtime.step()?;
            }
            Ok(Some(observation(runtime, "ticks")))
        }
        "until" => {
            let max_ticks = req.get("max_ticks").and_then(Value::as_u64).unwrap_or(600);
            let mut seen: Vec<Value> = Vec::new();
            let started = Instant::now();
            let mut stopped = "max_ticks";
            for n in 0..max_ticks {
                runtime.step()?;
                seen.extend(runtime.world.take_events());
                if holds(runtime, req, &seen) {
                    stopped = "condition";
                    break;
                }
                // in real time, so that what the Hive sends arrives meanwhile
                let due = started + Duration::from_secs_f64((n + 1) as f64 / 60.0);
                if let Some(wait) = due.checked_duration_since(Instant::now()) {
                    std::thread::sleep(wait);
                }
            }
            let mut obs = runtime.world.observe();
            obs["stopped"] = json!(stopped);
            obs["events"] = Value::Array(seen);
            Ok(Some(obs))
        }
        "frame" => {
            let scale = crate::level::LEVELS[runtime.world.level()].scale;
            let mut canvas =
                Canvas::new(runtime.world.scene.width, runtime.world.scene.height, scale);
            let bands = req.get("bands").and_then(Value::as_u64).unwrap_or(1) as usize;
            runtime.world.render(&mut canvas, bands.max(1));
            if let Some(path) = req.get("path").and_then(Value::as_str) {
                canvas.image.save(std::path::Path::new(path))?;
            }
            if let Some(expect) = req.get("expect").and_then(Value::as_str) {
                let path = std::path::Path::new(expect);
                if std::env::var_os("UPDATE_SCREENS").is_some() || !path.is_file() {
                    if let Some(dir) = path.parent() {
                        std::fs::create_dir_all(dir)?;
                    }
                    canvas.image.save(path)?;
                    return Ok(Some(
                        json!({"ok": true, "wrote": expect, "tick": runtime.world.tick}),
                    ));
                }
                let reference = Image::load(path)?;
                return Ok(Some(match canvas.image.differences(&reference) {
                    Some(0) => json!({"ok": true, "matches": expect, "tick": runtime.world.tick}),
                    Some(n) => {
                        let actual = path.with_extension("actual.png");
                        canvas.image.save(&actual)?;
                        json!({"ok": false, "differs": n, "expected": expect, "actual": actual, "tick": runtime.world.tick})
                    }
                    None => {
                        json!({"ok": false, "error": "the reference is another size", "expected": expect})
                    }
                }));
            }
            Ok(Some(json!({"ok": true, "tick": runtime.world.tick})))
        }
        "inject" => {
            let msg: HiveMessage = serde_json::from_value(
                req.get("message")
                    .cloned()
                    .context("inject needs message")?,
            )
            .context("inject: not a HiveMessage")?;
            runtime.incoming(msg)?;
            Ok(Some(observation(runtime, "injected")))
        }
        "level" => {
            let level = req
                .get("level")
                .and_then(Value::as_u64)
                .context("level needs level")? as usize;
            if level >= crate::level::LEVELS.len() {
                anyhow::bail!(
                    "no level {} (0 to {})",
                    level,
                    crate::level::LEVELS.len() - 1
                );
            }
            runtime.world.set_level(level);
            Ok(Some(observation(runtime, "level")))
        }
        "end" => Ok(None),
        other => anyhow::bail!("no such op: {}", other),
    }
}
