//! Filesystem event processing.

use notify::event::{AccessKind, AccessMode, CreateKind, ModifyKind, RemoveKind, RenameMode};
use notify::{Event, EventKind};
use std::collections::HashSet;
use std::path::Path;
use tracing::debug;

use crate::events::FsEvent;

/// Processes raw notify events into meaningful FsEvents
pub struct FsEventProcessor {
    ignore_patterns: Vec<String>,
    /// Track recently seen paths to avoid duplicate events
    #[allow(dead_code)] // dedup logic not implemented yet
    recent_paths: HashSet<String>,
}

impl FsEventProcessor {
    /// Create a new event processor
    pub fn new(ignore_patterns: Vec<String>) -> Self {
        Self {
            ignore_patterns,
            recent_paths: HashSet::new(),
        }
    }

    /// Process a raw notify event
    pub fn process_event(&self, event: &Event) -> Option<FsEvent> {
        // A rename reported as one event carries [from, to]; what matters
        // is where the file ended up.
        let path = match event.kind {
            EventKind::Modify(ModifyKind::Name(RenameMode::Both)) => event.paths.get(1)?,
            _ => event.paths.first()?,
        };

        // Check if path should be ignored
        if self.should_ignore(path) {
            debug!("Ignoring event for: {}", path.display());
            return None;
        }

        match &event.kind {
            EventKind::Create(create_kind) => self.handle_create(path, create_kind),
            // A finished write: inotify's IN_CLOSE_WRITE, once per write
            // session. (Its IN_MODIFY, surfaced as Modify(Data(Any)), fires
            // on every single write() call and would flood the cortex.) Files
            // replaced atomically — written to a temp file and renamed over
            // the original, as editors and `sed -i` do — arrive as a rename.
            EventKind::Access(AccessKind::Close(AccessMode::Write))
            | EventKind::Modify(ModifyKind::Name(RenameMode::To | RenameMode::Both)) => {
                self.handle_written(path)
            }
            EventKind::Remove(remove_kind) => self.handle_remove(path, remove_kind),
            EventKind::Access(access_kind) => self.handle_access(path, access_kind),
            _ => None,
        }
    }

    fn should_ignore(&self, path: &Path) -> bool {
        let path_str = path.to_string_lossy();

        for pattern in &self.ignore_patterns {
            if let Some(suffix) = pattern.strip_prefix('*') {
                // Suffix match (e.g., "*.log")
                if path_str.ends_with(suffix) {
                    return true;
                }
            } else if pattern.ends_with('*') {
                // Prefix match (e.g., ".git/*")
                let prefix = &pattern[..pattern.len() - 1];
                if path_str.contains(prefix) {
                    return true;
                }
            } else {
                // Exact match
                if path_str.contains(pattern) {
                    return true;
                }
            }
        }

        false
    }

    fn handle_create(&self, path: &Path, _kind: &CreateKind) -> Option<FsEvent> {
        // Check file size for large file detection
        if let Ok(metadata) = path.metadata() {
            let size = metadata.len();
            // Report files larger than 100MB
            if size > 100 * 1024 * 1024 {
                return Some(FsEvent::LargeFileCreated {
                    path: path.to_path_buf(),
                    size,
                });
            }
        }

        None
    }

    fn handle_written(&self, path: &Path) -> Option<FsEvent> {
        // Already gone by the time we look: a temporary file that got
        // renamed over the real one (whose rename we'll see separately).
        if !path.is_file() {
            return None;
        }

        self.is_config_file(path).then(|| FsEvent::ConfigModified {
            path: path.to_path_buf(),
        })
    }

    fn handle_remove(&self, _path: &Path, _kind: &RemoveKind) -> Option<FsEvent> {
        // Could report deletion of important files
        None
    }

    fn handle_access(&self, path: &Path, kind: &AccessKind) -> Option<FsEvent> {
        if kind == &AccessKind::Read {
            // Check if it's a sensitive file
            if self.is_sensitive_file(path) {
                return Some(FsEvent::SensitiveAccess {
                    path: path.to_path_buf(),
                    user: whoami::username(),
                });
            }
        }

        None
    }

    fn is_config_file(&self, path: &Path) -> bool {
        let path_str = path.to_string_lossy();

        // Check if in /etc
        if path_str.starts_with("/etc/") {
            return true;
        }

        // Check for common config extensions
        if let Some(ext) = path.extension() {
            let ext_str = ext.to_string_lossy().to_lowercase();
            return matches!(
                ext_str.as_str(),
                "conf" | "cfg" | "ini" | "yaml" | "yml" | "toml" | "json"
            );
        }

        // Check for dotfiles in home
        if let Some(name) = path.file_name() {
            let name_str = name.to_string_lossy();
            if name_str.starts_with('.') && path_str.contains("/home/") {
                return true;
            }
        }

        false
    }

