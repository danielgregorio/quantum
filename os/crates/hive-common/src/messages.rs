//! Hive Stack IPC message types.
//!
//! All communication between Hive components uses these typed messages.
//! Messages are serialized with bincode for efficient binary transport.

use crate::actions::Action;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Unique identifier for messages
pub type MessageId = uuid::Uuid;

/// Process information for context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessInfo {
    /// Process ID
    pub pid: u32,
    /// User ID
    pub uid: u32,
    /// Process name
    pub name: String,
    /// Command line arguments
    pub cmdline: Vec<String>,
    /// Working directory
    pub cwd: Option<PathBuf>,
    /// Parent process ID
    pub ppid: Option<u32>,
}

/// Log line with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogLine {
    /// Timestamp of the log entry
    pub timestamp: DateTime<Utc>,
    /// Log message content
    pub message: String,
    /// Log priority/level
    pub priority: u8,
    /// Unit/service name
    pub unit: Option<String>,
}

/// Severity levels for events
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Severity {
    /// Informational, no action needed
    Info,
    /// Something to be aware of
    Notice,
    /// Potential issue, may need attention
    Warning,
    /// Problem that needs attention
    Error,
    /// Serious problem requiring immediate action
    Critical,
}

impl Severity {
    /// Returns true if this severity requires user notification
    pub fn requires_notification(&self) -> bool {
        matches!(
            self,
            Severity::Warning | Severity::Error | Severity::Critical
        )
    }
}

/// Context provided to the SLM for generating suggestions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Context {
    /// Recent commands executed
    pub recent_commands: Vec<String>,
    /// Current working directory
    pub cwd: Option<PathBuf>,
    /// Active services
    pub active_services: Vec<String>,
    /// Recent log entries (errors/warnings only)
    pub recent_logs: Vec<LogLine>,
    /// System resource usage
    pub resources: Option<ResourceUsage>,
    /// The triggering event, if any
    pub trigger: Option<Box<HiveMessage>>,
}

/// System resource usage snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceUsage {
    /// CPU usage percentage (0-100)
    pub cpu_percent: f32,
    /// Memory usage in bytes
    pub memory_used: u64,
    /// Total memory in bytes
    pub memory_total: u64,
    /// Disk usage per mount point
    pub disk_usage: Vec<DiskUsage>,
}

/// Disk usage for a mount point
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskUsage {
    /// Mount point path
    pub mount: PathBuf,
    /// Used bytes
    pub used: u64,
    /// Total bytes
    pub total: u64,
}

/// A suggestion from the SLM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Suggestion {
    /// Unique ID for this suggestion
    pub id: u32,
    /// Short title
    pub title: String,
    /// Longer description/explanation
    pub description: String,
    /// Optional action to execute
    pub action: Option<Action>,
    /// Optional link for more information
    pub learn_more: Option<String>,
    /// Confidence score (0.0 - 1.0)
    pub confidence: f32,
}

