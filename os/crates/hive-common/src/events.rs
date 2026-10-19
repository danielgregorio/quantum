//! The Hive's events as the rules and the screen name them: what an
//! observation is called (`service-crash`, `disk-low`...) and the fields it
//! offers (`service`, `port`, `mount`...), filled in from the message
//! itself.
//!
//! This is the one table behind `qh:` (the rules hive-synapse fills in) and
//! `qs:` (the screen hive-screen plays): quantum/runtime/hive/schema.py
//! lists the same names and fields, and a test keeps the two together.

use crate::actions::is_valid_package_name;
use crate::messages::HiveMessage;
use std::collections::BTreeMap;

/// The observations a rule can be on, and the fields each one offers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Event {
    ServiceCrash,
    LogAnomaly,
    PortConflict,
    DiskLow,
    MemoryPressure,
    CommandObserved,
    CommandNotFound,
}

impl Event {
    pub const ALL: [Event; 7] = [
        Event::ServiceCrash,
        Event::LogAnomaly,
        Event::PortConflict,
        Event::DiskLow,
        Event::MemoryPressure,
        Event::CommandObserved,
        Event::CommandNotFound,
    ];

    pub fn parse(name: &str) -> Option<Event> {
        Event::ALL.into_iter().find(|e| e.name() == name)
    }

    /// The event's name, as a `.q` writes it.
    pub fn name(self) -> &'static str {
        match self {
            Event::ServiceCrash => "service-crash",
            Event::LogAnomaly => "log-anomaly",
            Event::PortConflict => "port-conflict",
            Event::DiskLow => "disk-low",
            Event::MemoryPressure => "memory-pressure",
            Event::CommandObserved => "command-observed",
            Event::CommandNotFound => "command-not-found",
        }
    }

    /// The fields an offer on this event may hold. `service` and `package`
    /// are only given for a valid name, so an offer that needs one is left
    /// out otherwise (see `fields_of`).
    pub fn fields(self) -> &'static [&'static str] {
        match self {
            Event::ServiceCrash => &["unit", "service", "exit_code"],
            Event::LogAnomaly => &["unit", "service"],
            Event::PortConflict => &["port", "requester", "holder"],
            Event::DiskLow => &["mount", "percent", "free_mb"],
            Event::MemoryPressure => &["free_mb", "total_mb"],
            Event::CommandObserved => &["cmd", "program"],
            Event::CommandNotFound => &["command", "package"],
        }
    }
}

/// An event's fields, by name.
pub type Fields = BTreeMap<String, String>;

/// The event a message is, and its fields' values; None for a message that
/// is not an observation.
pub fn fields_of(trigger: &HiveMessage) -> Option<(Event, Fields)> {
    let mut f = Fields::new();
    let mut put = |k: &str, v: String| {
        f.insert(k.to_string(), v);
    };
    let event = match trigger {
        HiveMessage::ServiceCrash {
            service, exit_code, ..
        } => {
            put("unit", service.clone());
            if let Some(name) = service_name(service) {
                put("service", name.to_string());
            }
            put("exit_code", exit_code.to_string());
            Event::ServiceCrash
        }
        HiveMessage::LogAnomaly { service, .. } => {
            put("unit", service.clone());
            if let Some(name) = service_name(service) {
                put("service", name.to_string());
            }
            Event::LogAnomaly
        }
        HiveMessage::PortConflict {
            port,
            requested_by,
            held_by,
        } => {
            put("port", port.to_string());
            put("requester", requested_by.name.clone());
            put("holder", held_by.name.clone());
            Event::PortConflict
        }
        HiveMessage::DiskSpaceLow {
            mount,
            usage_percent,
            available_bytes,
            ..
        } => {
            put("mount", mount.display().to_string());
            put("percent", (usage_percent.round() as i64).to_string());
            put("free_mb", (available_bytes / (1024 * 1024)).to_string());
            Event::DiskLow
        }
        HiveMessage::MemoryPressure {
            available_bytes,
            total_bytes,
            ..
        } => {
            put("free_mb", (available_bytes / (1024 * 1024)).to_string());
            put("total_mb", (total_bytes / (1024 * 1024)).to_string());
            Event::MemoryPressure
        }
        HiveMessage::CommandObserved { process, cmd, .. } => {
            put("cmd", cmd.clone());
            put("program", process.name.clone());
            Event::CommandObserved
        }
        HiveMessage::CommandNotFound { command, package } => {
            put("command", command.clone());
            if is_valid_package_name(package) {
                put("package", package.clone());
            }
            Event::CommandNotFound
        }
        _ => return None,
    };
    Some((event, f))
}

