//! The Hive in a box.
//!
//! Most of what the Hive does is decided between its daemons: an event
//! arrives from a nerve, hive-cortex routes it, hive-synapse suggests,
//! grove and the dashboard are told, an administrator approves, the
//! actuator is asked to act. None of that needs a VM. [`Lab`] runs the real
//! hive-cortex and hive-synapse and plays the rest itself: it injects what a
//! nerve would observe, speaks as grove and as the dashboard, and is the
//! actuator, which records what it is asked and runs nothing.
//!
//! The daemons run as they would on the system: hive-synapse drops to
//! `_hive-ai`, and each role connects under the binary name and user that
//! hive-cortex checks. Those users exist only in the lab: every daemon runs
//! in a private mount namespace where the lab's own `/etc/passwd` and
//! `/etc/group` are bound over the machine's, which stay untouched. That
//! takes root, as in a container or a throwaway VM.

pub mod agent;

use anyhow::{bail, Context as _, Result};
use chrono::Utc;
use hive_common::messages::{AnonymousLevel, HiveMessage, LogLine, ProcessInfo};
use serde::Serialize;
use serde_json::Value;
use std::collections::HashMap;
use std::ffi::CString;
use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, Command};
use tokio::sync::Notify;

/// The parts of the system the lab plays.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    /// An observer (as hive-nerve-process): what it sends is what the
    /// system did.
    Nerve,
    /// hive-actuator: receives the actions, runs none of them.
    Actuator,
    /// grove, a user's shell on the user socket.
    Shell,
    /// hive-dashboard, run by an administrator (root).
    Dashboard,
}

impl Role {
    pub const ALL: [Role; 4] = [Role::Nerve, Role::Actuator, Role::Shell, Role::Dashboard];

    /// The binary name hive-cortex reads from /proc/<pid>/cmdline.
    fn binary_name(self) -> &'static str {
        match self {
            Role::Nerve => "hive-nerve-process",
            Role::Actuator => "hive-actuator",
            Role::Shell => "grove",
            Role::Dashboard => "hive-dashboard",
        }
    }

    /// How hive-cortex logs the connection once it has accepted it.
    fn registered_as(self) -> &'static str {
        match self {
            Role::Nerve => "NerveProcess",
            Role::Actuator => "Actuator",
            Role::Shell => "Shell",
            Role::Dashboard => "Dashboard",
        }
    }

    pub fn parse(name: &str) -> Option<Role> {
        match name {
            "nerve" => Some(Role::Nerve),
            "actuator" => Some(Role::Actuator),
            "shell" | "grove" => Some(Role::Shell),
            "dashboard" => Some(Role::Dashboard),
            _ => None,
        }
    }
}

/// A message a role received, in the order the lab saw them.
#[derive(Debug, Clone, Serialize)]
pub struct Event {
    /// Milliseconds since the lab started.
    pub t: u64,
    /// Who received it.
    pub to: Role,
    /// The `HiveMessage` variant: Notification, ActionRequest...
    #[serde(rename = "type")]
    pub kind: String,
    /// The message, as JSON.
    pub message: Value,
}

pub struct Options {
    /// Where hive-cortex and hive-synapse are (target/debug, /usr/bin...).
    pub bin_dir: PathBuf,
    /// The hive-lab binary, started once per role.
    pub agent_exe: PathBuf,
    /// Start hive-synapse (without its model it answers with the mock
    /// backend; the rules that attach actions to events still apply).
    pub synapse: bool,
}

/// The ids of the lab's own users and groups.
#[derive(Debug, Clone, Copy)]
struct Ids {
    hive_gid: u32,
    act: u32,
    sense: u32,
    user: u32,
    user_gid: u32,
}

pub struct Lab {
    dir: PathBuf,
    cortex: Child,
    synapse: Option<Child>,
    stdins: HashMap<Role, ChildStdin>,
    agents: Vec<Child>,
    events: Arc<Mutex<Vec<Event>>>,
    arrived: Arc<Notify>,
    cursor: usize,
    started: Instant,
}

const READY: Duration = Duration::from_secs(15);

