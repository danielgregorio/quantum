//! Hive Cortex - Central Orchestrator Daemon
//!
//! The central nervous system of the Hive Stack. Manages connections from
//! all other components, routes messages, and coordinates system responses.
//!
//! # Security Model
//!
//! - Runs as root to manage other components
//! - Creates Unix sockets with proper permissions: the component socket
//!   (root:hive 0660) for the Hive's own daemons, and a user socket (0666)
//!   for grove and hive-dashboard, where what a connection may send depends
//!   on who it is (any user: questions; administrators: approving actions)
//! - Authenticates connections via peer credentials
//! - Routes messages based on component type

mod router;

use anyhow::{Context, Result};
use hive_common::anonymous::AnonymousManager;
use hive_common::config::Config;
use hive_common::ipc::{IpcError, IpcServer, IpcSocket};
use hive_common::messages::{HiveMessage, MessageId, Suggestion};
use nix::unistd::{Group, Uid, User};
use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;
use tokio::signal;
use tokio::sync::{mpsc, RwLock};
use tracing::{debug, error, info, warn};

use crate::router::MessageRouter;

/// Default socket paths
const SOCKET_PATH: &str = hive_common::CORTEX_SOCKET;
const USER_SOCKET_PATH: &str = hive_common::USER_SOCKET;

/// Connected component types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ComponentType {
    Synapse,
    Actuator,
    /// hive-dashboard — the interactive TUI panel showing notifications
    /// and suggestions. Not a systemd service (user-run, like top/htop): it
    /// connects through the user socket, and only an administrator's gets
    /// this type (see `is_administrator`).
    Dashboard,
    NerveProcess,
    NerveJournal,
    NerveNetwork,
    NerveFs,
    /// A user's shell (grove), connected through the user socket - never
    /// the component socket, so it is typed by where it connected, not by
    /// its binary name.
    Shell,
    Unknown,
}

impl ComponentType {
    fn from_name(name: &str) -> Self {
        match name {
            "hive-synapse" => ComponentType::Synapse,
            "hive-actuator" => ComponentType::Actuator,
            "hive-dashboard" => ComponentType::Dashboard,
            "hive-nerve-process" => ComponentType::NerveProcess,
            "hive-nerve-journal" => ComponentType::NerveJournal,
            "hive-nerve-network" => ComponentType::NerveNetwork,
            "hive-nerve-fs" => ComponentType::NerveFs,
            _ => ComponentType::Unknown,
        }
    }

    /// The observers (`hive-nerve-*`).
    fn is_nerve(self) -> bool {
        matches!(
            self,
            ComponentType::NerveProcess
                | ComponentType::NerveJournal
                | ComponentType::NerveNetwork
                | ComponentType::NerveFs
        )
    }
}

/// Connected component state
struct ConnectedComponent {
    component_type: ComponentType,
    tx: mpsc::Sender<HiveMessage>,
    /// Peer credentials, from the kernel: what a shell may make anonymous
    /// (itself), and who asked a question.
    pid: i32,
    uid: u32,
}

/// Shared state between all connection handlers
struct CortexState {
    #[allow(dead_code)] // read at construction only; not yet used for reload
    config: Config,
    components: HashMap<u64, ConnectedComponent>,
    next_conn_id: u64,
    pending_requests: HashMap<MessageId, u64>, // request_id -> conn_id
    // notification_id -> suggestions offered in that notification, kept
    // around so UserAction can look up which Action the user picked.
    pending_suggestions: HashMap<MessageId, Vec<Suggestion>>,
    // request id sent to synapse -> (asking connection, the asker's own id)
    pending_queries: HashMap<MessageId, (u64, MessageId)>,
    // package -> when it was last offered for a missing command
    offered_packages: HashMap<String, std::time::Instant>,
    anonymous: AnonymousManager,
}

impl CortexState {
    fn new(config: Config) -> Self {
        let mut anonymous = AnonymousManager::new();
        // Apply global quiet mode from config if set
        anonymous.set_global_quiet(config.general.anonymous_mode);

        Self {
            config,
            components: HashMap::new(),
            next_conn_id: 1,
            pending_requests: HashMap::new(),
            pending_suggestions: HashMap::new(),
            pending_queries: HashMap::new(),
            offered_packages: HashMap::new(),
            anonymous,
        }
    }

    fn register_component(
        &mut self,
        component_type: ComponentType,
        tx: mpsc::Sender<HiveMessage>,
        pid: i32,
        uid: u32,
    ) -> u64 {
        let conn_id = self.next_conn_id;
        self.next_conn_id += 1;

        self.components.insert(
            conn_id,
            ConnectedComponent {
                component_type,
                tx,
                pid,
                uid,
            },
        );

        conn_id
    }

