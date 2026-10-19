//! Prompt building utilities for the SLM.
//!
//! Constructs well-formatted prompts from system context to get
//! relevant suggestions from the language model.

use hive_common::messages::{Context, HiveMessage};

/// Builder for constructing prompts from system context
pub struct PromptBuilder {
    context: Option<Context>,
    user_query: Option<String>,
    system_prompt: String,
}

impl PromptBuilder {
    /// Create a new prompt builder
    pub fn new() -> Self {
        Self {
            context: None,
            user_query: None,
            system_prompt: DEFAULT_SYSTEM_PROMPT.to_string(),
        }
    }

    /// Add system context
    pub fn with_context(mut self, context: &Context) -> Self {
        self.context = Some(context.clone());
        self
    }

    /// Add a user query
    pub fn with_user_query(mut self, query: Option<&str>) -> Self {
        self.user_query = query.map(String::from);
        self
    }

    /// Set a custom system prompt
    #[allow(dead_code)]
    pub fn with_system_prompt(mut self, prompt: &str) -> Self {
        self.system_prompt = prompt.to_string();
        self
    }

    /// Build the whole prompt as one string (system part, then the rest).
    #[allow(dead_code)]
    pub fn build(self) -> String {
        let (system, user) = self.build_parts();
        format!("{system}\n\n{user}")
    }

    /// Build the prompt as a system part (who the assistant is) and a user
    /// part (the situation and the task), for chat-tuned models.
    pub fn build_parts(self) -> (String, String) {
        let mut prompt = String::new();

        // Context section
        if let Some(ctx) = &self.context {
            prompt.push_str("## Current System Context\n\n");

            // Recent commands
            if !ctx.recent_commands.is_empty() {
                prompt.push_str("### Recent Commands\n");
                for cmd in &ctx.recent_commands {
                    prompt.push_str(&format!("- `{}`\n", cmd));
                }
                prompt.push('\n');
            }

            // Recent logs (errors/warnings)
            if !ctx.recent_logs.is_empty() {
                prompt.push_str("### Recent Errors/Warnings\n");
                for log in &ctx.recent_logs {
                    let unit = log.unit.as_deref().unwrap_or("system");
                    prompt.push_str(&format!(
                        "- [{}] {}: {}\n",
                        log.timestamp.format("%H:%M:%S"),
                        unit,
                        log.message
                    ));
                }
                prompt.push('\n');
            }

            // Active services
            if !ctx.active_services.is_empty() {
                prompt.push_str("### Active Services\n");
                for svc in &ctx.active_services {
                    prompt.push_str(&format!("- {}\n", svc));
                }
                prompt.push('\n');
            }

            // Resource usage
            if let Some(resources) = &ctx.resources {
                prompt.push_str("### Resource Usage\n");
                prompt.push_str(&format!("- CPU: {:.1}%\n", resources.cpu_percent));
                let mem_used_mb = resources.memory_used / (1024 * 1024);
                let mem_total_mb = resources.memory_total / (1024 * 1024);
                prompt.push_str(&format!(
                    "- Memory: {} MB / {} MB ({:.1}%)\n",
                    mem_used_mb,
                    mem_total_mb,
                    (resources.memory_used as f64 / resources.memory_total as f64) * 100.0
                ));

                for disk in &resources.disk_usage {
                    let used_gb = disk.used / (1024 * 1024 * 1024);
                    let total_gb = disk.total / (1024 * 1024 * 1024);
                    prompt.push_str(&format!(
                        "- Disk {}: {} GB / {} GB\n",
                        disk.mount.display(),
                        used_gb,
                        total_gb
                    ));
                }
                prompt.push('\n');
            }

            // Current working directory
            if let Some(cwd) = &ctx.cwd {
                prompt.push_str(&format!("Current directory: {}\n\n", cwd.display()));
            }

            // Triggering event
            if let Some(trigger) = &ctx.trigger {
                prompt.push_str("### What Just Happened\n");
                prompt.push_str(&describe_trigger(trigger));
                prompt.push_str("\n\n");
            }
        }

        // User query
        if let Some(query) = &self.user_query {
            prompt.push_str("## User Question\n\n");
            prompt.push_str(query);
            prompt.push_str("\n\n");
        }

        // Request
        prompt.push_str("## Your Task\n\n");
        prompt.push_str("Based on the context above, give at most 3 short, specific suggestions. ");
        prompt.push_str("Put each on its own line starting with '- '. ");
        prompt.push_str("Include specific commands in backticks when relevant.\n");

        (self.system_prompt, prompt)
    }
}

