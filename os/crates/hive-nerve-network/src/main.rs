//! Hive Nerve: Network - Port Conflict Observer
//!
//! Reports services that fail to start because the port they want is
//! already taken, together with who holds it.
//!
//! A conflict is detected from the loser's side: its "Address already in
//! use" error in the journal (see [`bind_failure`]). Looking at listening
//! sockets alone can't find one — the process that failed to bind never gets
//! a socket — and two sockets on one port are usually no conflict at all (an
//! IPv4 plus an IPv6 listener, or SO_REUSEPORT workers). /proc/net is only
//! consulted afterwards, to name the holder (see [`proc_net`]).
//!
//! # Security Model
//!
//! - Runs as `_hive-sense` user with minimal privileges
//! - Read-only access to the journal (systemd-journal group) and /proc/net
//! - Cannot modify network configuration

mod bind_failure;
mod proc_net;
mod recent;

use anyhow::{Context, Result};
use hive_common::config::NetworkNerveConfig;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, ProcessInfo};
use std::collections::BTreeSet;
use std::path::Path;
use std::process::Stdio;
use std::time::{Duration, Instant};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::signal;
use tracing::{debug, error, info, warn};

use crate::bind_failure::BindFailure;
use crate::proc_net::Socket;
use crate::recent::RecentReports;

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// How long a reported (port, service) conflict stays quiet.
const REPORT_WINDOW: Duration = Duration::from_secs(300);

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_nerve_network")?;

    info!("Hive Nerve (Network) starting...");

    // Load configuration
    let config = load_config().await?;

    // Drop privileges if running as root
    if nix::unistd::geteuid().is_root() {
        drop_privileges(&config.user)?;
    }

    // Connect to cortex
    let cortex_socket =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = IpcSocket::connect(&cortex_socket)
        .await
        .context("Failed to connect to cortex")?;

    if config.watch_ports.is_empty() {
        info!("Hive Nerve (Network) ready, watching every port for conflicts");
    } else {
        info!(
            "Hive Nerve (Network) ready, watching ports {:?} for conflicts",
            config.watch_ports
        );
    }
    hive_common::systemd::report_ready();

    watch_bind_failures(&config, &mut cortex).await
}

async fn load_config() -> Result<NetworkNerveConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        let full_config = hive_common::config::Config::load(&config_path)?;
        Ok(full_config.nerves.network)
    } else {
        warn!("Config file not found, using defaults");
        Ok(NetworkNerveConfig::default())
    }
}

fn drop_privileges(username: &str) -> Result<()> {
    use nix::unistd::{setgid, setuid, Gid, Uid, User};

    let user = User::from_name(username)?.context(format!("User {} not found", username))?;

    setgid(Gid::from_raw(user.gid.as_raw()))?;
    setuid(Uid::from_raw(user.uid.as_raw()))?;

    info!("Dropped privileges to user {}", username);
    Ok(())
}

/// Arguments for the `journalctl` process bind failures are read from.
fn journalctl_args() -> Vec<String> {
    vec![
        "--follow".to_string(),
        // Only what's logged from now on, not a replay of recent history.
        "--lines=0".to_string(),
        "--no-pager".to_string(),
        "--output=json".to_string(),
        "--case-sensitive=false".to_string(),
        format!("--grep={}", bind_failure::JOURNAL_PATTERN),
    ]
}