    fn unregister_component(&mut self, conn_id: u64) {
        self.components.remove(&conn_id);
    }

    fn get_component_by_type(&self, component_type: ComponentType) -> Option<&ConnectedComponent> {
        self.components
            .values()
            .find(|c| c.component_type == component_type)
    }

    fn component_type_of(&self, conn_id: u64) -> Option<ComponentType> {
        self.components.get(&conn_id).map(|c| c.component_type)
    }

    fn components_of_type(
        &self,
        component_type: ComponentType,
    ) -> impl Iterator<Item = &ConnectedComponent> {
        self.components
            .values()
            .filter(move |c| c.component_type == component_type)
    }
}

type SharedState = Arc<RwLock<CortexState>>;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_cortex")?;

    info!("Hive Cortex starting...");

    // Load configuration
    let config = load_config().await?;

    // Create socket directory
    let socket_path =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| SOCKET_PATH.to_string());

    let user_socket_path =
        std::env::var("HIVE_USER_SOCKET").unwrap_or_else(|_| USER_SOCKET_PATH.to_string());

    create_socket_dir(&socket_path)?;
    create_socket_dir(&user_socket_path)?;

    // Initialize shared state
    let state = Arc::new(RwLock::new(CortexState::new(config)));

    // Create the servers
    info!("Creating socket at {}", socket_path);
    let server = IpcServer::bind(&socket_path)
        .await
        .context("Failed to create socket")?;
    info!("Creating user socket at {}", user_socket_path);
    let user_server = IpcServer::bind_for_all_users(&user_socket_path)
        .await
        .context("Failed to create user socket")?;

    info!("Hive Cortex ready, listening for connections");
    hive_common::systemd::report_ready();

    // Accept connections
    loop {
        tokio::select! {
            result = server.accept() => {
                match result {
                    Ok(socket) => {
                        let state = Arc::clone(&state);
                        tokio::spawn(async move {
                            if let Err(e) = handle_connection(socket, state, Origin::Component).await {
                                error!("Connection error: {}", e);
                            }
                        });
                    }
                    Err(e) => {
                        error!("Accept error: {}", e);
                    }
                }
            }
            result = user_server.accept() => {
                match result {
                    Ok(socket) => {
                        let state = Arc::clone(&state);
                        tokio::spawn(async move {
                            if let Err(e) = handle_connection(socket, state, Origin::User).await {
                                error!("User connection error: {}", e);
                            }
                        });
                    }
                    Err(e) => {
                        error!("User socket accept error: {}", e);
                    }
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    // Cleanup
    let _ = std::fs::remove_file(&socket_path);
    let _ = std::fs::remove_file(&user_socket_path);
    info!("Hive Cortex shut down");

    Ok(())
}

async fn load_config() -> Result<Config> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        Config::load(&config_path)
    } else {
        warn!("Config file not found, using defaults");
        Ok(Config::default())
    }
}

fn create_socket_dir(socket_path: &str) -> Result<()> {
    use std::os::unix::fs::PermissionsExt;

    if let Some(parent) = Path::new(socket_path).parent() {
        std::fs::create_dir_all(parent)?;
        std::fs::set_permissions(parent, std::fs::Permissions::from_mode(0o755))?;
    }

    // Remove old socket if exists
    let _ = std::fs::remove_file(socket_path);

    Ok(())
}

/// Which socket a connection came in on.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Origin {
    /// The component socket (root:hive): the Hive's own daemons and tools.
    Component,
    /// The user socket (any local user): grove.
    User,
}

/// What a connection on the user socket may send, by what it was typed as.
/// Everything else - a forged SuggestionResponse, an ActionRequest, a
/// Notification... - is dropped before routing: any local user can connect
/// there.
fn user_may_send(component_type: ComponentType, msg: &HiveMessage) -> bool {
    match component_type {
        ComponentType::Shell => matches!(
            msg,
            HiveMessage::UserQuery { .. }
                | HiveMessage::CommandNotFound { .. }
                | HiveMessage::AnonymousModeEnter { .. }
                | HiveMessage::AnonymousModeExit { .. }
                | HiveMessage::Ping { .. }
        ),
        ComponentType::Dashboard => matches!(
            msg,
            HiveMessage::UserAction { .. }
                | HiveMessage::UserDismiss { .. }
                | HiveMessage::Ping { .. }
        ),
        _ => false,
    }
}

