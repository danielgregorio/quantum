//! DruidOS TUI Installer
//!
//! A terminal-based installer for DruidOS with guided setup.
//!
//! Features:
//! - Disk selection and partitioning
//! - Filesystem choice (ZFS/ext4)
//! - User account creation
//! - Hive Stack configuration

use anyhow::Result;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph},
    Frame, Terminal,
};
use std::io::stdout;

/// Installation steps
#[derive(Debug, Clone, Copy, PartialEq)]
enum Step {
    Welcome,
    DiskSelection,
    Filesystem,
    Partitioning,
    UserSetup,
    HiveConfig,
    Confirm,
    Installing,
    Complete,
}

impl Step {
    fn title(&self) -> &'static str {
        match self {
            Step::Welcome => "Welcome to DruidOS",
            Step::DiskSelection => "Select Installation Disk",
            Step::Filesystem => "Choose Filesystem",
            Step::Partitioning => "Partition Layout",
            Step::UserSetup => "Create User Account",
            Step::HiveConfig => "Hive Configuration",
            Step::Confirm => "Confirm Installation",
            Step::Installing => "Installing...",
            Step::Complete => "Installation Complete",
        }
    }

    fn next(&self) -> Option<Step> {
        match self {
            Step::Welcome => Some(Step::DiskSelection),
            Step::DiskSelection => Some(Step::Filesystem),
            Step::Filesystem => Some(Step::Partitioning),
            Step::Partitioning => Some(Step::UserSetup),
            Step::UserSetup => Some(Step::HiveConfig),
            Step::HiveConfig => Some(Step::Confirm),
            Step::Confirm => Some(Step::Installing),
            Step::Installing => Some(Step::Complete),
            Step::Complete => None,
        }
    }

    fn prev(&self) -> Option<Step> {
        match self {
            Step::Welcome => None,
            Step::DiskSelection => Some(Step::Welcome),
            Step::Filesystem => Some(Step::DiskSelection),
            Step::Partitioning => Some(Step::Filesystem),
            Step::UserSetup => Some(Step::Partitioning),
            Step::HiveConfig => Some(Step::UserSetup),
            Step::Confirm => Some(Step::HiveConfig),
            Step::Installing => None,
            Step::Complete => None,
        }
    }
}

/// Detected disk
#[derive(Debug, Clone)]
struct Disk {
    path: String,
    model: String,
    size: String,
}

/// Filesystem choice
#[derive(Debug, Clone, Copy, PartialEq)]
enum Filesystem {
    Zfs,
    Ext4,
}

/// Installation configuration
#[derive(Debug, Clone)]
struct InstallConfig {
    disk: Option<Disk>,
    filesystem: Filesystem,
    username: String,
    password: String,
    hostname: String,
    enable_hive: bool,
}

impl Default for InstallConfig {
    fn default() -> Self {
        Self {
            disk: None,
            filesystem: Filesystem::Zfs,
            username: String::new(),
            password: String::new(),
            hostname: "druidos".to_string(),
            enable_hive: true,
        }
    }
}

/// Application state
struct App {
    step: Step,
    config: InstallConfig,
    disks: Vec<Disk>,
    disk_list_state: ListState,
    fs_list_state: ListState,
    input_field: usize,
    #[allow(dead_code)]
    // set but never read; text input writes directly into `config` fields instead
    input_buffer: String,
    progress: f32,
    status_message: String,
    should_quit: bool,
}

impl App {
    fn new() -> Self {
        let mut disk_list_state = ListState::default();
        disk_list_state.select(Some(0));

        let mut fs_list_state = ListState::default();
        fs_list_state.select(Some(0));

        Self {
            step: Step::Welcome,
            config: InstallConfig::default(),
            disks: detect_disks(),
            disk_list_state,
            fs_list_state,
            input_field: 0,
            input_buffer: String::new(),
            progress: 0.0,
            status_message: String::new(),
            should_quit: false,
        }
    }

