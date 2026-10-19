//! Actionable suggestions derived from the event that triggered a request.
//!
//! The model (and the mock backend) only ever produce text. Anything a user
//! can approve for hive-actuator to execute comes from here instead: fixed
//! rules mapping a *typed* trigger (a crashed unit, a full disk, ...) to a
//! *typed* `Action`, with parameters taken from the event itself — never
//! parsed out of model output. hive-actuator's whitelist still has the final
//! word on whether any of them may run.

use hive_common::actions::{is_valid_package_name, Action};
use hive_common::messages::{Context, HiveMessage};

/// An approvable suggestion, before it gets its id.
#[derive(Debug, Clone, PartialEq)]
pub struct ActionSuggestion {
    pub title: String,
    pub description: String,
    pub action: Action,
}

/// The actionable suggestions for whatever triggered this request, most
/// directly useful first.
pub fn for_context(context: &Context) -> Vec<ActionSuggestion> {
    match context.trigger.as_deref() {
        Some(HiveMessage::ServiceCrash { service, .. }) => match service_name(service) {
            Some(name) => vec![restart_service(service, name), recent_logs(name)],
            None => vec![],
        },
        Some(HiveMessage::LogAnomaly { service, .. }) => {
            service_name(service).map(recent_logs).into_iter().collect()
        }
        Some(HiveMessage::DiskSpaceLow { mount, .. }) => vec![run_command(
            "Show disk usage",
            format!("See how full {} and the other mounts are.", mount.display()),
            "df",
            &["-h"],
        )],
        Some(HiveMessage::CommandNotFound { command, package }) => {
            if is_valid_package_name(package) {
                vec![ActionSuggestion {
                    title: format!("Install {package}"),
                    description: format!(
                        "`{command}` isn't installed; the {package} package provides it."
                    ),
                    action: Action::InstallPackage {
                        name: package.clone(),
                        assume_yes: true,
                    },
                }]
            } else {
                vec![]
            }
        }
        Some(HiveMessage::PortConflict { port, .. }) => vec![run_command(
            "Show listening ports",
            format!("See which process is holding port {port}."),
            "ss",
            &["-tlnp"],
        )],
        _ => vec![],
    }
}

fn restart_service(unit: &str, name: &str) -> ActionSuggestion {
    ActionSuggestion {
        title: format!("Restart {name}"),
        description: format!("{unit} stopped unexpectedly. Run `systemctl restart {name}`."),
        action: Action::RestartService {
            name: name.to_string(),
        },
    }
}

fn recent_logs(name: &str) -> ActionSuggestion {
    run_command(
        &format!("Show recent logs for {name}"),
        format!("The last 50 journal lines from {name}, to see why it failed."),
        "journalctl",
        &["-n", "50", "-u", name],
    )
}

fn run_command(title: &str, description: String, cmd: &str, args: &[&str]) -> ActionSuggestion {
    ActionSuggestion {
        title: title.to_string(),
        description,
        action: Action::RunCommand {
            cmd: cmd.to_string(),
            args: args.iter().map(|a| a.to_string()).collect(),
            cwd: None,
            env: vec![],
        },
    }
}

/// `nginx.service` -> `nginx`, the form hive-actuator's whitelist uses.
///
/// Only service units qualify (restarting `init.scope` or a `.socket` isn't
/// a meaningful suggestion), and only names made of the characters systemd
/// allows in unit names — nothing that could read as an option or a glob.
fn service_name(unit: &str) -> Option<&str> {
    let name = unit.strip_suffix(".service")?;
    let valid = !name.is_empty()
        && !name.starts_with('-')
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '@' | '.' | '_' | ':' | '-'));
    valid.then_some(name)
}

#[cfg(test)]
mod tests {
    use super::*;
    use hive_common::messages::Severity;
    use std::path::PathBuf;

    fn context(trigger: Option<HiveMessage>) -> Context {
        Context {
            recent_commands: vec![],
            cwd: None,
            active_services: vec![],
            recent_logs: vec![],
            resources: None,
            trigger: trigger.map(Box::new),
        }
    }

    fn crash(service: &str) -> Context {
        context(Some(HiveMessage::ServiceCrash {
            service: service.to_string(),
            exit_code: 1,
            restart_count: 0,
            logs: vec![],
        }))
    }

    fn actions(suggestions: Vec<ActionSuggestion>) -> Vec<Action> {
        suggestions.into_iter().map(|s| s.action).collect()
    }

    #[test]
    fn a_crashed_service_gets_a_restart_then_its_logs() {
        assert_eq!(
            actions(for_context(&crash("nginx.service"))),
            vec![
                Action::RestartService {
                    name: "nginx".into()
                },
                Action::RunCommand {
                    cmd: "journalctl".into(),
                    args: vec!["-n".into(), "50".into(), "-u".into(), "nginx".into()],
                    cwd: None,
                    env: vec![],
                },
            ]
        );
    }

    #[test]
    fn restart_is_titled_after_the_service() {
        let suggestions = for_context(&crash("postgresql@16-main.service"));

        assert_eq!(suggestions[0].title, "Restart postgresql@16-main");
    }

    #[test]
    fn non_service_units_get_no_actions() {
        // What nerve-journal used to attribute every systemd message to.
        assert!(for_context(&crash("init.scope")).is_empty());
        assert!(for_context(&crash("docker.socket")).is_empty());
        assert!(for_context(&crash("kernel")).is_empty());
    }

    #[test]
    fn unit_names_that_could_be_options_or_globs_are_refused() {
        for unit in [
            ".service",
            "-x.service",
            "a b.service",
            "*.service",
            "nginx;reboot.service",
        ] {
            assert!(for_context(&crash(unit)).is_empty(), "accepted {unit:?}");
        }
    }

    #[test]
    fn a_log_anomaly_gets_the_logs_only() {
        let anomaly = context(Some(HiveMessage::LogAnomaly {
            service: "redis-server.service".into(),
            severity: Severity::Error,
            lines: vec![],
            pattern: None,
        }));

        assert!(matches!(
            actions(for_context(&anomaly)).as_slice(),
            [Action::RunCommand { cmd, args, .. }] if cmd == "journalctl" && args[3] == "redis-server"
        ));
    }

    #[test]
    fn low_disk_space_gets_disk_usage() {
        let low = context(Some(HiveMessage::DiskSpaceLow {
            mount: PathBuf::from("/"),
            available_bytes: 1,
            threshold_bytes: 2,
            usage_percent: 99.0,
        }));

        assert!(matches!(
            actions(for_context(&low)).as_slice(),
            [Action::RunCommand { cmd, args, .. }] if cmd == "df" && args == &["-h".to_string()]
        ));
    }

    #[test]
    fn a_missing_program_gets_its_package_offered() {
        let missing = |package: &str| {
            context(Some(HiveMessage::CommandNotFound {
                command: "htop".into(),
                package: package.into(),
            }))
        };
        assert_eq!(
            actions(for_context(&missing("htop"))),
            vec![Action::InstallPackage {
                name: "htop".into(),
                assume_yes: true
            }]
        );
        assert!(for_context(&missing("--allow-downgrades")).is_empty());
    }

    #[test]
    fn requests_without_a_trigger_get_no_actions() {
        assert!(for_context(&context(None)).is_empty());
    }
}
