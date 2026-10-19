//! Hive Nerve: Process - Command Observer
//!
//! Monitors process execution and command patterns. Detects potentially
//! dangerous commands and reports to hive-cortex for analysis.
//!
//! # Security Model
//!
//! - Runs as `_hive-sense` user with minimal privileges
//! - Sees executions through the kernel audit log (CAP_AUDIT_READ only, see
//!   the [`audit`] module); falls back to polling /proc, which misses
//!   short-lived commands, where the audit log isn't available

mod audit;
mod danger;

use anyhow::{Context, Result};
use hive_common::config::ProcessNerveConfig;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, ProcessInfo};
use std::collections::HashSet;
use std::path::Path;
use std::time::Duration;
use tokio::signal;
use tokio::sync::mpsc;
use tokio::time::interval;
use tracing::{error, info, warn};

use crate::audit::{AuditSocket, ExecAssembler, ExecEvent};

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// What the nerve tracks across executions.
struct ProcessState {
    /// PIDs already looked at by the /proc polling fallback.
    seen_pids: HashSet<u32>,
    /// Commands judged at all (`[nerves.process] intercept_commands`).
    intercept_commands: Vec<String>,
}

impl ProcessState {
    fn new(config: &ProcessNerveConfig) -> Self {
        Self {
            seen_pids: HashSet::new(),
            intercept_commands: config.intercept_commands.clone(),
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_nerve_process")?;

    info!("Hive Nerve (Process) starting...");

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

    info!(
        "Hive Nerve (Process) ready, intercepting {} commands",
        config.intercept_commands.len()
    );
    hive_common::systemd::report_ready();

    // Start monitoring
    monitor_processes(&config, &mut cortex).await
}

async fn load_config() -> Result<ProcessNerveConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        let full_config = hive_common::config::Config::load(&config_path)?;
        Ok(full_config.nerves.process)
    } else {
        warn!("Config file not found, using defaults");
        Ok(ProcessNerveConfig::default())
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

async fn monitor_processes(config: &ProcessNerveConfig, cortex: &mut IpcSocket) -> Result<()> {
    let mut state = ProcessState::new(config);

    match AuditSocket::subscribe() {
        Ok(socket) => {
            info!("Watching program executions through the kernel audit log");
            watch_audit_log(socket, cortex, &state).await;
        }
        Err(e) => {
            warn!(
                "Kernel audit log unavailable ({}); falling back to polling /proc, \
                 which misses short-lived commands",
                e
            );
            poll_processes(cortex, &mut state).await;
        }
    }

    info!("Hive Nerve (Process) shutting down");
    Ok(())
}

async fn watch_audit_log(socket: AuditSocket, cortex: &mut IpcSocket, state: &ProcessState) {
    let (tx, mut rx) = mpsc::channel::<ExecEvent>(1024);

    // recv(2) on the netlink socket blocks, so the reading happens on its
    // own thread.
    let reader = std::thread::Builder::new()
        .name("audit-reader".into())
        .spawn(move || {
            let mut assembler = ExecAssembler::new();
            let mut buf = vec![0u8; 16 * 1024];
            loop {
                let mut finished = Vec::new();
                match socket.recv(&mut buf, |kind, payload| {
                    finished.extend(assembler.push(kind, payload));
                }) {
                    Ok(()) => {}
                    Err(e) if e.raw_os_error() == Some(libc::ENOBUFS) => {
                        warn!("Kernel dropped audit records (reader fell behind)");
                    }
                    Err(e) => {
                        error!("Reading the audit log failed: {}", e);
                        return;
                    }
                }
                for event in finished {
                    if tx.blocking_send(event).is_err() {
                        return;
                    }
                }
            }
        });
    if let Err(e) = reader {
        error!("Could not start the audit reader thread: {}", e);
        return;
    }

    loop {
        tokio::select! {
            event = rx.recv() => match event {
                Some(event) => {
                    let process = ProcessInfo {
                        pid: event.pid,
                        uid: event.uid,
                        name: event.comm,
                        cmdline: event.argv,
                        cwd: event.cwd,
                        ppid: event.ppid,
                    };
                    let program = event.exe.unwrap_or_else(|| process.name.clone());
                    report_if_dangerous(cortex, state, process, &program).await;
                }
                None => {
                    error!("Audit reader stopped");
                    return;
                }
            },
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                return;
            }
        }
    }
}

async fn poll_processes(cortex: &mut IpcSocket, state: &mut ProcessState) {
    // Poll interval (more frequent for command interception)
    let mut poll_timer = interval(Duration::from_millis(250));

    loop {
        tokio::select! {
            _ = poll_timer.tick() => {
                if let Err(e) = scan_processes(cortex, state).await {
                    error!("Error scanning processes: {}", e);
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                return;
            }
        }
    }
}

/// Report `process` to cortex if running `program` with its arguments is
/// dangerous (see the danger module).
async fn report_if_dangerous(
    cortex: &mut IpcSocket,
    state: &ProcessState,
    process: ProcessInfo,
    program: &str,
) {
    let Some(finding) = danger::assess(
        program,
        &process.cmdline,
        process.cwd.as_deref(),
        &state.intercept_commands,
    ) else {
        return;
    };
    let cmdline = process.cmdline.join(" ");
    info!(
        "Detected dangerous command '{}': {} ({})",
        finding.command, cmdline, finding.reason
    );

    let msg = HiveMessage::CommandObserved {
        process,
        cmd: cmdline,
        timestamp: chrono::Utc::now(),
    };
    if let Err(e) = cortex.send(&msg).await {
        error!("Failed to send to cortex: {}", e);
    }
}

async fn scan_processes(cortex: &mut IpcSocket, state: &mut ProcessState) -> Result<()> {
    // Read /proc for all processes
    let proc_dir = std::fs::read_dir("/proc")?;

    for entry in proc_dir.flatten() {
        let name = entry.file_name();
        let name_str = name.to_string_lossy();

        // Only process numeric directories (PIDs)
        if let Ok(pid) = name_str.parse::<u32>() {
            // Skip if we've already seen this process
            if state.seen_pids.contains(&pid) {
                continue;
            }

            if let Some(info) = get_process_info(pid) {
                // The real executable when readable (unprivileged: only our
                // own processes), argv[0] otherwise.
                let program = std::fs::read_link(format!("/proc/{}/exe", pid))
                    .ok()
                    .and_then(|exe| exe.to_str().map(str::to_string))
                    .unwrap_or_else(|| info.cmdline[0].clone());
                report_if_dangerous(cortex, state, info, &program).await;
                state.seen_pids.insert(pid);
            }
        }
    }

    // Clean up old PIDs (remove PIDs that no longer exist)
    if state.seen_pids.len() > 10000 {
        state
            .seen_pids
            .retain(|pid| Path::new(&format!("/proc/{}", pid)).exists());
    }

    Ok(())
}

fn get_process_info(pid: u32) -> Option<ProcessInfo> {
    // Read cmdline
    let cmdline_path = format!("/proc/{}/cmdline", pid);
    let cmdline = std::fs::read_to_string(&cmdline_path)
        .ok()?
        .split('\0')
        .filter(|s| !s.is_empty())
        .map(String::from)
        .collect::<Vec<_>>();

    if cmdline.is_empty() {
        return None;
    }

    // Read comm (process name)
    let comm_path = format!("/proc/{}/comm", pid);
    let name = std::fs::read_to_string(&comm_path)
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|_| cmdline.first().cloned().unwrap_or_default());

    // Read status for UID and PPID
    let status_path = format!("/proc/{}/status", pid);
    let status = std::fs::read_to_string(&status_path).ok()?;

    let mut uid = 0u32;
    let mut ppid = None;

    for line in status.lines() {
        if line.starts_with("Uid:") {
            if let Some(val) = line.split_whitespace().nth(1) {
                uid = val.parse().unwrap_or(0);
            }
        } else if line.starts_with("PPid:") {
            if let Some(val) = line.split_whitespace().nth(1) {
                ppid = val.parse().ok();
            }
        }
    }

    // Read cwd
    let cwd_path = format!("/proc/{}/cwd", pid);
    let cwd = std::fs::read_link(&cwd_path).ok();

    Some(ProcessInfo {
        pid,
        uid,
        name,
        cmdline,
        cwd,
        ppid,
    })
}
