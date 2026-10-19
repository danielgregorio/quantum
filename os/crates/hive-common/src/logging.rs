//! Logging setup shared by every Hive binary.

use std::io::IsTerminal;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

/// Install the global tracing subscriber: `info` and above for
/// `crate_target` (e.g. `"hive_cortex"`), adjustable through the usual
/// `RUST_LOG` filter variable.
///
/// Running as a systemd service, whose stdout is the journal, events go to
/// journald as native entries: an ERROR or WARN keeps its priority (3, 4)
/// instead of every line landing as info, so `journalctl -p warning` and
/// priority filters work, and fields like the target stay queryable.
/// Anywhere else (a terminal, a pipe, a container) it's plain text on stdout,
/// with colors only on a terminal.
pub fn init(crate_target: &str) -> anyhow::Result<()> {
    let filter = tracing_subscriber::EnvFilter::from_default_env()
        .add_directive(format!("{crate_target}=info").parse()?);

    if stdout_is_journal() {
        if let Ok(journald) = tracing_journald::layer() {
            tracing_subscriber::registry()
                .with(filter)
                .with(journald)
                .init();
            return Ok(());
        }
    }

    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_ansi(std::io::stdout().is_terminal())
        .init();
    Ok(())
}

/// systemd sets `JOURNAL_STREAM=<device>:<inode>` for a service whose output
/// is connected to the journal. It's compared against stdout itself because
/// children inherit the variable even when their output goes elsewhere.
fn stdout_is_journal() -> bool {
    std::env::var("JOURNAL_STREAM").is_ok_and(|stream| matches_stdout(&stream))
}

fn matches_stdout(stream: &str) -> bool {
    use std::os::unix::fs::MetadataExt;
    std::fs::metadata("/proc/self/fd/1")
        .is_ok_and(|stdout| stream == format!("{}:{}", stdout.dev(), stdout.ino()))
}