/// All messages in the Hive Stack IPC protocol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HiveMessage {
    // =========================================================================
    // From nerves to cortex (observations)
    // =========================================================================
    /// A command was executed
    CommandObserved {
        /// Process info
        process: ProcessInfo,
        /// The command string
        cmd: String,
        /// Timestamp
        timestamp: DateTime<Utc>,
    },

    /// A port conflict was detected
    PortConflict {
        /// The conflicting port
        port: u16,
        /// Process trying to bind
        requested_by: ProcessInfo,
        /// Process already holding the port
        held_by: ProcessInfo,
    },

    /// An anomaly was detected in logs
    LogAnomaly {
        /// Service/unit name
        service: String,
        /// Severity of the anomaly
        severity: Severity,
        /// Relevant log lines
        lines: Vec<LogLine>,
        /// Pattern that matched (if applicable)
        pattern: Option<String>,
    },

    /// A service crashed
    ServiceCrash {
        /// Service name
        service: String,
        /// Exit code
        exit_code: i32,
        /// Number of restarts in recent period
        restart_count: u32,
        /// Recent logs from the service
        logs: Vec<LogLine>,
    },

    /// Disk space is running low
    DiskSpaceLow {
        /// Mount point
        mount: PathBuf,
        /// Available bytes
        available_bytes: u64,
        /// Threshold that triggered this
        threshold_bytes: u64,
        /// Usage percentage
        usage_percent: f32,
    },

    /// High memory pressure detected
    MemoryPressure {
        /// Available memory in bytes
        available_bytes: u64,
        /// Total memory in bytes
        total_bytes: u64,
        /// Top memory consumers
        top_consumers: Vec<ProcessInfo>,
    },

    /// A file was modified in a watched directory
    FileChanged {
        /// Path to the file
        path: PathBuf,
        /// Type of change
        change_type: FileChangeType,
        /// Process that made the change (if known)
        by_process: Option<ProcessInfo>,
    },

    /// Network connection state changed
    NetworkChanged {
        /// Interface name
        interface: String,
        /// Whether it's now connected
        connected: bool,
        /// IP addresses (if connected)
        addresses: Vec<String>,
    },

    // =========================================================================
    // From cortex to synapse (SLM requests)
    // =========================================================================
    /// Request suggestions from the SLM
    SuggestionRequest {
        /// Request ID for correlation
        request_id: MessageId,
        /// Context for the SLM
        context: Context,
        /// Optional user query
        user_query: Option<String>,
        /// Maximum number of suggestions to return
        max_suggestions: u8,
    },

    // =========================================================================
    // From synapse to cortex (SLM responses)
    // =========================================================================
    /// Response with suggestions from SLM
    SuggestionResponse {
        /// Request ID this responds to
        request_id: MessageId,
        /// Generated suggestions
        suggestions: Vec<Suggestion>,
        /// Processing time in milliseconds
        processing_time_ms: u32,
    },

    // =========================================================================
    // From cortex to actuator (action requests)
    // =========================================================================
    /// Request to execute an action
    ActionRequest {
        /// Request ID
        request_id: MessageId,
        /// The action to execute
        action: Action,
        /// Whether user confirmation is required
        requires_confirmation: bool,
        /// Timeout in seconds (0 = no timeout)
        timeout_secs: u32,
    },

    // =========================================================================
    // From actuator to cortex (action results)
    // =========================================================================
    /// Result of an action execution
    ActionResponse {
        /// Request ID this responds to
        request_id: MessageId,
        /// The action that was executed
        action: Action,
        /// Whether it succeeded
        success: bool,
        /// Output/error message
        output: Option<String>,
        /// Exit code (for commands)
        exit_code: Option<i32>,
    },

    // =========================================================================
    // From cortex to shell (UI notifications)
    // =========================================================================
    /// Show a notification to the user
    Notification {
        /// Notification ID
        id: MessageId,
        /// Title
        title: String,
        /// Body text
        body: String,
        /// Severity level
        severity: Severity,
        /// Available actions
        actions: Vec<Suggestion>,
        /// Auto-dismiss after seconds (0 = manual dismiss)
        timeout_secs: u32,
        /// The event behind it, as the rules and the screen name it
        /// (`service-crash`, `offer`...); None for a plain notice.
        #[serde(default)]
        kind: Option<String>,
        /// Its fields (`service`, `port`, `count`...), as `{field}`s are
        /// filled in from them.
        #[serde(default)]
        fields: std::collections::BTreeMap<String, String>,
    },

    // =========================================================================
    // From shell to cortex (user interactions)
    // =========================================================================
    /// User selected an action from a notification
    UserAction {
        /// Notification ID
        notification_id: MessageId,
        /// Selected suggestion ID
        suggestion_id: u32,
        /// Whether the user has already gone through a second, explicit
        /// confirmation step for this specific action (e.g. hive-dashboard
        /// requiring a second keypress for dangerous suggestions). Cortex
        /// combines this with `Action::is_dangerous()` when deciding
        /// `ActionRequest::requires_confirmation` — approving a suggestion
        /// once is not, by itself, confirmation for a dangerous action.
        confirmed: bool,
    },

    /// User dismissed a notification
    UserDismiss {
        /// Notification ID
        notification_id: MessageId,
    },

    /// A user ran a program that isn't installed, and a package of that name
    /// is available (grove checks). Sent by a shell; cortex passes it to
    /// synapse as the trigger for an "Install" suggestion.
    CommandNotFound {
        /// What the user typed
        command: String,
        /// The package that would provide it
        package: String,
    },

    /// A user asked the Hive something in plain language (grove's `? ...`).
    /// Answered with a `SuggestionResponse` carrying the same `request_id`,
    /// sent back to the asking connection only.
    UserQuery {
        /// Chosen by the asker, to match the answer
        request_id: MessageId,
        /// The question, as typed
        query: String,
        /// The asker's working directory
        cwd: Option<PathBuf>,
    },

    /// A user asked the Hive for a change of the machine's settings (the
    /// Ajustes app, `hive request`): its name, its keyboard, its screen's
    /// level. Cortex turns it into an offer, "<user> asks: ...", that an
    /// administrator approves as any other; the actuator then runs the
    /// action through its whitelist. Any local user may ask; nothing runs
    /// on the asking.
    UserRequest {
        /// What they ask for: one of the settings actions (SetHostname,
        /// SetKeyboard, SetScreenLevel); anything else is refused
        action: Action,
        /// Why, in their words (shown with the offer)
        reason: String,
    },

    /// User entered anonymous mode
    AnonymousModeEnter {
        /// Level of anonymity
        level: AnonymousLevel,
        /// Process ID that requested it (for Detach mode)
        pid: Option<u32>,
    },

    /// User exited anonymous mode
    AnonymousModeExit {
        /// Process ID (for Detach mode)
        pid: Option<u32>,
    },

    // =========================================================================
    // Control messages
    // =========================================================================
    /// Ping to check if component is alive
    Ping {
        /// Timestamp of ping
        timestamp: DateTime<Utc>,
    },

    /// Response to ping
    Pong {
        /// Original ping timestamp
        ping_timestamp: DateTime<Utc>,
        /// Component name
        component: String,
    },

    /// Request to reload configuration
    ReloadConfig,

    /// Shutdown request
    Shutdown {
        /// Reason for shutdown
        reason: String,
    },
}

