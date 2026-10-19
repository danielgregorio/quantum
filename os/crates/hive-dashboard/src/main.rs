//! Hive Dashboard - Interactive TUI panel for notifications and suggestions
//!
//! The user-run replacement for the archived hive-shell GUI overlay. An
//! interactive terminal tool (run manually in a terminal/pane, like `top` —
//! no systemd service) that connects to hive-cortex's user socket; cortex
//! only lets an administrator's dashboard in (root, or sudo/admin/wheel).
//!
//! Each suggestion inside a Notification becomes its own row; approving one
//! sends `HiveMessage::UserAction` back to cortex, which dispatches the
//! associated `Action` to hive-actuator on the user's behalf.

use anyhow::{Context, Result};
use crossterm::event::{Event, EventStream, KeyCode, KeyEventKind};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use futures::StreamExt;
use hive_common::actions::Action;
use hive_common::ipc::{IpcError, IpcSocket};
use hive_common::messages::{HiveMessage, Severity, Suggestion};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap};
use ratatui::{Frame, Terminal};
use std::io::stdout;
use uuid::Uuid;

/// How long to wait for cortex to accept the connection before giving up.
const HANDSHAKE_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(5);

/// What happened after the user approved a suggestion.
#[derive(Debug, Clone, PartialEq)]
enum Outcome {
    /// No Action attached to the suggestion — nothing to wait for.
    NoAction,
    /// Sent to cortex; waiting for the matching ActionResponse.
    Sent(Action),
    Succeeded(Option<String>),
    Failed(Option<String>),
}

/// One line in the dashboard's list. A Notification with N suggestions
/// becomes N rows (sharing `notification_id`); one with none becomes a
/// single informational row.
#[derive(Debug, Clone)]
struct Row {
    notification_id: Uuid,
    title: String,
    body: String,
    severity: Severity,
    suggestion: Option<Suggestion>,
    outcome: Option<Outcome>,
}

/// Whether `row` is the suggestion waiting for its second Enter. A row
/// with no suggestion never is, even when nothing is waiting.
fn is_armed(armed: Option<(Uuid, u32)>, row: &Row) -> bool {
    match (armed, &row.suggestion) {
        (Some(waiting), Some(s)) => waiting == (row.notification_id, s.id),
        _ => false,
    }
}

/// Expands an incoming Notification into the rows it contributes.
fn notification_to_rows(
    notification_id: Uuid,
    title: &str,
    body: &str,
    severity: Severity,
    suggestions: Vec<Suggestion>,
) -> Vec<Row> {
    if suggestions.is_empty() {
        vec![Row {
            notification_id,
            title: title.to_string(),
            body: body.to_string(),
            severity,
            suggestion: None,
            outcome: None,
        }]
    } else {
        suggestions
            .into_iter()
            .map(|s| Row {
                notification_id,
                title: title.to_string(),
                body: body.to_string(),
                severity,
                suggestion: Some(s),
                outcome: None,
            })
            .collect()
    }
}

/// Removes every row belonging to a dismissed (or fully handled) notification.
fn dismiss_notification(rows: &mut Vec<Row>, notification_id: Uuid) {
    rows.retain(|r| r.notification_id != notification_id);
}

/// Matches an incoming ActionResponse to whichever row is waiting on that
/// exact Action, and updates its outcome. Returns whether a match was
/// found. If two identical Actions are in flight at once this matches the
/// first — an accepted approximation given the protocol doesn't echo back
/// notification/suggestion ids on ActionResponse (see hive-cortex's
/// act_on_suggestion).
fn apply_action_response(
    rows: &mut [Row],
    action: &Action,
    success: bool,
    output: Option<String>,
) -> bool {
    for row in rows.iter_mut() {
        if matches!(&row.outcome, Some(Outcome::Sent(pending)) if pending == action) {
            row.outcome = Some(if success {
                Outcome::Succeeded(output)
            } else {
                Outcome::Failed(output)
            });
            return true;
        }
    }
    false
}

/// Keeps the selection in bounds as the list grows/shrinks, wrapping
/// around at either end.
fn move_selection(state: &mut ListState, len: usize, delta: i32) {
    if len == 0 {
        state.select(None);
        return;
    }
    let current = state.selected().unwrap_or(0) as i32;
    let new = current.rem_euclid(len as i32) + delta;
    state.select(Some(new.rem_euclid(len as i32) as usize));
}

enum KeyAction {
    Quit,
    MoveUp,
    MoveDown,
    Approve,
    Dismiss,
    None,
}

