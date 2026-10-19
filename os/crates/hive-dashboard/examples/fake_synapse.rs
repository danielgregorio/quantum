//! Manual end-to-end test helper: connects to cortex and sends one
//! SuggestionResponse carrying a real Action, to exercise the
//! UserAction -> ActionRequest -> hive-actuator path without depending on
//! the real hive-synapse's mock text parser (parse_suggestions doesn't
//! attach an Action to anything it parses yet, so this is the only way to
//! test that leg today).
//!
//! Not part of any automated test — run manually alongside the real
//! daemons, e.g.:
//!   HIVE_CORTEX_SOCKET=/run/hive/cortex.sock cargo run --release \
//!       --example fake_synapse -p hive-dashboard
//!
//! Set FAKE_SYNAPSE_ACTION=dangerous to send a RemovePackage suggestion
//! instead of the default always-allowed CleanPackageCache — useful for
//! exercising hive-dashboard's two-press confirmation flow
//! (Action::is_dangerous) end to end.

use hive_common::actions::Action;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, Suggestion};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let socket_path =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| "/run/hive/cortex.sock".into());
    let mut sock = IpcSocket::connect(&socket_path).await?;
    eprintln!("fake_synapse: connected to {}", socket_path);

    let dangerous = std::env::var("FAKE_SYNAPSE_ACTION").as_deref() == Ok("dangerous");
    let suggestion = if dangerous {
        Suggestion {
            id: 1,
            title: "Remove unused package".to_string(),
            description: "nginx-extras looks unused and can be removed".to_string(),
            action: Some(Action::RemovePackage {
                name: "nginx-extras".to_string(),
                purge: false,
            }),
            learn_more: None,
            confidence: 0.7,
        }
    } else {
        Suggestion {
            id: 1,
            title: "Clean apt cache".to_string(),
            description: "Free up disk space by cleaning the apt package cache".to_string(),
            action: Some(Action::CleanPackageCache),
            learn_more: None,
            confidence: 0.95,
        }
    };

    sock.send(&HiveMessage::SuggestionResponse {
        request_id: uuid::Uuid::new_v4(),
        suggestions: vec![suggestion],
        processing_time_ms: 1,
    })
    .await?;
    eprintln!("fake_synapse: sent SuggestionResponse with a CleanPackageCache suggestion");

    // Keep the connection open briefly so cortex doesn't immediately
    // register-then-unregister us mid-flow.
    tokio::time::sleep(std::time::Duration::from_secs(10)).await;
    Ok(())
}