/// Groups whose members may act on the Hive's suggestions, besides root:
/// the ones a distribution makes its administrators (Ubuntu's first user is
/// in sudo). Not `hive`: that is the service accounts' group.
const ADMIN_GROUPS: &[&str] = &["sudo", "admin", "wheel"];

/// Whether `uid` may approve actions: root, or an account in one of
/// `ADMIN_GROUPS` - judged by the account's groups (from the kernel-verified
/// uid), not by anything the connecting process says.
fn is_administrator(uid: u32) -> bool {
    if uid == 0 {
        return true;
    }
    let Ok(Some(user)) = User::from_uid(Uid::from_raw(uid)) else {
        return false;
    };
    let Ok(name) = std::ffi::CString::new(user.name.as_str()) else {
        return false;
    };
    let Ok(groups) = nix::unistd::getgrouplist(&name, user.gid) else {
        return false;
    };
    groups.into_iter().any(|gid| {
        matches!(Group::from_gid(gid), Ok(Some(group)) if ADMIN_GROUPS.contains(&group.name.as_str()))
    })
}

async fn handle_connection(
    mut socket: IpcSocket,
    state: SharedState,
    origin: Origin,
) -> Result<()> {
    // Get peer credentials
    let creds = socket.peer_credentials()?;
    info!(
        "New connection from pid={}, uid={} ({:?} socket)",
        creds.pid, creds.uid, origin
    );

    let component_type = match origin {
        // A shell unless it's hive-dashboard run by an administrator. The
        // name alone decides nothing: authority comes from the uid.
        Origin::User => match get_component_type(creds.pid) {
            ComponentType::Dashboard if is_administrator(creds.uid) => ComponentType::Dashboard,
            ComponentType::Dashboard => {
                warn!(
                    "Refusing hive-dashboard for uid {}: acting on the Hive's suggestions takes \
                     root or membership in {}",
                    creds.uid,
                    ADMIN_GROUPS.join(", ")
                );
                return Ok(());
            }
            _ => ComponentType::Shell,
        },
        // Determine component type from process name, then verify it
        // against the connection's real uid — a self-reported name alone is
        // spoofable. hive-dashboard belongs on the user socket.
        Origin::Component => match get_component_type(creds.pid) {
            ComponentType::Dashboard => {
                warn!("hive-dashboard connected to the component socket; it uses the user socket");
                ComponentType::Unknown
            }
            claimed_type => verify_component_identity(claimed_type, creds.uid),
        },
    };
    info!("Component type: {:?}", component_type);

    // Create channel for sending messages to this connection
    let (tx, mut rx) = mpsc::channel::<HiveMessage>(100);

    // Register component
    let conn_id = {
        let mut state = state.write().await;
        state.register_component(component_type, tx, creds.pid, creds.uid)
    };

    info!("Registered connection {} as {:?}", conn_id, component_type);

    // Handle messages
    loop {
        tokio::select! {
            // Receive from socket
            result = socket.recv() => {
                match result {
                    Ok(msg) => {
                        debug!("Received {} from conn {}", msg.type_name(), conn_id);
                        if origin == Origin::User && !user_may_send(component_type, &msg) {
                            warn!(
                                "Rejecting {} from user connection {} (uid {})",
                                msg.type_name(), conn_id, creds.uid
                            );
                            continue;
                        }
                        if let Err(e) = route_message(msg, conn_id, &state).await {
                            error!("Error routing message: {}", e);
                        }
                    }
                    Err(IpcError::ConnectionClosed) => {
                        info!("Connection {} closed", conn_id);
                        break;
                    }
                    Err(e) => {
                        error!("Receive error: {}", e);
                        break;
                    }
                }
            }
            // Send to socket
            Some(msg) = rx.recv() => {
                debug!("Sending {} to conn {}", msg.type_name(), conn_id);
                if let Err(e) = socket.send(&msg).await {
                    error!("Send error: {}", e);
                    break;
                }
            }
        }
    }

    // Unregister component. A shell that went anonymous and then closed
    // (exit, crash) takes its anonymity with it: a later process reusing its
    // pid must not inherit it.
    {
        let mut state = state.write().await;
        state.unregister_component(conn_id);
        if component_type == ComponentType::Shell {
            state.anonymous.remove_session_for_pid(creds.pid as u32);
            state
                .pending_queries
                .retain(|_, (conn, _)| *conn != conn_id);
        }
    }

    info!("Connection {} terminated", conn_id);
    Ok(())
}

