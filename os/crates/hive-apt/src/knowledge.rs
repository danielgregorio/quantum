//! Package knowledge structures.

use serde::{Deserialize, Serialize};

/// Package knowledge from YAML files
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PackageKnowledge {
    pub package: String,

    #[serde(default)]
    pub aliases: Vec<String>,

    pub description: Option<String>,

    #[serde(default)]
    pub category: Option<String>,

    #[serde(default)]
    pub install_notes: Vec<String>,

    #[serde(default)]
    pub post_install: Vec<PostInstallCommand>,

    #[serde(default)]
    pub warnings: Vec<Warning>,

    #[serde(default)]
    pub common_issues: Vec<CommonIssue>,

    #[serde(default)]
    pub tuning_tips: Vec<TuningTip>,

    #[serde(default)]
    pub zfs_setup: Option<String>,

    #[serde(default)]
    pub alternatives: Vec<Alternative>,

    #[serde(default)]
    pub related_packages: Vec<String>,

    #[serde(default)]
    pub related_commands: Vec<String>,

    #[serde(default)]
    pub dependencies: Vec<String>,

    #[serde(default)]
    pub ports: Vec<Port>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PostInstallCommand {
    pub command: Option<String>,
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Warning {
    #[serde(rename = "type")]
    pub warning_type: Option<String>,
    pub message: String,
    pub severity: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommonIssue {
    pub pattern: String,
    pub solution: String,
    #[serde(default)]
    pub auto_suggest: bool,
    pub severity: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TuningTip {
    pub name: String,
    pub description: String,
    pub default: Option<String>,
    pub recommended: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alternative {
    pub name: String,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Port {
    pub port: u16,
    pub protocol: Option<String>,
    pub description: Option<String>,
}
