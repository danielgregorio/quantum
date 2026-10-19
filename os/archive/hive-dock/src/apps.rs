//! Application detection and management.

use anyhow::{Context, Result};
use freedesktop_entry_parser::parse_entry;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use tracing::{debug, warn};

/// Information about a desktop application
#[derive(Debug, Clone)]
pub struct AppInfo {
    /// Application ID (desktop file basename without .desktop)
    pub id: String,
    /// Display name
    pub name: String,
    /// Exec command
    pub exec: String,
    /// Icon name or path
    pub icon: Option<String>,
    /// Application categories
    pub categories: Vec<String>,
    /// Whether the app should be shown in menus
    pub no_display: bool,
    /// Path to the desktop file
    pub desktop_file: PathBuf,
}

/// Directories to search for .desktop files
const DESKTOP_DIRS: &[&str] = &[
    "/usr/share/applications",
    "/usr/local/share/applications",
    "/var/lib/flatpak/exports/share/applications",
];

/// Manages application discovery
pub struct AppManager {
    /// Cached applications by ID
    apps: HashMap<String, AppInfo>,
    /// Pinned apps (in order)
    pinned: Vec<String>,
}

impl AppManager {
    /// Create a new app manager
    pub fn new() -> Self {
        Self {
            apps: HashMap::new(),
            pinned: Vec::new(),
        }
    }

    /// Scan for installed applications
    pub fn scan_applications(&mut self) -> Result<()> {
        self.apps.clear();

        // Also check user-specific location
        let home = std::env::var("HOME").unwrap_or_else(|_| String::from("/root"));
        let user_apps = format!("{}/.local/share/applications", home);

        let mut dirs: Vec<&str> = DESKTOP_DIRS.to_vec();
        dirs.push(&user_apps);

        for dir in dirs {
            let dir_path = Path::new(dir);
            if !dir_path.exists() {
                continue;
            }

            debug!("Scanning applications in: {}", dir);

            if let Ok(entries) = fs::read_dir(dir_path) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map_or(false, |e| e == "desktop") {
                        if let Err(e) = self.parse_desktop_file(&path) {
                            debug!("Failed to parse {}: {}", path.display(), e);
                        }
                    }
                }
            }
        }

        debug!("Found {} applications", self.apps.len());
        Ok(())
    }

    /// Parse a .desktop file
    fn parse_desktop_file(&mut self, path: &Path) -> Result<()> {
        let content = fs::read_to_string(path)
            .with_context(|| format!("Failed to read {}", path.display()))?;

        let entry = parse_entry(&content)
            .map_err(|e| anyhow::anyhow!("Failed to parse desktop file: {:?}", e))?;

        // Get the Desktop Entry section
        let desktop_entry = entry.section("Desktop Entry");

        // Skip if hidden or no display
        if desktop_entry.attr("Hidden").map_or(false, |v| v == "true") {
            return Ok(());
        }

        // Get required fields
        let name = desktop_entry
            .attr("Name")
            .ok_or_else(|| anyhow::anyhow!("Missing Name field"))?;

        let exec = desktop_entry
            .attr("Exec")
            .ok_or_else(|| anyhow::anyhow!("Missing Exec field"))?;

        // Get ID from filename
        let id = path
            .file_stem()
            .and_then(|s| s.to_str())
            .ok_or_else(|| anyhow::anyhow!("Invalid filename"))?;

        // Parse categories
        let categories: Vec<String> = desktop_entry
            .attr("Categories")
            .map(|c| c.split(';').filter(|s| !s.is_empty()).map(String::from).collect())
            .unwrap_or_default();

        let app_info = AppInfo {
            id: id.to_string(),
            name: name.to_string(),
            exec: exec.to_string(),
            icon: desktop_entry.attr("Icon").map(String::from),
            categories,
            no_display: desktop_entry.attr("NoDisplay").map_or(false, |v| v == "true"),
            desktop_file: path.to_path_buf(),
        };

        self.apps.insert(id.to_string(), app_info);
        Ok(())
    }

    /// Get all visible applications
    pub fn get_visible_apps(&self) -> Vec<&AppInfo> {
        self.apps
            .values()
            .filter(|app| !app.no_display)
            .collect()
    }

    /// Get an application by ID
    pub fn get_app(&self, id: &str) -> Option<&AppInfo> {
        self.apps.get(id)
    }

    /// Set pinned applications
    pub fn set_pinned(&mut self, pinned: Vec<String>) {
        self.pinned = pinned;
    }

    /// Get pinned applications
    pub fn get_pinned(&self) -> Vec<&AppInfo> {
        self.pinned
            .iter()
            .filter_map(|id| self.apps.get(id))
            .collect()
    }

    /// Add app to pinned
    pub fn pin_app(&mut self, id: &str) {
        if !self.pinned.contains(&id.to_string()) {
            self.pinned.push(id.to_string());
        }
    }

    /// Remove app from pinned
    pub fn unpin_app(&mut self, id: &str) {
        self.pinned.retain(|p| p != id);
    }

    /// Launch an application
    pub fn launch_app(&self, id: &str) -> Result<()> {
        let app = self.get_app(id)
            .ok_or_else(|| anyhow::anyhow!("Application not found: {}", id))?;

        // Parse exec command (remove field codes like %f, %u, etc.)
        let exec = app.exec
            .split_whitespace()
            .filter(|part| !part.starts_with('%'))
            .collect::<Vec<_>>()
            .join(" ");

        debug!("Launching {}: {}", id, exec);

        // Use sh -c to handle complex exec commands
        std::process::Command::new("sh")
            .arg("-c")
            .arg(&exec)
            .spawn()
            .with_context(|| format!("Failed to launch {}", id))?;

        Ok(())
    }
}

impl Default for AppManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_manager_creation() {
        let manager = AppManager::new();
        assert!(manager.apps.is_empty());
        assert!(manager.pinned.is_empty());
    }

    #[test]
    fn test_pinning() {
        let mut manager = AppManager::new();

        manager.pin_app("firefox");
        assert!(manager.pinned.contains(&"firefox".to_string()));

        manager.pin_app("firefox"); // Duplicate
        assert_eq!(manager.pinned.len(), 1);

        manager.unpin_app("firefox");
        assert!(manager.pinned.is_empty());
    }
}