/// The event behind a request, in words a model can act on: what ran,
/// which service, which port — not just the event's type.
pub fn describe_trigger(trigger: &HiveMessage) -> String {
    match trigger {
        HiveMessage::CommandObserved { process, cmd, .. } => {
            let cwd = process
                .cwd
                .as_ref()
                .map(|c| format!(" in {}", c.display()))
                .unwrap_or_default();
            format!("A user ran a potentially dangerous command{cwd}: `{cmd}`")
        }
        HiveMessage::ServiceCrash {
            service,
            exit_code,
            logs,
            ..
        } => {
            let mut text = format!("The service {service} crashed (exit code {exit_code}).");
            for line in logs.iter().take(5) {
                text.push_str(&format!("\n  log: {}", line.message));
            }
            text
        }
        HiveMessage::LogAnomaly { service, lines, .. } => {
            let mut text = format!("{service} is logging an unusual number of errors:");
            for line in lines.iter().take(5) {
                text.push_str(&format!("\n  log: {}", line.message));
            }
            text
        }
        HiveMessage::PortConflict {
            port,
            requested_by,
            held_by,
        } => format!(
            "{} could not start listening on port {port}: it is already held by {}.",
            requested_by.name, held_by.name
        ),
        HiveMessage::CommandNotFound { command, package } => format!(
            "A user tried to run `{command}`, which isn't installed; the {package} package provides it."
        ),
        HiveMessage::DiskSpaceLow {
            mount,
            usage_percent,
            available_bytes,
            ..
        } => format!(
            "The filesystem {} is {usage_percent:.0}% full ({} MB free).",
            mount.display(),
            available_bytes / (1024 * 1024)
        ),
        other => format!("Event: {}", other.type_name()),
    }
}

impl Default for PromptBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Kept short on purpose: on a VM's CPU every prompt token costs time
/// before the first word of the answer (a ~200-token prompt took most of a
/// 20-second answer on two vCPUs).
const DEFAULT_SYSTEM_PROMPT: &str =
    "You are the Hive, the assistant built into DruidOS, a Linux system. \
You watch system events and suggest what the user can safely do next: short, specific, \
with commands in backticks. You run offline; say so when unsure.";

#[cfg(test)]
mod tests {
    use super::*;
    use hive_common::messages::LogLine;
    use std::path::PathBuf;

    #[test]
    fn test_basic_prompt() {
        let prompt = PromptBuilder::new().build();
        assert!(prompt.contains("Hive"));
        assert!(prompt.contains("suggestions"));
    }

    #[test]
    fn system_and_user_parts_are_separate() {
        let (system, user) = PromptBuilder::new().build_parts();
        assert!(system.contains("You are the Hive"));
        assert!(!user.contains("You are the Hive"));
        assert!(user.contains("at most 3"));
    }

    #[test]
    fn triggers_are_described_with_their_details() {
        use hive_common::messages::ProcessInfo;
        let process = |name: &str| ProcessInfo {
            pid: 1,
            uid: 0,
            name: name.to_string(),
            cmdline: vec![],
            cwd: Some(PathBuf::from("/etc")),
            ppid: None,
        };

        let command = describe_trigger(&HiveMessage::CommandObserved {
            process: process("rm"),
            cmd: "rm -rf nginx".into(),
            timestamp: chrono::Utc::now(),
        });
        assert!(
            command.contains("`rm -rf nginx`") && command.contains("/etc"),
            "{command}"
        );

        let crash = describe_trigger(&HiveMessage::ServiceCrash {
            service: "nginx.service".into(),
            exit_code: 1,
            restart_count: 0,
            logs: vec![LogLine {
                timestamp: chrono::Utc::now(),
                message: "bind() to 0.0.0.0:80 failed".into(),
                priority: 3,
                unit: None,
            }],
        });
        assert!(
            crash.contains("nginx.service") && crash.contains("bind() to 0.0.0.0:80"),
            "{crash}"
        );

        let conflict = describe_trigger(&HiveMessage::PortConflict {
            port: 8080,
            requested_by: process("python3"),
            held_by: process("user nobody (uid 65534)"),
        });
        assert!(
            conflict.contains("python3")
                && conflict.contains("8080")
                && conflict.contains("nobody"),
            "{conflict}"
        );
    }

    #[test]
    fn test_prompt_with_context() {
        let context = Context {
            recent_commands: vec!["ls -la".to_string(), "cd /home".to_string()],
            cwd: Some(PathBuf::from("/home/user")),
            active_services: vec!["nginx.service".to_string()],
            recent_logs: vec![LogLine {
                timestamp: chrono::Utc::now(),
                message: "failed to bind to port 80".to_string(),
                priority: 3,
                unit: Some("nginx".to_string()),
            }],
            resources: None,
            trigger: None,
        };

        let prompt = PromptBuilder::new()
            .with_context(&context)
            .with_user_query(Some("Why is nginx failing?"))
            .build();

        assert!(prompt.contains("ls -la"));
        assert!(prompt.contains("nginx"));
        assert!(prompt.contains("port 80"));
        assert!(prompt.contains("Why is nginx failing?"));
    }
}
