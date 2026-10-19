//! Terminal configuration.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Terminal configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TermConfig {
    /// Font configuration
    pub font: FontConfig,
    /// Color scheme
    pub colors: ColorScheme,
    /// Window configuration
    pub window: WindowConfig,
    /// Hive integration settings
    pub hive: HiveConfig,
    /// Shell to use
    pub shell: ShellConfig,
}

impl Default for TermConfig {
    fn default() -> Self {
        Self {
            font: FontConfig::default(),
            colors: ColorScheme::default(),
            window: WindowConfig::default(),
            hive: HiveConfig::default(),
            shell: ShellConfig::default(),
        }
    }
}

/// Font configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FontConfig {
    /// Font family
    pub family: String,
    /// Font size in points
    pub size: f32,
    /// Line height multiplier
    pub line_height: f32,
    /// Enable ligatures
    pub ligatures: bool,
}

impl Default for FontConfig {
    fn default() -> Self {
        Self {
            family: "JetBrains Mono".to_string(),
            size: 13.0,
            line_height: 1.2,
            ligatures: true,
        }
    }
}

/// Color scheme matching DruidOS design system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColorScheme {
    /// Background color
    pub background: String,
    /// Foreground color
    pub foreground: String,
    /// Cursor color
    pub cursor: String,
    /// Selection color
    pub selection: String,
    /// ANSI colors (0-15)
    pub ansi: AnsiColors,
}

impl Default for ColorScheme {
    fn default() -> Self {
        Self {
            background: "#0D0D0D".to_string(),
            foreground: "#FFFFFF".to_string(),
            cursor: "#7B5CFF".to_string(),
            selection: "#333333".to_string(),
            ansi: AnsiColors::default(),
        }
    }
}

/// ANSI color palette
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnsiColors {
    /// Black
    pub black: String,
    /// Red
    pub red: String,
    /// Green
    pub green: String,
    /// Yellow
    pub yellow: String,
    /// Blue
    pub blue: String,
    /// Magenta
    pub magenta: String,
    /// Cyan
    pub cyan: String,
    /// White
    pub white: String,
    /// Bright black
    pub bright_black: String,
    /// Bright red
    pub bright_red: String,
    /// Bright green
    pub bright_green: String,
    /// Bright yellow
    pub bright_yellow: String,
    /// Bright blue
    pub bright_blue: String,
    /// Bright magenta
    pub bright_magenta: String,
    /// Bright cyan
    pub bright_cyan: String,
    /// Bright white
    pub bright_white: String,
}

impl Default for AnsiColors {
    fn default() -> Self {
        Self {
            black: "#0D0D0D".to_string(),
            red: "#F87171".to_string(),
            green: "#4ADE80".to_string(),
            yellow: "#FBBF24".to_string(),
            blue: "#60A5FA".to_string(),
            magenta: "#9D85FF".to_string(),
            cyan: "#22D3EE".to_string(),
            white: "#E5E5E5".to_string(),
            bright_black: "#666666".to_string(),
            bright_red: "#FCA5A5".to_string(),
            bright_green: "#86EFAC".to_string(),
            bright_yellow: "#FDE047".to_string(),
            bright_blue: "#93C5FD".to_string(),
            bright_magenta: "#C4B5FD".to_string(),
            bright_cyan: "#67E8F9".to_string(),
            bright_white: "#FFFFFF".to_string(),
        }
    }
}

/// Window configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowConfig {
    /// Window title
    pub title: String,
    /// Initial width in columns
    pub columns: u16,
    /// Initial height in rows
    pub rows: u16,
    /// Window opacity (0.0-1.0)
    pub opacity: f32,
    /// Padding in pixels
    pub padding: u32,
    /// Enable window decorations
    pub decorations: bool,
}

impl Default for WindowConfig {
    fn default() -> Self {
        Self {
            title: "hive-term".to_string(),
            columns: 120,
            rows: 36,
            opacity: 0.95,
            padding: 8,
            decorations: true,
        }
    }
}

/// Hive integration configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HiveConfig {
    /// Enable Hive integration
    pub enabled: bool,
    /// Show Hive suggestions inline
    pub inline_suggestions: bool,
    /// Report commands to Hive
    pub report_commands: bool,
    /// Anonymous mode level (none, quiet, detach, full)
    pub anonymous_mode: Option<String>,
}

impl Default for HiveConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            inline_suggestions: true,
            report_commands: true,
            anonymous_mode: None,
        }
    }
}

/// Shell configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShellConfig {
    /// Shell program path (None = use $SHELL or /bin/sh)
    pub program: Option<String>,
    /// Shell arguments
    pub args: Vec<String>,
    /// Working directory
    pub working_directory: Option<PathBuf>,
    /// Environment variables to set
    pub env: Vec<(String, String)>,
}

impl Default for ShellConfig {
    fn default() -> Self {
        Self {
            program: None,
            args: vec![],
            working_directory: None,
            env: vec![],
        }
    }
}

impl TermConfig {
    /// Load configuration from file
    pub fn load(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let config: Self = toml::from_str(&content)?;
        Ok(config)
    }

    /// Load configuration from default locations
    pub fn load_default() -> Self {
        // Try user config first
        if let Some(config_dir) = dirs::config_dir() {
            let user_config = config_dir.join("hive-term/config.toml");
            if user_config.exists() {
                if let Ok(config) = Self::load(user_config.to_str().unwrap()) {
                    return config;
                }
            }
        }

        // Try system config
        let system_config = "/etc/hive/term.toml";
        if std::path::Path::new(system_config).exists() {
            if let Ok(config) = Self::load(system_config) {
                return config;
            }
        }

        // Fall back to defaults
        Self::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = TermConfig::default();
        assert_eq!(config.font.family, "JetBrains Mono");
        assert_eq!(config.window.columns, 120);
        assert!(config.hive.enabled);
    }

    #[test]
    fn test_color_scheme() {
        let colors = ColorScheme::default();
        assert_eq!(colors.background, "#0D0D0D");
        assert_eq!(colors.cursor, "#7B5CFF");
    }
}