fn get_component_type(pid: i32) -> ComponentType {
    // /proc/{pid}/comm is tempting (simpler) but the kernel truncates it to
    // TASK_COMM_LEN-1 = 15 bytes, which silently mismatches every binary
    // name longer than that ("hive-nerve-process" -> "hive-nerve-proc").
    // argv[0] from /proc/{pid}/cmdline isn't truncated, so use that instead.
    let cmdline_path = format!("/proc/{}/cmdline", pid);
    match std::fs::read(cmdline_path) {
        Ok(raw) => component_type_from_cmdline_bytes(&raw),
        Err(_) => ComponentType::Unknown,
    }
}

/// Parses the component type out of raw `/proc/{pid}/cmdline` bytes
/// (NUL-separated argv), taking the basename of argv[0] in case the
/// process was invoked by path rather than a bare name on PATH.
fn component_type_from_cmdline_bytes(raw: &[u8]) -> ComponentType {
    let Some(argv0) = raw.split(|&b| b == 0).next() else {
        return ComponentType::Unknown;
    };
    let Ok(argv0) = std::str::from_utf8(argv0) else {
        return ComponentType::Unknown;
    };
    let name = Path::new(argv0)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or(argv0);
    ComponentType::from_name(name)
}

/// The system user each privileged component type must run as, matching
/// `User=` in `config/systemd/hive-*.service`. `None` means there's no
/// dedicated user to check (the type is either unprivileged, or — like
/// Dashboard — a user-run interactive tool with no systemd unit at all).
fn expected_user(component_type: ComponentType) -> Option<&'static str> {
    match component_type {
        ComponentType::Synapse => Some("_hive-ai"),
        ComponentType::Actuator => Some("_hive-act"),
        ComponentType::NerveProcess
        | ComponentType::NerveJournal
        | ComponentType::NerveNetwork
        | ComponentType::NerveFs => Some("_hive-sense"),
        ComponentType::Dashboard | ComponentType::Shell | ComponentType::Unknown => None,
    }
}

/// Verifies a self-reported component type against the connection's real
/// uid, downgrading to `Unknown` on any mismatch. `/proc/{pid}/comm` alone
/// (used by `get_component_type`) is just the process's own claim — a
/// hostile process can name its binary `hive-actuator` and would otherwise
/// get registered as one, receiving whatever cortex forwards to that role.
fn verify_component_identity(claimed: ComponentType, uid: u32) -> ComponentType {
    let Some(expected_username) = expected_user(claimed) else {
        return claimed;
    };

    match User::from_uid(Uid::from_raw(uid)) {
        Ok(Some(user)) if user.name == expected_username => claimed,
        Ok(Some(user)) => {
            warn!(
                "Connection claimed {:?} but runs as '{}' (expected '{}'); downgrading to Unknown",
                claimed, user.name, expected_username
            );
            ComponentType::Unknown
        }
        Ok(None) => {
            warn!(
                "Connection claimed {:?} but uid {} has no user entry; downgrading to Unknown",
                claimed, uid
            );
            ComponentType::Unknown
        }
        Err(e) => {
            warn!(
                "Failed to resolve uid {}: {}; downgrading {:?} to Unknown",
                uid, e, claimed
            );
            ComponentType::Unknown
        }
    }
}