/// What pressing Approve should do, given whether this exact suggestion is
/// already "armed" from a previous press.
#[derive(Debug, PartialEq)]
enum ApprovalDecision {
    /// Not dangerous, or already confirmed once — send UserAction now.
    Send { confirmed: bool },
    /// Dangerous and not yet armed — don't send anything, just mark this
    /// suggestion as awaiting a second press.
    Arm,
}

/// Dangerous actions need a second, explicit Enter press before
/// hive-dashboard will send `UserAction{confirmed: true}` — a single
/// keypress is treated as consent for a routine suggestion but not for one
/// hive-actuator would otherwise reject outright (see
/// `Action::is_dangerous`). `armed` identifies whichever (notification,
/// suggestion) pair was armed by the previous press, if any.
fn decide_approval(
    armed: Option<(Uuid, u32)>,
    notification_id: Uuid,
    suggestion: &Suggestion,
) -> ApprovalDecision {
    let dangerous = suggestion.action.as_ref().is_some_and(|a| a.is_dangerous());
    if !dangerous {
        return ApprovalDecision::Send { confirmed: false };
    }
    if armed == Some((notification_id, suggestion.id)) {
        ApprovalDecision::Send { confirmed: true }
    } else {
        ApprovalDecision::Arm
    }
}

fn handle_key(code: KeyCode) -> KeyAction {
    match code {
        KeyCode::Char('q') | KeyCode::Char('Q') => KeyAction::Quit,
        KeyCode::Up | KeyCode::Char('k') => KeyAction::MoveUp,
        KeyCode::Down | KeyCode::Char('j') => KeyAction::MoveDown,
        KeyCode::Enter => KeyAction::Approve,
        KeyCode::Char('d') | KeyCode::Esc => KeyAction::Dismiss,
        _ => KeyAction::None,
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    hive_common::logging::init("hive_dashboard")?;

    let cortex_socket =
        std::env::var("HIVE_USER_SOCKET").unwrap_or_else(|_| hive_common::USER_SOCKET.to_string());
    let mut cortex = IpcSocket::connect(&cortex_socket).await.with_context(|| {
        format!(
            "Failed to connect to cortex at {} — is hive-cortex running?",
            cortex_socket
        )
    })?;
    // Before taking over the terminal: find out whether cortex let us in.
    handshake(&mut cortex).await?;

    enable_raw_mode()?;
    let mut out = stdout();
    execute!(out, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(out);
    let mut terminal = Terminal::new(backend)?;

    let result = run(&mut terminal, &mut cortex).await;

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    result
}

/// Ping cortex and wait for its Pong. Cortex closes the connection at once
/// on a user who isn't an administrator - say so plainly instead of drawing
/// an empty dashboard.
async fn handshake(cortex: &mut IpcSocket) -> Result<()> {
    cortex
        .send(&HiveMessage::Ping {
            timestamp: chrono::Utc::now(),
        })
        .await
        .context("Failed to reach hive-cortex")?;
    let reply = tokio::time::timeout(HANDSHAKE_TIMEOUT, async {
        loop {
            match cortex.recv().await {
                Ok(HiveMessage::Pong { .. }) => return Ok(()),
                Ok(_) => continue,
                Err(e) => return Err(e),
            }
        }
    })
    .await;
    match reply {
        Ok(Ok(())) => Ok(()),
        Ok(Err(IpcError::ConnectionClosed)) | Ok(Err(IpcError::Io(_))) => anyhow::bail!(
            "hive-cortex turned hive-dashboard away: approving the Hive's suggestions takes an \
             administrator (root, or a member of sudo, admin or wheel)"
        ),
        Ok(Err(e)) => Err(e).context("Failed to talk to hive-cortex"),
        Err(_) => anyhow::bail!("hive-cortex did not answer within {:?}", HANDSHAKE_TIMEOUT),
    }
}

async fn run<B: ratatui::backend::Backend>(
    terminal: &mut Terminal<B>,
    cortex: &mut IpcSocket,
) -> Result<()> {
    let mut rows: Vec<Row> = Vec::new();
    let mut list_state = ListState::default();
    let mut events = EventStream::new();
    let mut status = "Connected. Waiting for Hive activity...".to_string();
    // (notification_id, suggestion_id) awaiting a second Enter press to
    // confirm a dangerous action — see `decide_approval`.
    let mut armed: Option<(Uuid, u32)> = None;

    loop {
        terminal.draw(|f| render(f, &rows, &mut list_state, &status, armed))?;

        tokio::select! {
            maybe_event = events.next() => {
                let Some(Ok(Event::Key(key))) = maybe_event else { continue };
                if key.kind != KeyEventKind::Press {
                    continue;
                }
                match handle_key(key.code) {
                    KeyAction::Quit => return Ok(()),
                    KeyAction::MoveUp => {
                        move_selection(&mut list_state, rows.len(), -1);
                        armed = None;
                    }
                    KeyAction::MoveDown => {
                        move_selection(&mut list_state, rows.len(), 1);
                        armed = None;
                    }
                    KeyAction::Approve => {
                        // Extract plain owned values before the .await —
                        // avoid holding a Vec borrow across an await point.
                        let approval = list_state.selected().and_then(|i| rows.get(i)).map(|row| {
                            (
                                row.notification_id,
                                row.title.clone(),
                                row.suggestion.clone(),
                            )
                        });
                        match approval {
                            Some((notification_id, title, Some(suggestion))) => {
                                match decide_approval(armed, notification_id, &suggestion) {
                                    ApprovalDecision::Arm => {
                                        armed = Some((notification_id, suggestion.id));
                                        status = format!(
                                            "'{}' is dangerous — press Enter again to confirm, Esc to cancel",
                                            suggestion.title
                                        );
                                    }
                                    ApprovalDecision::Send { confirmed } => {
                                        let _ = cortex
                                            .send(&HiveMessage::UserAction {
                                                notification_id,
                                                suggestion_id: suggestion.id,
                                                confirmed,
                                            })
                                            .await;
                                        if let Some(row) = list_state
                                            .selected()
                                            .and_then(|i| rows.get_mut(i))
                                        {
                                            row.outcome = Some(match suggestion.action {
                                                Some(a) => Outcome::Sent(a),
                                                None => Outcome::NoAction,
                                            });
                                        }
                                        armed = None;
                                        status = format!("Approved: {}", title);
                                    }
                                }
                            }
                            Some((_, _, None)) => {
                                status = "This alert has no action to approve.".to_string();
                            }
                            None => {}
                        }
                    }
                    KeyAction::Dismiss => {
                        if let Some(i) = list_state.selected() {
                            if let Some(row) = rows.get(i) {
                                let notification_id = row.notification_id;
                                let is_armed = armed
                                    == row.suggestion.as_ref().map(|s| (notification_id, s.id));
                                if is_armed {
                                    armed = None;
                                    status = "Confirmation cancelled.".to_string();
                                } else {
                                    let _ = cortex
                                        .send(&HiveMessage::UserDismiss { notification_id })
                                        .await;
                                    dismiss_notification(&mut rows, notification_id);
                                    armed = None;
                                    status = "Dismissed.".to_string();
                                }
                            }
                        }
                    }
                    KeyAction::None => {}
                }
            }
            msg = cortex.recv() => {
                match msg {
                    Ok(HiveMessage::Notification { id, title, body, severity, actions, .. }) => {
                        rows.extend(notification_to_rows(id, &title, &body, severity, actions));
                        if list_state.selected().is_none() && !rows.is_empty() {
                            list_state.select(Some(0));
                        }
                    }
                    Ok(HiveMessage::ActionResponse { action, success, output, .. }) => {
                        let found = apply_action_response(&mut rows, &action, success, output);
                        if !found {
                            tracing::debug!("ActionResponse with no matching pending row");
                        }
                    }
                    Ok(_) => {}
                    Err(IpcError::ConnectionClosed) => {
                        status = "Connection to cortex closed.".to_string();
                        terminal.draw(|f| render(f, &rows, &mut list_state, &status, armed))?;
                        return Ok(());
                    }
                    Err(e) => {
                        tracing::warn!("Error receiving from cortex: {}", e);
                    }
                }
            }
        }
    }
}

fn severity_style(severity: Severity) -> Style {
    match severity {
        Severity::Critical | Severity::Error => Style::default().fg(Color::Red),
        Severity::Warning => Style::default().fg(Color::Yellow),
        Severity::Notice | Severity::Info => Style::default().fg(Color::Cyan),
    }
}

fn outcome_label(outcome: &Option<Outcome>) -> &'static str {
    match outcome {
        None => "",
        Some(Outcome::NoAction) => " (acknowledged)",
        Some(Outcome::Sent(_)) => " (pending...)",
        Some(Outcome::Succeeded(_)) => " (done)",
        Some(Outcome::Failed(_)) => " (failed)",
    }
}

fn render(
    f: &mut Frame,
    rows: &[Row],
    list_state: &mut ListState,
    status: &str,
    armed: Option<(Uuid, u32)>,
) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(3), Constraint::Length(1)])
        .split(f.area());

    let panes = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(45), Constraint::Percentage(55)])
        .split(chunks[0]);

    render_list(f, panes[0], rows, list_state, armed);
    render_detail(f, panes[1], rows, list_state.selected());

    let status_line = Paragraph::new(format!(
        " {} | \u{2191}/\u{2193} navigate  Enter approve  d/Esc dismiss  q quit",
        status
    ))
    .style(Style::default().fg(Color::DarkGray));
    f.render_widget(status_line, chunks[1]);
}

