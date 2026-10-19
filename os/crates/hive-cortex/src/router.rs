//! Message routing logic for cortex.

use crate::{ComponentType, SharedState};
use anyhow::Result;
use hive_common::actions::is_valid_package_name;
use hive_common::anonymous::AnonymousSession;
use hive_common::messages::{HiveMessage, MessageId, Severity, Suggestion};
use tracing::{debug, info, warn};
use uuid::Uuid;

/// Routes messages between components
pub struct MessageRouter {
    state: SharedState,
}

impl MessageRouter {
    pub fn new(state: SharedState) -> Self {
        Self { state }
    }

    /// Route a message to the appropriate destination(s)
    pub async fn route(&self, msg: HiveMessage, from_conn: u64) -> Result<()> {
        match &msg {
            // Nerve observations -> Synapse for analysis, Dashboard for notification
            HiveMessage::CommandObserved { process, .. } => {
                // A command run from an anonymous shell is hidden too: the
                // shell is its parent (or further up, through `sh -c`, a
                // pipeline...). Commands are usually gone by now, but their
                // parent pid came with the observation, and the shell is
                // still alive to walk up from.
                {
                    let state = self.state.read().await;
                    if state.anonymous.session_count() > 0 {
                        let hidden = std::iter::once(process.pid)
                            .chain(process.ppid.into_iter().flat_map(|ppid| {
                                std::iter::once(ppid).chain(process_ancestry(ppid))
                            }))
                            .any(|pid| state.anonymous.should_hide_process(pid));
                        if hidden {
                            info!("Skipping observation for anonymous process {}", process.pid);
                            return Ok(());
                        }
                    }
                }
                self.forward_to_synapse(msg.clone(), from_conn).await?;
            }

            HiveMessage::PortConflict {
                port,
                requested_by,
                held_by,
            } => {
                let problem = format!("port {} for {}", port, requested_by.name);
                let Some(held) = self.news(problem).await else {
                    return Ok(());
                };
                // Forward to synapse for analysis
                self.forward_to_synapse(msg.clone(), from_conn).await?;
                // Notify the dashboard immediately
                self.notify_dashboard(
                    "Port Conflict Detected",
                    &with_held(
                        format!(
                            "{} could not bind port {}: already held by {}",
                            requested_by.name, port, held_by.name
                        ),
                        held,
                    ),
                    Severity::Warning,
                )
                .await?;
            }

            HiveMessage::LogAnomaly {
                service, severity, ..
            } => {
                let Some(held) = self.news(format!("anomaly {}", service)).await else {
                    return Ok(());
                };
                self.forward_to_synapse(msg.clone(), from_conn).await?;
                if severity.requires_notification() {
                    self.notify_dashboard(
                        "Log Anomaly Detected",
                        &with_held(format!("Issues detected in {}", service), held),
                        *severity,
                    )
                    .await?;
                }
            }

            HiveMessage::ServiceCrash {
                service, exit_code, ..
            } => {
                let Some(held) = self.news(format!("crash {}", service)).await else {
                    return Ok(());
                };
                self.forward_to_synapse(msg.clone(), from_conn).await?;
                self.notify_dashboard(
                    "Service Crashed",
                    &with_held(format!("{} exited with code {}", service, exit_code), held),
                    Severity::Error,
                )
                .await?;
            }

            HiveMessage::DiskSpaceLow {
                mount,
                usage_percent,
                ..
            } => {
                let Some(held) = self.news(format!("disk {}", mount.display())).await else {
                    return Ok(());
                };
                self.forward_to_synapse(msg.clone(), from_conn).await?;
                self.notify_dashboard(
                    "Low Disk Space",
                    &with_held(
                        format!("{} is {:.1}% full", mount.display(), usage_percent),
                        held,
                    ),
                    Severity::Warning,
                )
                .await?;
            }

            HiveMessage::MemoryPressure { .. } => {
                if self.news("memory".to_string()).await.is_none() {
                    return Ok(());
                }
                self.forward_to_synapse(msg.clone(), from_conn).await?;
                self.notify_dashboard(
                    "Memory Pressure",
                    "System is running low on memory",
                    Severity::Warning,
                )
                .await?;
            }

            // Plain notifications from nerves (hive-nerve-fs reports its
            // filesystem events this way) -> the dashboard. Rebuilt through
            // notify_dashboard instead of forwarded as-is: that drops
            // `actions`, so no sender can smuggle suggestions in here — only
            // synapse-originated ones (stored by offer_suggestions) can ever
            // be acted on. Non-nerves have no business sending these at all.
            HiveMessage::Notification {
                title,
                body,
                severity,
                ..
            } => {
                let sender_type = {
                    let state = self.state.read().await;
                    state.component_type_of(from_conn)
                };
                if sender_type.is_some_and(|t| t.is_nerve()) {
                    info!("Notification from {:?}: {}: {}", sender_type, title, body);
                    self.notify_dashboard(title, body, *severity).await?;
                } else {
                    warn!(
                        "Rejecting Notification from connection {} (component type {:?}, \
                         expected a nerve)",
                        from_conn, sender_type
                    );
                }
            }

            // Synapse responses -> stored + surfaced to the dashboard as a
            // Notification (HiveMessage::Notification.actions already
            // exists for exactly this). NOT forward_to_requester: the
            // requester was whichever nerve observed the triggering event,
            // and it has no use for the suggestions — the human does.
            //
            // Only the real hive-synapse may originate suggestions: this
            // is the input that ultimately gets dispatched to hive-actuator
            // via act_on_suggestion, so an unauthenticated connection
            // injecting one here is as dangerous as injecting an
            // ActionRequest directly (see the rejection below).
            HiveMessage::SuggestionResponse {
                request_id,
                suggestions,
                processing_time_ms,
            } => {
                let sender_type = {
                    let state = self.state.read().await;
                    state.component_type_of(from_conn)
                };
                if sender_type == Some(ComponentType::Synapse) {
                    let query = {
                        let mut state = self.state.write().await;
                        state.pending_queries.remove(request_id)
                    };
                    match query {
                        // An answer to a user's question goes to that user
                        // only - and as text: whatever a question gets is
                        // never something to execute.
                        Some((asker, asker_request_id)) => {
                            let answer = HiveMessage::SuggestionResponse {
                                request_id: asker_request_id,
                                suggestions: suggestions
                                    .iter()
                                    .cloned()
                                    .map(|s| Suggestion { action: None, ..s })
                                    .collect(),
                                processing_time_ms: *processing_time_ms,
                            };
                            let state = self.state.read().await;
                            if let Some(component) = state.components.get(&asker) {
                                let _ = component.tx.send(answer).await;
                            }
                        }
                        None => self.offer_suggestions(suggestions.clone()).await?,
                    }
                } else {
                    warn!(
                        "Rejecting SuggestionResponse from connection {} (component type {:?}, \
                         expected Synapse)",
                        from_conn, sender_type
                    );
                }
            }

            // ActionRequest is cortex-internal only (cortex -> actuator, see
            // HiveMessage docs). No external component should ever send one
            // in on the wire; reject rather than blindly forwarding it, or
            // any connected component could get the actuator to execute
            // arbitrary whitelisted actions. Cortex's own internal path is
            // the UserAction arm below, which calls forward_to_actuator
            // directly rather than routing through here.
            HiveMessage::ActionRequest { request_id, .. } => {
                warn!(
                    "Rejecting ActionRequest {} received from external connection {} \
                     (only hive-cortex may originate action requests)",
                    request_id, from_conn
                );
            }

            // Action responses -> original requester (the dashboard, for a
            // UserAction-triggered request)
            HiveMessage::ActionResponse { request_id, .. } => {
                self.forward_to_requester(*request_id, msg).await?;
            }

            // User approved a suggestion from the dashboard - an
            // administrator's (see is_administrator); nothing else may.
            HiveMessage::UserAction {
                notification_id,
                suggestion_id,
                confirmed,
            } => {
                if self.sent_by(from_conn, ComponentType::Dashboard).await {
                    self.act_on_suggestion(*notification_id, *suggestion_id, *confirmed, from_conn)
                        .await?;
                } else {
                    warn!(
                        "Rejecting UserAction from connection {} (not a dashboard)",
                        from_conn
                    );
                }
            }

            HiveMessage::UserDismiss { notification_id } => {
                if self.sent_by(from_conn, ComponentType::Dashboard).await {
                    let mut state = self.state.write().await;
                    state.pending_suggestions.remove(notification_id);
                    debug!("User dismissed notification {}", notification_id);
                }
            }

            HiveMessage::CommandNotFound { command, package } => {
                self.offer_package(command, package, from_conn).await?;
            }

            HiveMessage::UserQuery {
                request_id,
                query,
                cwd,
            } => {
                self.ask_synapse(*request_id, query, cwd.clone(), from_conn)
                    .await?;
            }

            // Anonymous mode: a shell may hide itself (and what it runs),
            // nothing else - not another user's process, not an arbitrary
            // pid.
            HiveMessage::AnonymousModeEnter { level, pid } => {
                let mut state = self.state.write().await;
                match state.components.get(&from_conn) {
                    Some(c)
                        if c.component_type == ComponentType::Shell
                            && *pid == Some(c.pid as u32) =>
                    {
                        info!("Anonymous mode entered: {:?} for pid {}", level, c.pid);
                        let session = AnonymousSession::for_process(*level, c.pid as u32);
                        state.anonymous.add_session(session);
                    }
                    other => warn!(
                        "Rejecting AnonymousModeEnter for pid {:?} from connection {} ({:?}): \
                         only a shell, for its own pid",
                        pid,
                        from_conn,
                        other.map(|c| c.component_type)
                    ),
                }
            }

            HiveMessage::AnonymousModeExit { pid } => {
                let mut state = self.state.write().await;
                let own_pid = state
                    .components
                    .get(&from_conn)
                    .filter(|c| c.component_type == ComponentType::Shell)
                    .map(|c| c.pid as u32);
                if own_pid.is_some() && *pid == own_pid {
                    info!("Anonymous mode exited for pid {:?}", pid);
                    state
                        .anonymous
                        .remove_session_for_pid(own_pid.unwrap_or_default());
                } else {
                    warn!(
                        "Rejecting AnonymousModeExit for pid {:?} from connection {}",
                        pid, from_conn
                    );
                }
            }

            // Control messages
            HiveMessage::Ping { timestamp } => {
                self.send_pong(from_conn, *timestamp).await?;
            }

            HiveMessage::Pong { .. } => {
                debug!("Received pong from conn {}", from_conn);
            }

            HiveMessage::ReloadConfig => {
                info!("Reloading configuration");
                // TODO: Reload config and broadcast to components
            }

            HiveMessage::Shutdown { reason } => {
                info!("Shutdown requested: {}", reason);
                // TODO: Graceful shutdown
            }

            // Pass through other messages
            _ => {
                debug!("Unhandled message type: {}", msg.type_name());
            }
        }

        Ok(())
    }