async fn route_message(msg: HiveMessage, from_conn: u64, state: &SharedState) -> Result<()> {
    let router = MessageRouter::new(state.clone());
    router.route(msg, from_conn).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn component_type_from_name_matches_known_binaries() {
        assert_eq!(
            ComponentType::from_name("hive-synapse"),
            ComponentType::Synapse
        );
        assert_eq!(
            ComponentType::from_name("hive-actuator"),
            ComponentType::Actuator
        );
        assert_eq!(
            ComponentType::from_name("hive-nerve-fs"),
            ComponentType::NerveFs
        );
        assert_eq!(
            ComponentType::from_name("hive-dashboard"),
            ComponentType::Dashboard
        );
    }

    #[test]
    fn component_type_from_name_defaults_to_unknown() {
        assert_eq!(
            ComponentType::from_name("some-random-binary"),
            ComponentType::Unknown
        );
        assert_eq!(ComponentType::from_name(""), ComponentType::Unknown);
    }

    #[test]
    fn component_type_from_cmdline_resolves_names_too_long_for_proc_comm() {
        // /proc/{pid}/comm truncates to TASK_COMM_LEN-1 = 15 bytes, which
        // would read back as "hive-nerve-proc" for these three -- verify
        // the cmdline-based path (not comm-based) still resolves them
        // correctly regardless of length.
        assert_eq!(
            component_type_from_cmdline_bytes(b"/usr/bin/hive-nerve-process\0"),
            ComponentType::NerveProcess
        );
        assert_eq!(
            component_type_from_cmdline_bytes(b"hive-nerve-journal\0"),
            ComponentType::NerveJournal
        );
        assert_eq!(
            component_type_from_cmdline_bytes(b"hive-nerve-network\0"),
            ComponentType::NerveNetwork
        );
    }

    #[test]
    fn component_type_from_cmdline_uses_argv0_basename_and_ignores_later_args() {
        assert_eq!(
            component_type_from_cmdline_bytes(b"/opt/hive/hive-synapse\0--verbose\0"),
            ComponentType::Synapse
        );
    }

    #[test]
    fn component_type_from_cmdline_handles_empty_or_invalid_input() {
        assert_eq!(
            component_type_from_cmdline_bytes(b""),
            ComponentType::Unknown
        );
        assert_eq!(
            component_type_from_cmdline_bytes(&[0xff, 0xfe]),
            ComponentType::Unknown
        );
    }

    #[test]
    fn uid_mismatch_downgrades_privileged_claim_to_unknown() {
        // uid 0 is always "root" on a real Linux box, never one of the
        // dedicated _hive-* service accounts.
        assert_eq!(
            verify_component_identity(ComponentType::Actuator, 0),
            ComponentType::Unknown
        );
        assert_eq!(
            verify_component_identity(ComponentType::Synapse, 0),
            ComponentType::Unknown
        );
        assert_eq!(
            verify_component_identity(ComponentType::NerveFs, 0),
            ComponentType::Unknown
        );
    }

    #[test]
    fn uid_with_no_passwd_entry_downgrades_to_unknown() {
        assert_eq!(
            verify_component_identity(ComponentType::Actuator, 999_999),
            ComponentType::Unknown
        );
    }

    #[test]
    fn the_user_socket_only_takes_user_messages() {
        use hive_common::messages::Severity;

        let shell = ComponentType::Shell;
        let dashboard = ComponentType::Dashboard;
        let approve = HiveMessage::UserAction {
            notification_id: uuid::Uuid::new_v4(),
            suggestion_id: 1,
            confirmed: true,
        };
        let ask = HiveMessage::UserQuery {
            request_id: uuid::Uuid::new_v4(),
            query: "why".into(),
            cwd: None,
        };
        assert!(user_may_send(shell, &ask));
        assert!(user_may_send(
            shell,
            &HiveMessage::AnonymousModeExit { pid: Some(1) }
        ));
        assert!(user_may_send(
            shell,
            &HiveMessage::CommandNotFound {
                command: "htop".into(),
                package: "htop".into()
            }
        ));
        // Only an administrator's dashboard approves - and it doesn't ask.
        assert!(!user_may_send(shell, &approve));
        assert!(user_may_send(dashboard, &approve));
        assert!(!user_may_send(dashboard, &ask));

        for forged in [
            HiveMessage::UserAction {
                notification_id: uuid::Uuid::new_v4(),
                suggestion_id: 1,
                confirmed: true,
            },
            HiveMessage::SuggestionResponse {
                request_id: uuid::Uuid::new_v4(),
                suggestions: vec![],
                processing_time_ms: 0,
            },
            HiveMessage::Notification {
                id: uuid::Uuid::new_v4(),
                title: "t".into(),
                body: "b".into(),
                severity: Severity::Info,
                actions: vec![],
                timeout_secs: 0,
            },
            HiveMessage::UserDismiss {
                notification_id: uuid::Uuid::new_v4(),
            },
            HiveMessage::Shutdown { reason: "x".into() },
        ] {
            assert!(
                !user_may_send(shell, &forged),
                "accepted {}",
                forged.type_name()
            );
            assert!(
                !user_may_send(ComponentType::Unknown, &forged),
                "accepted {}",
                forged.type_name()
            );
        }
    }

    #[test]
    fn root_is_an_administrator_and_nobody_is_not() {
        assert!(is_administrator(0));
        // nobody (65534) is in no administrators' group anywhere.
        assert!(!is_administrator(65534));
        assert!(!is_administrator(999_999));
    }

    #[test]
    fn unchecked_types_pass_through_regardless_of_uid() {
        assert_eq!(
            verify_component_identity(ComponentType::Dashboard, 0),
            ComponentType::Dashboard
        );
        assert_eq!(
            verify_component_identity(ComponentType::Unknown, 0),
            ComponentType::Unknown
        );
    }
}