impl Lab {
    pub async fn start(opts: Options) -> Result<Lab> {
        if !nix::unistd::geteuid().is_root() {
            bail!(
                "hive-lab runs as root, in a container or a throwaway VM: it gives the Hive its own \
                 users in a private mount namespace, without touching this machine's /etc/passwd"
            );
        }
        for bin in ["hive-cortex", "hive-synapse"] {
            if !opts.bin_dir.join(bin).is_file() {
                bail!(
                    "no {} in {} (build the workspace first: cargo build --workspace)",
                    bin,
                    opts.bin_dir.display()
                );
            }
        }
        // Not $TMPDIR: the lab's users must reach the sockets, and a
        // per-user temporary directory is closed to them.
        let tmp =
            std::env::var_os("HIVE_LAB_TMP").map_or_else(|| PathBuf::from("/tmp"), PathBuf::from);
        let dir = tmp.join(format!(
            "hive-lab-{}-{}",
            std::process::id(),
            Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(dir.join("run"))?;
        set_mode(&dir, 0o755)?;
        set_mode(&dir.join("run"), 0o755)?;
        let ids = write_identity(&dir)?;
        std::fs::write(dir.join("config.toml"), "# hive-lab: the defaults\n")?;
        set_mode(&dir.join("config.toml"), 0o644)?;
        // The roles run as the lab's users, who may not reach the binary
        // where it was built (a home directory is often closed to others).
        let agent_exe = dir.join("hive-lab-agent");
        if std::fs::hard_link(&opts.agent_exe, &agent_exe).is_err() {
            std::fs::copy(&opts.agent_exe, &agent_exe)
                .with_context(|| format!("cannot copy {}", opts.agent_exe.display()))?;
        }
        set_mode(&agent_exe, 0o755)?;

        let started = Instant::now();
        let cortex = spawn_daemon(&opts.bin_dir.join("hive-cortex"), &dir, "cortex")?;
        let (cortex_sock, user_sock) = (dir.join("run/cortex.sock"), dir.join("run/user.sock"));
        wait_until(READY, || cortex_sock.exists() && user_sock.exists())
            .await
            .with_context(|| {
                format!(
                    "hive-cortex did not open its sockets\n{}",
                    tail(&dir, "cortex", 20)
                )
            })?;

        let mut lab = Lab {
            dir: dir.clone(),
            cortex,
            synapse: None,
            stdins: HashMap::new(),
            agents: Vec::new(),
            events: Arc::new(Mutex::new(Vec::new())),
            arrived: Arc::new(Notify::new()),
            cursor: 0,
            started,
        };
        if opts.synapse {
            lab.synapse = Some(spawn_daemon(
                &opts.bin_dir.join("hive-synapse"),
                &dir,
                "synapse",
            )?);
            lab.wait_registered("Synapse", 1).await?;
        }
        for role in Role::ALL {
            lab.spawn_agent(role, &agent_exe, ids)?;
            lab.wait_registered(role.registered_as(), 1).await?;
        }
        Ok(lab)
    }

    /// The lab's directory: run/ (the sockets), cortex.log, synapse.log,
    /// the lab's passwd and group.
    pub fn dir(&self) -> &Path {
        &self.dir
    }

    fn spawn_agent(&mut self, role: Role, exe: &Path, ids: Ids) -> Result<()> {
        let socket = match role {
            Role::Shell | Role::Dashboard => self.dir.join("run/user.sock"),
            Role::Nerve | Role::Actuator => self.dir.join("run/cortex.sock"),
        };
        let mut cmd = Command::new(exe);
        cmd.arg0(role.binary_name())
            .env("HIVE_LAB_AGENT", "1")
            .env("HIVE_LAB_SOCKET", &socket)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .kill_on_drop(true);
        match role {
            Role::Nerve => {
                cmd.uid(ids.sense).gid(ids.hive_gid);
            }
            Role::Actuator => {
                cmd.uid(ids.act)
                    .gid(ids.hive_gid)
                    .env("HIVE_LAB_AUTO_ACT", "1");
            }
            Role::Shell => {
                cmd.uid(ids.user).gid(ids.user_gid);
            }
            Role::Dashboard => {} // root: an administrator
        }
        let mut child = cmd
            .spawn()
            .with_context(|| format!("cannot start the {:?} agent", role))?;
        let stdin = child.stdin.take().context("agent stdin")?;
        let stdout = child.stdout.take().context("agent stdout")?;
        let (events, arrived, started) = (self.events.clone(), self.arrived.clone(), self.started);
        tokio::spawn(async move {
            let mut lines = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = lines.next_line().await {
                let Ok(message) = serde_json::from_str::<Value>(&line) else {
                    continue;
                };
                let kind = match &message {
                    Value::Object(map) => map.keys().next().cloned().unwrap_or_default(),
                    Value::String(s) => s.clone(),
                    _ => String::new(),
                };
                let t = started.elapsed().as_millis() as u64;
                events.lock().unwrap().push(Event {
                    t,
                    to: role,
                    kind,
                    message,
                });
                arrived.notify_waiters();
            }
        });
        self.stdins.insert(role, stdin);
        self.agents.push(child);
        Ok(())
    }

    async fn wait_registered(&self, component: &str, count: usize) -> Result<()> {
        let needle = format!(" as {}", component);
        let dir = self.dir.clone();
        wait_until(READY, || {
            log_text(&dir, "cortex")
                .lines()
                .filter(|l| l.contains("Registered connection") && l.ends_with(&needle))
                .count()
                >= count
        })
        .await
        .with_context(|| {
            format!(
                "hive-cortex did not register {}\n{}\n{}",
                component,
                tail(&self.dir, "cortex", 20),
                tail(&self.dir, "synapse", 10)
            )
        })
    }

    /// Sends a message as a role: a nerve's observation, grove's question,
    /// the dashboard's answer.
    pub async fn send(&mut self, role: Role, msg: &HiveMessage) -> Result<()> {
        let stdin = self.stdins.get_mut(&role).context("no such role")?;
        let mut line = serde_json::to_string(msg)?;
        line.push('\n');
        stdin.write_all(line.as_bytes()).await?;
        stdin.flush().await?;
        Ok(())
    }

    /// Everything received since the last call (or since the last `until`).
    pub fn take_new(&mut self) -> Vec<Event> {
        let events = self.events.lock().unwrap();
        let new = events[self.cursor..].to_vec();
        self.cursor = events.len();
        new
    }

    /// Every event so far.
    pub fn all_events(&self) -> Vec<Event> {
        self.events.lock().unwrap().clone()
    }

    /// Waits for the first new event that matches, and returns it with the
    /// ones before it. The next `take_new`/`until` starts after it.
    pub async fn until(
        &mut self,
        matches: impl Fn(&Event) -> bool,
        timeout: Duration,
    ) -> Result<(Event, Vec<Event>)> {
        let deadline = Instant::now() + timeout;
        loop {
            let notified = self.arrived.notified();
            {
                let events = self.events.lock().unwrap();
                if let Some(i) = events[self.cursor..].iter().position(&matches) {
                    let upto = self.cursor + i;
                    let before = events[self.cursor..upto].to_vec();
                    let found = events[upto].clone();
                    self.cursor = upto + 1;
                    return Ok((found, before));
                }
            }
            let left = deadline.saturating_duration_since(Instant::now());
            if left.is_zero() {
                bail!("nothing matched in {:.1} s", timeout.as_secs_f32());
            }
            let _ = tokio::time::timeout(left, notified).await;
        }
    }

    /// The last lines a daemon logged ("cortex" or "synapse").
    pub fn log(&self, daemon: &str, lines: usize) -> String {
        tail(&self.dir, daemon, lines)
    }

    /// Stops everything and removes the lab's directory.
    pub async fn end(mut self) {
        self.stdins.clear(); // the agents see their stdin close and leave
        for mut child in self.agents.drain(..) {
            let _ = tokio::time::timeout(Duration::from_secs(2), child.wait()).await;
            let _ = child.kill().await;
        }
        if let Some(mut synapse) = self.synapse.take() {
            let _ = synapse.kill().await;
        }
        let _ = self.cortex.kill().await;
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}

// --- what a nerve observes, ready made ---

pub fn process(pid: u32, uid: u32, name: &str) -> ProcessInfo {
    ProcessInfo {
        pid,
        uid,
        name: name.to_string(),
        cmdline: vec![name.to_string()],
        cwd: None,
        ppid: None,
    }
}

pub fn log_line(text: &str, unit: &str) -> LogLine {
    LogLine {
        timestamp: Utc::now(),
        message: text.to_string(),
        priority: 3,
        unit: Some(unit.to_string()),
    }
}

/// A unit that failed: `nginx.service` exited with `exit_code` after
/// `restarts` restarts.
pub fn service_crash(service: &str, exit_code: i32, restarts: u32, logs: &[&str]) -> HiveMessage {
    HiveMessage::ServiceCrash {
        service: service.to_string(),
        exit_code,
        restart_count: restarts,
        logs: logs.iter().map(|l| log_line(l, service)).collect(),
    }
}

pub fn port_conflict(port: u16, requested_by: &str, held_by: &str) -> HiveMessage {
    HiveMessage::PortConflict {
        port,
        requested_by: process(4242, 0, requested_by),
        held_by: process(1717, 0, held_by),
    }
}

pub fn disk_low(mount: &str, usage_percent: f32) -> HiveMessage {
    let total: u64 = 20 * 1024 * 1024 * 1024;
    let available = ((1.0 - usage_percent as f64 / 100.0) * total as f64) as u64;
    HiveMessage::DiskSpaceLow {
        mount: PathBuf::from(mount),
        available_bytes: available,
        threshold_bytes: total / 10,
        usage_percent,
    }
}

pub fn command_observed(cmd: &str, uid: u32) -> HiveMessage {
    let name = cmd.split_whitespace().next().unwrap_or(cmd);
    HiveMessage::CommandObserved {
        process: ProcessInfo {
            cmdline: cmd.split_whitespace().map(str::to_string).collect(),
            ..process(5151, uid, name)
        },
        cmd: cmd.to_string(),
        timestamp: Utc::now(),
    }
}

pub fn user_query(text: &str) -> HiveMessage {
    HiveMessage::UserQuery {
        request_id: uuid::Uuid::new_v4(),
        query: text.to_string(),
        cwd: None,
    }
}

pub fn anonymous(on: bool) -> HiveMessage {
    if on {
        HiveMessage::AnonymousModeEnter {
            level: AnonymousLevel::Detach,
            pid: None,
        }
    } else {
        HiveMessage::AnonymousModeExit { pid: None }
    }
}

// --- the private namespace and the lab's users ---

/// Writes the lab's passwd and group: the machine's, plus the Hive's
/// service users (all in group `hive`, which owns the component socket) and
/// a user for grove, unless the machine already has them.
fn write_identity(dir: &Path) -> Result<Ids> {
    let mut passwd = std::fs::read_to_string("/etc/passwd").unwrap_or_default();
    let mut group = std::fs::read_to_string("/etc/group").unwrap_or_default();
    let field = |text: &str, name: &str, idx: usize| -> Option<u32> {
        text.lines()
            .find(|l| l.split(':').next() == Some(name))
            .and_then(|l| l.split(':').nth(idx))
            .and_then(|v| v.parse().ok())
    };
    let hive_gid = field(&group, "hive", 2).unwrap_or(61000);
    if field(&group, "hive", 2).is_none() {
        group.push_str(&format!(
            "hive:x:{}:_hive-ai,_hive-act,_hive-sense\n",
            hive_gid
        ));
    }
    let mut user = |name: &str, uid: u32, gid: u32| -> u32 {
        match field(&passwd, name, 2) {
            Some(existing) => existing,
            None => {
                passwd.push_str(&format!(
                    "{}:x:{}:{}::/nonexistent:/usr/sbin/nologin\n",
                    name, uid, gid
                ));
                uid
            }
        }
    };
    user("_hive-ai", 61001, hive_gid); // hive-synapse drops to it by name
    let act = user("_hive-act", 61002, hive_gid);
    let sense = user("_hive-sense", 61003, hive_gid);
    let user_gid = 61010;
    let lab_user = user("druid", 61010, user_gid);
    if field(&group, "druid", 2).is_none() {
        group.push_str(&format!("druid:x:{}:\n", user_gid));
    }
    std::fs::write(dir.join("passwd"), passwd)?;
    std::fs::write(dir.join("group"), group)?;
    set_mode(&dir.join("passwd"), 0o644)?;
    set_mode(&dir.join("group"), 0o644)?;
    Ok(Ids {
        hive_gid,
        act,
        sense,
        user: lab_user,
        user_gid,
    })
}

/// Starts hive-cortex or hive-synapse in a private mount namespace with the
/// lab's passwd and group, its sockets and config in the lab's directory,
/// and its log in `<name>.log`.
fn spawn_daemon(bin: &Path, dir: &Path, name: &str) -> Result<Child> {
    let log = std::fs::File::create(dir.join(format!("{}.log", name)))?;
    let passwd = CString::new(dir.join("passwd").as_os_str().as_encoded_bytes())?;
    let group = CString::new(dir.join("group").as_os_str().as_encoded_bytes())?;
    let mut cmd = Command::new(bin);
    cmd.env("HIVE_CORTEX_SOCKET", dir.join("run/cortex.sock"))
        .env("HIVE_USER_SOCKET", dir.join("run/user.sock"))
        .env("HIVE_CONFIG", dir.join("config.toml"))
        .env("NO_COLOR", "1")
        .env_remove("JOURNAL_STREAM")
        .stdin(Stdio::null())
        .stdout(log.try_clone()?)
        .stderr(log)
        .kill_on_drop(true);
    // SAFETY: runs in the child between fork and exec; it only makes
    // syscalls (unshare, mount) on paths prepared before the fork.
    unsafe {
        cmd.pre_exec(move || enter_namespace(&passwd, &group));
    }
    cmd.spawn()
        .with_context(|| format!("cannot start {}", bin.display()))
}

fn enter_namespace(passwd: &std::ffi::CStr, group: &std::ffi::CStr) -> std::io::Result<()> {
    use nix::mount::{mount, MsFlags};
    use nix::sched::{unshare, CloneFlags};
    let io = |e: nix::errno::Errno| std::io::Error::from_raw_os_error(e as i32);
    unshare(CloneFlags::CLONE_NEWNS).map_err(io)?;
    mount(
        None::<&str>,
        "/",
        None::<&str>,
        MsFlags::MS_REC | MsFlags::MS_PRIVATE,
        None::<&str>,
    )
    .map_err(io)?;
    mount(
        Some(passwd),
        "/etc/passwd",
        None::<&str>,
        MsFlags::MS_BIND,
        None::<&str>,
    )
    .map_err(io)?;
    mount(
        Some(group),
        "/etc/group",
        None::<&str>,
        MsFlags::MS_BIND,
        None::<&str>,
    )
    .map_err(io)?;
    Ok(())
}

fn set_mode(path: &Path, mode: u32) -> Result<()> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(mode))?;
    Ok(())
}

async fn wait_until(timeout: Duration, ready: impl Fn() -> bool) -> Result<()> {
    let deadline = Instant::now() + timeout;
    while !ready() {
        if Instant::now() > deadline {
            bail!("timed out after {:.0} s", timeout.as_secs_f32());
        }
        tokio::time::sleep(Duration::from_millis(25)).await;
    }
    Ok(())
}

fn log_text(dir: &Path, daemon: &str) -> String {
    let raw = std::fs::read_to_string(dir.join(format!("{}.log", daemon))).unwrap_or_default();
    strip_ansi(&raw)
}

fn tail(dir: &Path, daemon: &str, lines: usize) -> String {
    let text = log_text(dir, daemon);
    let all: Vec<&str> = text.lines().collect();
    all[all.len().saturating_sub(lines)..].join("\n")
}

fn strip_ansi(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '\u{1b}' && chars.peek() == Some(&'[') {
            for d in chars.by_ref() {
                if d.is_ascii_alphabetic() {
                    break;
                }
            }
        } else {
            out.push(c);
        }
    }
    out
}