    async fn forward_to_synapse(&self, msg: HiveMessage, _from: u64) -> Result<()> {
        let state = self.state.read().await;
        if let Some(synapse) = state.get_component_by_type(ComponentType::Synapse) {
            let request_id = Uuid::new_v4();

            // Build context from the message
            let context = hive_common::messages::Context {
                recent_commands: vec![],
                cwd: None,
                active_services: vec![],
                recent_logs: vec![],
                resources: None,
                trigger: Some(Box::new(msg)),
            };

            let request = HiveMessage::SuggestionRequest {
                request_id,
                context,
                user_query: None,
                max_suggestions: 3,
            };

            let _ = synapse.tx.send(request).await;
        } else {
            debug!("Synapse not connected, skipping analysis");
        }
        Ok(())
    }

    /// Whether a problem a nerve reports is news: its first report, or the
    /// first since PROBLEM_REPORT_INTERVAL. A service in a restart loop
    /// crashes every few seconds, and each crash would queue up the model
    /// and stack the same notice and offers on every dashboard again. Some
    /// (how many reports of it were held since it was last passed on) when
    /// it is news, None when this report is held too.
    async fn news(&self, problem: String) -> Option<u32> {
        let mut state = self.state.write().await;
        let (now, interval) = (std::time::Instant::now(), state.problem_report_interval);
        state
            .reported_problems
            .retain(|_, (at, held)| *held > 0 || now.duration_since(*at) < interval);
        match state.reported_problems.get_mut(&problem) {
            Some((at, held)) if now.duration_since(*at) < interval => {
                *held += 1;
                debug!("Holding a repeated report: {}", problem);
                None
            }
            Some((at, held)) => {
                let since = *held;
                (*at, *held) = (now, 0);
                Some(since)
            }
            None => {
                state.reported_problems.insert(problem, (now, 0));
                Some(0)
            }
        }
    }

    async fn sent_by(&self, conn: u64, component_type: ComponentType) -> bool {
        self.state.read().await.component_type_of(conn) == Some(component_type)
    }

