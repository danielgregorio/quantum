//! `hive-lab term -- PROGRAM ARGS...`: one program in a pseudo-terminal,
//! driven by JSON lines, for where the Hive lab does not start the Hive
//! itself: in the VM lab (scripts/lab/vm), the guest runs the real dashboard
//! and grove this way, and the screen is rendered in the guest, by the same
//! terminal emulator the Hive lab uses.
//!
//! Requests on stdin, one answer per line on stdout:
//! - `{"op":"view"}`: `screen` (text) and `cursor`;
//! - `{"op":"keys","keys":["Down","Enter","text"]}`;
//! - `{"op":"until","contains":"...","excludes":"...","timeout":5}`;
//! - `{"op":"stop"}`, or the end of stdin, stops the program.

use crate::tui::Tui;
use anyhow::{bail, Context as _, Result};
use serde_json::{json, Value};
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;

pub async fn run(args: Vec<String>) -> Result<()> {
    let (mut rows, mut cols) = (30u16, 100u16);
    let mut args = args.into_iter();
    let mut program = Vec::new();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--rows" => rows = args.next().context("--rows N")?.parse()?,
            "--cols" => cols = args.next().context("--cols N")?.parse()?,
            "--" => {
                program.extend(args.by_ref());
            }
            other => bail!("hive-lab term: unknown argument {}", other),
        }
    }
    let Some((name, rest)) = program.split_first() else {
        bail!("usage: hive-lab term [--rows N] [--cols N] -- PROGRAM ARGS...");
    };
    let mut cmd = Command::new(name);
    cmd.args(rest);
    let mut tui = Tui::spawn(cmd, rows, cols, || Ok(()))?;

    let mut stdin = BufReader::new(tokio::io::stdin()).lines();
    while let Some(line) = stdin.next_line().await? {
        if line.trim().is_empty() {
            continue;
        }
        let answer = match serde_json::from_str::<Value>(&line) {
            Ok(req) => match handle(&mut tui, &req).await {
                Ok(Some(answer)) => answer,
                Ok(None) => break,
                Err(e) => json!({"ok": false, "error": format!("{:#}", e)}),
            },
            Err(e) => json!({"ok": false, "error": format!("not JSON: {}", e)}),
        };
        println!("{}", answer);
    }
    tui.stop().await;
    println!("{}", json!({"ok": true, "stopped": true}));
    Ok(())
}

async fn handle(tui: &mut Tui, req: &Value) -> Result<Option<Value>> {
    let s = |k: &str| req.get(k).and_then(Value::as_str);
    match s("op").unwrap_or_default() {
        "view" => {
            let screen = tui.screen();
            Ok(Some(
                json!({"ok": true, "screen": screen.text, "cursor": screen.cursor}),
            ))
        }
        "keys" => {
            let keys: Vec<String> = req
                .get("keys")
                .and_then(Value::as_array)
                .map(|a| {
                    a.iter()
                        .filter_map(|v| v.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default();
            tui.keys(&keys)?;
            Ok(Some(json!({"ok": true, "typed": keys.len()})))
        }
        "until" => {
            let text = s("contains").context("until needs contains")?;
            let timeout = req.get("timeout").and_then(Value::as_f64).unwrap_or(5.0);
            match tui
                .until(text, s("excludes"), Duration::from_secs_f64(timeout))
                .await
            {
                Ok(screen) => Ok(Some(json!({"ok": true, "screen": screen.text}))),
                Err(e) => Ok(Some(json!({"ok": false, "error": format!("{:#}", e)}))),
            }
        }
        "stop" => Ok(None),
        other => bail!("unknown op {:?}", other),
    }
}
