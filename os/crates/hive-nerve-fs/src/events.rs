//! Filesystem event types.

use std::path::PathBuf;

/// Significant filesystem events
#[derive(Debug, Clone)]
#[allow(dead_code)] // PermissionChanged: not yet emitted by watcher.rs
pub enum FsEvent {
    /// A configuration file was modified
    ConfigModified { path: PathBuf },

    /// File permissions were changed
    PermissionChanged {
        path: PathBuf,
        old_mode: u32,
        new_mode: u32,
    },

    /// A large file was created
    LargeFileCreated { path: PathBuf, size: u64 },

    /// A sensitive file was accessed
    SensitiveAccess { path: PathBuf, user: String },
}

impl FsEvent {
    /// Get a human-readable description of the event
    #[allow(dead_code)] // not yet consumed outside tests; for cortex notifications
    pub fn description(&self) -> String {
        match self {
            FsEvent::ConfigModified { path } => {
                format!("Configuration file modified: {}", path.display())
            }
            FsEvent::PermissionChanged {
                path,
                old_mode,
                new_mode,
            } => {
                format!(
                    "Permissions changed on {}: {:o} -> {:o}",
                    path.display(),
                    old_mode,
                    new_mode
                )
            }
            FsEvent::LargeFileCreated { path, size } => {
                format!(
                    "Large file created: {} ({:.2} MB)",
                    path.display(),
                    *size as f64 / 1024.0 / 1024.0
                )
            }
            FsEvent::SensitiveAccess { path, user } => {
                format!("Sensitive file accessed by {}: {}", user, path.display())
            }
        }
    }

    /// Get the severity level for this event
    #[allow(dead_code)] // not yet consumed outside tests; for cortex notifications
    pub fn severity(&self) -> &'static str {
        match self {
            FsEvent::ConfigModified { .. } => "notice",
            FsEvent::PermissionChanged { new_mode, .. } => {
                if new_mode & 0o002 != 0 {
                    "warning" // World-writable
                } else {
                    "notice"
                }
            }
            FsEvent::LargeFileCreated { .. } => "notice",
            FsEvent::SensitiveAccess { .. } => "warning",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_event_description() {
        let event = FsEvent::ConfigModified {
            path: PathBuf::from("/etc/nginx/nginx.conf"),
        };

        let desc = event.description();
        assert!(desc.contains("/etc/nginx/nginx.conf"));
        assert!(desc.contains("modified"));
    }

    #[test]
    fn test_permission_severity() {
        // World-writable should be warning
        let world_writable = FsEvent::PermissionChanged {
            path: PathBuf::from("/tmp/test"),
            old_mode: 0o644,
            new_mode: 0o666,
        };
        assert_eq!(world_writable.severity(), "warning");

        // Normal permission change is notice
        let normal = FsEvent::PermissionChanged {
            path: PathBuf::from("/tmp/test"),
            old_mode: 0o644,
            new_mode: 0o600,
        };
        assert_eq!(normal.severity(), "notice");
    }
}