    /// A shell ran into a program that isn't installed, and a package of
    /// that name exists: have synapse offer it (an administrator decides).
    /// Validated here, deduplicated for a while, and skipped for anonymous
    /// shells.
    async fn offer_package(&self, command: &str, package: &str, from_conn: u64) -> Result<()> {
        let valid_command = !command.is_empty()
            && command.len() <= 64
            && !command.contains('/')
            && !command.chars().any(char::is_control);
        let (uid, trigger) = {
            let mut state = self.state.write().await;
            let Some(shell) = state
                .components
                .get(&from_conn)
                .filter(|c| c.component_type == ComponentType::Shell)
            else {
                warn!(
                    "Rejecting CommandNotFound from connection {} (not a shell)",
                    from_conn
                );
                return Ok(());
            };
            let (uid, pid) = (shell.uid, shell.pid as u32);
            if !valid_command || !is_valid_package_name(package) {
                warn!(
                    "Ignoring CommandNotFound from uid {} with an invalid command or package",
                    uid
                );
                return Ok(());
            }
            if state.anonymous.should_hide_process(pid) {
                return Ok(());
            }
            let now = std::time::Instant::now();
            state
                .offered_packages
                .retain(|_, offered| now.duration_since(*offered) < PACKAGE_OFFER_INTERVAL);
            if state.offered_packages.contains_key(package) {
                debug!("Already offered {} recently", package);
                return Ok(());
            }
            state.offered_packages.insert(package.to_string(), now);
            (
                uid,
                HiveMessage::CommandNotFound {
                    command: command.to_string(),
                    package: package.to_string(),
                },
            )
        };
        info!(
            "Command not found for uid {}: offering to install {}",
            uid, package
        );
        self.forward_to_synapse(trigger, from_conn).await
    }

    /// A user's question (from a shell on the user socket) -> synapse, with
    /// the answer routed back to that connection (see SuggestionResponse).
    async fn ask_synapse(
        &self,
        asker_request_id: MessageId,
        query: &str,
        cwd: Option<std::path::PathBuf>,
        from_conn: u64,
    ) -> Result<()> {
        let mut state = self.state.write().await;
        let Some(asker) = state.components.get(&from_conn) else {
            return Ok(());
        };
        if asker.component_type != ComponentType::Shell {
            warn!(
                "Rejecting UserQuery from connection {} ({:?}): only shells ask",
                from_conn, asker.component_type
            );
            return Ok(());
        }
        // Who asked, not what: questions can be private.
        info!(
            "Question from uid {} (connection {}, {} chars)",
            asker.uid,
            from_conn,
            query.chars().count()
        );
        let Some(synapse) = state.get_component_by_type(ComponentType::Synapse) else {
            warn!("Synapse not connected, cannot answer a question");
            return Ok(());
        };
        let synapse = synapse.tx.clone();
        let request_id = Uuid::new_v4();
        state
            .pending_queries
            .insert(request_id, (from_conn, asker_request_id));
        drop(state);

        let request = HiveMessage::SuggestionRequest {
            request_id,
            context: hive_common::messages::Context {
                recent_commands: vec![],
                cwd,
                active_services: vec![],
                recent_logs: vec![],
                resources: None,
                trigger: None,
            },
            user_query: Some(query.to_string()),
            max_suggestions: 3,
        };
        let _ = synapse.send(request).await;
        Ok(())
    }

    /// Called only from `act_on_suggestion` below (cortex's own internal
    /// action-dispatch path). Inbound `ActionRequest` from the wire is
    /// rejected rather than routed here; see that arm in `route()`.
    async fn forward_to_actuator(&self, msg: HiveMessage) -> Result<()> {
        let state = self.state.read().await;
        if let Some(actuator) = state.get_component_by_type(ComponentType::Actuator) {
            let _ = actuator.tx.send(msg).await;
        } else {
            warn!("Actuator not connected");
        }
        Ok(())
    }

    async fn forward_to_requester(&self, request_id: MessageId, msg: HiveMessage) -> Result<()> {
        let conn_id = {
            let mut state = self.state.write().await;
            state.pending_requests.remove(&request_id)
        };

        if let Some(conn_id) = conn_id {
            let state = self.state.read().await;
            if let Some(component) = state.components.get(&conn_id) {
                let _ = component.tx.send(msg).await;
            }
        }
        Ok(())
    }

    async fn notify_dashboard(&self, title: &str, body: &str, severity: Severity) -> Result<()> {
        self.notify_dashboard_for_pid(title, body, severity, None)
            .await
    }

    async fn notify_dashboard_for_pid(
        &self,
        title: &str,
        body: &str,
        severity: Severity,
        pid: Option<u32>,
    ) -> Result<()> {
        let state = self.state.read().await;

        // Check if notifications should be suppressed for this PID
        if state.anonymous.should_suppress_notifications(pid) {
            debug!("Suppressing notification for anonymous session");
            return Ok(());
        }

        let notification = HiveMessage::Notification {
            id: Uuid::new_v4(),
            title: title.to_string(),
            body: body.to_string(),
            severity,
            actions: vec![],
            timeout_secs: 10,
        };
        // Every administrator's dashboard, not the first one found: with two
        // open, which one that was depended on a HashMap's order.
        for dashboard in state.components_of_type(ComponentType::Dashboard) {
            let _ = dashboard.tx.send(notification.clone()).await;
        }
        // Users' shells get these system notices too (never suggestions,
        // which can be about someone else's commands). try_send: a shell
        // that stopped reading must not stall the router.
        for shell in state.components_of_type(ComponentType::Shell) {
            let _ = shell.tx.try_send(notification.clone());
        }
        Ok(())
    }

    /// Stores suggestions from a SuggestionResponse and offers them to the
    /// dashboard as a Notification (its `actions` field carries the
    /// suggestions themselves, so the dashboard can render and let the user
    /// pick one). No-op if no dashboard is connected — suggestions are
    /// still stored, so a dashboard that connects later via UserAction on a
    /// stale id would still... actually it can't discover the id without a
    /// live dashboard having seen the Notification, so this is effectively
    /// dropped when nothing is watching. That's fine: nothing regresses
    /// versus today, where suggestions go nowhere at all.
    async fn offer_suggestions(&self, suggestions: Vec<Suggestion>) -> Result<()> {
        if suggestions.is_empty() {
            return Ok(());
        }

        let notification_id = Uuid::new_v4();
        {
            let mut state = self.state.write().await;
            state
                .pending_suggestions
                .insert(notification_id, suggestions.clone());
        }

        let state = self.state.read().await;
        if state.anonymous.should_suppress_notifications(None) {
            debug!("Suppressing suggestion notification for anonymous session");
            return Ok(());
        }
        let notification = HiveMessage::Notification {
            id: notification_id,
            title: "Hive Suggestion".to_string(),
            body: format!("{} suggestion(s) available", suggestions.len()),
            severity: Severity::Info,
            actions: suggestions,
            timeout_secs: 0,
        };
        // Offered to every administrator's dashboard; the first to approve
        // takes it (act_on_suggestion removes it), so it never runs twice.
        let mut told = 0;
        for dashboard in state.components_of_type(ComponentType::Dashboard) {
            let _ = dashboard.tx.send(notification.clone()).await;
            told += 1;
        }
        if told == 0 {
            debug!("Dashboard not connected, suggestions stored but not shown");
        }
        Ok(())
    }

