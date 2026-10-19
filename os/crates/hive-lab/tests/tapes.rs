//! Every tape in tapes/ plays clean: the real hive-cortex and hive-synapse,
//! the nerves, the actuator, grove and the dashboard played by hive-lab.
//!
//! The lab runs as root (its users live in a private mount namespace), and
//! it starts the daemons the workspace built, so this test skips itself,
//! saying why, as any other user or before `cargo build --workspace`.
//! `scripts/lab/hive-tapes.sh` builds and plays them with sudo.

use std::path::{Path, PathBuf};
use std::process::Command;

#[test]
fn every_tape_plays() {
    if !nix::unistd::geteuid().is_root() {
        eprintln!("skipped: the Hive lab runs as root (scripts/lab/hive-tapes.sh uses sudo)");
        return;
    }
    let exe = Path::new(env!("CARGO_BIN_EXE_hive-lab"));
    let bin_dir = exe.parent().expect("target dir");
    if !bin_dir.join("hive-cortex").is_file() || !bin_dir.join("hive-synapse").is_file() {
        eprintln!("skipped: build the daemons first (cargo build --workspace)");
        return;
    }
    let mut tapes: Vec<PathBuf> =
        std::fs::read_dir(Path::new(env!("CARGO_MANIFEST_DIR")).join("tapes"))
            .expect("tapes/")
            .map(|e| e.expect("entry").path())
            .filter(|p| p.extension().is_some_and(|x| x == "jsonl"))
            .collect();
    tapes.sort();
    assert!(!tapes.is_empty(), "no tapes");
    let mut failures = Vec::new();
    for tape in &tapes {
        let out = Command::new(exe)
            .arg("--play")
            .arg(tape)
            .output()
            .expect("run hive-lab");
        if !out.status.success() {
            failures.push(format!(
                "{}:\n{}{}",
                tape.display(),
                String::from_utf8_lossy(&out.stdout),
                String::from_utf8_lossy(&out.stderr)
            ));
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}