/// `nginx.service` -> `nginx`, the form hive-actuator's whitelist uses.
///
/// Only service units qualify (restarting `init.scope` or a `.socket` isn't
/// a meaningful suggestion), and only names made of the characters systemd
/// allows in unit names — nothing that could read as an option or a glob.
pub fn service_name(unit: &str) -> Option<&str> {
    let name = unit.strip_suffix(".service")?;
    valid_service_name(name).then_some(name)
}

pub fn valid_service_name(name: &str) -> bool {
    !name.is_empty()
        && !name.starts_with('-')
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '@' | '.' | '_' | ':' | '-'))
}

/// The `{field}`s of a text.
pub fn placeholders(text: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(start) = rest.find('{') {
        let after = &rest[start + 1..];
        match after.find('}') {
            Some(end) => {
                out.push(&after[..end]);
                rest = &after[end + 1..];
            }
            None => break,
        }
    }
    out
}

/// The text with every `{field}` replaced; None when the event does not
/// provide one of them.
pub fn fill(text: &str, fields: &Fields) -> Option<String> {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(start) = rest.find('{') {
        out.push_str(&rest[..start]);
        let after = &rest[start + 1..];
        let end = after.find('}')?;
        out.push_str(fields.get(&after[..end])?);
        rest = &after[end + 1..];
    }
    out.push_str(rest);
    Some(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_event_parses_back_from_its_name() {
        for event in Event::ALL {
            assert_eq!(Event::parse(event.name()), Some(event));
        }
        assert_eq!(Event::parse("reboot"), None);
    }

    #[test]
    fn a_crash_of_a_service_unit_has_its_service_name() {
        let (event, fields) = fields_of(&HiveMessage::ServiceCrash {
            service: "nginx.service".into(),
            exit_code: 1,
            restart_count: 2,
            logs: vec![],
        })
        .unwrap();
        assert_eq!(event, Event::ServiceCrash);
        assert_eq!(fields.get("unit").unwrap(), "nginx.service");
        assert_eq!(fields.get("service").unwrap(), "nginx");
        assert_eq!(fields.get("exit_code").unwrap(), "1");
        assert_eq!(
            fill("Restart {service} ({exit_code})", &fields).unwrap(),
            "Restart nginx (1)"
        );
    }

    #[test]
    fn a_unit_that_is_not_a_service_has_no_service_field() {
        let (_, fields) = fields_of(&HiveMessage::ServiceCrash {
            service: "docker.socket".into(),
            exit_code: 1,
            restart_count: 0,
            logs: vec![],
        })
        .unwrap();
        assert!(!fields.contains_key("service"));
        assert_eq!(fill("Restart {service}", &fields), None);
        assert_eq!(placeholders("a {b} c {d}"), vec!["b", "d"]);
    }

    #[test]
    fn service_names_are_what_systemd_allows() {
        assert_eq!(service_name("redis-server.service"), Some("redis-server"));
        assert_eq!(service_name("getty@tty1.service"), Some("getty@tty1"));
        assert_eq!(service_name("init.scope"), None);
        assert_eq!(service_name("--evil.service"), None);
        assert_eq!(service_name("a b.service"), None);
    }
}