    /// The user picked a suggestion in the dashboard. Look it up, and if it
    /// carries an Action, dispatch it to the actuator directly (bypassing
    /// the wire-level ActionRequest rejection in `route()`, since this
    /// really is cortex originating the request).
    async fn act_on_suggestion(
        &self,
        notification_id: MessageId,
        suggestion_id: u32,
        confirmed: bool,
        from_conn: u64,
    ) -> Result<()> {
        let suggestion = {
            let mut state = self.state.write().await;
            let Some(suggestions) = state.pending_suggestions.remove(&notification_id) else {
                warn!("UserAction for unknown notification {}", notification_id);
                return Ok(());
            };
            suggestions.into_iter().find(|s| s.id == suggestion_id)
        };

        let Some(suggestion) = suggestion else {
            warn!(
                "UserAction: suggestion {} not found in notification {}",
                suggestion_id, notification_id
            );
            return Ok(());
        };

        let Some(action) = suggestion.action else {
            info!(
                "User accepted suggestion {} ({}), which has no associated action",
                suggestion_id, suggestion.title
            );
            return Ok(());
        };

        let request_id = Uuid::new_v4();
        {
            let mut state = self.state.write().await;
            state.pending_requests.insert(request_id, from_conn);
        }

        info!(
            "Dispatching action for suggestion {} ({}): {:?}",
            suggestion_id, suggestion.title, action
        );
        // Dangerous actions need a second, explicit confirmation beyond the
        // initial approval — hive-dashboard sets `confirmed` only after its
        // own two-keypress flow for suggestions whose action is_dangerous().
        // A dangerous action that arrives unconfirmed (e.g. a client that
        // skips the second step) still gets requires_confirmation: true and
        // is rejected by hive-actuator's fail-closed handling.
        let requires_confirmation = action.is_dangerous() && !confirmed;
        self.forward_to_actuator(HiveMessage::ActionRequest {
            request_id,
            action,
            requires_confirmation,
            timeout_secs: 0,
        })
        .await
    }

    async fn send_pong(
        &self,
        conn_id: u64,
        ping_timestamp: chrono::DateTime<chrono::Utc>,
    ) -> Result<()> {
        let state = self.state.read().await;
        if let Some(component) = state.components.get(&conn_id) {
            let pong = HiveMessage::Pong {
                ping_timestamp,
                component: "hive-cortex".to_string(),
            };
            let _ = component.tx.send(pong).await;
        }
        Ok(())
    }
}

/// How long an "Install <package>" offer stands before the same package can
/// be offered again - a user retrying a missing command shouldn't queue up
/// the model or flood the dashboard.
const PACKAGE_OFFER_INTERVAL: std::time::Duration = std::time::Duration::from_secs(600);

/// How long a problem a nerve reported stands before the same problem is
/// passed on again (see MessageRouter::news).
pub(crate) const PROBLEM_REPORT_INTERVAL: std::time::Duration = std::time::Duration::from_secs(300);

/// A notice's body, and how many times the problem was held since it was
/// last reported.
fn with_held(body: String, held: u32) -> String {
    match held {
        0 => body,
        1 => format!("{} (once more since the last report)", body),
        n => format!("{} ({} more times since the last report)", body, n),
    }
}

/// Parent, grandparent... of `pid`, from /proc, up to (not including) init.
fn process_ancestry(pid: u32) -> Vec<u32> {
    let mut ancestors = Vec::new();
    let mut current = pid;
    // Bounded: a pid tree is never this deep, and /proc can change under us.
    for _ in 0..64 {
        let Ok(stat) = std::fs::read_to_string(format!("/proc/{current}/stat")) else {
            break;
        };
        match parent_from_stat(&stat) {
            Some(parent) if parent > 1 && parent != current => {
                ancestors.push(parent);
                current = parent;
            }
            _ => break,
        }
    }
    ancestors
}