/// Type of file change
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum FileChangeType {
    Created,
    Modified,
    Deleted,
    Renamed,
    Permissions,
}

/// Anonymous mode levels
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum AnonymousLevel {
    /// Hive observes but doesn't show notifications
    Quiet,
    /// This specific terminal/process is invisible to Hive
    Detach,
    /// New isolated namespace, no logging, no interception
    Full,
}

impl HiveMessage {
    /// Encode message to bytes using bincode
    pub fn encode(&self) -> Result<Vec<u8>, bincode::Error> {
        bincode::serialize(self)
    }

    /// Decode message from bytes
    pub fn decode(bytes: &[u8]) -> Result<Self, bincode::Error> {
        bincode::deserialize(bytes)
    }

    /// Get message type name for logging
    pub fn type_name(&self) -> &'static str {
        match self {
            HiveMessage::CommandObserved { .. } => "CommandObserved",
            HiveMessage::PortConflict { .. } => "PortConflict",
            HiveMessage::LogAnomaly { .. } => "LogAnomaly",
            HiveMessage::ServiceCrash { .. } => "ServiceCrash",
            HiveMessage::DiskSpaceLow { .. } => "DiskSpaceLow",
            HiveMessage::MemoryPressure { .. } => "MemoryPressure",
            HiveMessage::FileChanged { .. } => "FileChanged",
            HiveMessage::NetworkChanged { .. } => "NetworkChanged",
            HiveMessage::SuggestionRequest { .. } => "SuggestionRequest",
            HiveMessage::SuggestionResponse { .. } => "SuggestionResponse",
            HiveMessage::ActionRequest { .. } => "ActionRequest",
            HiveMessage::ActionResponse { .. } => "ActionResponse",
            HiveMessage::Notification { .. } => "Notification",
            HiveMessage::UserAction { .. } => "UserAction",
            HiveMessage::UserDismiss { .. } => "UserDismiss",
            HiveMessage::UserQuery { .. } => "UserQuery",
            HiveMessage::CommandNotFound { .. } => "CommandNotFound",
            HiveMessage::UserRequest { .. } => "UserRequest",
            HiveMessage::AnonymousModeEnter { .. } => "AnonymousModeEnter",
            HiveMessage::AnonymousModeExit { .. } => "AnonymousModeExit",
            HiveMessage::Ping { .. } => "Ping",
            HiveMessage::Pong { .. } => "Pong",
            HiveMessage::ReloadConfig => "ReloadConfig",
            HiveMessage::Shutdown { .. } => "Shutdown",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_roundtrip() {
        let msg = HiveMessage::Ping {
            timestamp: Utc::now(),
        };

        let encoded = msg.encode().unwrap();
        let decoded = HiveMessage::decode(&encoded).unwrap();

        assert_eq!(decoded.type_name(), "Ping");
    }

    #[test]
    fn test_severity_ordering() {
        assert!(Severity::Critical > Severity::Error);
        assert!(Severity::Error > Severity::Warning);
        assert!(Severity::Warning > Severity::Notice);
        assert!(Severity::Notice > Severity::Info);
    }
}
