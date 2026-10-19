//! Hive Synapse - SLM Inference Daemon
//!
//! This daemon runs an on-device Small Language Model (SLM) that provides
//! intelligent suggestions based on system context. It operates in complete
//! isolation with no network access.
//!
//! # Security Model
//!
//! - Runs as `_hive-ai` user with minimal privileges
//! - No network access (seccomp restricted)
//! - Only receives context, only returns suggestions: text from the model,
//!   plus typed actions from the Hive's rules on the triggering event (never
//!   parsed out of model output; see the `rules` module)
//! - Communicates exclusively with hive-cortex via Unix socket

mod actions;
mod inference;
mod prompt;
mod queue;
mod rules;

use anyhow::{Context, Result};
use hive_common::config::SynapseConfig;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, MessageId, Suggestion};
use std::path::Path;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Instant;
use tokio::signal;
use tokio::sync::mpsc;
use tracing::{error, info, warn};

use crate::inference::InferenceEngine;
use crate::prompt::PromptBuilder;
use crate::queue::RequestQueue;

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// Suggestion requests kept waiting while the model is busy (see queue).
const MAX_PENDING_REQUESTS: usize = 3;

/// Counter for generating suggestion IDs
static SUGGESTION_COUNTER: AtomicU32 = AtomicU32::new(1);

/// A suggestion request waiting for the model.
struct Request {
    id: MessageId,
    context: hive_common::messages::Context,
    user_query: Option<String>,
    max_suggestions: u8,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_synapse")?;

    info!("Hive Synapse starting...");

    // Load configuration
    let config = load_config().await?;

    // The rules: what to offer on an event (config/hive/hive.q, compiled).
    match rules::Rules::load(&config.rules_path) {
        Ok(rules) => rules::install(rules),
        Err(e) => error!("{:#}; using the rules this build was made with", e),
    }

    // Drop privileges if running as root
    if nix::unistd::geteuid().is_root() {
        drop_privileges(&config.user)?;
    }

    // Initialize inference engine
    let engine = Arc::new(InferenceEngine::new(&config).await?);

    // Connect to cortex
    let cortex_socket =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = IpcSocket::connect(&cortex_socket)
        .await
        .context("Failed to connect to cortex")?;

    info!("Hive Synapse ready");
    hive_common::systemd::report_ready();

    // Requests are answered by a worker, so the socket keeps being read (and
    // stale requests dropped) while the model is generating.
    let queue = Arc::new(RequestQueue::new(MAX_PENDING_REQUESTS));
    let (responses, mut outgoing) = mpsc::channel::<HiveMessage>(8);
    tokio::spawn(answer_requests(engine, queue.clone(), responses));

