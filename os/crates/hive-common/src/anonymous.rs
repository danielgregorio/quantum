//! Anonymous mode implementation.
//!
//! Provides three levels of privacy:
//!
//! - **Quiet**: Hive observes but doesn't show notifications
//! - **Detach**: The specific terminal/process is invisible to Hive
//! - **Full**: New isolated namespace with no logging
//!
//! # Usage
//!
//! ```no_run
//! use hive_common::anonymous::{AnonymousSession, AnonymousManager};
//! use hive_common::AnonymousLevel;
//!
//! // Create a quiet session (still observed, no notifications)
//! let session = AnonymousSession::new(AnonymousLevel::Quiet);
//!
//! // Use manager to check processes
//! let mut manager = AnonymousManager::new();
//! let session = AnonymousSession::for_process(AnonymousLevel::Detach, 1234);
//! manager.add_session(session);
//!
//! // Check if a process should be hidden
//! if manager.should_hide_process(1234) {
//!     // Skip observation
//! }
//! ```

use crate::messages::AnonymousLevel;
use std::collections::HashSet;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

/// Counter for session IDs
static SESSION_COUNTER: AtomicU64 = AtomicU64::new(1);

/// Generate a unique session ID
fn next_session_id() -> u64 {
    SESSION_COUNTER.fetch_add(1, Ordering::Relaxed)
}

/// An anonymous session
#[derive(Debug, Clone)]
pub struct AnonymousSession {
    /// Unique session identifier
    pub id: u64,
    /// Privacy level
    pub level: AnonymousLevel,
    /// Process ID that initiated the session (if applicable)
    pub initiator_pid: Option<u32>,
    /// All PIDs covered by this session (for Detach mode)
    pub covered_pids: HashSet<u32>,
    /// When the session was created
    pub created_at: Instant,
    /// Optional timeout (None = no timeout)
    pub timeout: Option<Duration>,
}

impl AnonymousSession {
    /// Create a new anonymous session
    pub fn new(level: AnonymousLevel) -> Self {
        Self {
            id: next_session_id(),
            level,
            initiator_pid: None,
            covered_pids: HashSet::new(),
            created_at: Instant::now(),
            timeout: None,
        }
    }

    /// Create a session for a specific process
    pub fn for_process(level: AnonymousLevel, pid: u32) -> Self {
        let mut session = Self::new(level);
        session.initiator_pid = Some(pid);
        session.covered_pids.insert(pid);
        session
    }

    /// Create a session with a timeout
    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    /// Add a PID to the session (for child processes)
    pub fn add_pid(&mut self, pid: u32) {
        self.covered_pids.insert(pid);
    }

    /// Remove a PID from the session
    pub fn remove_pid(&mut self, pid: u32) {
        self.covered_pids.remove(&pid);
    }

    /// Check if the session has expired
    pub fn is_expired(&self) -> bool {
        if let Some(timeout) = self.timeout {
            self.created_at.elapsed() > timeout
        } else {
            false
        }
    }

    /// Check if a specific PID is covered by this session
    pub fn covers_pid(&self, pid: u32) -> bool {
        match self.level {
            AnonymousLevel::Quiet => false, // Quiet doesn't hide processes
            AnonymousLevel::Detach => self.covered_pids.contains(&pid),
            AnonymousLevel::Full => self.covered_pids.contains(&pid),
        }
    }

    /// Check if notifications should be suppressed
    pub fn suppress_notifications(&self) -> bool {
        match self.level {
            AnonymousLevel::Quiet => true,
            AnonymousLevel::Detach => true,
            AnonymousLevel::Full => true,
        }
    }
}

/// Manages anonymous sessions
#[derive(Debug, Default)]
pub struct AnonymousManager {
    /// Active sessions
    sessions: Vec<AnonymousSession>,
    /// Global quiet mode (suppresses notifications for everything)
    global_quiet: bool,
}

impl AnonymousManager {
    /// Create a new manager
    pub fn new() -> Self {
        Self {
            sessions: Vec::new(),
            global_quiet: false,
        }
    }

    /// Set global quiet mode
    pub fn set_global_quiet(&mut self, quiet: bool) {
        self.global_quiet = quiet;
    }

    /// Check if global quiet mode is enabled
    pub fn is_global_quiet(&self) -> bool {
        self.global_quiet
    }

    /// Add a new session
    pub fn add_session(&mut self, session: AnonymousSession) -> u64 {
        let id = session.id;
        self.sessions.push(session);
        id
    }

    /// Remove a session by ID
    pub fn remove_session(&mut self, session_id: u64) -> Option<AnonymousSession> {
        if let Some(pos) = self.sessions.iter().position(|s| s.id == session_id) {
            Some(self.sessions.remove(pos))
        } else {
            None
        }
    }

    /// Remove a session by PID
    pub fn remove_session_for_pid(&mut self, pid: u32) -> Option<AnonymousSession> {
        if let Some(pos) = self
            .sessions
            .iter()
            .position(|s| s.initiator_pid == Some(pid))
        {
            Some(self.sessions.remove(pos))
        } else {
            None
        }
    }

    /// Get session by ID
    pub fn get_session(&self, session_id: u64) -> Option<&AnonymousSession> {
        self.sessions.iter().find(|s| s.id == session_id)
    }