/// The ppid field of /proc/<pid>/stat: `pid (comm) state ppid ...`, where
/// comm can itself contain spaces and parentheses - so parse after the
/// last `)`.
fn parent_from_stat(stat: &str) -> Option<u32> {
    let after_comm = &stat[stat.rfind(')')? + 1..];
    after_comm.split_whitespace().nth(1)?.parse().ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::CortexState;
    use chrono::Utc;
    use hive_common::actions::{Action, NotificationUrgency};
    use hive_common::config::Config;
    use hive_common::messages::ProcessInfo;
    use std::sync::Arc;
    use tokio::sync::{mpsc, RwLock};

    async fn new_state() -> SharedState {
        Arc::new(RwLock::new(CortexState::new(Config::default())))
    }

    /// Registers a fake component and returns its connection id and message receiver.
    async fn register(
        state: &SharedState,
        component_type: ComponentType,
    ) -> (u64, mpsc::Receiver<HiveMessage>) {
        let (tx, rx) = mpsc::channel(10);
        let conn_id = state
            .write()
            .await
            .register_component(component_type, tx, 1, 1000);
        (conn_id, rx)
    }

    fn process_info(pid: u32) -> ProcessInfo {
        ProcessInfo {
            pid,
            uid: 1000,
            name: "bash".to_string(),
            cmdline: vec!["bash".to_string()],
            cwd: None,
            ppid: None,
        }
    }

    #[tokio::test]
    async fn ping_gets_ponged_back_to_sender() {
        let state = new_state().await;
        let (conn_id, mut rx) = register(&state, ComponentType::Unknown).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::Ping {
                    timestamp: Utc::now(),
                },
                conn_id,
            )
            .await
            .unwrap();

        let reply = rx.recv().await.expect("expected a reply");
        assert_eq!(reply.type_name(), "Pong");
    }

    #[tokio::test]
    async fn command_observed_forwards_to_synapse_as_suggestion_request() {
        let state = new_state().await;
        let (synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveProcess).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::CommandObserved {
                    process: process_info(4242),
                    cmd: "rm -rf /".to_string(),
                    timestamp: Utc::now(),
                },
                nerve_conn,
            )
            .await
            .unwrap();

        let forwarded = synapse_rx
            .recv()
            .await
            .expect("synapse should receive a request");
        assert_eq!(forwarded.type_name(), "SuggestionRequest");
        assert_ne!(synapse_conn, nerve_conn);
    }

    #[tokio::test]
    async fn command_observed_skipped_for_anonymous_process() {
        let state = new_state().await;
        let (_synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveProcess).await;

        let anonymous_pid = 9999;
        {
            let mut guard = state.write().await;
            guard.anonymous.add_session(AnonymousSession::for_process(
                hive_common::messages::AnonymousLevel::Detach,
                anonymous_pid,
            ));
        }

        let router = MessageRouter::new(state);
        router
            .route(
                HiveMessage::CommandObserved {
                    process: process_info(anonymous_pid),
                    cmd: "ls".to_string(),
                    timestamp: Utc::now(),
                },
                nerve_conn,
            )
            .await
            .unwrap();

        // Give a misbehaving forward a moment to land before asserting silence.
        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        assert!(
            synapse_rx.try_recv().is_err(),
            "anonymous process's command should not reach synapse"
        );
    }

    #[tokio::test]
    async fn port_conflict_notifies_dashboard_and_forwards_to_synapse() {
        let state = new_state().await;
        let (_synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveNetwork).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::PortConflict {
                    port: 8080,
                    requested_by: process_info(1),
                    held_by: process_info(2),
                },
                nerve_conn,
            )
            .await
            .unwrap();

        assert_eq!(
            synapse_rx
                .recv()
                .await
                .expect("synapse notified")
                .type_name(),
            "SuggestionRequest"
        );
        match dashboard_rx.recv().await.expect("dashboard notified") {
            HiveMessage::Notification { body, .. } => {
                // Says who failed and who holds the port, not just the number.
                assert_eq!(body, "bash could not bind port 8080: already held by bash");
            }
            other => panic!("expected Notification, got {}", other.type_name()),
        }
    }

    fn crash(service: &str) -> HiveMessage {
        HiveMessage::ServiceCrash {
            service: service.to_string(),
            exit_code: 1,
            restart_count: 0,
            logs: vec![],
        }
    }

    /// The body of the next Notification, None when nothing more arrived.
    async fn next_notice(rx: &mut mpsc::Receiver<HiveMessage>) -> Option<String> {
        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        match rx.try_recv().ok()? {
            HiveMessage::Notification { body, .. } => Some(body),
            other => panic!("expected Notification, got {}", other.type_name()),
        }
    }

    #[tokio::test]
    async fn a_crash_loop_is_reported_once_until_the_interval_passes_then_with_what_was_held() {
        // Found in the VM lab: a unit with Restart=on-failure crashed every
        // second, and every crash reached the model and stacked "Service
        // Crashed" and its offers on the dashboard again.
        let state = new_state().await;
        let (_synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveJournal).await;
        let router = MessageRouter::new(state.clone());

        for _ in 0..3 {
            router
                .route(crash("nginx.service"), nerve_conn)
                .await
                .unwrap();
        }
        assert_eq!(
            next_notice(&mut dashboard_rx).await.as_deref(),
            Some("nginx.service exited with code 1")
        );
        assert_eq!(next_notice(&mut dashboard_rx).await, None, "held");
        assert!(synapse_rx.try_recv().is_ok());
        assert!(synapse_rx.try_recv().is_err(), "the model is asked once");

        // another service's crash is news
        router
            .route(crash("postgresql.service"), nerve_conn)
            .await
            .unwrap();
        assert_eq!(
            next_notice(&mut dashboard_rx).await.as_deref(),
            Some("postgresql.service exited with code 1")
        );

        // once the interval has passed, the loop is reported again, with
        // how many crashes were held
        state.write().await.problem_report_interval = std::time::Duration::ZERO;
        router
            .route(crash("nginx.service"), nerve_conn)
            .await
            .unwrap();
        assert_eq!(
            next_notice(&mut dashboard_rx).await.as_deref(),
            Some("nginx.service exited with code 1 (2 more times since the last report)")
        );
    }

    fn sample_suggestion(id: u32, action: Option<Action>) -> Suggestion {
        Suggestion {
            id,
            title: format!("Suggestion {}", id),
            description: "A test suggestion".to_string(),
            action,
            learn_more: None,
            confidence: 0.9,
        }
    }

    #[tokio::test]
    async fn suggestion_response_stores_and_notifies_dashboard() {
        let state = new_state().await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (synapse_conn, _synapse_rx) = register(&state, ComponentType::Synapse).await;
        let router = MessageRouter::new(state.clone());

        let suggestions = vec![sample_suggestion(1, None)];
        router
            .route(
                HiveMessage::SuggestionResponse {
                    request_id: Uuid::new_v4(),
                    suggestions: suggestions.clone(),
                    processing_time_ms: 10,
                },
                synapse_conn,
            )
            .await
            .unwrap();

        let notification = dashboard_rx
            .recv()
            .await
            .expect("dashboard should be notified");
        match notification {
            HiveMessage::Notification { actions, .. } => {
                assert_eq!(actions.len(), 1);
                assert_eq!(actions[0].id, 1);
            }
            other => panic!("expected Notification, got {}", other.type_name()),
        }

        assert_eq!(state.read().await.pending_suggestions.len(), 1);
    }

    #[tokio::test]
    async fn every_dashboard_is_offered_a_suggestion_and_the_first_approval_takes_it() {
        // Two administrators each with a dashboard open: both are told, and
        // an action approved in one is not run again when the other approves.
        let state = new_state().await;
        let (first_conn, mut first_rx) = register(&state, ComponentType::Dashboard).await;
        let (second_conn, mut second_rx) = register(&state, ComponentType::Dashboard).await;
        let (synapse_conn, _synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let router = MessageRouter::new(state.clone());

        let restart = Action::RestartService {
            name: "nginx".to_string(),
        };
        router
            .route(
                HiveMessage::SuggestionResponse {
                    request_id: Uuid::new_v4(),
                    suggestions: vec![sample_suggestion(1, Some(restart))],
                    processing_time_ms: 10,
                },
                synapse_conn,
            )
            .await
            .unwrap();

        let mut ids = Vec::new();
        for rx in [&mut first_rx, &mut second_rx] {
            let offer = tokio::time::timeout(tokio::time::Duration::from_secs(1), rx.recv()).await;
            match offer.ok().flatten().expect("each dashboard is offered it") {
                HiveMessage::Notification { id, actions, .. } => {
                    assert_eq!(actions.len(), 1);
                    ids.push(id);
                }
                other => panic!("expected Notification, got {}", other.type_name()),
            }
        }
        assert_eq!(ids[0], ids[1], "the same offer");

        for conn in [first_conn, second_conn] {
            router
                .route(
                    HiveMessage::UserAction {
                        notification_id: ids[0],
                        suggestion_id: 1,
                        confirmed: false,
                    },
                    conn,
                )
                .await
                .unwrap();
        }
        assert!(matches!(
            actuator_rx.recv().await,
            Some(HiveMessage::ActionRequest { .. })
        ));
        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        assert!(actuator_rx.try_recv().is_err(), "approved twice, run once");
    }

    #[tokio::test]
    async fn suggestion_response_from_a_non_synapse_connection_is_rejected() {
        // Only hive-synapse's real connection may originate suggestions —
        // otherwise any connected component could get an Action dispatched
        // to hive-actuator via act_on_suggestion just by claiming to have
        // a suggestion for the user to approve.
        let state = new_state().await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (impostor_conn, _impostor_rx) = register(&state, ComponentType::Unknown).await;
        let router = MessageRouter::new(state.clone());

        router
            .route(
                HiveMessage::SuggestionResponse {
                    request_id: Uuid::new_v4(),
                    suggestions: vec![sample_suggestion(1, None)],
                    processing_time_ms: 10,
                },
                impostor_conn,
            )
            .await
            .unwrap();

        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        assert!(
            dashboard_rx.try_recv().is_err(),
            "dashboard should not have been notified of a suggestion from a non-Synapse sender"
        );
        assert!(state.read().await.pending_suggestions.is_empty());
    }

    fn notification_with_actions(actions: Vec<Suggestion>) -> HiveMessage {
        HiveMessage::Notification {
            id: Uuid::new_v4(),
            title: "Filesystem Event".to_string(),
            body: "Config file modified: /etc/hosts".to_string(),
            severity: Severity::Notice,
            actions,
            timeout_secs: 10,
        }
    }

    #[tokio::test]
    async fn notification_from_a_nerve_reaches_the_dashboard_without_actions() {
        // hive-nerve-fs reports filesystem events as plain Notifications;
        // they used to fall through to "Unhandled message type" and vanish.
        // Any `actions` a sender attaches are dropped, so a nerve can't
        // plant actionable suggestions that bypass hive-synapse.
        let state = new_state().await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveFs).await;
        let router = MessageRouter::new(state.clone());

        router
            .route(
                notification_with_actions(vec![sample_suggestion(1, None)]),
                nerve_conn,
            )
            .await
            .unwrap();

        match dashboard_rx
            .recv()
            .await
            .expect("dashboard should be notified")
        {
            HiveMessage::Notification {
                title,
                body,
                actions,
                ..
            } => {
                assert_eq!(title, "Filesystem Event");
                assert_eq!(body, "Config file modified: /etc/hosts");
                assert!(
                    actions.is_empty(),
                    "sender-supplied actions must be dropped"
                );
            }
            other => panic!("expected Notification, got {}", other.type_name()),
        }
        assert!(state.read().await.pending_suggestions.is_empty());
    }

    #[tokio::test]
    async fn notification_from_a_non_nerve_connection_is_rejected() {
        let state = new_state().await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (impostor_conn, _impostor_rx) = register(&state, ComponentType::Unknown).await;
        let router = MessageRouter::new(state);

        router
            .route(notification_with_actions(vec![]), impostor_conn)
            .await
            .unwrap();

        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        assert!(
            dashboard_rx.try_recv().is_err(),
            "dashboard should not relay notifications from non-nerve senders"
        );
    }

    #[tokio::test]
    async fn user_action_forwards_to_actuator_for_non_dangerous_suggestion() {
        let state = new_state().await;
        let (dashboard_conn, _dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let notification_id = Uuid::new_v4();
        let action = Action::ShowNotification {
            title: "hi".into(),
            body: "hi".into(),
            urgency: NotificationUrgency::Normal,
            actions: vec![],
            icon: None,
        };
        state
            .write()
            .await
            .pending_suggestions
            .insert(notification_id, vec![sample_suggestion(7, Some(action))]);

        let router = MessageRouter::new(state.clone());
        router
            .route(
                HiveMessage::UserAction {
                    notification_id,
                    suggestion_id: 7,
                    confirmed: false,
                },
                dashboard_conn,
            )
            .await
            .unwrap();

        let forwarded = actuator_rx
            .recv()
            .await
            .expect("actuator should receive the dispatched action");
        match forwarded {
            HiveMessage::ActionRequest {
                requires_confirmation,
                ..
            } => assert!(!requires_confirmation),
            other => panic!("expected ActionRequest, got {}", other.type_name()),
        }
        assert!(
            !state
                .read()
                .await
                .pending_suggestions
                .contains_key(&notification_id),
            "acted-on suggestion should be cleared"
        );
    }

    #[tokio::test]
    async fn user_action_marks_dangerous_suggestion_as_requiring_confirmation() {
        let state = new_state().await;
        let (dashboard_conn, _dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let notification_id = Uuid::new_v4();
        let action = Action::RemovePackage {
            name: "nginx".into(),
            purge: false,
        };
        state
            .write()
            .await
            .pending_suggestions
            .insert(notification_id, vec![sample_suggestion(1, Some(action))]);

        let router = MessageRouter::new(state);
        router
            .route(
                HiveMessage::UserAction {
                    notification_id,
                    suggestion_id: 1,
                    confirmed: false,
                },
                dashboard_conn,
            )
            .await
            .unwrap();

        let forwarded = actuator_rx
            .recv()
            .await
            .expect("actuator should receive it");
        match forwarded {
            HiveMessage::ActionRequest {
                requires_confirmation,
                ..
            } => assert!(
                requires_confirmation,
                "RemovePackage is dangerous and unconfirmed, should still require confirmation"
            ),
            other => panic!("expected ActionRequest, got {}", other.type_name()),
        }
    }

    #[tokio::test]
    async fn user_action_confirmed_bypasses_requires_confirmation_for_dangerous_suggestion() {
        let state = new_state().await;
        let (dashboard_conn, _dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let notification_id = Uuid::new_v4();
        let action = Action::RemovePackage {
            name: "nginx".into(),
            purge: false,
        };
        state
            .write()
            .await
            .pending_suggestions
            .insert(notification_id, vec![sample_suggestion(1, Some(action))]);

        let router = MessageRouter::new(state);
        router
            .route(
                HiveMessage::UserAction {
                    notification_id,
                    suggestion_id: 1,
                    confirmed: true,
                },
                dashboard_conn,
            )
            .await
            .unwrap();

        let forwarded = actuator_rx
            .recv()
            .await
            .expect("actuator should receive it");
        match forwarded {
            HiveMessage::ActionRequest {
                requires_confirmation,
                ..
            } => assert!(
                !requires_confirmation,
                "an already-confirmed dangerous action should not be flagged as still requiring confirmation"
            ),
            other => panic!("expected ActionRequest, got {}", other.type_name()),
        }
    }

    #[tokio::test]
    async fn user_action_with_unknown_notification_id_is_a_noop() {
        let state = new_state().await;
        let (dashboard_conn, _dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::UserAction {
                    notification_id: Uuid::new_v4(),
                    suggestion_id: 1,
                    confirmed: false,
                },
                dashboard_conn,
            )
            .await
            .unwrap();

        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        assert!(actuator_rx.try_recv().is_err());
    }

    #[tokio::test]
    async fn user_dismiss_clears_pending_suggestion() {
        let state = new_state().await;
        let (dashboard_conn, _dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let notification_id = Uuid::new_v4();
        state
            .write()
            .await
            .pending_suggestions
            .insert(notification_id, vec![sample_suggestion(1, None)]);

        let router = MessageRouter::new(state.clone());
        router
            .route(HiveMessage::UserDismiss { notification_id }, dashboard_conn)
            .await
            .unwrap();

        assert!(!state
            .read()
            .await
            .pending_suggestions
            .contains_key(&notification_id));
    }

    #[tokio::test]
    async fn action_request_from_an_external_connection_is_rejected() {
        // No component should be able to make cortex forward an
        // ActionRequest just by sending one in — see the comment on the
        // ActionRequest arm in `route()`.
        let state = new_state().await;
        let (requester_conn, _requester_rx) = register(&state, ComponentType::Synapse).await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::ActionRequest {
                    request_id: Uuid::new_v4(),
                    action: Action::ShowNotification {
                        title: "test".to_string(),
                        body: "test".to_string(),
                        urgency: NotificationUrgency::Normal,
                        actions: vec![],
                        icon: None,
                    },
                    requires_confirmation: false,
                    timeout_secs: 0,
                },
                requester_conn,
            )
            .await
            .unwrap();

        tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
        assert!(
            actuator_rx.try_recv().is_err(),
            "actuator should never receive an externally-injected ActionRequest"
        );
    }

    #[tokio::test]
    async fn action_response_routes_back_to_the_original_requester() {
        // pending_requests is normally populated by cortex's own internal
        // action-dispatch path (not built yet — see the ActionRequest arm
        // in `route()`); seed it directly here to test forward_to_requester
        // in isolation from that still-missing piece.
        let state = new_state().await;
        let (requester_conn, mut requester_rx) = register(&state, ComponentType::Synapse).await;
        let (actuator_conn, _actuator_rx) = register(&state, ComponentType::Actuator).await;
        let request_id = Uuid::new_v4();
        state
            .write()
            .await
            .pending_requests
            .insert(request_id, requester_conn);

        let router = MessageRouter::new(state);
        router
            .route(
                HiveMessage::ActionResponse {
                    request_id,
                    action: Action::ShowNotification {
                        title: "test".to_string(),
                        body: "test".to_string(),
                        urgency: NotificationUrgency::Normal,
                        actions: vec![],
                        icon: None,
                    },
                    success: true,
                    output: None,
                    exit_code: None,
                },
                actuator_conn,
            )
            .await
            .unwrap();

        let reply = requester_rx
            .recv()
            .await
            .expect("original requester should get the response");
        assert_eq!(reply.type_name(), "ActionResponse");
    }

    async fn register_shell(state: &SharedState, pid: i32) -> (u64, mpsc::Receiver<HiveMessage>) {
        let (tx, rx) = mpsc::channel(10);
        let conn_id = state
            .write()
            .await
            .register_component(ComponentType::Shell, tx, pid, 1000);
        (conn_id, rx)
    }

    #[tokio::test]
    async fn a_question_is_answered_to_the_asking_shell_only_as_text() {
        let state = new_state().await;
        let (synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (_dashboard_conn, mut dashboard_rx) = register(&state, ComponentType::Dashboard).await;
        let (asker, mut asker_rx) = register_shell(&state, 500).await;
        let (_other, mut other_rx) = register_shell(&state, 501).await;
        let router = MessageRouter::new(state);

        let asker_id = Uuid::new_v4();
        router
            .route(
                HiveMessage::UserQuery {
                    request_id: asker_id,
                    query: "why did nginx fail".into(),
                    cwd: Some("/etc".into()),
                },
                asker,
            )
            .await
            .unwrap();

        let synapse_id = match synapse_rx.recv().await.expect("synapse asked") {
            HiveMessage::SuggestionRequest {
                request_id,
                user_query,
                context,
                ..
            } => {
                assert_eq!(user_query.as_deref(), Some("why did nginx fail"));
                assert_eq!(context.cwd.as_deref(), Some(std::path::Path::new("/etc")));
                assert!(context.trigger.is_none());
                // Cortex's own id, not the one the asker picked.
                assert_ne!(request_id, asker_id);
                request_id
            }
            other => panic!("expected SuggestionRequest, got {}", other.type_name()),
        };

        let action = Action::RestartService {
            name: "nginx".into(),
        };
        router
            .route(
                HiveMessage::SuggestionResponse {
                    request_id: synapse_id,
                    suggestions: vec![sample_suggestion(1, Some(action))],
                    processing_time_ms: 10,
                },
                synapse_conn,
            )
            .await
            .unwrap();

        match asker_rx.recv().await.expect("asker answered") {
            HiveMessage::SuggestionResponse {
                request_id,
                suggestions,
                ..
            } => {
                assert_eq!(request_id, asker_id);
                assert_eq!(suggestions.len(), 1);
                assert!(
                    suggestions[0].action.is_none(),
                    "answers are never executable"
                );
            }
            other => panic!("expected SuggestionResponse, got {}", other.type_name()),
        }
        assert!(other_rx.try_recv().is_err(), "another shell saw the answer");
        assert!(
            dashboard_rx.try_recv().is_err(),
            "the dashboard saw the answer"
        );
    }

    #[tokio::test]
    async fn only_shells_ask_questions() {
        let state = new_state().await;
        let (_synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (unknown, _rx) = register(&state, ComponentType::Unknown).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::UserQuery {
                    request_id: Uuid::new_v4(),
                    query: "hi".into(),
                    cwd: None,
                },
                unknown,
            )
            .await
            .unwrap();
        assert!(synapse_rx.try_recv().is_err());
    }

    #[tokio::test]
    async fn a_shell_can_make_only_itself_anonymous() {
        use hive_common::messages::AnonymousLevel;

        let state = new_state().await;
        let (shell, _rx) = register_shell(&state, 700).await;
        let (dashboard, _drx) = register(&state, ComponentType::Dashboard).await;
        let router = MessageRouter::new(state.clone());

        for (pid, conn) in [(Some(1), shell), (None, shell), (Some(700), dashboard)] {
            router
                .route(
                    HiveMessage::AnonymousModeEnter {
                        level: AnonymousLevel::Detach,
                        pid,
                    },
                    conn,
                )
                .await
                .unwrap();
        }
        assert_eq!(state.read().await.anonymous.session_count(), 0);

        router
            .route(
                HiveMessage::AnonymousModeEnter {
                    level: AnonymousLevel::Detach,
                    pid: Some(700),
                },
                shell,
            )
            .await
            .unwrap();
        assert!(state.read().await.anonymous.should_hide_process(700));

        router
            .route(HiveMessage::AnonymousModeExit { pid: Some(700) }, shell)
            .await
            .unwrap();
        assert_eq!(state.read().await.anonymous.session_count(), 0);
    }

    #[tokio::test]
    async fn commands_run_from_an_anonymous_shell_are_not_forwarded() {
        let state = new_state().await;
        let (_synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveProcess).await;
        // Pids above the kernel's pid_max, so /proc ancestry plays no part
        // here: the command's own ppid is the anonymous shell.
        let shell_pid = 5_000_000;
        state
            .write()
            .await
            .anonymous
            .add_session(AnonymousSession::for_process(
                hive_common::messages::AnonymousLevel::Detach,
                shell_pid,
            ));
        let router = MessageRouter::new(state);

        let observed = |ppid| HiveMessage::CommandObserved {
            process: ProcessInfo {
                ppid,
                ..process_info(5_000_002)
            },
            cmd: "rm -rf /etc/x".to_string(),
            timestamp: Utc::now(),
        };
        router
            .route(observed(Some(shell_pid)), nerve_conn)
            .await
            .unwrap();
        assert!(
            synapse_rx.try_recv().is_err(),
            "a child of the anonymous shell was forwarded"
        );

        router
            .route(observed(Some(5_000_001)), nerve_conn)
            .await
            .unwrap();
        assert!(
            synapse_rx.try_recv().is_ok(),
            "an unrelated command was hidden"
        );
    }

    #[tokio::test]
    async fn shells_get_system_notices() {
        let state = new_state().await;
        let (_synapse_conn, _synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (nerve_conn, _nerve_rx) = register(&state, ComponentType::NerveJournal).await;
        let (_a, mut a_rx) = register_shell(&state, 10).await;
        let (_b, mut b_rx) = register_shell(&state, 11).await;
        let router = MessageRouter::new(state);

        router
            .route(
                HiveMessage::ServiceCrash {
                    service: "nginx.service".into(),
                    exit_code: 1,
                    restart_count: 0,
                    logs: vec![],
                },
                nerve_conn,
            )
            .await
            .unwrap();

        for rx in [&mut a_rx, &mut b_rx] {
            match rx.try_recv().expect("shell notified") {
                HiveMessage::Notification {
                    title,
                    body,
                    actions,
                    ..
                } => {
                    assert_eq!(title, "Service Crashed");
                    assert!(body.contains("nginx.service"));
                    assert!(actions.is_empty());
                }
                other => panic!("expected Notification, got {}", other.type_name()),
            }
        }
    }

    #[tokio::test]
    async fn a_missing_program_is_offered_once_and_only_from_shells() {
        let state = new_state().await;
        let (_synapse_conn, mut synapse_rx) = register(&state, ComponentType::Synapse).await;
        let (shell, _shell_rx) = register_shell(&state, 800).await;
        let (unknown, _unknown_rx) = register(&state, ComponentType::Unknown).await;
        let router = MessageRouter::new(state);
        let missing = |package: &str| HiveMessage::CommandNotFound {
            command: "htop".into(),
            package: package.into(),
        };

        router.route(missing("htop"), unknown).await.unwrap();
        router
            .route(missing("--allow-downgrades"), shell)
            .await
            .unwrap();
        assert!(synapse_rx.try_recv().is_err());

        router.route(missing("htop"), shell).await.unwrap();
        match synapse_rx.try_recv().expect("offered") {
            HiveMessage::SuggestionRequest { context, .. } => assert!(matches!(
                context.trigger.as_deref(),
                Some(HiveMessage::CommandNotFound { package, .. }) if package == "htop"
            )),
            other => panic!("expected SuggestionRequest, got {}", other.type_name()),
        }
        router.route(missing("htop"), shell).await.unwrap();
        assert!(synapse_rx.try_recv().is_err(), "offered twice in a row");
    }

    #[tokio::test]
    async fn only_dashboards_approve_suggestions() {
        let state = new_state().await;
        let (_actuator_conn, mut actuator_rx) = register(&state, ComponentType::Actuator).await;
        let (shell, _shell_rx) = register_shell(&state, 900).await;
        let notification_id = Uuid::new_v4();
        state.write().await.pending_suggestions.insert(
            notification_id,
            vec![sample_suggestion(
                1,
                Some(Action::RestartService {
                    name: "nginx".into(),
                }),
            )],
        );
        let router = MessageRouter::new(state.clone());

        router
            .route(
                HiveMessage::UserAction {
                    notification_id,
                    suggestion_id: 1,
                    confirmed: true,
                },
                shell,
            )
            .await
            .unwrap();
        assert!(actuator_rx.try_recv().is_err());
        assert!(state
            .read()
            .await
            .pending_suggestions
            .contains_key(&notification_id));
    }

    #[test]
    fn parent_pid_is_read_past_a_comm_with_spaces_and_parens() {
        assert_eq!(
            parent_from_stat("1234 (bash) S 1200 1234 1234 0"),
            Some(1200)
        );
        assert_eq!(parent_from_stat("99 (my (odd) prog) R 42 99 99"), Some(42));
        assert_eq!(parent_from_stat("garbage"), None);
    }
}
