//! Actionable suggestions derived from the event that triggered a request.
//!
//! The model (and the mock backend) only ever produce text. Anything a user
//! can approve for hive-actuator to execute comes from the Hive's rules
//! instead (the `rules` module): typed offers on a *typed* trigger (a crashed
//! unit, a full disk, ...), written in Quantum (config/hive/hive.q) and
//! compiled to rules.toml, with their parameters taken from the event
//! itself — never parsed out of model output. hive-actuator's whitelist
//! still has the final word on whether any of them may run.

use hive_common::messages::Context;

pub use crate::rules::ActionSuggestion;

/// The actionable suggestions for whatever triggered this request, in the
/// order the rules give them, from the rules the daemon loaded.
pub fn for_context(context: &Context) -> Vec<ActionSuggestion> {
    match context.trigger.as_deref() {
        Some(trigger) => crate::rules::current().offers(trigger),
        None => vec![],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hive_common::actions::Action;
    use hive_common::messages::{HiveMessage, Severity};
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
