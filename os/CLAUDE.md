# CLAUDE.md - Quantum OS Development Guide

This document provides essential context for AI assistants working on Quantum OS, in `os/` of the Quantum repository. Quantum OS starts as DruidOS (danielgregorio/druidos, whose history stays there): the names below (DruidOS, `druidos-*` packages, the `hive-*` daemons, `grove`) are still DruidOS's until a rename is decided. Paths in this guide are relative to `os/`.

## Project Overview

DruidOS is a Linux distribution designed for virtualization (VM-first) with an integrated Small Language Model (SLM) that acts as a living consciousness observing the system in real-time. The OS provides quality-of-life improvements without hiding Unix complexity.

**Target: TUI-only.** DruidOS has no graphical desktop goal. The primary (and only) user interface is `grove`, an interactive terminal shell. A prior GUI track (Wayland/Hyprland desktop, and a separate direct-framebuffer engine) was paused and moved to `archive/` — see [Directory Structure](#directory-structure).

**Tagline:** "The Swarm is watching. The Swarm is learning."

> **Note:** The internal component naming uses the "hive-" prefix (hive-cortex, hive-synapse, etc.) as part of the "Hive Stack" architecture, referring to the swarm-like consciousness that observes the system.

## Core Philosophy

1. **VM-First**: Optimized for VirtIO, not bare-metal
2. **Integrated Consciousness**: Native SLM that observes, learns, and assists
3. **Quality of Life, Not Simplification**: Unix remains complex, but users have help
4. **Rust Everywhere**: Memory safety, performance, modernity
5. **Transparency**: User sees what the Hive sees
6. **Escape Hatch**: Anonymous mode when user wants to fly solo
7. **Terminal-First**: No GUI goal. `grove` is the interface; everything the Hive surfaces has to work over a plain terminal/console

## Technical Stack

### Base System
- **Base**: Ubuntu 24.04 — `scripts/build-iso.sh` remasters the Ubuntu Server ISO (Subiquity installer, DruidOS layer as the only install source)
- **Kernel**: Ubuntu's stock kernel today. Goal: Linux 6.12+ stripped (VirtIO only, ~50 modules) — `scripts/build-kernel.sh` exists but the ISO doesn't use it yet
- **Init**: systemd
- **Filesystem**: ZFS (default) / ext4 (minimal option) — see [ZFS Dataset Layout](#zfs-dataset-layout)
- **Package Manager**: APT/DPKG (Ubuntu repos)
- **Bootloader**: GRUB today (Ubuntu installer default, menu also on the serial console). Goal: systemd-boot (UEFI native)

### Hive Stack (100% Rust)
| Component | Description |
|-----------|-------------|
| `hive-cortex` | Central orchestrator daemon (root) |
| `hive-synapse` | SLM inference daemon (Qwen 0.5B Q4) |
| `hive-nerve-journal` | Log observer |
| `hive-nerve-network` | Network/port observer |
| `hive-nerve-process` | Process observer |
| `hive-nerve-fs` | Filesystem observer |
| `hive-actuator` | Action executor (whitelisted actions only) |
| `hive-apt` | Intelligent apt wrapper |
| `hive-zfs` | ZFS snapshot integration |
| `hive-dashboard` | Interactive TUI panel — shows Hive notifications/suggestions, lets the user approve or dismiss them |

### Interface
- **Shell**: `grove` — interactive shell, the only user-facing surface for running commands. Runs in any terminal (local tty, serial console, SSH); no display server required. Talks to the Hive over cortex's user socket (`/run/hive/user.sock`, any local user): `? question` asks in plain language (answered as text by synapse, never an action), system notices (crashed service, port conflict, low disk) print at the next prompt, and `anon [on|off]` makes cortex ignore what that shell runs (its children too, by process ancestry). Without a reachable Hive it is just a shell.
- **Notifications/suggestions**: `hive-dashboard` — a separate ratatui TUI tool the user runs manually (like `top`), not a systemd service. It connects to the user socket, where cortex only accepts it from an administrator (root, or a member of sudo/admin/wheel, from the account's groups) and refuses anyone else with a clear message. Approving a suggestion sends `HiveMessage::UserAction`, which `hive-cortex` turns into an `ActionRequest` to `hive-actuator` on the user's behalf.
- **Missing programs**: when grove can't find a program but `apt-cache policy` shows an installable package of that exact name, grove says so and sends `CommandNotFound`; synapse offers "Install <package>" (a typed `InstallPackage`), which an administrator can approve in the dashboard. Offered at most once per package per 10 minutes.

### Archived: GUI Track
A Wayland/Hyprland desktop (`hive-shell`, `hive-dock`, `hive-term`, Mesa+LLVMpipe) and a separate direct-framebuffer engine (`bark` HAL + `spore` 2D renderer) were explored but never integrated end-to-end. Both are paused in `archive/`, outside the Cargo workspace. Not on the roadmap unless the GUI target comes back.

## Directory Structure

```
druidos/
├── Cargo.toml                    # Workspace manifest
├── README.md
├── CLAUDE.md                     # This file
├── docs/
│   ├── architecture.md
│   ├── security-model.md
│   └── user-guide.md
│
├── grove/                         # Interactive shell (primary UI)
│
├── crates/
│   ├── hive-common/              # Shared types, utilities
│   ├── hive-cortex/              # Main orchestrator daemon
│   ├── hive-synapse/             # SLM inference daemon
│   ├── hive-nerve-journal/       # Journald observer
│   ├── hive-nerve-network/       # Network observer
│   ├── hive-nerve-process/       # Process observer
│   ├── hive-nerve-fs/            # Filesystem observer
│   ├── hive-actuator/            # Action executor
│   ├── hive-apt/                 # APT wrapper
│   └── hive-zfs/                 # ZFS integration
│
├── archive/                       # Paused GUI track (not a workspace member)
│   ├── bark/                     # Framebuffer HAL
│   ├── spore/                    # 2D rendering engine
│   ├── hive-shell/               # Desktop overlay
│   ├── hive-dock/                # Dock bar
│   ├── hive-term/                # Terminal emulator
│   ├── examples/                 # bark/spore examples (e.g. fb-test)
│   ├── assets/                   # UI fonts/icons/themes
│   └── config/                   # hyprland/, waybar/, applications/*.desktop
│
├── knowledge/                    # Package knowledge base
│   ├── packages/                 # Per-package YAML files
│   ├── patterns/                 # Error pattern detection
│   └── commands/                 # Command-specific knowledge
│
├── config/
│   └── hive/
│
├── scripts/
│   ├── build-kernel.sh
│   ├── build-initramfs.sh
│   ├── build-image.sh
│   └── setup-zfs.sh
│
└── installer/
```

## Build Commands

```bash
# Build entire workspace
cargo build --workspace

# Build specific crate
cargo build -p hive-cortex

# Run tests
cargo test --workspace

# Format code
cargo fmt --all

# Run clippy lints
cargo clippy --workspace -- -D warnings

# Build release
cargo build --workspace --release

# Everything CI checks, in one command (run before pushing)
./scripts/check.sh
```

CI (`.github/workflows/os.yml` at the repository root) runs `fmt`/`clippy`/`test` and the Hive lab's tapes on every pull request that touches `os/`. DruidOS's ISO build and release workflows were not brought over (a release workflow there would fire on Quantum's own tags); the ISO is built with `scripts/build-iso.sh` and the ISO lab below.

Cargo can't cross-compile this workspace from Windows; `bash scripts/test-on-forge.sh` runs `scripts/check.sh` on the Forge homelab host instead.

### Hive Lab (the Hive in a box: seconds, no VM)

Start here for anything the Hive decides: rules, suggestions, notifications, approvals, what a user may send, and how grove and the dashboard show it (the real programs run in a pseudo-terminal and their screens are read as text). `crates/hive-lab` runs the real `hive-cortex` and `hive-synapse` and plays the nerves, the actuator (which records actions and runs none), grove and the dashboard, under the binary names and users cortex checks, in a private mount namespace (root, as in a container). See `crates/hive-lab/README.md`.

```bash
scripts/lab/hive-tapes.sh                        # every tape in crates/hive-lab/tapes/, ~4 s
sudo target/debug/hive-lab                       # by hand: {"op":"start"}, {"op":"crash",...}, {"op":"observe"}
sudo target/debug/hive-lab --record my.jsonl     # a session becomes a tape; --play runs it again
```

A behaviour worth keeping is a tape: add it to `crates/hive-lab/tapes/` and CI plays it. Use the ISO lab below only for what needs the real system (boot, the installer, what nerves notice and what actions do).

### ISO Lab (build → boot → install → e2e, on Forge with KVM)

`scripts/lab/lab.sh` builds the real ISO and tests it end to end in QEMU/KVM guests on Forge — no human in the loop. Run from the repo root (Git Bash on Windows is fine):

```bash
bash scripts/lab/lab.sh dev          # Rust/unit change: build + hot-swap into an installed guest + e2e (~1 min)
bash scripts/lab/lab.sh iso          # rebuild the ISO (~1 min, base Ubuntu ISO is cached)
bash scripts/lab/lab.sh boot         # boot the ISO like a CD, BIOS + UEFI, until the installer UI (~45 s)
bash scripts/lab/lab.sh install      # unattended install → golden disk for this ISO (~3 min)
bash scripts/lab/lab.sh install-interactive  # the production path: the ISO's own UI, default answers (~5 min)
bash scripts/lab/lab.sh test         # e2e checks on a fresh overlay of the golden disk
bash scripts/lab/lab.sh all          # everything above, in order
bash scripts/lab/lab.sh status       # running stages, current ISO, recent runs + exit codes
bash scripts/lab/lab.sh fetch        # copy the latest run's evidence to qemu-workspace/runs/
```

- **Pieces:** `lab.sh` (local, syncs the working tree) → `remote.sh` (Forge, one detached container per stage; `attach` re-follows after an SSH drop) → `harness.py` (QEMU via QMP: screendumps + OCR for screen-only stages, serial log, SSH into the guest) → `e2e/guest-checks.sh` (runs inside the installed guest, TAP output).
- **Evidence:** every run keeps `serial.log`, `screens/*.png` (+ OCR text), `result.json`, and stage logs in `~/druidos-lab/runs/<id>/` on Forge. When a screen-based step passes suspiciously fast, look at its `screens/*-match.png`.
- **Golden disks** are keyed by ISO hash (`~/druidos-lab/golden/<sha16>-<firmware>-zfs/`), so a rebuilt ISO is never tested against a disk installed from an older one. The install uses a ZFS root (`harness.py install --storage zfs`, the default; `direct` = plain ext4). `dev`'s hot-swap replaces binaries, units, polkit rules and `/etc/hive/{config,whitelist}.toml` — anything else (audit rules, packages, the model) needs a new ISO.
- **Adding an e2e check:** add a `check "name" command...` line to `scripts/lab/e2e/guest-checks.sh`; `lab.sh dev` picks it up.
- The production ISO never autoinstalls. Only the lab's `install` stage adds `autoinstall` (direct kernel boot + a CIDATA seed with a throwaway user and SSH key). `install-interactive` drives the real UI instead — GRUB default entry, keys via QMP, each screen recognized by its body text through OCR (`INTERACTIVE_SCREENS` in `harness.py`, keys chosen from Subiquity's focus rules) — and judges the installed system by the `root=` on its serial console. `--grub-entry 1 --expect-root /dev/mapper/ubuntu--vg` tests the manual-storage entry.

## Security Architecture

```
hive-cortex (root) - orchestrator
    │
    ├── hive-synapse (user: _hive-ai)
    │   └── No network access
    │   └── Seccomp restricted
    │   └── Model output is text only; typed actions come from fixed
    │       rules on the triggering event, never parsed from model output
    │
    ├── grove / any local user -> /run/hive/user.sock (0666)
    │   └── Only UserQuery, CommandNotFound, AnonymousModeEnter/Exit
    │       (own pid), Ping
    │   └── hive-dashboard of an administrator: only UserAction,
    │       UserDismiss, Ping; anyone else's is refused
    │   └── Gets system notices and answers to its own questions,
    │       never suggestions or anything executable
    │
    ├── hive-nerve-* (user: _hive-sense)
    │   └── Read-only access to what they observe
    │   └── Minimal capabilities (none, except hive-nerve-process:
    │       CAP_AUDIT_READ, to receive the exec audit records)
    │
    └── hive-actuator (user: _hive-act)
        └── Only component that can act
        └── Whitelist of allowed actions
        └── Rate-limited
        └── Service control via polkit, and package changes via
            PackageKit (pkcon) + polkit - apt/dpkg would refuse _hive-act -
            both capped at the OS level by
            config/polkit/60-druidos-hive-actuator.rules
```

### Security Rules

1. **NEVER** allow free-form command execution without whitelist validation
2. **ALWAYS** check for shell injection in command arguments
3. **ALWAYS** validate actions pass through `hive-actuator` whitelist
4. **NEVER** give `hive-synapse` network access
5. **ALWAYS** use peer credentials for IPC authentication

## IPC Protocol

All internal communication uses typed Rust structs via Unix sockets, no free-form text:

```rust
pub enum HiveMessage {
    // From nerves to cortex
    CommandObserved { pid: u32, uid: u32, cmd: String, cwd: PathBuf },
    PortConflict { port: u16, requested_by: ProcessInfo, held_by: ProcessInfo },
    LogAnomaly { service: String, severity: Severity, lines: Vec<LogLine> },
    ServiceCrash { service: String, exit_code: i32, restart_count: u32 },
    DiskSpaceLow { mount: PathBuf, available_bytes: u64, threshold_bytes: u64 },

    // From cortex to synapse
    SuggestionRequest { context: Context, user_query: Option<String> },

    // From synapse to cortex
    SuggestionResponse { suggestions: Vec<Suggestion> },

    // From cortex to actuator
    ActionRequest { action: Action, requires_confirmation: bool },

    // From actuator to cortex
    ActionResult { action: Action, success: bool, output: Option<String> },
}
```

### Serialization

Use `bincode` for efficient binary serialization over Unix sockets.

## Coding Conventions

### Rust Standards

1. **Edition**: Rust 2021
2. **Formatting**: Use `cargo fmt` (rustfmt defaults)
3. **Linting**: Pass `cargo clippy -- -D warnings`
4. **Error Handling**: Use `anyhow` for applications, `thiserror` for libraries
5. **Async Runtime**: tokio with `features = ["full"]`

### Daemon Pattern

All hive daemons follow this template:

```rust
use hive_common::{HiveMessage, IpcSocket, Config};
use tokio::net::UnixListener;

#[tokio::main]
async fn main() -> Result<()> {
    // 1. Load configuration
    let config = Config::load("/etc/hive/config.toml")?;

    // 2. Set up logging
    tracing_subscriber::init();

    // 3. Drop privileges if needed
    drop_privileges(&config.user)?;

    // 4. Connect to cortex
    let cortex = IpcSocket::connect("/run/hive/cortex.sock").await?;

    // 5. Main event loop
    loop {
        tokio::select! {
            msg = cortex.recv() => {
                handle_message(msg?).await?;
            }
            event = watch_something() => {
                let msg = process_event(event?);
                cortex.send(msg).await?;
            }
        }
    }
}
```

### File Organization per Crate

```
crates/hive-{name}/
├── Cargo.toml
└── src/
    ├── main.rs          # Entry point (for binaries)
    ├── lib.rs           # Library root (if applicable)
    ├── config.rs        # Configuration loading
    └── {feature}.rs     # Feature-specific modules
```

### Naming Conventions

- **Crates**: `hive-{component}` (kebab-case)
- **Modules**: snake_case
- **Types/Traits**: PascalCase
- **Functions/Methods**: snake_case
- **Constants**: SCREAMING_SNAKE_CASE

## Knowledge Base Format

### Package Knowledge (YAML)

```yaml
# knowledge/packages/{package}.yaml
package: postgresql
description: "Relational database management system"

install_notes:
  - "Default port: 5432"
  - "Config location: /etc/postgresql/{version}/main/"

warnings:
  - type: resource
    message: "Can consume significant memory"
  - type: security
    message: "By default only accepts local connections"

common_issues:
  - pattern: "FATAL: role .* does not exist"
    solution: "Create role with: sudo -u postgres createuser {username}"

alternatives:
  - name: mariadb
    reason: "If you need MySQL compatibility"

related_commands:
  - "psql"
  - "pg_dump"
```

### Command Knowledge (YAML)

```yaml
# knowledge/commands/{command}.yaml
command: rm
risk_level: high

patterns:
  - pattern: "rm -rf /"
    severity: critical
    message: "This will destroy your entire system"

  - pattern: "rm -rf /etc/*"
    severity: high
    message: "This will delete system configuration"
    auto_snapshot: true

suggestions:
  - trigger: "rm -rf"
    suggest: "Consider using trash-cli for safer deletion"
```

## Dependencies

### Core Workspace Dependencies

```toml
[workspace.dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"
bincode = "1"
tracing = "0.1"
tracing-subscriber = "0.3"
anyhow = "1"
thiserror = "1"
nix = { version = "0.27", features = ["user", "socket", "process"] }
libc = "0.2"
notify = "6"                      # File watching
netstat2 = "0.9"                  # Port monitoring
procfs = "0.16"                   # Process info
zbus = "4"                        # D-Bus
candle-core = "0.4"               # LLM inference
```

## Design System

Archived along with the GUI track (dark-theme color tokens, Inter/JetBrains Mono typography, blur/shadow effects) — see git history prior to the TUI-only pivot if the GUI target comes back. No terminal-specific design system has been defined yet.

## Implementation Priority

### Phase 0: Foundation
1. `hive-common` - Define all shared types
2. `hive-cortex` - Basic daemon with socket management
3. `hive-nerve-process` - Simple command observation
4. Basic IPC with Unix sockets and peer credentials

### Phase 1: Consciousness
5. `hive-synapse` - Integrate llama.cpp or candle
6. `hive-nerve-journal` - Watch journald for errors
7. `hive-nerve-network` - Monitor ports
8. Knowledge base YAML structure

### Phase 2: Integration
9. `hive-apt` - Wrap apt with knowledge
10. `hive-zfs` - Automatic snapshots
11. `hive-actuator` - Secure action execution
12. Anonymous mode implementation

### Phase 3: Grove UX
13. ~~Grove as the delivery surface~~ — resolved differently: `hive-dashboard`, a separate ratatui TUI panel, not Grove (Grove is sync/no-tokio — converting it was a bigger lift than a standalone async tool). Run manually, like `top`. Grove itself runs external programs since 2026-09 (pipes, lists, redirections, background jobs).
14. Command interception/observation surfaced inline in Grove sessions

*(Archived: the former "Phase 2: Desktop" — hive-shell, hive-term, hive-dock, Hyprland — see [Directory Structure](#directory-structure).)*

## Anonymous Mode

Three levels of privacy:

```rust
pub enum AnonymousLevel {
    Quiet,   // Hive observes but doesn't show notifications
    Detach,  // This specific terminal/process is invisible
    Full,    // New isolated namespace, no logging
}
```

## ZFS Dataset Layout

The ISO installs with the Ubuntu installer's ZFS layout (the lab's autoinstall uses `storage: layout: name: zfs`), so the dataset names are the installer's, with a random suffix — never hardcode them:

```
bpool/BOOT/ubuntu_<id>        → /boot
rpool/ROOT/ubuntu_<id>        → /     (+ children: var/lib/dpkg, var/lib/apt, var/log, usr/local, srv, ...)
rpool/USERDATA/home_<id>      → /home
rpool/USERDATA/root_<id>      → /root
```

`hive_common::zfs::system_datasets()` finds the root and boot datasets from `/proc/self/mountinfo`. Before a package change (`Action::should_snapshot_first`: install/remove/upgrade), `hive-actuator` and `hive-apt` take a `zfs snapshot -r` of each (one call per pool — ZFS refuses several pools in one call), named `hive-before-<change>-<UTC time>`, and **refuse the change if the snapshot fails**. `hive-actuator` runs as `_hive-act`: its unit's `ExecStartPre=-+hive-actuator delegate-snapshots` runs `zfs allow -u _hive-act snapshot,mount` on those datasets as root at every start — snapshot only, no destroy or rollback (e2e checks both refusals). `actuator.snapshot_dataset` in the config overrides detection. Pruning: `hive-zfs-prune.timer` (daily, persistent) runs `hive-zfs prune` as root, which destroys (`-r`) each system dataset's `hive-*` snapshots older than `[zfs] prune_after_days` (14), sparing the newest `keep_newest` (3). A snapshot's age comes from the timestamp in its name; snapshots not named by the Hive are never touched.

**ZFS by default on the real ISO.** Subiquity's storage screen offers only LVM or a plain partition, and ignores an autoinstall `layout` for its interactive defaults. So `build-iso.sh` ships `/autoinstall.yaml` on the ISO root: every section interactive except `storage` (`layout: zfs`, largest disk) — the user still gets "Confirm destructive action" before anything is erased, and it is never a full autoinstall (no `autoinstall` kernel argument). A second GRUB entry, "choose storage yourself", points `subiquity.autoinstallpath` at `/druidos/manual-storage.yaml` (`interactive-sections: ["*"]`): the stock flow, LVM/ext4/manual, without safety snapshots. The lab's own `install` is unaffected (its CIDATA seed takes precedence over the ISO file).

## Common Tasks

### Adding a New Nerve Component

1. Create `crates/hive-nerve-{name}/`
2. Add to workspace in root `Cargo.toml`
3. Follow the daemon template pattern
4. Register with `hive-cortex` socket
5. Define new `HiveMessage` variants in `hive-common`

### Adding Package Knowledge

1. Create `knowledge/packages/{package}.yaml`
2. Follow the YAML schema with required fields
3. Include install_notes, warnings, common_issues

### Adding Command Patterns

1. Create or edit `knowledge/commands/{command}.yaml`
2. Define patterns with severity levels
3. Include auto_snapshot flag for destructive operations

## Testing Guidelines

1. Unit tests go in the same file as the code (`#[cfg(test)]` module)
2. Integration tests go in `tests/` directory per crate
3. Use `tokio::test` for async tests
4. Mock IPC connections for daemon tests

## Git Workflow

1. Create feature branches from main
2. Use conventional commit messages (feat:, fix:, docs:, refactor:)
3. Run `cargo fmt && cargo clippy` before committing
4. Ensure `cargo test --workspace` passes

## Open Questions

These architectural decisions need resolution:

~~1. SLM loading~~ — resolved: lazy, on the first suggestion request (`preload = false` in `[synapse]`; ~1 s to load the 0.5B model). Keeps boot fast and ~1.5 GB of memory free until the Hive has something to say.
~~2. Inference backend~~ — resolved: **candle** (pure Rust, no C/C++ toolchain; it was already the default feature). `hive-synapse` runs Qwen2.5-0.5B-Instruct Q4_K_M (GGUF, 491 MB, sha256-pinned and shipped in the ISO) on the CPU. Measured in the lab VM (2 vCPU, `CPUQuota=200%`): ~11–17 s per answer, most of it prompt processing — suggestions are asynchronous, so the prompt is kept short and bursts are dropped oldest-first. `MemoryMax=2G` (peak ~1.56 GB). `backend = "ollama"` remains dev/test only (`PrivateNetwork=yes` blocks it in production anyway); `mock` is the fallback when the model files are missing.
3. Command interception granularity: Every command or just dangerous ones?
4. Knowledge base: Embedded at compile time or loaded from files at runtime?

~~5. Notification delivery without a GUI~~ — resolved: `hive-dashboard` (see [Technical Stack](#technical-stack)). Dangerous actions (`Action::is_dangerous`) take a second Enter on the same suggestion to confirm (`decide_approval`); anything reaching `hive-actuator` unconfirmed is still rejected, fail-closed.
