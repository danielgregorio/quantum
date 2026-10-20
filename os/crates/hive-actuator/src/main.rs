//! Hive Actuator - Secure Action Executor
//!
//! The only Hive component allowed to execute actions on the system.
//! All actions must pass through a whitelist and may require user confirmation.
//!
//! # Security Model
//!
//! - Runs as `_hive-act` user with specific capabilities
//! - Actions validated against whitelist
//! - Rate-limited to prevent abuse
//! - Snapshots the system (ZFS) before changing packages, and refuses to
//!   change them when that snapshot can't be taken

mod whitelist;

use anyhow::{Context, Result};
use hive_common::actions::Action;
use hive_common::config::ActuatorConfig;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, MessageId};
use hive_common::zfs;
use std::collections::{HashMap, VecDeque};
use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::time::{Duration, Instant};
use tokio::process::Command;
use tokio::signal;
use tracing::{debug, error, info, warn};

use crate::whitelist::Whitelist;

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// Rate limiter state
struct RateLimiter {
    actions: VecDeque<Instant>,
    max_per_minute: u32,
}

impl RateLimiter {
    fn new(max_per_minute: u32) -> Self {
        Self {
            actions: VecDeque::new(),
            max_per_minute,
        }
    }

    fn check(&mut self) -> bool {
        let now = Instant::now();
        let one_minute_ago = now - Duration::from_secs(60);

        // Remove old entries
        while let Some(front) = self.actions.front() {
            if *front < one_minute_ago {
                self.actions.pop_front();
            } else {
                break;
            }
        }

        // Check rate
        if self.actions.len() < self.max_per_minute as usize {
            self.actions.push_back(now);
            true
        } else {
            false
        }
    }
}

/// Enforces the actuator's global rate limit, plus tighter per-action-type
/// limits sourced from the whitelist's `[rate_limits]` table.
struct RateLimiters {
    global: RateLimiter,
    per_type_limits: HashMap<String, u32>,
    per_type: HashMap<String, RateLimiter>,
}

impl RateLimiters {
    fn new(global_max: u32, per_type_limits: HashMap<String, u32>) -> Self {
        Self {
            global: RateLimiter::new(global_max),
            per_type_limits,
            per_type: HashMap::new(),
        }
    }

