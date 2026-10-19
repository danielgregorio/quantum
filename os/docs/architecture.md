# DruidOS Architecture

This document describes the architecture of DruidOS and its Hive Stack.

## Overview

DruidOS is a VM-first Linux distribution with an integrated Small Language Model (SLM) called the Hive. The Hive observes the system in real-time and provides intelligent assistance.

**Target: TUI-only.** There is no graphical desktop goal. `grove` (an interactive shell) is the sole user-facing interface. A prior GUI track (Wayland/Hyprland desktop: `hive-shell`, `hive-dock`, `hive-term`) was archived — see `CLAUDE.md`.

```
┌─────────────────────────────────────────────────────────────────────┐
│                             grove                                    │
│                   (interactive shell, the only UI)                   │
└──────────────────────────────┬────────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────────┐
│                                │   Hive Stack                          │
│  ┌─────────────────────────────▼───────────────────┐                  │
│  │               hive-cortex                        │                  │
│  │           (Central Orchestrator)                 │                  │
│  └───┬───────────────┬───────────────┬─────────────┘                  │
│      │               │               │                                 │
│  ┌───▼───┐       ┌───▼───┐       ┌───▼───┐                            │
│  │synapse│       │actuator│      │ nerves │                            │
│  │ (SLM) │       │(actions)│     │(observe)│                           │
│  └───────┘       └────────┘      └────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### Core Components

#### hive-cortex
The central orchestrator daemon running as root. Manages connections, routes messages, and coordinates system responses.

- **Sockets**: `/run/hive/cortex.sock` (components, root:hive 0660) and `/run/hive/user.sock` (grove, any local user, user messages only)
- **User**: root
- **Responsibilities**:
  - Accept connections from all Hive components
  - Route messages between components
  - Manage anonymous mode sessions
  - Coordinate suggestions and actions

#### hive-synapse
The SLM inference daemon. Runs a small language model (Qwen 0.5B Q4) for generating suggestions.

- **User**: `_hive-ai`
- **Restrictions**:
  - No network access
  - Seccomp restricted
  - Model output is text only; the only actions it suggests come from
    fixed rules on the triggering event (e.g. a crashed service ->
    RestartService for that service), never parsed from model output
- **Model**: Qwen 0.5B Q4 (~300MB)

#### hive-actuator
The action executor with a whitelist of allowed operations.

- **User**: `_hive-act`
- **Responsibilities**:
  - Execute approved actions
  - Validate against whitelist
  - Rate limit operations
  - Log all actions

### Observer Components (Nerves)

#### hive-nerve-process
Monitors process execution and command-line activity.

- **Observes**: Command execution, from the kernel audit log: every program
  run from a login session, with its argv captured at exec time (auditd rule
  `config/audit/60-druidos-hive-exec.rules`), so even a millisecond-long
  `rm -rf` is seen. Falls back to polling /proc, which misses short-lived
  commands, where the audit log is unavailable.
- **Privileges**: `CAP_AUDIT_READ` only (receive audit records; nothing else)
- **Detects**: Dangerous commands, sudo usage

#### hive-nerve-journal
Watches journald for log anomalies and service crashes.

- **Observes**: System logs, service status
- **Detects**: Errors, crashes, restart loops

#### hive-nerve-network
Monitors network ports and connections.

- **Observes**: Open ports, network connections
- **Detects**: Port conflicts, unexpected listeners

#### hive-nerve-fs
Watches filesystem for configuration changes.

- **Observes**: Config file changes, permissions
- **Detects**: Sensitive file access, large file creation

### Interface

#### grove
Interactive shell — the only user-facing surface for running commands. Runs in any terminal (local tty, serial console, SSH); no display server required. Connects to cortex's user socket: `? question` sends a `UserQuery` (answered by synapse as text, back to that shell only), system notices print at the next prompt, and `anon [on|off]` sends `AnonymousModeEnter`/`Exit` for grove's own pid - cortex then skips observations of grove and its descendants.

#### hive-dashboard
Interactive ratatui TUI panel showing Hive notifications and suggestions, with approve/dismiss. Run manually by the user in a terminal/pane (like `top`) — not a systemd service, since it needs a TTY. Connects to cortex's user socket; cortex accepts it only from an administrator (root, or a member of sudo, admin or wheel) and the dashboard checks that with a ping before taking over the terminal. Approving a suggestion sends `UserAction`, which cortex turns into an `ActionRequest`. Package actions run through PackageKit, which polkit allows `_hive-act` to use for installs, removals and updates from trusted sources.

### Archived: GUI Track

A Wayland/Hyprland desktop (`hive-shell`, `hive-dock`, `hive-term`) was explored but never integrated end-to-end (no systemd service ever shipped for any of them). The code is paused in `archive/`, outside the Cargo workspace. Not on the roadmap unless the GUI target comes back.

### Integration Components

#### hive-apt
Intelligent apt wrapper that provides package knowledge.

- **Features**: Install notes, warnings, alternatives

#### hive-zfs
ZFS snapshot housekeeping. `hive-zfs prune`, run daily as root by `hive-zfs-prune.timer`, removes the Hive's own `hive-*` safety snapshots once they are older than `[zfs] prune_after_days`, keeping the newest `keep_newest`; nobody else's snapshots are touched.

## IPC Protocol

All components communicate via Unix sockets using typed Rust messages serialized with bincode.

### Message Types

```rust
pub enum HiveMessage {
    // Observations
    CommandObserved { process: ProcessInfo, cmd: String, timestamp: DateTime },
    PortConflict { port: u16, requested_by: ProcessInfo, held_by: ProcessInfo },
    LogAnomaly { service: String, severity: Severity, lines: Vec<LogLine> },
    ServiceCrash { service: String, exit_code: i32, restart_count: u32 },