    fn next_step(&mut self) {
        if let Some(next) = self.step.next() {
            self.step = next;
        }
    }

    fn prev_step(&mut self) {
        if let Some(prev) = self.step.prev() {
            self.step = prev;
        }
    }
}

/// Detect available disks
fn detect_disks() -> Vec<Disk> {
    // In a real implementation, this would scan /sys/block
    // For now, return mock data
    vec![
        Disk {
            path: "/dev/vda".to_string(),
            model: "VirtIO Block Device".to_string(),
            size: "20 GB".to_string(),
        },
        Disk {
            path: "/dev/sda".to_string(),
            model: "QEMU HARDDISK".to_string(),
            size: "40 GB".to_string(),
        },
    ]
}

fn main() -> Result<()> {
    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Create app state
    let mut app = App::new();

    // Main loop
    let result = run_app(&mut terminal, &mut app);

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    result
}

fn run_app<B: ratatui::backend::Backend>(terminal: &mut Terminal<B>, app: &mut App) -> Result<()> {
    loop {
        terminal.draw(|f| ui(f, app))?;

        if let Event::Key(key) = event::read()? {
            if key.kind == KeyEventKind::Press {
                match key.code {
                    KeyCode::Char('q') => {
                        app.should_quit = true;
                    }
                    KeyCode::Esc => {
                        if app.step != Step::Installing {
                            app.prev_step();
                        }
                    }
                    KeyCode::Enter => {
                        handle_enter(app);
                    }
                    KeyCode::Up | KeyCode::Char('k') => {
                        handle_up(app);
                    }
                    KeyCode::Down | KeyCode::Char('j') => {
                        handle_down(app);
                    }
                    KeyCode::Tab => {
                        handle_tab(app);
                    }
                    KeyCode::Char(c) => {
                        handle_char(app, c);
                    }
                    KeyCode::Backspace => {
                        handle_backspace(app);
                    }
                    _ => {}
                }
            }
        }

        if app.should_quit {
            return Ok(());
        }
    }
}

fn handle_enter(app: &mut App) {
    match app.step {
        Step::Welcome => app.next_step(),
        Step::DiskSelection => {
            if let Some(i) = app.disk_list_state.selected() {
                app.config.disk = app.disks.get(i).cloned();
                app.next_step();
            }
        }
        Step::Filesystem => {
            if let Some(i) = app.fs_list_state.selected() {
                app.config.filesystem = if i == 0 {
                    Filesystem::Zfs
                } else {
                    Filesystem::Ext4
                };
                app.next_step();
            }
        }
        Step::Partitioning => app.next_step(),
        Step::UserSetup => {
            if !app.config.username.is_empty() && !app.config.password.is_empty() {
                app.next_step();
            }
        }
        Step::HiveConfig => app.next_step(),
        Step::Confirm => {
            app.next_step();
            // Start installation in background (mock)
            app.progress = 0.0;
            app.status_message = "Starting installation...".to_string();
        }
        Step::Installing => {
            // Progress updates would happen here
            if app.progress >= 1.0 {
                app.next_step();
            }
        }
        Step::Complete => {
            app.should_quit = true;
        }
    }
}

fn handle_up(app: &mut App) {
    match app.step {
        Step::DiskSelection => {
            let i = app.disk_list_state.selected().unwrap_or(0);
            let new_i = if i > 0 {
                i - 1
            } else {
                app.disks.len().saturating_sub(1)
            };
            app.disk_list_state.select(Some(new_i));
        }
        Step::Filesystem => {
            let i = app.fs_list_state.selected().unwrap_or(0);
            let new_i = if i > 0 { i - 1 } else { 1 };
            app.fs_list_state.select(Some(new_i));
        }
        Step::UserSetup => {
            app.input_field = app.input_field.saturating_sub(1);
        }
        _ => {}
    }
}

