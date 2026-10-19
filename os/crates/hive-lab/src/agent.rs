//! An agent: one of the roles the lab plays (a nerve, the actuator, grove,
//! the dashboard), as a process of its own. hive-cortex tells components
//! apart by their binary's name and their uid, so each role is the hive-lab
//! binary started under that role's name (argv[0]) and user.
//!
//! It bridges the role's socket to the driver: a JSON line on stdin is a
//! `HiveMessage` to send; each message received is printed as a JSON line.
//! The actuator answers every `ActionRequest` itself, without running
//! anything: the lab records what the Hive would do.

use anyhow::{Context, Result};
use hive_common::messages::HiveMessage;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;
use tokio::sync::mpsc;

/// What the lab's actuator answers: success, and that nothing ran.
pub const NOT_EXECUTED: &str = "hive-lab: recorded, not executed";

pub async fn run() -> Result<()> {
    let path = std::env::var("HIVE_LAB_SOCKET").context("HIVE_LAB_SOCKET is not set")?;
    let auto_act = std::env::var_os("HIVE_LAB_AUTO_ACT").is_some();

    let mut stream = None;
    for _ in 0..100 {
        match UnixStream::connect(&path).await {
            Ok(s) => {
                stream = Some(s);
                break;
            }
            Err(_) => tokio::time::sleep(Duration::from_millis(50)).await,
        }
    }
    let stream = stream.with_context(|| format!("cannot connect to {}", path))?;
    let (mut reader, mut writer) = stream.into_split();
    let (outgoing, mut to_send) = mpsc::channel::<HiveMessage>(64);

    // The socket's framing (ipc.rs): a little-endian u32 length, then the
    // bincode message. Reading and writing are separate tasks, so neither is
    // ever cancelled halfway through a frame.
    let writing = tokio::spawn(async move {
        while let Some(msg) = to_send.recv().await {
            let bytes = msg.encode()?;
            writer
                .write_all(&(bytes.len() as u32).to_le_bytes())
                .await?;
            writer.write_all(&bytes).await?;
            writer.flush().await?;
        }
        anyhow::Ok(())
    });

    let answers = outgoing.clone();
    let reading = tokio::spawn(async move {
        let mut stdout = tokio::io::stdout();
        loop {
            let mut len = [0u8; 4];
            if reader.read_exact(&mut len).await.is_err() {
                return anyhow::Ok(());
            }
            let mut body = vec![0u8; u32::from_le_bytes(len) as usize];
            reader.read_exact(&mut body).await?;
            let msg = HiveMessage::decode(&body)?;
            let mut line = serde_json::to_string(&msg)?;
            line.push('\n');
            stdout.write_all(line.as_bytes()).await?;
            stdout.flush().await?;
            if auto_act {
                if let HiveMessage::ActionRequest {
                    request_id, action, ..
                } = msg
                {
                    let _ = answers
                        .send(HiveMessage::ActionResponse {
                            request_id,
                            action,
                            success: true,
                            output: Some(NOT_EXECUTED.to_string()),
                            exit_code: Some(0),
                        })
                        .await;
                }
            }
        }
    });

    let mut lines = BufReader::new(tokio::io::stdin()).lines();
    while let Some(line) = lines.next_line().await? {
        if line.trim().is_empty() {
            continue;
        }
        let msg: HiveMessage =
            serde_json::from_str(&line).with_context(|| format!("not a HiveMessage: {}", line))?;
        if outgoing.send(msg).await.is_err() {
            break;
        }
    }
    // stdin closed: the driver is done with this role.
    drop(outgoing);
    reading.abort();
    let _ = writing.await;
    Ok(())
}