    loop {
        tokio::select! {
            result = cortex.recv() => {
                match result {
                    Ok(HiveMessage::SuggestionRequest { request_id, context, user_query, max_suggestions }) => {
                        info!("Received suggestion request {}", request_id);
                        let request = Request { id: request_id, context, user_query, max_suggestions };
                        if request.user_query.is_some() {
                            queue.push_priority(request);
                        } else if let Some(dropped) = queue.push(request) {
                            warn!(
                                "Busy: dropped suggestion request {} in favor of newer ones",
                                dropped.id
                            );
                        }
                    }
                    Ok(other) => warn!("Received unexpected message type: {}", other.type_name()),
                    Err(hive_common::ipc::IpcError::ConnectionClosed) => {
                        warn!("Connection to cortex closed, exiting");
                        break;
                    }
                    Err(e) => {
                        error!("Error receiving message: {}", e);
                    }
                }
            }
            Some(response) = outgoing.recv() => {
                if let Err(e) = cortex.send(&response).await {
                    error!("Failed to send suggestion response: {}", e);
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    info!("Hive Synapse shutting down");
    Ok(())
}

async fn load_config() -> Result<SynapseConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        let full_config = hive_common::config::Config::load(&config_path)?;
        Ok(full_config.synapse)
    } else {
        warn!("Config file not found, using defaults");
        Ok(SynapseConfig::default())
    }
}

fn drop_privileges(username: &str) -> Result<()> {
    use nix::unistd::{setgid, setuid, Gid, Uid, User};

    let user = User::from_name(username)?.context(format!("User {} not found", username))?;

    setgid(Gid::from_raw(user.gid.as_raw()))?;
    setuid(Uid::from_raw(user.uid.as_raw()))?;

    info!("Dropped privileges to user {}", username);
    Ok(())
}

/// The worker: answer queued requests one at a time.
async fn answer_requests(
    engine: Arc<InferenceEngine>,
    queue: Arc<RequestQueue<Request>>,
    responses: mpsc::Sender<HiveMessage>,
) {
    loop {
        let request = queue.pop().await;
        let response = answer(&engine, request).await;
        if responses.send(response).await.is_err() {
            return;
        }
    }
}

async fn answer(engine: &InferenceEngine, request: Request) -> HiveMessage {
    let start = Instant::now();

    // Approvable suggestions come from rules on the trigger, ahead of the
    // model's text-only ones (see the actions module) - and don't depend on
    // the model working at all.
    let mut suggestions: Vec<Suggestion> = actions::for_context(&request.context)
        .into_iter()
        .map(|s| {
            info!("Suggesting '{}': {:?}", s.title, s.action);
            Suggestion {
                id: next_suggestion_id(),
                title: s.title,
                description: s.description,
                action: Some(s.action),
                learn_more: None,
                confidence: 0.9,
            }
        })
        .collect();

    let (system, user) = PromptBuilder::new()
        .with_context(&request.context)
        .with_user_query(request.user_query.as_deref())
        .build_parts();
    match engine.generate(&system, &user).await {
        Ok(text) => suggestions.extend(parse_suggestions(&text)),
        Err(e) => error!("Inference failed for request {}: {:#}", request.id, e),
    }

    suggestions.truncate(request.max_suggestions as usize);
    let processing_time_ms = start.elapsed().as_millis() as u32;
    info!(
        "Sent suggestion response ({} suggestions, {}ms)",
        suggestions.len(),
        processing_time_ms
    );

    HiveMessage::SuggestionResponse {
        request_id: request.id,
        suggestions,
        processing_time_ms,
    }
}

/// Parse the model's response into structured suggestions
fn parse_suggestions(response: &str) -> Vec<Suggestion> {
    let mut suggestions = Vec::new();

    // Simple parsing: each line starting with "- " is a suggestion
    for line in response.lines() {
        let line = line.trim();
        if line.starts_with("- ") || line.starts_with("* ") {
            let text = line[2..].trim().to_string();
            if !text.is_empty() {
                suggestions.push(Suggestion {
                    id: next_suggestion_id(),
                    title: extract_title(&text),
                    description: text,
                    action: None, // Could parse commands from backticks
                    learn_more: None,
                    confidence: 0.7, // Default confidence for mock
                });
            }
        }
    }

    // If no structured suggestions, treat entire response as one suggestion
    if suggestions.is_empty() && !response.trim().is_empty() {
        suggestions.push(Suggestion {
            id: next_suggestion_id(),
            title: "Suggestion".to_string(),
            description: response.trim().to_string(),
            action: None,
            learn_more: None,
            confidence: 0.5,
        });
    }

    suggestions
}

fn next_suggestion_id() -> u32 {
    SUGGESTION_COUNTER.fetch_add(1, Ordering::Relaxed)
}

fn extract_title(text: &str) -> String {
    // Take first sentence or first N chars as title. Truncate by char
    // count, not byte length — `text[..47]` panics if byte 47 lands
    // mid-character for any non-ASCII input (LLM output isn't guaranteed
    // to be ASCII).
    if let Some(end) = text.find(['.', ':', '!', '?']) {
        text[..end].trim().to_string()
    } else if text.chars().count() > 50 {
        let truncated: String = text.chars().take(47).collect();
        format!("{}...", truncated)
    } else {
        text.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_suggestions_reads_dash_and_star_bullets() {
        let response = "Here's what I found:\n- First suggestion\n* Second suggestion\nNot a bullet, ignored\n";
        let suggestions = parse_suggestions(response);

        assert_eq!(suggestions.len(), 2);
        assert_eq!(suggestions[0].description, "First suggestion");
        assert_eq!(suggestions[1].description, "Second suggestion");
    }

    #[test]
    fn parse_suggestions_falls_back_to_whole_response_when_unstructured() {
        let response = "Just a plain sentence with no bullets.";
        let suggestions = parse_suggestions(response);

        assert_eq!(suggestions.len(), 1);
        assert_eq!(suggestions[0].description, response);
        assert_eq!(suggestions[0].title, "Suggestion");
    }

    #[test]
    fn parse_suggestions_on_empty_response_yields_nothing() {
        assert!(parse_suggestions("").is_empty());
        assert!(parse_suggestions("   \n  ").is_empty());
    }

    #[test]
    fn extract_title_stops_at_first_sentence_boundary() {
        assert_eq!(
            extract_title("Restart nginx. It will pick up the new config."),
            "Restart nginx"
        );
        assert_eq!(extract_title("Check disk space: df -h"), "Check disk space");
    }

    #[test]
    fn extract_title_truncates_long_untruncated_text() {
        let text = "a".repeat(80);
        let title = extract_title(&text);
        assert_eq!(title, format!("{}...", "a".repeat(47)));
    }

    #[test]
    fn extract_title_returns_short_text_unchanged() {
        assert_eq!(extract_title("short"), "short");
    }

    #[test]
    fn extract_title_does_not_panic_on_multibyte_text_near_the_truncation_point() {
        // 50 emoji (4 bytes each in UTF-8) with no sentence-ending
        // punctuation — byte offset 47 falls mid-character if this isn't
        // handled on a char boundary.
        let text = "🦀".repeat(50);
        let _ = extract_title(&text);
    }
}