fn handle_down(app: &mut App) {
    match app.step {
        Step::DiskSelection => {
            let i = app.disk_list_state.selected().unwrap_or(0);
            let new_i = if i < app.disks.len() - 1 { i + 1 } else { 0 };
            app.disk_list_state.select(Some(new_i));
        }
        Step::Filesystem => {
            let i = app.fs_list_state.selected().unwrap_or(0);
            let new_i = if i < 1 { i + 1 } else { 0 };
            app.fs_list_state.select(Some(new_i));
        }
        Step::UserSetup if app.input_field < 2 => {
            app.input_field += 1;
        }
        _ => {}
    }
}

fn handle_tab(app: &mut App) {
    if app.step == Step::UserSetup {
        app.input_field = (app.input_field + 1) % 3;
    }
}

fn handle_char(app: &mut App, c: char) {
    if app.step == Step::UserSetup {
        match app.input_field {
            0 => app.config.username.push(c),
            1 => app.config.password.push(c),
            2 => app.config.hostname.push(c),
            _ => {}
        }
    }
}

fn handle_backspace(app: &mut App) {
    if app.step == Step::UserSetup {
        match app.input_field {
            0 => {
                app.config.username.pop();
            }
            1 => {
                app.config.password.pop();
            }
            2 => {
                app.config.hostname.pop();
            }
            _ => {}
        }
    }
}

fn ui(f: &mut Frame, app: &App) {
    // Main layout
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Min(10),   // Content
            Constraint::Length(3), // Footer
        ])
        .split(f.area());

    // Header
    render_header(f, chunks[0], app);

    // Content based on step
    match app.step {
        Step::Welcome => render_welcome(f, chunks[1]),
        Step::DiskSelection => render_disk_selection(f, chunks[1], app),
        Step::Filesystem => render_filesystem(f, chunks[1], app),
        Step::Partitioning => render_partitioning(f, chunks[1], app),
        Step::UserSetup => render_user_setup(f, chunks[1], app),
        Step::HiveConfig => render_hive_config(f, chunks[1], app),
        Step::Confirm => render_confirm(f, chunks[1], app),
        Step::Installing => render_installing(f, chunks[1], app),
        Step::Complete => render_complete(f, chunks[1]),
    }

    // Footer
    render_footer(f, chunks[2], app);
}

fn render_header(f: &mut Frame, area: Rect, app: &App) {
    let title = format!(" DruidOS Installer - {} ", app.step.title());
    let header = Paragraph::new(title)
        .style(
            Style::default()
                .fg(Color::Rgb(123, 92, 255))
                .add_modifier(Modifier::BOLD),
        )
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
        );
    f.render_widget(header, area);
}

fn render_footer(f: &mut Frame, area: Rect, app: &App) {
    let hints = match app.step {
        Step::Welcome => "Press Enter to continue, Q to quit",
        Step::DiskSelection | Step::Filesystem => "↑/↓ to select, Enter to confirm, Esc to go back",
        Step::UserSetup => "Tab to switch fields, Enter to continue",
        Step::Confirm => "Enter to start installation, Esc to go back",
        Step::Installing => "Please wait...",
        Step::Complete => "Press Enter to reboot",
        _ => "Enter to continue, Esc to go back",
    };

    let footer = Paragraph::new(hints)
        .style(Style::default().fg(Color::Rgb(160, 160, 160)))
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
        );
    f.render_widget(footer, area);
}

fn render_welcome(f: &mut Frame, area: Rect) {
    let text = vec![
        Line::from(""),
        Line::from(Span::styled(
            "The Swarm is watching. The Swarm is learning.",
            Style::default()
                .fg(Color::Rgb(123, 92, 255))
                .add_modifier(Modifier::ITALIC),
        )),
        Line::from(""),
        Line::from("Welcome to the DruidOS installer."),
        Line::from(""),
        Line::from("DruidOS is a VM-first Linux distribution with an integrated"),
        Line::from("Small Language Model (SLM) that acts as a living consciousness"),
        Line::from("observing your system in real-time."),
        Line::from(""),
        Line::from("This installer will guide you through:"),
        Line::from("  • Disk selection and partitioning"),
        Line::from("  • Filesystem configuration (ZFS or ext4)"),
        Line::from("  • User account creation"),
        Line::from("  • Hive Stack configuration"),
        Line::from(""),
        Line::from(Span::styled(
            "Press Enter to begin installation",
            Style::default().add_modifier(Modifier::BOLD),
        )),
    ];

    let paragraph = Paragraph::new(text).alignment(Alignment::Center).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
    );
    f.render_widget(paragraph, area);
}

