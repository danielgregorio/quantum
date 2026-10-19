//! The Hive's rules: what synapse offers when an event happens.
//!
//! The rules are written in Quantum (config/hive/hive.q) and compiled to
//! config/hive/rules.toml, which is installed as /etc/hive/rules.toml. Each
//! rule is an event and its offers; an offer is a title, a description and a
//! typed `Action`, any of which may hold `{field}`, a field of the event. The
//! fields are filled in here, from the event itself: nothing in an offer
//! ever comes from the model's text. hive-actuator's whitelist still has the
//! final word on whether an action may run.
//!
//! The build embeds the committed rules.toml as its built-in rules, for a
//! system without the file (the lab, a test, a broken install).

use anyhow::{bail, Context as _, Result};
use hive_common::actions::{is_valid_package_name, Action};
use hive_common::events::{fields_of, fill, placeholders, valid_service_name, Event};
use hive_common::messages::HiveMessage;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::path::Path;
use std::sync::OnceLock;

/// The committed rules, compiled from config/hive/hive.q.
pub const BUILTIN: &str = include_str!("../../../config/hive/rules.toml");

/// An approvable suggestion, before it gets its id.
#[derive(Debug, Clone, PartialEq)]
pub struct ActionSuggestion {
    pub title: String,
    pub description: String,
    pub action: Action,
}

// ---------------------------------------------------------------- the file

#[derive(Deserialize)]
struct File {
    meta: Meta,
    #[serde(default)]
    rules: Vec<RuleToml>,
}

#[derive(Deserialize)]
struct Meta {
    version: u32,
}

#[derive(Deserialize)]
struct RuleToml {
    event: String,
    #[serde(default)]
    offers: Vec<OfferToml>,
}

#[derive(Deserialize)]
struct OfferToml {
    title: String,
    #[serde(default)]
    description: String,
    action: String,
    /// The action's own parameters, every one a string (a number or a
    /// placeholder, typed when the action is built).
    #[serde(flatten)]
    params: BTreeMap<String, String>,
}

// ---------------------------------------------------------------- actions

/// The actions an offer may name, by the kebab-case of the Action variant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Kind {
    RunCommand,
    StartService,
    StopService,
    RestartService,
    ReloadService,
    EnableService,
    DisableService,
    InstallPackage,
    RemovePackage,
    UpdatePackageLists,
    UpgradePackages,
    CleanPackageCache,
    KillPortProcess,
    CreateSnapshot,
    ListSnapshots,
}

impl Kind {
    fn parse(name: &str) -> Option<Kind> {
        Some(match name {
            "run-command" => Kind::RunCommand,
            "start-service" => Kind::StartService,
            "stop-service" => Kind::StopService,
            "restart-service" => Kind::RestartService,
            "reload-service" => Kind::ReloadService,
            "enable-service" => Kind::EnableService,
            "disable-service" => Kind::DisableService,
            "install-package" => Kind::InstallPackage,
            "remove-package" => Kind::RemovePackage,
            "update-package-lists" => Kind::UpdatePackageLists,
            "upgrade-packages" => Kind::UpgradePackages,
            "clean-package-cache" => Kind::CleanPackageCache,
            "kill-port-process" => Kind::KillPortProcess,
            "create-snapshot" => Kind::CreateSnapshot,
            "list-snapshots" => Kind::ListSnapshots,
            _ => return None,
        })
    }