    /// Get session for a PID
    pub fn get_session_for_pid(&self, pid: u32) -> Option<&AnonymousSession> {
        self.sessions.iter().find(|s| s.covers_pid(pid))
    }

    /// Check if a process should be hidden from observation
    pub fn should_hide_process(&self, pid: u32) -> bool {
        self.sessions
            .iter()
            .any(|s| s.covers_pid(pid) && !s.is_expired())
    }

    /// Check if notifications should be suppressed for a process
    pub fn should_suppress_notifications(&self, pid: Option<u32>) -> bool {
        if self.global_quiet {
            return true;
        }

        if let Some(pid) = pid {
            self.sessions
                .iter()
                .any(|s| s.covers_pid(pid) && s.suppress_notifications() && !s.is_expired())
        } else {
            false
        }
    }

    /// Clean up expired sessions
    pub fn cleanup_expired(&mut self) {
        self.sessions.retain(|s| !s.is_expired());
    }

    /// Get the number of active sessions
    pub fn session_count(&self) -> usize {
        self.sessions.len()
    }

    /// Add a PID to an existing session
    pub fn add_pid_to_session(&mut self, session_id: u64, pid: u32) -> bool {
        if let Some(session) = self.sessions.iter_mut().find(|s| s.id == session_id) {
            session.add_pid(pid);
            true
        } else {
            false
        }
    }
}

/// Helper to check if current process should enter anonymous mode
pub fn should_enter_anonymous() -> bool {
    // Check environment variable
    if std::env::var("HIVE_ANONYMOUS").is_ok() {
        return true;
    }

    // Check for presence of .hive-anonymous file in current directory
    if std::path::Path::new(".hive-anonymous").exists() {
        return true;
    }

    false
}

/// Parse anonymous level from string
pub fn parse_anonymous_level(s: &str) -> Option<AnonymousLevel> {
    match s.to_lowercase().as_str() {
        "quiet" | "q" => Some(AnonymousLevel::Quiet),
        "detach" | "d" => Some(AnonymousLevel::Detach),
        "full" | "f" => Some(AnonymousLevel::Full),
        _ => None,
    }
}

/// Get anonymous level from environment
pub fn anonymous_level_from_env() -> Option<AnonymousLevel> {
    std::env::var("HIVE_ANONYMOUS")
        .ok()
        .and_then(|s| parse_anonymous_level(&s))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_creation() {
        let session = AnonymousSession::new(AnonymousLevel::Quiet);
        assert!(session.id > 0);
        assert!(!session.is_expired());
    }

    #[test]
    fn test_session_for_process() {
        let session = AnonymousSession::for_process(AnonymousLevel::Detach, 1234);
        assert_eq!(session.initiator_pid, Some(1234));
        assert!(session.covers_pid(1234));
        assert!(!session.covers_pid(5678));
    }

    #[test]
    fn test_session_with_timeout() {
        let session =
            AnonymousSession::new(AnonymousLevel::Quiet).with_timeout(Duration::from_millis(10));

        assert!(!session.is_expired());
        std::thread::sleep(Duration::from_millis(15));
        assert!(session.is_expired());
    }

    #[test]
    fn test_manager_add_remove() {
        let mut manager = AnonymousManager::new();

        let session = AnonymousSession::for_process(AnonymousLevel::Detach, 1234);
        let id = manager.add_session(session);

        assert_eq!(manager.session_count(), 1);
        assert!(manager.should_hide_process(1234));
        assert!(!manager.should_hide_process(5678));

        manager.remove_session(id);
        assert_eq!(manager.session_count(), 0);
        assert!(!manager.should_hide_process(1234));
    }

    #[test]
    fn test_global_quiet() {
        let mut manager = AnonymousManager::new();

        assert!(!manager.should_suppress_notifications(None));

        manager.set_global_quiet(true);
        assert!(manager.should_suppress_notifications(None));
        assert!(manager.should_suppress_notifications(Some(1234)));
    }

    #[test]
    fn test_parse_level() {
        assert!(matches!(
            parse_anonymous_level("quiet"),
            Some(AnonymousLevel::Quiet)
        ));
        assert!(matches!(
            parse_anonymous_level("DETACH"),
            Some(AnonymousLevel::Detach)
        ));
        assert!(matches!(
            parse_anonymous_level("f"),
            Some(AnonymousLevel::Full)
        ));
        assert!(parse_anonymous_level("invalid").is_none());
    }

    #[test]
    fn test_quiet_mode_behavior() {
        let session = AnonymousSession::new(AnonymousLevel::Quiet);
        // Quiet mode doesn't hide processes, just suppresses notifications
        assert!(!session.covers_pid(1234));
        assert!(session.suppress_notifications());
    }

    #[test]
    fn test_cleanup_expired() {
        let mut manager = AnonymousManager::new();

        let expired = AnonymousSession::for_process(AnonymousLevel::Detach, 1234)
            .with_timeout(Duration::from_millis(1));
        let valid = AnonymousSession::for_process(AnonymousLevel::Detach, 5678);

        manager.add_session(expired);
        manager.add_session(valid);

        std::thread::sleep(Duration::from_millis(5));

        assert_eq!(manager.session_count(), 2);
        manager.cleanup_expired();
        assert_eq!(manager.session_count(), 1);
    }
}