    fn is_sensitive_file(&self, path: &Path) -> bool {
        let path_str = path.to_string_lossy();

        // SSH keys and config
        if path_str.contains(".ssh/") {
            return true;
        }

        // GPG data
        if path_str.contains(".gnupg/") {
            return true;
        }

        // Password files
        if path_str.ends_with("/passwd") || path_str.ends_with("/shadow") {
            return true;
        }

        // Private keys
        if let Some(name) = path.file_name() {
            let name_str = name.to_string_lossy();
            if name_str.contains("private") || name_str.contains("secret") {
                return true;
            }
        }

        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ignore_patterns() {
        let processor = FsEventProcessor::new(vec![
            "*.log".to_string(),
            "*.tmp".to_string(),
            ".git/*".to_string(),
        ]);

        assert!(processor.should_ignore(Path::new("/var/log/test.log")));
        assert!(processor.should_ignore(Path::new("/tmp/file.tmp")));
        assert!(processor.should_ignore(Path::new("/home/user/project/.git/config")));
        assert!(!processor.should_ignore(Path::new("/etc/nginx/nginx.conf")));
    }

    #[test]
    fn test_is_config_file() {
        let processor = FsEventProcessor::new(vec![]);

        assert!(processor.is_config_file(Path::new("/etc/nginx/nginx.conf")));
        assert!(processor.is_config_file(Path::new("/etc/fstab")));
        assert!(processor.is_config_file(Path::new("/home/user/.bashrc")));
        assert!(processor.is_config_file(Path::new("/app/config.yaml")));
        assert!(!processor.is_config_file(Path::new("/usr/bin/ls")));
    }

    fn config_modified_path(event: Option<FsEvent>) -> Option<std::path::PathBuf> {
        match event {
            Some(FsEvent::ConfigModified { path }) => Some(path),
            _ => None,
        }
    }

    #[test]
    fn finished_write_to_a_config_file_is_reported() {
        // inotify reports a completed write as IN_CLOSE_WRITE. The old code
        // waited for Modify(Data(Content)), which the inotify backend never
        // emits, so no config change was ever reported.
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("app.toml");
        std::fs::write(&file, "x = 1").unwrap();
        let processor = FsEventProcessor::new(vec![]);

        let event = Event::new(EventKind::Access(AccessKind::Close(AccessMode::Write)))
            .add_path(file.clone());

        assert_eq!(
            config_modified_path(processor.process_event(&event)),
            Some(file)
        );
    }

    #[test]
    fn individual_write_calls_are_not_reported() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("app.toml");
        std::fs::write(&file, "x = 1").unwrap();
        let processor = FsEventProcessor::new(vec![]);

        let event = Event::new(EventKind::Modify(ModifyKind::Data(
            notify::event::DataChange::Any,
        )))
        .add_path(file);

        assert!(processor.process_event(&event).is_none());
    }

    #[test]
    fn atomic_replace_reports_the_destination_not_the_temp_file() {
        let dir = tempfile::tempdir().unwrap();
        let temp = dir.path().join("sedAbC123"); // already renamed away
        let file = dir.path().join("app.conf");
        std::fs::write(&file, "x = 1").unwrap();
        let processor = FsEventProcessor::new(vec![]);

        let rename = Event::new(EventKind::Modify(ModifyKind::Name(RenameMode::Both)))
            .add_path(temp.clone())
            .add_path(file.clone());
        let temp_closed =
            Event::new(EventKind::Access(AccessKind::Close(AccessMode::Write))).add_path(temp);

        assert_eq!(
            config_modified_path(processor.process_event(&rename)),
            Some(file)
        );
        assert!(processor.process_event(&temp_closed).is_none());
    }

    #[test]
    fn writes_to_non_config_files_are_not_reported() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("notes");
        std::fs::write(&file, "x").unwrap();
        let processor = FsEventProcessor::new(vec![]);

        let event =
            Event::new(EventKind::Access(AccessKind::Close(AccessMode::Write))).add_path(file);

        assert!(processor.process_event(&event).is_none());
    }

    #[test]
    fn test_is_sensitive_file() {
        let processor = FsEventProcessor::new(vec![]);

        assert!(processor.is_sensitive_file(Path::new("/home/user/.ssh/id_rsa")));
        assert!(processor.is_sensitive_file(Path::new("/etc/shadow")));
        assert!(processor.is_sensitive_file(Path::new("/home/user/.gnupg/secring.gpg")));
        assert!(!processor.is_sensitive_file(Path::new("/etc/hosts")));
    }
}
