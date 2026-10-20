//! `hive`: the Hive's commands for the person at the console.
//!
//!     hive apps                      the applications installed with the Hive
//!     hive ajustes [PAGE]            an app on the Hive's screen (quantum pixel), as this user
//!     hive request set-hostname NAME
//!     hive request set-keyboard LAYOUT [MODEL]
//!     hive request set-screen-level auto|plain|effects|fine   [--reason TEXT]
//!
//! An app is a Quantum project folder under /usr/share/quantum-os/apps
//! (`QUANTUM_OS_APPS`); `hive NAME` opens it on the screen the way
//! `hive ajustes` does. A request goes to hive-cortex's user socket as a
//! `UserRequest`, which any local user may send: the Hive offers it in the
//! user's name, an administrator approves it on the screen (F1) or the
//! dashboard, and the actuator runs it through its whitelist. Nothing runs
//! on the asking. The Ajustes app's "Pedir à Hive" buttons run this.

use anyhow::{bail, Context, Result};
use hive_common::actions::{is_valid_hostname, is_valid_keyboard, Action};
use hive_common::ipc::blocking::Connection;
use hive_common::messages::HiveMessage;
use std::path::PathBuf;

const USAGE: &str = "hive: the Hive's commands
  hive apps                         the applications installed with the Hive
  hive ajustes [PAGE]               the machine's settings on the screen (any app: hive NAME)
  hive request set-hostname NAME    ask the Hive to name the machine
  hive request set-keyboard LAYOUT [MODEL]        us, or br (abnt2)
  hive request set-screen-level auto|plain|effects|fine
      [--reason TEXT]               why, shown with the offer";

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let code = match run(&args) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("hive: {:#}", e);
            1
        }
    };
    std::process::exit(code);
}

fn apps_dir() -> PathBuf {
    std::env::var_os("QUANTUM_OS_APPS")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/usr/share/quantum-os/apps"))
}

fn run(args: &[String]) -> Result<i32> {
    let Some(cmd) = args.first() else {
        eprintln!("{}", USAGE);
        return Ok(2);
    };
    match cmd.as_str() {
        "-h" | "--help" | "help" => {
            println!("{}", USAGE);
            Ok(0)
        }
        "apps" => {
            let mut names: Vec<String> = std::fs::read_dir(apps_dir())
                .map(|dir| {
                    dir.filter_map(|e| e.ok())
                        .filter(|e| e.path().join("quantum.config.yaml").is_file())
                        .map(|e| e.file_name().to_string_lossy().to_string())
                        .collect()
                })
                .unwrap_or_default();
            names.sort();
            for name in names {
                println!("{}", name);
            }
            Ok(0)
        }
        "request" => request(&args[1..]),
        name => open(name, &args[1..]),
    }
}

/// `hive NAME [PAGE]`: the app on the screen, through `quantum pixel`,
/// which takes this process over (exec) so Esc ends it.
fn open(name: &str, rest: &[String]) -> Result<i32> {
    if name.starts_with('-') || name.contains('/') {
        bail!("no such command: {} (hive --help)", name);
    }
    let app = apps_dir().join(name);
    if !app.join("quantum.config.yaml").is_file() {
        bail!(
            "no app named {} in {} (hive apps lists them)",
            name,
            apps_dir().display()
        );
    }
    std::env::set_current_dir(&app).with_context(|| format!("cannot enter {}", app.display()))?;
    use std::os::unix::process::CommandExt;
    let err = std::process::Command::new("quantum")
        .arg("pixel")
        .args(rest)
        .exec();
    Err(err).context("cannot run quantum pixel (is the Quantum runtime installed?)")
}

/// `hive request ...`: the setting, as an Action, to hive-cortex.
fn request(args: &[String]) -> Result<i32> {
    let mut reason = String::new();
    let mut words: Vec<&str> = Vec::new();
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--reason" {
            reason = args.get(i + 1).cloned().context("--reason needs a text")?;
            i += 2;
        } else {
            words.push(&args[i]);
            i += 1;
        }
    }
    let action = parse_setting(&words)?;
    let what = action.describe_setting().context("not a setting")?;
    let path = std::env::var_os("HIVE_USER_SOCKET")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(hive_common::USER_SOCKET));
    let mut conn = Connection::connect(&path).with_context(|| {
        format!(
            "the Hive is not listening at {} (is hive-cortex running?)",
            path.display()
        )
    })?;
    conn.send(&HiveMessage::UserRequest { action, reason })
        .context("could not send the request to the Hive")?;
    println!(
        "asked the Hive: {}. An administrator approves it on the screen (F1, Enter) or the dashboard.",
        what
    );
    Ok(0)
}

/// The words after `request`, as the action they name.
fn parse_setting(words: &[&str]) -> Result<Action> {
    match words {
        ["set-hostname", name] => {
            if !is_valid_hostname(name) {
                bail!("{}: a name is letters, digits and hyphens, up to 63", name);
            }
            Ok(Action::SetHostname {
                name: name.to_string(),
            })
        }
        ["set-keyboard", layout] | ["set-keyboard", layout, _] => {
            let model = words.get(2).copied().unwrap_or("");
            if !is_valid_keyboard(layout, model) {
                bail!(
                    "{} {}: the keyboards are us (pc105) and br (abnt2)",
                    layout,
                    model
                );
            }
            Ok(Action::SetKeyboard {
                layout: layout.to_string(),
                model: model.to_string(),
            })
        }
        ["set-screen-level", level] => {
            let level = match *level {
                "auto" | "measure" => None,
                "0" | "plain" => Some(0),
                "1" | "effects" => Some(1),
                "2" | "fine" => Some(2),
                other => bail!("{}: a level is auto, plain, effects or fine", other),
            };
            Ok(Action::SetScreenLevel { level })
        }
        _ => bail!(
            "what to ask for: set-hostname NAME, set-keyboard LAYOUT [MODEL], set-screen-level LEVEL"
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_words_of_a_request_become_the_action() {
        assert_eq!(
            parse_setting(&["set-hostname", "forja"]).unwrap(),
            Action::SetHostname {
                name: "forja".into()
            }
        );
        assert!(parse_setting(&["set-hostname", "Forja!"]).is_err());
        assert_eq!(
            parse_setting(&["set-keyboard", "br", "abnt2"]).unwrap(),
            Action::SetKeyboard {
                layout: "br".into(),
                model: "abnt2".into()
            }
        );
        assert_eq!(
            parse_setting(&["set-keyboard", "us"]).unwrap(),
            Action::SetKeyboard {
                layout: "us".into(),
                model: "".into()
            }
        );
        assert!(parse_setting(&["set-keyboard", "fr"]).is_err());
        assert_eq!(
            parse_setting(&["set-screen-level", "fine"]).unwrap(),
            Action::SetScreenLevel { level: Some(2) }
        );
        assert_eq!(
            parse_setting(&["set-screen-level", "auto"]).unwrap(),
            Action::SetScreenLevel { level: None }
        );
        assert!(parse_setting(&["set-screen-level", "9"]).is_err());
        assert!(parse_setting(&["restart-service", "nginx"]).is_err());
    }
}