    /// Checks (and consumes budget from) the global limit, then the
    /// per-type limit if one is configured for `action_type`. Short-circuits
    /// on the global limit so a global rejection doesn't also consume a
    /// per-type slot.
    fn check(&mut self, action_type: &str) -> bool {
        if !self.global.check() {
            return false;
        }
        match self.per_type_limits.get(action_type) {
            Some(&max) => self
                .per_type
                .entry(action_type.to_string())
                .or_insert_with(|| RateLimiter::new(max))
                .check(),
            None => true,
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_actuator")?;

    info!("Hive Actuator starting...");

    // Load configuration
    let config = load_config().await?;

    if std::env::args().nth(1).as_deref() == Some("delegate-snapshots") {
        return delegate_snapshots(&config).await;
    }

    let snapshots = SafetySnapshots::from_config(&config);
    if snapshots.datasets.is_empty() {
        info!("No ZFS system datasets to snapshot (root not on ZFS, or auto_snapshot off)");
    } else {
        info!(
            "Snapshots before package changes: {}",
            snapshots.datasets.join(" ")
        );
    }

    // Load whitelist
    let whitelist = Whitelist::load(
        config
            .whitelist_path
            .to_str()
            .unwrap_or("/etc/hive/actuator-whitelist.toml"),
    )?;
    info!(
        "Whitelist loaded ({} per-type rate limit overrides)",
        whitelist.rate_limit_overrides().len()
    );

    // Initialize rate limiters: global cap from ActuatorConfig, tighter
    // per-action-type caps from the whitelist's [rate_limits] table.
    let mut rate_limiter =
        RateLimiters::new(config.rate_limit, whitelist.rate_limit_overrides().clone());

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

    info!("Hive Actuator ready");
    hive_common::systemd::report_ready();

    // Main event loop
    loop {
        tokio::select! {
            result = cortex.recv() => {
                match result {
                    Ok(msg) => {
                        if let Err(e) = handle_message(msg, &config, &whitelist, &mut rate_limiter, &snapshots, &mut cortex).await {
                            error!("Error handling message: {}", e);
                        }
                    }
                    Err(hive_common::ipc::IpcError::ConnectionClosed) => {
                        warn!("Connection to cortex closed, exiting");
                        break;
                    }
                    Err(e) => {
                        error!("Error receiving message: {}", e);
                    }
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    info!("Hive Actuator shutting down");
    Ok(())
}

async fn load_config() -> Result<ActuatorConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        let full_config = hive_common::config::Config::load(&config_path)?;
        Ok(full_config.actuator)
    } else {
        warn!("Config file not found, using defaults");
        Ok(ActuatorConfig::default())
    }
}

/// `hive-actuator delegate-snapshots`: run as root by the unit's
/// `ExecStartPre=` before the daemon starts as its own unprivileged user.
/// ZFS delegation lets that user snapshot the system datasets (`snapshot`
/// needs `mount` alongside it) and nothing more: no destroy, no rollback.
/// The datasets are looked up afresh on every start, so this is idempotent.
async fn delegate_snapshots(config: &ActuatorConfig) -> Result<()> {
    let snapshots = SafetySnapshots::from_config(config);
    if snapshots.datasets.is_empty() {
        info!("No ZFS system datasets: no snapshot permission to delegate");
        return Ok(());
    }
    for dataset in &snapshots.datasets {
        let output = Command::new(&snapshots.zfs)
            .args(["allow", "-u", &config.user, "snapshot,mount", dataset])
            .output()
            .await
            .context("Failed to run zfs allow")?;
        if !output.status.success() {
            anyhow::bail!(
                "zfs allow on {} failed: {}",
                dataset,
                String::from_utf8_lossy(&output.stderr).trim()
            );
        }
        info!(
            "Delegated snapshot permission on {} to {}",
            dataset, config.user
        );
    }
    Ok(())
}

/// The actuator's safety net: which datasets it snapshots before an action
/// that changes the system, and with which `zfs` program.
struct SafetySnapshots {
    datasets: Vec<String>,
    zfs: PathBuf,
}

impl SafetySnapshots {
    /// `snapshot_dataset` when the config names one, otherwise the datasets
    /// the system is mounted from; none at all with `auto_snapshot` off.
    fn from_config(config: &ActuatorConfig) -> Self {
        let datasets = match (&config.snapshot_dataset, config.auto_snapshot) {
            (_, false) => vec![],
            (Some(dataset), true) => vec![dataset.clone()],
            (None, true) => zfs::system_datasets(),
        };
        Self {
            datasets,
            zfs: PathBuf::from("zfs"),
        }
    }

    /// Snapshot the system if `action` calls for it, returning the snapshots
    /// taken: none when it doesn't, or when there is nothing to snapshot.
    async fn before(&self, action: &Action) -> Result<Vec<String>> {
        if self.datasets.is_empty() || !action.should_snapshot_first() {
            return Ok(vec![]);
        }
        let name = zfs::snapshot_name_now(&snapshot_label(action));
        let (program, datasets) = (self.zfs.clone(), self.datasets.clone());
        tokio::task::spawn_blocking(move || zfs::create_snapshots_with(program, &datasets, &name))
            .await?
    }
}

/// What the snapshot was for, as `zfs list -t snapshot` will show it.
fn snapshot_label(action: &Action) -> String {
    match action {
        Action::InstallPackage { name, .. } => format!("before-install-{name}"),
        Action::RemovePackage { name, .. } => format!("before-remove-{name}"),
        Action::UpgradePackages { .. } => "before-upgrade".to_string(),
        other => format!("before-{}", other.type_name()),
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

async fn handle_message(
    msg: HiveMessage,
    config: &ActuatorConfig,
    whitelist: &Whitelist,
    rate_limiter: &mut RateLimiters,
    snapshots: &SafetySnapshots,
    cortex: &mut IpcSocket,
) -> Result<()> {
    match msg {
        HiveMessage::ActionRequest {
            request_id,
            action,
            requires_confirmation,
            timeout_secs,
        } => {
            info!("Received action request: {:?}", action);

            // Check rate limit (global, then any per-type override)
            if !rate_limiter.check(action.type_name()) {
                warn!("Rate limit exceeded, rejecting action");
                send_response(
                    cortex,
                    request_id,
                    action,
                    false,
                    Some("Rate limit exceeded".into()),
                    None,
                )
                .await?;
                return Ok(());
            }

            // Check whitelist
            if !whitelist.is_allowed(&action) {
                warn!("Action not in whitelist: {:?}", action);
                send_response(
                    cortex,
                    request_id,
                    action,
                    false,
                    Some("Action not allowed".into()),
                    None,
                )
                .await?;
                return Ok(());
            }

            // requires_confirmation arrives already resolved by hive-cortex
            // as `action.is_dangerous() && !confirmed` (confirmed comes
            // from hive-dashboard's second-Enter-press flow — see
            // MessageRouter::act_on_suggestion). If it's still true here,
            // either the action genuinely wasn't confirmed yet, or this
            // ActionRequest bypassed that flow entirely — either way, fail
            // closed rather than execute something nobody explicitly
            // confirmed.
            if requires_confirmation && config.confirm_dangerous {
                warn!(
                    "Action requires confirmation but wasn't confirmed — rejecting: {:?}",
                    action
                );
                send_response(
                    cortex,
                    request_id,
                    action,
                    false,
                    Some("Action requires confirmation and was not confirmed".into()),
                    None,
                )
                .await?;
                return Ok(());
            }

            // Snapshot the system before changing it. No snapshot, no
            // action: going ahead would take away the rollback that makes
            // the change safe to approve in the first place.
            match snapshots.before(&action).await {
                Ok(taken) if !taken.is_empty() => {
                    info!("Created snapshot: {}", taken.join(" "));
                }
                Ok(_) => {}
                Err(e) => {
                    error!("Refusing {:?}: safety snapshot failed: {:#}", action, e);
                    send_response(
                        cortex,
                        request_id,
                        action,
                        false,
                        Some(format!(
                            "Refused: could not snapshot the system first ({e:#})"
                        )),
                        None,
                    )
                    .await?;
                    return Ok(());
                }
            }

            // Execute the action
            let timeout = if timeout_secs > 0 {
                Duration::from_secs(timeout_secs as u64)
            } else {
                Duration::from_secs(60)
            };

            let result = execute_action(&action, timeout).await;

            match result {
                Ok((output, exit_code)) => {
                    if exit_code.map_or(true, |c| c == 0) {
                        info!("Action completed with exit code {:?}", exit_code);
                    } else {
                        warn!(
                            "Action failed with exit code {:?}: {}",
                            exit_code,
                            output.as_deref().unwrap_or("")
                        );
                    }
                    send_response(
                        cortex,
                        request_id,
                        action,
                        exit_code.map_or(true, |c| c == 0),
                        output,
                        exit_code,
                    )
                    .await?;
                }
                Err(e) => {
                    error!("Action failed: {}", e);
                    send_response(cortex, request_id, action, false, Some(e.to_string()), None)
                        .await?;
                }
            }
        }
        _ => {
            debug!("Ignoring non-action message: {}", msg.type_name());
        }
    }

    Ok(())
}

async fn send_response(
    cortex: &mut IpcSocket,
    request_id: MessageId,
    action: Action,
    success: bool,
    output: Option<String>,
    exit_code: Option<i32>,
) -> Result<()> {
    let response = HiveMessage::ActionResponse {
        request_id,
        action,
        success,
        output,
        exit_code,
    };

    cortex.send(&response).await?;
    Ok(())
}

/// Package changes go through PackageKit. hive-actuator runs as _hive-act,
/// which apt and dpkg refuse outright (they need root, and the unit's
/// NoNewPrivileges rules out sudo); polkit lets that user install, remove
/// and update packages through packagekitd, and nothing more (see
/// config/polkit/60-druidos-hive-actuator.rules). Names were checked by the
/// whitelist, so none of them can be an option.
async fn package_kit(args: &[&str], timeout: Duration) -> Result<(Option<String>, Option<i32>)> {
    let mut command = Command::new("pkcon");
    command.args(["--noninteractive", "--plain"]).args(args);
    let output = tokio::time::timeout(timeout.max(Duration::from_secs(600)), command.output())
        .await
        .context("pkcon timed out")?
        .context("Failed to run pkcon")?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let combined = if stderr.trim().is_empty() {
        stdout.to_string()
    } else {
        format!("{stdout}\n{stderr}")
    };
    Ok((Some(combined), output.status.code()))
}

/// `systemctl ARGS`: its exit code and, when it fails, what it said
/// (polkit's "Access denied", "Job for nginx.service failed because..."):
/// a failed action tells the administrator why.
/// Where the settings the Hive applied live, for the daemons that read
/// them (hive-screen reads `screen-level`): the unit's StateDirectory,
/// /var/lib/hive/settings.
fn settings_dir() -> PathBuf {
    std::env::var_os("HIVE_SETTINGS_DIR")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("STATE_DIRECTORY").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("/var/lib/hive/settings"))
}

/// A setting the Hive applied, as a file under `settings_dir()`: its text
/// (with a newline), or removed when `value` is None.
fn write_setting(name: &str, value: Option<String>) -> Result<()> {
    let dir = settings_dir();
    let path = dir.join(name);
    match value {
        Some(text) => {
            std::fs::create_dir_all(&dir).with_context(|| format!("creating {}", dir.display()))?;
            std::fs::write(&path, format!("{}\n", text))
                .with_context(|| format!("writing {}", path.display()))
        }
        None => match std::fs::remove_file(&path) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(e).with_context(|| format!("removing {}", path.display())),
        },
    }
}

/// A program run for a setting: what it said when it failed, and its code.
async fn run(program: &str, args: &[&str]) -> Result<(Option<String>, Option<i32>)> {
    let output = Command::new(program).args(args).output().await?;
    let said = (!output.status.success())
        .then(|| String::from_utf8_lossy(&output.stderr).trim().to_string());
    Ok((said, output.status.code()))
}

async fn systemctl(args: &[&str]) -> Result<(Option<String>, Option<i32>)> {
    let output = Command::new("systemctl").args(args).output().await?;
    let said = (!output.status.success())
        .then(|| String::from_utf8_lossy(&output.stderr).trim().to_string());
    Ok((said, output.status.code()))
}

async fn execute_action(
    action: &Action,
    timeout: Duration,
) -> Result<(Option<String>, Option<i32>)> {
    match action {
        Action::RunCommand {
            cmd,
            args,
            cwd,
            env,
        } => {
            let mut command = Command::new(cmd);
            command.args(args);

            if let Some(dir) = cwd {
                command.current_dir(dir);
            }

            for (key, value) in env {
                command.env(key, value);
            }

            command.stdout(Stdio::piped());
            command.stderr(Stdio::piped());

            let output = tokio::time::timeout(timeout, command.output())
                .await
                .context("Command timed out")?
                .context("Failed to execute command")?;

            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);

            let combined = if stderr.is_empty() {
                stdout.to_string()
            } else {
                format!("{}\n{}", stdout, stderr)
            };

            Ok((Some(combined), output.status.code()))
        }

        Action::CreateSnapshot {
            dataset,
            name,
            recursive,
        } => {
            let snapshot_name = format!("{}@{}", dataset, name);
            let mut args = vec!["snapshot"];
            if *recursive {
                args.push("-r");
            }
            args.push(&snapshot_name);

            let output = Command::new("zfs").args(&args).output().await?;

            let exit_code = output.status.code();
            let output_str = if output.status.success() {
                Some(format!("Created snapshot: {}", snapshot_name))
            } else {
                Some(String::from_utf8_lossy(&output.stderr).to_string())
            };

            Ok((output_str, exit_code))
        }

        Action::RestoreSnapshot { dataset, snapshot } => {
            let full_snapshot = format!("{}@{}", dataset, snapshot);
            let output = Command::new("zfs")
                .args(["rollback", "-r", &full_snapshot])
                .output()
                .await?;

            Ok((
                Some(String::from_utf8_lossy(&output.stderr).to_string()),
                output.status.code(),
            ))
        }

        Action::ListSnapshots { dataset } => {
            let mut args = vec!["list", "-t", "snapshot", "-o", "name,creation"];
            if let Some(ds) = dataset {
                args.push("-r");
                args.push(ds);
            }

            let output = Command::new("zfs").args(&args).output().await?;

            Ok((
                Some(String::from_utf8_lossy(&output.stdout).to_string()),
                output.status.code(),
            ))
        }

        Action::DeleteSnapshot { dataset, snapshot } => {
            let full_snapshot = format!("{}@{}", dataset, snapshot);
            let output = Command::new("zfs")
                .args(["destroy", &full_snapshot])
                .output()
                .await?;

            Ok((
                Some(String::from_utf8_lossy(&output.stderr).to_string()),
                output.status.code(),
            ))
        }

        Action::InstallPackage { name, .. } => package_kit(&["install", name], timeout).await,

        // PackageKit has no purge: configuration files stay behind.
        Action::RemovePackage { name, .. } => package_kit(&["remove", name], timeout).await,

        Action::UpdatePackageLists => package_kit(&["refresh"], timeout).await,

        Action::UpgradePackages { packages } => {
            let mut args = vec!["update"];
            args.extend(packages.iter().map(String::as_str));
            package_kit(&args, timeout).await
        }

        Action::StartService { name } => systemctl(&["start", name]).await,

        Action::StopService { name } => systemctl(&["stop", name]).await,

        Action::RestartService { name } => systemctl(&["restart", name]).await,

        Action::ReloadService { name } => systemctl(&["reload", name]).await,

        Action::EnableService { name, now } => {
            let mut args = vec!["enable"];
            if *now {
                args.push("--now");
            }
            args.push(name);
            systemctl(&args).await
        }

        Action::DisableService { name, now } => {
            let mut args = vec!["disable"];
            if *now {
                args.push("--now");
            }
            args.push(name);
            systemctl(&args).await
        }

        // The machine's settings. The name goes through systemd's hostnamed
        // over D-Bus, which polkit lets _hive-act do
        // (config/polkit/61-druidos-hive-settings.rules).
        Action::SetHostname { name } => run("hostnamectl", &["set-hostname", name]).await,

        // The keyboard and the screen's level are files in the settings
        // the Hive applied, which hive-screen watches: no root, no restart.
        // (localectl would be the way for the keyboard, but Ubuntu's
        // localed refuses: "Setting X11 and console keymaps is not
        // supported in Debian"; /etc/default/keyboard stays the
        // installer's, and the screen reads the Hive's setting first.)
        Action::SetKeyboard { layout, model } => {
            write_setting(
                "keyboard",
                Some(format!("{} {}", layout, model).trim().to_string()),
            )?;
            Ok((None, Some(0)))
        }

        Action::SetScreenLevel { level } => {
            write_setting("screen-level", level.map(|l| l.to_string()))?;
            Ok((None, Some(0)))
        }

        Action::KillPortProcess { port, signal } => {
            // First find PIDs using the port
            let lsof_output = Command::new("lsof")
                .args(["-t", "-i", &format!(":{}", port)])
                .output()
                .await?;

            if !lsof_output.status.success() || lsof_output.stdout.is_empty() {
                return Ok((Some(format!("No process found on port {}", port)), Some(0)));
            }

            let stdout = String::from_utf8_lossy(&lsof_output.stdout);
            let pids: Vec<&str> = stdout.trim().lines().collect();

            let sig = signal.unwrap_or(15); // SIGTERM
            let sig_arg = format!("-{}", sig);
            for pid in &pids {
                let _ = Command::new("kill").args([&sig_arg, *pid]).output().await;
            }

            Ok((
                Some(format!(
                    "Killed {} process(es) on port {}",
                    pids.len(),
                    port
                )),
                Some(0),
            ))
        }

        Action::OpenUrl { url } => {
            let output = Command::new("xdg-open").arg(url).output().await?;

            Ok((None, output.status.code()))
        }

        Action::ShowNotification {
            title,
            body,
            urgency,
            ..
        } => {
            let urgency_str = match urgency {
                hive_common::actions::NotificationUrgency::Low => "low",
                hive_common::actions::NotificationUrgency::Normal => "normal",
                hive_common::actions::NotificationUrgency::Critical => "critical",
            };

            let output = Command::new("notify-send")
                .args(["-u", urgency_str, title, body])
                .output()
                .await?;

            Ok((None, output.status.code()))
        }

        Action::OpenFile { path, editor, line } => {
            let editor_cmd = editor.as_deref().unwrap_or("xdg-open");
            let mut args: Vec<String> = vec![];

            // Handle line number for common editors
            if let Some(ln) = line {
                if editor_cmd.contains("vim") || editor_cmd.contains("nvim") {
                    args.push(format!("+{}", ln));
                } else if editor_cmd.contains("code") {
                    args.push("-g".to_string());
                    args.push(format!("{}:{}", path.display(), ln));
                    let output = Command::new(editor_cmd).args(&args).output().await?;
                    return Ok((None, output.status.code()));
                }
            }

            args.push(path.display().to_string());
            let output = Command::new(editor_cmd).args(&args).output().await?;

            Ok((None, output.status.code()))
        }

        Action::CreateDirectory {
            path,
            parents,
            mode,
        } => {
            let path_str = path.display().to_string();
            let mode_str = mode.map(|m| format!("{:o}", m));

            let mut args = Vec::new();
            if *parents {
                args.push("-p".to_string());
            }
            if let Some(ref m) = mode_str {
                args.push("-m".to_string());
                args.push(m.clone());
            }
            args.push(path_str);

            let output = Command::new("mkdir").args(&args).output().await?;

            Ok((None, output.status.code()))
        }

        Action::MoveFile { from, to } => {
            let output = Command::new("mv")
                .args([
                    from.to_string_lossy().as_ref(),
                    to.to_string_lossy().as_ref(),
                ])
                .output()
                .await?;

            Ok((None, output.status.code()))
        }

        Action::CopyFile {
            from,
            to,
            recursive,
        } => {
            let mut args = Vec::new();
            if *recursive {
                args.push("-r".to_string());
            }
            args.push(from.to_string_lossy().to_string());
            args.push(to.to_string_lossy().to_string());

            let output = Command::new("cp").args(&args).output().await?;

            Ok((None, output.status.code()))
        }

        Action::DeleteFile { path, permanent } => {
            if *permanent {
                let output = Command::new("rm")
                    .args(["-rf", &path.to_string_lossy()])
                    .output()
                    .await?;
                Ok((None, output.status.code()))
            } else {
                // Try to use trash-cli if available
                let output = Command::new("trash-put")
                    .arg(path.to_string_lossy().to_string())
                    .output()
                    .await;

                match output {
                    Ok(out) => Ok((None, out.status.code())),
                    Err(_) => {
                        // Fall back to rm
                        let output = Command::new("rm")
                            .args(["-rf", &path.to_string_lossy()])
                            .output()
                            .await?;
                        Ok((None, output.status.code()))
                    }
                }
            }
        }

        Action::ChangePermissions {
            path,
            mode,
            recursive,
        } => {
            let mode_str = format!("{:o}", mode);
            let mut args = vec![];
            if *recursive {
                args.push("-R");
            }
            args.push(&mode_str);

            let path_str = path.to_string_lossy().to_string();
            args.push(&path_str);

            let output = Command::new("chmod").args(&args).output().await?;

            Ok((None, output.status.code()))
        }

        Action::AddFirewallRule { rule } => {
            // Use ufw for firewall management
            let action = match rule.action {
                hive_common::actions::FirewallAction::Allow => "allow",
                hive_common::actions::FirewallAction::Deny => "deny",
            };

            let mut args = vec![action.to_string()];

            if let Some(port) = rule.port {
                if let Some(proto) = &rule.protocol {
                    args.push(format!("{}/{}", port, proto));
                } else {
                    args.push(port.to_string());
                }
            }

            if let Some(src) = &rule.source {
                args.push("from".to_string());
                args.push(src.clone());
            }

            let output = Command::new("ufw")
                .args(args.iter().map(|s| s.as_str()).collect::<Vec<_>>())
                .output()
                .await?;

            Ok((
                Some(String::from_utf8_lossy(&output.stdout).to_string()),
                output.status.code(),
            ))
        }

        Action::Reboot { delay_secs } => {
            let output = Command::new("shutdown")
                .args(["-r", &format!("+{}", delay_secs / 60)])
                .output()
                .await?;

            Ok((None, output.status.code()))
        }

        Action::Shutdown { delay_secs } => {
            let output = Command::new("shutdown")
                .args(["-h", &format!("+{}", delay_secs / 60)])
                .output()
                .await?;

            Ok((None, output.status.code()))
        }

        Action::Suspend => {
            let output = Command::new("systemctl").arg("suspend").output().await?;

            Ok((None, output.status.code()))
        }

        Action::CleanPackageCache => {
            let output = Command::new("apt").args(["clean"]).output().await?;

            Ok((
                Some("Package cache cleaned".to_string()),
                output.status.code(),
            ))
        }

        Action::CleanSystem { targets } => {
            let mut results: Vec<String> = vec![];

            for target in targets {
                match target {
                    hive_common::actions::CleanTarget::JournalLogs { older_than_days } => {
                        let _ = Command::new("journalctl")
                            .args(["--vacuum-time", &format!("{}d", older_than_days)])
                            .output()
                            .await;
                        results.push("Cleaned journal logs".to_string());
                    }
                    hive_common::actions::CleanTarget::TempFiles => {
                        let _ = Command::new("rm").args(["-rf", "/tmp/*"]).output().await;
                        results.push("Cleaned temp files".to_string());
                    }
                    hive_common::actions::CleanTarget::PackageCache => {
                        let _ = Command::new("apt").args(["clean"]).output().await;
                        results.push("Cleaned package cache".to_string());
                    }
                    hive_common::actions::CleanTarget::Thumbnails => {
                        let _ = Command::new("rm")
                            .args(["-rf", "~/.cache/thumbnails/*"])
                            .output()
                            .await;
                        results.push("Cleaned thumbnails".to_string());
                    }
                    hive_common::actions::CleanTarget::OldKernels { keep_count } => {
                        // This is complex and distro-specific, just log it
                        results.push(format!(
                            "Old kernels cleanup requested (keep {})",
                            keep_count
                        ));
                    }
                    hive_common::actions::CleanTarget::Trash { older_than_days } => {
                        let _ = Command::new("trash-empty")
                            .arg(older_than_days.to_string())
                            .output()
                            .await;
                        results.push("Emptied trash".to_string());
                    }
                }
            }

            Ok((Some(results.join("\n")), Some(0)))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_setting_is_a_file_the_screen_reads_and_none_removes_it() {
        let dir = std::env::temp_dir().join(format!("hive-settings-{}", std::process::id()));
        std::env::set_var("HIVE_SETTINGS_DIR", &dir);
        write_setting("keyboard", Some("br abnt2".into())).unwrap();
        assert_eq!(
            std::fs::read_to_string(dir.join("keyboard")).unwrap(),
            "br abnt2\n"
        );
        write_setting("screen-level", Some("2".into())).unwrap();
        write_setting("screen-level", None).unwrap();
        assert!(!dir.join("screen-level").exists());
        write_setting("screen-level", None).unwrap();
        std::env::remove_var("HIVE_SETTINGS_DIR");
        let _ = std::fs::remove_dir_all(&dir);
    }
    use hive_common::actions::NotificationUrgency;

    #[test]
    fn rate_limiter_allows_up_to_the_configured_max() {
        let mut limiter = RateLimiter::new(3);

        assert!(limiter.check());
        assert!(limiter.check());
        assert!(limiter.check());
        assert!(
            !limiter.check(),
            "4th action within the window should be rejected"
        );
    }

    #[test]
    fn rate_limiter_with_zero_max_rejects_everything() {
        let mut limiter = RateLimiter::new(0);
        assert!(!limiter.check());
    }

    #[test]
    fn rate_limiters_enforce_per_type_limit_tighter_than_global() {
        let mut limiters = RateLimiters::new(100, [("InstallPackage".to_string(), 2)].into());

        assert!(limiters.check("InstallPackage"));
        assert!(limiters.check("InstallPackage"));
        assert!(
            !limiters.check("InstallPackage"),
            "3rd InstallPackage should hit the per-type override, well under the global cap"
        );
    }

    #[test]
    fn rate_limiters_fall_back_to_global_when_no_override_configured() {
        let mut limiters = RateLimiters::new(2, HashMap::new());

        assert!(limiters.check("ShowNotification"));
        assert!(limiters.check("OpenFile"));
        assert!(
            !limiters.check("OpenUrl"),
            "global cap should apply across action types with no override"
        );
    }

    #[test]
    fn rate_limiters_global_rejection_short_circuits_per_type_check() {
        let mut limiters = RateLimiters::new(0, [("InstallPackage".to_string(), 5)].into());
        assert!(!limiters.check("InstallPackage"));
    }

    /// A stand-in `zfs` that appends its arguments to a file and exits with
    /// `exit`, complaining the way real zfs does without permission.
    #[cfg(unix)]
    fn fake_zfs(dir: &Path, exit: i32) -> (PathBuf, PathBuf) {
        use std::os::unix::fs::PermissionsExt;
        let program = dir.join(format!("zfs-exit-{exit}"));
        let args = dir.join(format!("zfs-exit-{exit}.args"));
        std::fs::write(
            &program,
            format!(
                "#!/bin/sh\necho \"$@\" >> '{}'\necho 'cannot create snapshots : permission denied' >&2\nexit {exit}\n",
                args.display()
            ),
        )
        .unwrap();
        std::fs::set_permissions(&program, std::fs::Permissions::from_mode(0o755)).unwrap();
        (program, args)
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn the_system_is_snapshotted_before_package_changes_only() {
        let dir = tempfile::tempdir().unwrap();
        let (program, args) = fake_zfs(dir.path(), 0);
        let snapshots = SafetySnapshots {
            datasets: vec!["rpool/ROOT/d".into(), "bpool/BOOT/d".into()],
            zfs: program,
        };

        let taken = snapshots
            .before(&Action::RemovePackage {
                name: "nginx".into(),
                purge: false,
            })
            .await
            .unwrap();
        assert_eq!(taken.len(), 2);
        assert!(
            taken[0].starts_with("rpool/ROOT/d@hive-before-remove-nginx-")
                && taken[1].starts_with("bpool/BOOT/d@hive-before-remove-nginx-"),
            "{taken:?}"
        );

        for action in [
            Action::RestartService {
                name: "nginx".into(),
            },
            Action::RunCommand {
                cmd: "journalctl".into(),
                args: vec![],
                cwd: None,
                env: vec![],
            },
            Action::ShowNotification {
                title: "hi".into(),
                body: "hi".into(),
                urgency: NotificationUrgency::Normal,
                actions: vec![],
                icon: None,
            },
        ] {
            assert!(snapshots.before(&action).await.unwrap().is_empty());
        }
        // One recursive snapshot per pool, for the package change only.
        let calls = std::fs::read_to_string(&args).unwrap();
        assert_eq!(calls.lines().count(), 2, "{calls}");
    }

    #[tokio::test]
    async fn nothing_is_snapshotted_without_zfs_datasets() {
        let snapshots = SafetySnapshots {
            datasets: vec![],
            zfs: PathBuf::from("/nonexistent/zfs"),
        };
        let taken = snapshots
            .before(&Action::InstallPackage {
                name: "nginx".into(),
                assume_yes: true,
            })
            .await
            .unwrap();
        assert!(taken.is_empty());
    }

    #[test]
    fn auto_snapshot_off_or_an_explicit_dataset_override_detection() {
        let off = ActuatorConfig {
            auto_snapshot: false,
            snapshot_dataset: Some("tank/os".into()),
            ..ActuatorConfig::default()
        };
        assert!(SafetySnapshots::from_config(&off).datasets.is_empty());

        let explicit = ActuatorConfig {
            snapshot_dataset: Some("tank/os".into()),
            ..ActuatorConfig::default()
        };
        assert_eq!(
            SafetySnapshots::from_config(&explicit).datasets,
            vec!["tank/os"]
        );
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn a_package_change_is_refused_when_its_snapshot_fails() {
        let dir = tempfile::tempdir().unwrap();
        let socket_path = dir.path().join("test.sock");
        let (program, _) = fake_zfs(dir.path(), 1);
        let server = hive_common::ipc::IpcServer::bind(&socket_path)
            .await
            .unwrap();

        let server_task = tokio::spawn(async move {
            let mut conn = server.accept().await.unwrap();
            let whitelist = Whitelist::from_config(crate::whitelist::WhitelistConfig::default());
            let snapshots = SafetySnapshots {
                datasets: vec!["rpool/ROOT/d".into()],
                zfs: program,
            };
            let mut rate_limiter = RateLimiters::new(30, HashMap::new());

            handle_message(
                HiveMessage::ActionRequest {
                    request_id: uuid::Uuid::new_v4(),
                    // A package that doesn't exist, in case the refusal ever
                    // regresses and apt really runs.
                    action: Action::RemovePackage {
                        name: "druidos-test-no-such-package".into(),
                        purge: false,
                    },
                    requires_confirmation: false,
                    timeout_secs: 0,
                },
                &ActuatorConfig::default(),
                &whitelist,
                &mut rate_limiter,
                &snapshots,
                &mut conn,
            )
            .await
            .unwrap();
        });

        let mut client = hive_common::ipc::IpcSocket::connect(&socket_path)
            .await
            .unwrap();
        let response = client.recv().await.unwrap();
        server_task.await.unwrap();

        match response {
            HiveMessage::ActionResponse {
                success, output, ..
            } => {
                assert!(!success, "must not act without its safety snapshot");
                let output = output.unwrap_or_default();
                assert!(
                    output.contains("snapshot") && output.contains("permission denied"),
                    "{output}"
                );
            }
            other => panic!("expected ActionResponse, got {}", other.type_name()),
        }
    }

    #[tokio::test]
    async fn requires_confirmation_action_is_rejected_not_executed() {
        let dir = tempfile::tempdir().unwrap();
        let socket_path = dir.path().join("test.sock");
        let server = hive_common::ipc::IpcServer::bind(&socket_path)
            .await
            .unwrap();

        let server_task = tokio::spawn(async move {
            let mut conn = server.accept().await.unwrap();

            let whitelist_config = crate::whitelist::WhitelistConfig {
                service: crate::whitelist::ServiceRule {
                    allowed: ["nginx".to_string()].into_iter().collect(),
                    ..Default::default()
                },
                ..Default::default()
            };
            let whitelist = Whitelist::from_config(whitelist_config);
            // confirm_dangerous: true by default — the case under test.
            let config = ActuatorConfig::default();
            let mut rate_limiter = RateLimiters::new(30, HashMap::new());

            handle_message(
                HiveMessage::ActionRequest {
                    request_id: uuid::Uuid::new_v4(),
                    action: Action::RestartService {
                        name: "nginx".into(),
                    },
                    requires_confirmation: true,
                    timeout_secs: 0,
                },
                &config,
                &whitelist,
                &mut rate_limiter,
                &SafetySnapshots {
                    datasets: vec![],
                    zfs: PathBuf::from("zfs"),
                },
                &mut conn,
            )
            .await
            .unwrap();
        });

        let mut client = hive_common::ipc::IpcSocket::connect(&socket_path)
            .await
            .unwrap();
        let response = client.recv().await.unwrap();
        server_task.await.unwrap();

        match response {
            HiveMessage::ActionResponse {
                success, output, ..
            } => {
                assert!(!success, "action requiring confirmation must not execute");
                assert!(output.unwrap_or_default().contains("confirmation"));
            }
            other => panic!("expected ActionResponse, got {}", other.type_name()),
        }
    }
}