fn render_disk_selection(f: &mut Frame, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .disks
        .iter()
        .map(|d| ListItem::new(format!("{} - {} ({})", d.path, d.model, d.size)))
        .collect();

    let list = List::new(items)
        .block(
            Block::default()
                .title(" Available Disks ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
        )
        .highlight_style(
            Style::default()
                .bg(Color::Rgb(123, 92, 255))
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("▶ ");

    f.render_stateful_widget(list, area, &mut app.disk_list_state.clone());
}

fn render_filesystem(f: &mut Frame, area: Rect, app: &App) {
    let items = vec![
        ListItem::new("ZFS (recommended) - Snapshots, compression, data integrity"),
        ListItem::new("ext4 - Traditional Linux filesystem"),
    ];

    let list = List::new(items)
        .block(
            Block::default()
                .title(" Choose Filesystem ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
        )
        .highlight_style(
            Style::default()
                .bg(Color::Rgb(123, 92, 255))
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("▶ ");

    f.render_stateful_widget(list, area, &mut app.fs_list_state.clone());
}

fn render_partitioning(f: &mut Frame, area: Rect, app: &App) {
    let fs_name = if app.config.filesystem == Filesystem::Zfs {
        "ZFS"
    } else {
        "ext4"
    };

    let text = vec![
        Line::from(""),
        Line::from(format!(
            "The following partition layout will be created on {}:",
            app.config
                .disk
                .as_ref()
                .map(|d| d.path.as_str())
                .unwrap_or("(none)")
        )),
        Line::from(""),
        Line::from("  Partition 1: 512 MB  - EFI System Partition (FAT32)"),
        Line::from("  Partition 2: 1 GB    - /boot (ext4)"),
        Line::from(format!("  Partition 3: Rest    - / ({})", fs_name)),
        Line::from(""),
        Line::from(Span::styled(
            "WARNING: All data on the selected disk will be erased!",
            Style::default()
                .fg(Color::Rgb(248, 113, 113))
                .add_modifier(Modifier::BOLD),
        )),
    ];

    let paragraph = Paragraph::new(text).block(
        Block::default()
            .title(" Partition Layout ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
    );
    f.render_widget(paragraph, area);
}

fn render_user_setup(f: &mut Frame, area: Rect, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(2)
        .constraints([
            Constraint::Length(3),
            Constraint::Length(3),
            Constraint::Length(3),
            Constraint::Min(0),
        ])
        .split(area);

    let username_style = if app.input_field == 0 {
        Style::default().fg(Color::Rgb(123, 92, 255))
    } else {
        Style::default().fg(Color::Rgb(160, 160, 160))
    };

    let password_style = if app.input_field == 1 {
        Style::default().fg(Color::Rgb(123, 92, 255))
    } else {
        Style::default().fg(Color::Rgb(160, 160, 160))
    };

    let hostname_style = if app.input_field == 2 {
        Style::default().fg(Color::Rgb(123, 92, 255))
    } else {
        Style::default().fg(Color::Rgb(160, 160, 160))
    };

    let username = Paragraph::new(app.config.username.as_str()).block(
        Block::default()
            .title(" Username ")
            .borders(Borders::ALL)
            .border_style(username_style),
    );
    f.render_widget(username, chunks[0]);

    let password_display = "*".repeat(app.config.password.len());
    let password = Paragraph::new(password_display).block(
        Block::default()
            .title(" Password ")
            .borders(Borders::ALL)
            .border_style(password_style),
    );
    f.render_widget(password, chunks[1]);

    let hostname = Paragraph::new(app.config.hostname.as_str()).block(
        Block::default()
            .title(" Hostname ")
            .borders(Borders::ALL)
            .border_style(hostname_style),
    );
    f.render_widget(hostname, chunks[2]);
}

fn render_hive_config(f: &mut Frame, area: Rect, app: &App) {
    let text = vec![
        Line::from(""),
        Line::from("Hive Stack Configuration:"),
        Line::from(""),
        Line::from(format!(
            "  [{}] Enable Hive Stack (AI-powered assistance)",
            if app.config.enable_hive { "x" } else { " " }
        )),
        Line::from(""),
        Line::from("The Hive Stack includes:"),
        Line::from("  • hive-cortex - Central orchestrator"),
        Line::from("  • hive-synapse - Local SLM for suggestions"),
        Line::from("  • hive-actuator - Safe action executor"),
        Line::from("  • Nerve components - System observers"),
    ];

    let paragraph = Paragraph::new(text).block(
        Block::default()
            .title(" Hive Configuration ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
    );
    f.render_widget(paragraph, area);
}

fn render_confirm(f: &mut Frame, area: Rect, app: &App) {
    let disk_info = app
        .config
        .disk
        .as_ref()
        .map(|d| format!("{} ({})", d.path, d.size))
        .unwrap_or_else(|| "(none)".to_string());

    let text = vec![
        Line::from(""),
        Line::from("Please confirm the following installation settings:"),
        Line::from(""),
        Line::from(format!("  Disk:       {}", disk_info)),
        Line::from(format!(
            "  Filesystem: {}",
            if app.config.filesystem == Filesystem::Zfs {
                "ZFS"
            } else {
                "ext4"
            }
        )),
        Line::from(format!("  Username:   {}", app.config.username)),
        Line::from(format!("  Hostname:   {}", app.config.hostname)),
        Line::from(format!(
            "  Hive Stack: {}",
            if app.config.enable_hive { "Yes" } else { "No" }
        )),
        Line::from(""),
        Line::from(Span::styled(
            "Press Enter to begin installation",
            Style::default()
                .fg(Color::Rgb(74, 222, 128))
                .add_modifier(Modifier::BOLD),
        )),
    ];

    let paragraph = Paragraph::new(text).block(
        Block::default()
            .title(" Confirm Installation ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
    );
    f.render_widget(paragraph, area);
}

fn render_installing(f: &mut Frame, area: Rect, app: &App) {
    let progress_width = ((area.width - 4) as f32 * app.progress) as u16;
    let progress_bar = "█".repeat(progress_width as usize);
    let remaining = "░".repeat((area.width - 4 - progress_width) as usize);

    let text = vec![
        Line::from(""),
        Line::from("Installing DruidOS..."),
        Line::from(""),
        Line::from(format!("{}{}", progress_bar, remaining)),
        Line::from(format!("{:.0}%", app.progress * 100.0)),
        Line::from(""),
        Line::from(&app.status_message as &str),
    ];

    let paragraph = Paragraph::new(text).alignment(Alignment::Center).block(
        Block::default()
            .title(" Installing ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
    );
    f.render_widget(paragraph, area);
}

fn render_complete(f: &mut Frame, area: Rect) {
    let text = vec![
        Line::from(""),
        Line::from(Span::styled(
            "Installation Complete!",
            Style::default()
                .fg(Color::Rgb(74, 222, 128))
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from("DruidOS has been successfully installed."),
        Line::from(""),
        Line::from("The Swarm is ready."),
        Line::from(""),
        Line::from("Please remove the installation media and press Enter to reboot."),
    ];

    let paragraph = Paragraph::new(text).alignment(Alignment::Center).block(
        Block::default()
            .title(" Complete ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(51, 51, 51))),
    );
    f.render_widget(paragraph, area);
}