async fn watch_bind_failures(config: &NetworkNerveConfig, cortex: &mut IpcSocket) -> Result<()> {
    let mut child = Command::new("journalctl")
        .args(journalctl_args())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .context("Failed to spawn journalctl")?;
    let stdout = child.stdout.take().context("Failed to capture stdout")?;
    let mut lines = BufReader::new(stdout).lines();
    let mut recent = RecentReports::new(REPORT_WINDOW);

    loop {
        tokio::select! {
            line = lines.next_line() => {
                match line {
                    Ok(Some(line)) => {
                        if let Err(e) = handle_journal_line(&line, config, cortex, &mut recent).await {
                            error!("Error handling journal entry: {}", e);
                        }
                    }
                    Ok(None) => {
                        warn!("Journal stream ended");
                        break;
                    }
                    Err(e) => error!("Error reading journal: {}", e),
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    let _ = child.kill().await;
    info!("Hive Nerve (Network) shutting down");
    Ok(())
}

async fn handle_journal_line(
    line: &str,
    config: &NetworkNerveConfig,
    cortex: &mut IpcSocket,
    recent: &mut RecentReports,
) -> Result<()> {
    let entry: serde_json::Value =
        serde_json::from_str(line).context("Failed to parse journal JSON")?;
    let Some(failure) = bind_failure::from_journal_entry(&entry) else {
        debug!("Journal entry mentions an address in use but no port; skipping");
        return Ok(());
    };
    if !config.watch_ports.is_empty() && !config.watch_ports.contains(&failure.port) {
        return Ok(());
    }
    if !recent.should_report(failure.port, &failure.requester(), Instant::now()) {
        return Ok(());
    }

    let holders = proc_net::holders_of(failure.port);
    report_conflict(cortex, &failure, &holders).await
}

async fn report_conflict(
    cortex: &mut IpcSocket,
    failure: &BindFailure,
    holders: &[Socket],
) -> Result<()> {
    let holder = describe_holders(holders, username);

    let msg = HiveMessage::PortConflict {
        port: failure.port,
        requested_by: ProcessInfo {
            pid: failure.pid,
            uid: failure.uid,
            name: failure.comm.clone(),
            cmdline: failure.cmdline.clone(),
            cwd: None,
            ppid: None,
        },
        // The holder's process can't be identified unprivileged (see
        // proc_net): pid 0 means unknown, and `name` says what is known.
        held_by: ProcessInfo {
            pid: 0,
            uid: holders.first().map_or(u32::MAX, |s| s.uid),
            name: holder.clone(),
            cmdline: vec![],
            cwd: None,
            ppid: None,
        },
    };

    cortex.send(&msg).await?;
    info!(
        "Reported port conflict on port {}: {} could not bind; held by {}",
        failure.port,
        failure.requester(),
        holder
    );
    Ok(())
}

fn username(uid: u32) -> Option<String> {
    nix::unistd::User::from_uid(nix::unistd::Uid::from_raw(uid))
        .ok()
        .flatten()
        .map(|user| user.name)
}

/// e.g. "user nobody (uid 65534)". An IPv4 + IPv6 listener is two sockets
/// but one holder, so owners are deduplicated.
fn describe_holders(holders: &[Socket], lookup: impl Fn(u32) -> Option<String>) -> String {
    let uids: BTreeSet<u32> = holders.iter().map(|s| s.uid).collect();
    if uids.is_empty() {
        return "an unknown process (nothing is bound to the port any more)".to_string();
    }
    let owners: Vec<String> = uids
        .into_iter()
        .map(|uid| match lookup(uid) {
            Some(name) => format!("{name} (uid {uid})"),
            None => format!("uid {uid}"),
        })
        .collect();
    let noun = if owners.len() == 1 { "user" } else { "users" };
    format!("{noun} {}", owners.join(", "))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::proc_net::Protocol;

    fn socket(uid: u32, inode: u64) -> Socket {
        Socket {
            protocol: Protocol::Tcp,
            port: 80,
            uid,
            inode,
        }
    }

    fn names(uid: u32) -> Option<String> {
        match uid {
            0 => Some("root".into()),
            33 => Some("www-data".into()),
            _ => None,
        }
    }

    #[test]
    fn a_dual_stack_holder_is_one_user() {
        let holders = [socket(33, 1), socket(33, 2)];
        assert_eq!(describe_holders(&holders, names), "user www-data (uid 33)");
    }

    #[test]
    fn several_owners_and_unknown_uids_are_all_named() {
        let holders = [socket(33, 1), socket(0, 2), socket(4242, 3)];
        assert_eq!(
            describe_holders(&holders, names),
            "users root (uid 0), www-data (uid 33), uid 4242"
        );
    }

    #[test]
    fn a_holder_that_already_went_away_is_said_to_be_unknown() {
        assert!(describe_holders(&[], names).starts_with("an unknown process"));
    }

    #[test]
    fn journalctl_follows_new_bind_failures_only() {
        let args = journalctl_args();
        assert!(args.contains(&"--lines=0".to_string()));
        assert!(args.contains(&"--case-sensitive=false".to_string()));
        assert!(args
            .iter()
            .any(|a| a.starts_with("--grep=") && a.contains("EADDRINUSE")));
    }

    #[test]
    fn the_shipped_config_watches_every_port() {
        let shipped = concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../config/hive/default.toml"
        );
        let config = hive_common::config::Config::load(shipped).unwrap();
        assert!(config.nerves.network.watch_ports.is_empty());
    }
}