fn render_list(
    f: &mut Frame,
    area: Rect,
    rows: &[Row],
    list_state: &mut ListState,
    armed: Option<(Uuid, u32)>,
) {
    let items: Vec<ListItem> = if rows.is_empty() {
        vec![ListItem::new("  (nothing yet)")]
    } else {
        rows.iter()
            .map(|r| {
                let label = match &r.suggestion {
                    Some(s) => format!("{} \u{2014} {}", r.title, s.title),
                    None => r.title.clone(),
                };
                let is_armed = is_armed(armed, r);
                let suffix = if is_armed {
                    " (CONFIRM? press Enter again)".to_string()
                } else {
                    outcome_label(&r.outcome).to_string()
                };
                let style = if is_armed {
                    Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)
                } else {
                    severity_style(r.severity)
                };
                ListItem::new(Line::from(vec![Span::styled(
                    format!("{}{}", label, suffix),
                    style,
                )]))
            })
            .collect()
    };

    let list = List::new(items)
        .block(
            Block::default()
                .title(" Hive Dashboard ")
                .borders(Borders::ALL),
        )
        .highlight_style(Style::default().add_modifier(Modifier::REVERSED));

    f.render_stateful_widget(list, area, list_state);
}

fn render_detail(f: &mut Frame, area: Rect, rows: &[Row], selected: Option<usize>) {
    let text = match selected.and_then(|i| rows.get(i)) {
        None => "Select a notification on the left.".to_string(),
        Some(row) => match &row.suggestion {
            Some(s) => format!(
                "{}\n\n{}\n\nConfidence: {:.0}%\n\n{}",
                row.body,
                s.description,
                s.confidence * 100.0,
                s.learn_more.as_deref().unwrap_or("")
            ),
            None => row.body.clone(),
        },
    };

    let paragraph = Paragraph::new(text)
        .wrap(Wrap { trim: true })
        .block(Block::default().title(" Detail ").borders(Borders::ALL));
    f.render_widget(paragraph, area);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_notice_without_a_suggestion_is_never_shown_as_awaiting_confirmation() {
        // nothing armed and no suggestion: None == None must not read as armed
        let notice = Row {
            notification_id: Uuid::new_v4(),
            title: "Service Crashed".into(),
            body: "nginx.service exited with code 1".into(),
            severity: Severity::Error,
            suggestion: None,
            outcome: None,
        };
        assert!(!is_armed(None, &notice));
        assert!(!is_armed(Some((notice.notification_id, 1)), &notice));
    }

    fn sample_suggestion(id: u32, action: Option<Action>) -> Suggestion {
        Suggestion {
            id,
            title: "Restart nginx".to_string(),
            description: "nginx failed health checks".to_string(),
            action,
            learn_more: None,
            confidence: 0.8,
        }
    }

    #[test]
    fn notification_with_no_suggestions_becomes_one_informational_row() {
        let rows =
            notification_to_rows(Uuid::new_v4(), "Crash", "details", Severity::Error, vec![]);
        assert_eq!(rows.len(), 1);
        assert!(rows[0].suggestion.is_none());
    }

    #[test]
    fn notification_with_suggestions_becomes_one_row_per_suggestion() {
        let suggestions = vec![sample_suggestion(1, None), sample_suggestion(2, None)];
        let id = Uuid::new_v4();
        let rows = notification_to_rows(
            id,
            "Port conflict",
            "details",
            Severity::Warning,
            suggestions,
        );
        assert_eq!(rows.len(), 2);
        assert!(rows.iter().all(|r| r.notification_id == id));
        assert_eq!(rows[0].suggestion.as_ref().unwrap().id, 1);
        assert_eq!(rows[1].suggestion.as_ref().unwrap().id, 2);
    }

    #[test]
    fn dismiss_removes_only_rows_for_that_notification() {
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        let mut rows =
            notification_to_rows(a, "A", "", Severity::Info, vec![sample_suggestion(1, None)]);
        rows.extend(notification_to_rows(
            b,
            "B",
            "",
            Severity::Info,
            vec![sample_suggestion(2, None)],
        ));

        dismiss_notification(&mut rows, a);

        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].notification_id, b);
    }

    #[test]
    fn action_response_updates_the_matching_sent_row() {
        let action = Action::RestartService {
            name: "nginx".into(),
        };
        let mut rows = notification_to_rows(
            Uuid::new_v4(),
            "Crash",
            "",
            Severity::Error,
            vec![sample_suggestion(1, Some(action.clone()))],
        );
        rows[0].outcome = Some(Outcome::Sent(action.clone()));

        let found = apply_action_response(&mut rows, &action, true, Some("restarted".into()));

        assert!(found);
        assert_eq!(
            rows[0].outcome,
            Some(Outcome::Succeeded(Some("restarted".into())))
        );
    }

    #[test]
    fn action_response_with_no_matching_row_is_reported_as_not_found() {
        let action = Action::RestartService {
            name: "nginx".into(),
        };
        let mut rows: Vec<Row> = Vec::new();
        assert!(!apply_action_response(&mut rows, &action, true, None));
    }

    #[test]
    fn move_selection_wraps_around_in_both_directions() {
        let mut state = ListState::default();
        state.select(Some(0));

        move_selection(&mut state, 3, -1);
        assert_eq!(state.selected(), Some(2));

        move_selection(&mut state, 3, 1);
        assert_eq!(state.selected(), Some(0));
    }

    #[test]
    fn move_selection_on_empty_list_selects_nothing() {
        let mut state = ListState::default();
        move_selection(&mut state, 0, 1);
        assert_eq!(state.selected(), None);
    }

    #[test]
    fn decide_approval_sends_immediately_for_non_dangerous_action() {
        let notification_id = Uuid::new_v4();
        let suggestion = sample_suggestion(
            1,
            Some(Action::RestartService {
                name: "nginx".into(),
            }),
        );
        assert_eq!(
            decide_approval(None, notification_id, &suggestion),
            ApprovalDecision::Send { confirmed: false }
        );
    }

    #[test]
    fn decide_approval_sends_immediately_when_suggestion_has_no_action() {
        let notification_id = Uuid::new_v4();
        let suggestion = sample_suggestion(1, None);
        assert_eq!(
            decide_approval(None, notification_id, &suggestion),
            ApprovalDecision::Send { confirmed: false }
        );
    }

    #[test]
    fn decide_approval_arms_a_dangerous_action_on_first_press() {
        let notification_id = Uuid::new_v4();
        let suggestion = sample_suggestion(
            1,
            Some(Action::RemovePackage {
                name: "nginx".into(),
                purge: false,
            }),
        );
        assert_eq!(
            decide_approval(None, notification_id, &suggestion),
            ApprovalDecision::Arm
        );
    }

    #[test]
    fn decide_approval_sends_confirmed_on_matching_second_press() {
        let notification_id = Uuid::new_v4();
        let suggestion = sample_suggestion(
            1,
            Some(Action::RemovePackage {
                name: "nginx".into(),
                purge: false,
            }),
        );
        let armed = Some((notification_id, suggestion.id));
        assert_eq!(
            decide_approval(armed, notification_id, &suggestion),
            ApprovalDecision::Send { confirmed: true }
        );
    }

    #[test]
    fn decide_approval_re_arms_if_the_armed_row_does_not_match() {
        let notification_id = Uuid::new_v4();
        let suggestion = sample_suggestion(
            1,
            Some(Action::RemovePackage {
                name: "nginx".into(),
                purge: false,
            }),
        );
        // Armed for a different suggestion_id -> selecting this one should
        // require its own fresh confirmation, not ride on the old one.
        let armed = Some((notification_id, 99));
        assert_eq!(
            decide_approval(armed, notification_id, &suggestion),
            ApprovalDecision::Arm
        );
    }

    #[test]
    fn handle_key_maps_expected_keys() {
        assert!(matches!(handle_key(KeyCode::Char('q')), KeyAction::Quit));
        assert!(matches!(handle_key(KeyCode::Enter), KeyAction::Approve));
        assert!(matches!(handle_key(KeyCode::Esc), KeyAction::Dismiss));
        assert!(matches!(handle_key(KeyCode::Char('x')), KeyAction::None));
    }
}