    fn required(self) -> &'static [&'static str] {
        match self {
            Kind::RunCommand => &["cmd"],
            Kind::StartService
            | Kind::StopService
            | Kind::RestartService
            | Kind::ReloadService
            | Kind::EnableService
            | Kind::DisableService => &["service"],
            Kind::InstallPackage | Kind::RemovePackage => &["package"],
            Kind::KillPortProcess => &["port"],
            Kind::CreateSnapshot => &["dataset", "name"],
            Kind::UpdatePackageLists
            | Kind::UpgradePackages
            | Kind::CleanPackageCache
            | Kind::ListSnapshots => &[],
        }
    }

    /// The action, from its parameters with the fields filled in. None when
    /// a value is not what the action takes (a port that is not a number, a
    /// name that could read as an option): no offer is better than a wrong one.
    fn build(self, p: &BTreeMap<String, String>) -> Option<Action> {
        let get = |name: &str| p.get(name).map(String::as_str);
        let flag = |name: &str, default: bool| match get(name) {
            None => Some(default),
            Some("true") => Some(true),
            Some("false") => Some(false),
            Some(_) => None,
        };
        let service = || {
            get("service")
                .filter(|s| valid_service_name(s))
                .map(str::to_string)
        };
        let package = || {
            get("package")
                .filter(|s| is_valid_package_name(s))
                .map(str::to_string)
        };
        Some(match self {
            Kind::RunCommand => Action::RunCommand {
                cmd: get("cmd")?.to_string(),
                args: get("args")
                    .unwrap_or("")
                    .split_whitespace()
                    .map(str::to_string)
                    .collect(),
                cwd: None,
                env: vec![],
            },
            Kind::StartService => Action::StartService { name: service()? },
            Kind::StopService => Action::StopService { name: service()? },
            Kind::RestartService => Action::RestartService { name: service()? },
            Kind::ReloadService => Action::ReloadService { name: service()? },
            Kind::EnableService => Action::EnableService {
                name: service()?,
                now: flag("now", true)?,
            },
            Kind::DisableService => Action::DisableService {
                name: service()?,
                now: flag("now", true)?,
            },
            Kind::InstallPackage => Action::InstallPackage {
                name: package()?,
                assume_yes: true,
            },
            Kind::RemovePackage => Action::RemovePackage {
                name: package()?,
                purge: flag("purge", false)?,
            },
            Kind::UpdatePackageLists => Action::UpdatePackageLists,
            Kind::UpgradePackages => Action::UpgradePackages {
                packages: get("packages")
                    .unwrap_or("")
                    .split_whitespace()
                    .map(str::to_string)
                    .collect(),
            },
            Kind::CleanPackageCache => Action::CleanPackageCache,
            Kind::KillPortProcess => Action::KillPortProcess {
                port: get("port")?.parse().ok()?,
                signal: match get("signal") {
                    None => None,
                    Some(s) => Some(s.parse().ok()?),
                },
            },
            Kind::CreateSnapshot => Action::CreateSnapshot {
                dataset: get("dataset")?.to_string(),
                name: get("name")?.to_string(),
                recursive: flag("recursive", true)?,
            },
            Kind::ListSnapshots => Action::ListSnapshots {
                dataset: get("dataset").map(str::to_string),
            },
        })
    }
}

// ---------------------------------------------------------------- the rules

#[derive(Debug)]
struct Offer {
    title: String,
    description: String,
    kind: Kind,
    params: BTreeMap<String, String>,
}

#[derive(Debug)]
struct Rule {
    event: Event,
    offers: Vec<Offer>,
}

/// The rules, checked: every event and action is one the Hive has, and
/// every `{field}` is a field of its event.
#[derive(Debug)]
pub struct Rules {
    rules: Vec<Rule>,
}

impl Rules {
    pub fn parse(text: &str) -> Result<Rules> {
        let file: File = toml::from_str(text).context("not a rules file")?;
        if file.meta.version != 1 {
            bail!(
                "rules file version {}; this build reads version 1",
                file.meta.version
            );
        }
        let mut rules: Vec<Rule> = Vec::new();
        for rule in file.rules {
            let event = Event::parse(&rule.event)
                .with_context(|| format!("{:?} is not an event the Hive reports", rule.event))?;
            if rules.iter().any(|r| r.event == event) {
                bail!("two rules on {}", rule.event);
            }
            let mut offers = Vec::new();
            for offer in rule.offers {
                let kind = Kind::parse(&offer.action).with_context(|| {
                    format!("{:?} is not an action an offer can name", offer.action)
                })?;
                for name in kind.required() {
                    if !offer.params.contains_key(*name) {
                        bail!("an offer of {} needs {}", offer.action, name);
                    }
                }
                let texts = std::iter::once(&offer.title)
                    .chain(std::iter::once(&offer.description))
                    .chain(offer.params.values());
                for text in texts {
                    for field in placeholders(text) {
                        if !event.fields().contains(&field) {
                            bail!(
                                "{{{}}} is not a field of {} (it has: {})",
                                field,
                                rule.event,
                                event.fields().join(", ")
                            );
                        }
                    }
                }
                offers.push(Offer {
                    title: offer.title,
                    description: offer.description,
                    kind,
                    params: offer.params,
                });
            }
            rules.push(Rule { event, offers });
        }
        Ok(Rules { rules })
    }