    // Suggestions
    SuggestionRequest { context: Context, user_query: Option<String> },
    SuggestionResponse { suggestions: Vec<Suggestion> },

    // Actions
    ActionRequest { action: Action, requires_confirmation: bool },
    ActionResponse { success: bool, output: Option<String> },

    // Anonymous mode
    AnonymousModeEnter { level: AnonymousLevel, pid: Option<u32> },
    AnonymousModeExit { pid: Option<u32> },

    // Control
    Ping, Pong, ReloadConfig, Shutdown
}
```

## Security Model

### Privilege Separation

```
                    ┌─────────────┐
                    │   root      │
                    │ hive-cortex │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  _hive-ai   │ │ _hive-sense │ │  _hive-act  │
    │ hive-synapse│ │  nerves     │ │ hive-actuator│
    └─────────────┘ └─────────────┘ └─────────────┘
```

### Security Rules

1. hive-synapse has no network access and is seccomp restricted
2. Nerves have read-only access to what they observe
3. hive-actuator uses a whitelist for all actions
4. All IPC uses peer credentials for authentication

### Anonymous Mode

Three levels of privacy:

1. **Quiet**: Hive observes but doesn't show notifications
2. **Detach**: Specific processes are invisible to Hive
3. **Full**: Isolated namespace with no logging

## Data Flow

### Command Observation Flow

```
1. User runs a command (in grove, or any shell hive-nerve-process observes)
2. hive-nerve-process detects execution
3. Observation sent to hive-cortex
4. hive-cortex forwards to hive-synapse
5. hive-synapse generates suggestions
6. Suggestions sent back to hive-cortex
7. hive-cortex stores the suggestions and sends a Notification
   (carrying them) to hive-dashboard
```

### Action Execution Flow

```
1. User approves a suggestion in hive-dashboard (sends UserAction).
   For actions flagged dangerous (Action::is_dangerous), the first Enter
   press only arms the row — a second Enter press is required to send
   UserAction{confirmed: true}; navigating away or pressing Esc/d cancels
   the pending confirmation instead of dismissing the notification.
2. hive-cortex looks up the suggestion and constructs an ActionRequest
   internally (requires_confirmation = is_dangerous && !confirmed), and
   sends it to hive-actuator
3. hive-actuator validates against the whitelist, then rejects if
   requires_confirmation is still true (skipped/bypassed confirmation)
4. Action executed (or rejected)
5. Result (ActionResponse) sent back through hive-cortex to hive-dashboard
```

## Configuration

### File Locations

- `/etc/hive/config.toml` - Main configuration
- `/var/lib/hive/knowledge/` - Knowledge base
- `~/.config/hive/` - User configuration

### Knowledge Base

YAML files providing package and command knowledge:

- `packages/{name}.yaml` - Package information
- `commands/{name}.yaml` - Command patterns
- `patterns/*.yaml` - Error detection patterns

## ZFS Dataset Layout

DruidOS installs with the Ubuntu installer's ZFS layout; dataset names carry
a random suffix chosen at install time:

```
bpool/BOOT/ubuntu_<id>        → /boot
rpool/ROOT/ubuntu_<id>        → /     (children: var/lib/dpkg, var/lib/apt, var/log, usr/local, srv, ...)
rpool/USERDATA/home_<id>      → /home
rpool/USERDATA/root_<id>      → /root
```

**Safety snapshots.** Before a package change, `hive-actuator` (for an
approved action) and `hive-apt` (for the user) take a recursive snapshot of
the root and boot datasets (found in the mount table, not configured; one
`zfs` call per pool, since ZFS can't snapshot two pools in one call), named `hive-before-<change>-<UTC time>`. If the snapshot fails,
the change is refused. `hive-actuator` runs unprivileged; ZFS delegation
(`zfs allow -u _hive-act snapshot,mount`, applied as root by its unit's
`ExecStartPre` on every start) lets it snapshot and nothing else.