    /// The rules this build was made with (config/hive/rules.toml).
    pub fn builtin() -> Rules {
        Rules::parse(BUILTIN).expect("the committed rules.toml is checked in CI")
    }

    /// The rules at `path`; the built-in ones when there is no file there.
    pub fn load(path: &Path) -> Result<Rules> {
        if !path.is_file() {
            tracing::warn!(
                "No rules at {}; using the rules this build was made with",
                path.display()
            );
            return Ok(Rules::builtin());
        }
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("cannot read {}", path.display()))?;
        Rules::parse(&text).with_context(|| format!("{} is not a rules file", path.display()))
    }

    /// What to offer for an event: each offer of its rule whose fields the
    /// event provides, filled in.
    pub fn offers(&self, trigger: &HiveMessage) -> Vec<ActionSuggestion> {
        let Some((event, fields)) = fields_of(trigger) else {
            return vec![];
        };
        let Some(rule) = self.rules.iter().find(|r| r.event == event) else {
            return vec![];
        };
        rule.offers
            .iter()
            .filter_map(|offer| {
                let title = fill(&offer.title, &fields)?;
                let description = fill(&offer.description, &fields)?;
                let params = offer
                    .params
                    .iter()
                    .map(|(k, v)| Some((k.clone(), fill(v, &fields)?)))
                    .collect::<Option<BTreeMap<_, _>>>()?;
                let action = offer.kind.build(&params)?;
                Some(ActionSuggestion {
                    title,
                    description,
                    action,
                })
            })
            .collect()
    }
}

static RULES: OnceLock<Rules> = OnceLock::new();

/// Makes `rules` the daemon's; the built-in rules serve until then.
pub fn install(rules: Rules) {
    let _ = RULES.set(rules);
}

pub fn current() -> &'static Rules {
    RULES.get_or_init(Rules::builtin)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_committed_rules_are_this_builds_rules() {
        let rules = Rules::builtin();
        assert!(!rules.rules.is_empty());
    }

    #[test]
    fn a_rules_file_is_checked_as_the_compiler_checks_it() {
        let bad = |body: &str| {
            Rules::parse(&format!("[meta]\nversion = 1\n{body}"))
                .unwrap_err()
                .to_string()
        };
        assert!(bad("[[rules]]\nevent = \"full-moon\"").contains("not an event"));
        assert!(bad(
            "[[rules]]\nevent = \"disk-low\"\n[[rules.offers]]\ntitle = \"x\"\naction = \"reboot\""
        )
        .contains("not an action"));
        assert!(bad(
            "[[rules]]\nevent = \"disk-low\"\n[[rules.offers]]\ntitle = \"x\"\naction = \"run-command\""
        )
        .contains("needs cmd"));
        assert!(bad(
            "[[rules]]\nevent = \"disk-low\"\n[[rules.offers]]\ntitle = \"{service}\"\naction = \"run-command\"\ncmd = \"df\""
        )
        .contains("not a field of disk-low"));
        assert!(Rules::parse("[meta]\nversion = 2\n")
            .unwrap_err()
            .to_string()
            .contains("version 2"));
    }

    #[test]
    fn an_offer_whose_value_is_not_what_the_action_takes_is_left_out() {
        let rules = Rules::parse(
            "[meta]\nversion = 1\n[[rules]]\nevent = \"port-conflict\"\n\
             [[rules.offers]]\ntitle = \"Free {port}\"\naction = \"kill-port-process\"\nport = \"{holder}\"\n\
             [[rules.offers]]\ntitle = \"Ports\"\naction = \"run-command\"\ncmd = \"ss\"\nargs = \"-tlnp\"",
        )
        .unwrap();
        let process = |name: &str| hive_common::messages::ProcessInfo {
            pid: 1,
            uid: 0,
            name: name.into(),
            cmdline: vec![],
            cwd: None,
            ppid: None,
        };
        let offers = rules.offers(&HiveMessage::PortConflict {
            port: 8080,
            requested_by: process("app"),
            held_by: process("nginx"),
        });
        // the holder's name is not a port number: that offer goes, the other stays
        assert_eq!(offers.len(), 1);
        assert_eq!(offers[0].title, "Ports");
    }
}
