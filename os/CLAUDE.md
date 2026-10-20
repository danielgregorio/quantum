# CLAUDE.md - Quantum OS Development Guide

This document provides essential context for AI assistants working on Quantum OS, in `os/` of the Quantum repository. Quantum OS starts as DruidOS (danielgregorio/druidos, whose history stays there): the names below (DruidOS, `druidos-*` packages, the `hive-*` daemons, `grove`) are still DruidOS's until a rename is decided. Paths in this guide are relative to `os/`.

## Project Overview

DruidOS is a Linux distribution designed for virtualization (VM-first) with an integrated Small Language Model (SLM) that acts as a living consciousness observing the system in real-time. The OS provides quality-of-life improvements without hiding Unix complexity.

**Target: a terminal, and one screen.** DruidOS has no desktop goal: no window system, no compositor, no GPU stack. `grove`, an interactive terminal shell, is where work is done, and everything the Hive surfaces works over a plain terminal. What the machine's console shows besides is **the Hive's screen**: a small pixel-art scene declared in Quantum (`config/screen/screen.q`) and drawn by `hive-screen`, a daemon of a few hundred kilobytes that draws on the CPU, lists the Hive's offers for an administrator to approve with the keyboard, and scales with the cores the VM gives it. A prior GUI track (Wayland/Hyprland desktop, and a separate direct-framebuffer engine) was paused and moved to `archive/` — see [Directory Structure](#directory-structure); the screen is not that track come back, it is one program with no stack under it.

**Tagline:** "The Swarm is watching. The Swarm is learning."

> **Note:** The internal component naming uses the "hive-" prefix (hive-cortex, hive-synapse, etc.) as part of the "Hive Stack" architecture, referring to the swarm-like consciousness that observes the system.

## Core Philosophy

1. **VM-First**: Optimized for VirtIO, not bare-metal
2. **Integrated Consciousness**: Native SLM that observes, learns, and assists
3. **Quality of Life, Not Simplification**: Unix remains complex, but users have help
4. **Rust Everywhere**: Memory safety, performance, modernity
5. **Transparency**: User sees what the Hive sees
6. **Escape Hatch**: Anonymous mode when user wants to fly solo
7. **Terminal-First**: No desktop goal. `grove` is the interface; everything the Hive surfaces has to work over a plain terminal/console. The Hive's screen (`hive-screen`) is a view of the same things on the console, never the only way to them

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
- **The screen**: `hive-screen` — the Hive's screen on the machine's console, declared in Quantum (`config/screen/screen.q`, `q:application type="screen"`, the `qs:` tags; `docs/targets/screen.md` is the reference) and compiled to `config/screen/screen.toml`, a font sheet and the sprite sheets. It connects to the user socket as the dashboard does, and cortex lets it in as one (by its binary name and an administrator's uid): every notice reaches it with the event's name and fields, and every offer, which it lists for the keyboard to approve (a dangerous action asks for Enter twice) or dismiss. On the system it is `hive-screen.service`: it draws on the console through DRM/KMS (one dumb buffer on the first connected connector, the scene scaled up by a whole number, black around), reads the keyboard from `/dev/input`, and keeps the kernel's text console off `tty1` (its terminal, `TTYPath=`) while it runs, sharing it (Ctrl+Alt+F2 takes the console to a text terminal and the display is let go; Ctrl+Alt+F1 brings it back whole); it runs as `_hive-screen` (groups video and input), under the other daemons' hardening, below hive-synapse in the CPU queue (`Nice=`, `CPUWeight=`), and draws only when the picture changed, and only the rows that changed. How much it shows is a **presentation level** (`crates/hive-screen/src/level.rs`), chosen as it runs by the frame time it measures and capped by the cores the kernel gives it (read twice a second, so a vCPU plugged in counts at once): `plain` (1 core: the scene as declared, no particles, 15 pictures a second at most), `effects` (2 cores: the particles, 30 a second), `fine` (4 cores: two pixels to the scene's one, so a tween or a particle lands on its own pixel, plus the emitters the scene keeps for it, `qs:emitter level="2"`). A level changes how the scene shows, never what happens in it; a frame is drawn in bands, one thread a core, and is the same picture whatever their number; a scene at rest costs nothing at any level; `HIVE_SCREEN_LEVEL=N` in the unit's environment pins a level. The daemon logs what a frame costs at each level it visits. `--play` drives it from stdin with no display, at level 1 unless asked (`{"op":"level","level":2}`): the Hive lab runs it that way. The VM lab's machine has a `virtio-gpu` and 4 vCPUs: `shot` reads the display through QMP `screendump`, `press` its keyboard, `cpus` leaves 1 to 4 of its vCPUs online in the guest; `screen-console.jsonl` follows a real crash to the honey back in the cell on the real display, `screen-levels.jsonl` the level following the cores from 2 to 4 and back (`// needs: kvm`: under emulation a whole-screen present costs 80 ms a frame, so the lab skips it without `/dev/kvm`; CI has it), and `screen-vt.jsonl` the console going to another terminal and coming back. **Pages on the screen**: the screen is also where the machine's Quantum applications show. `quantum pixel` (`quantum/runtime/ui_pixel.py`), run by any local user in a project's folder, is the fourth renderer of a page beside the browser, the console and the desktop: it starts the application's server in its process, connects to the daemon's pixel socket (`/run/hive-screen/pixel.sock`, mode 0666 in `RuntimeDirectory=hive-screen`; `crates/hive-screen/src/pixel.rs`), sends each page's view tree as JSON lines (`show`) and hears what the user did (`click`, `submit` with the form's fields, `change`, `navigate`, `reload`, `close`), which it posts to the page as a browser would. The daemon lays the page out in cells of its font and draws it over the scene (`window.rs`), the keyboard its own while it shows: Tab/Shift+Tab between the elements that react, the arrows inside one, Enter acts, Space marks, Esc closes (the scene is whole again, the page's runtime ends), the last line says the keys that apply; the keyboard is read whole from `/dev/input` by the machine's layout (US, or ABNT2 with `ç` and the dead accents composed with the vowel after them, from `XKBLAYOUT` in `/etc/default/keyboard` or `HIVE_SCREEN_KEYBOARD`; Shift, Caps Lock, AltGr, repeats; `input.rs`). The page is drawn as a window in the look of a window manager in pixel art (`window.rs`): a frame with a 1-px bevel (light above and left, dark below and right on what is raised, the reverse on what is sunken) and a 3-px shadow, the scene dimmed around it, a honey title bar with the Esc key drawn on it, a status bar with the keys that apply, fields sunken and buttons raised; the window is as tall as its content, up to the canvas, and sits in the middle. At the fine level the page is drawn pixel for pixel on the canvas of two pixels to the scene's one, 100 columns by up to 29 rows instead of 49 by up to 13 (the console's `sm` breakpoint, so an `hbox` with `stack_below` sits side by side), and flows again when the level changes, keeping its focus. The page moves (`world.rs`, `Motion`): the jelly on opening (the window's picture scaled about its centre with a Back ease, 12 ticks), the lamp on closing (every column of the last picture converges on the bottom left corner, the far side bending first, 14 ticks), the curtain when a page is shown again after an action (the old picture stays where a 4×4 ordered dither has not reached, 8 ticks); the window is drawn once a frame on a canvas of its own and composed over the dimmed scene, whole or in its transition; nothing moves at the `plain` level, `HIVE_SCREEN_MOTION=off` stops it all, the play protocol's `until` takes `still` and the observation says `motion`, and `tests/play.rs` keeps a frame of each transition half way; Up and Down go between elements that do not take them, Home and End to the first and the last, and a scrollbar at the right edge shows where a long page is. One page at a time. The play protocol shows a page with no runtime (`show`), types (`act` with `type` and every key by name) and waits (`until` with `pixel`, `text`, `shown`), and `--pixel-socket` gives a test the socket: the UI parity test (`tests/apps/test_ui_parity_script.py`) runs its one script on the screen with `quantum pixel` as the page's runtime, which the OS workflow runs against the build; `crates/hive-screen/tests/play.rs` keeps a reference frame of a page (`window.png`); `screen-page.jsonl` in the Hive lab reads a page as data; `screen-pixel.jsonl` in the VM lab brings a page from a local user's program to the real screen and types into it from the real keyboard; `screen-abnt2.jsonl` sets the system's keyboard to `br`, restarts the daemon and types `ação` with the cedilla key and the dead tilde.
- **Missing programs**: when grove can't find a program but `apt-cache policy` shows an installable package of that exact name, grove says so and sends `CommandNotFound`; synapse offers "Install <package>" (a typed `InstallPackage`), which an administrator can approve in the dashboard. Offered at most once per package per 10 minutes.

### Archived: GUI Track
A Wayland/Hyprland desktop (`hive-shell`, `hive-dock`, `hive-term`, Mesa+LLVMpipe) and a separate direct-framebuffer engine (`bark` HAL + `spore` 2D renderer) were explored but never integrated end-to-end. Both are paused in `archive/`, outside the Cargo workspace, and stay there: `hive-screen` is written fresh (what held up in `spore` was taken as ideas, not as a dependency), and a desktop is not on the roadmap.

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
│   ├── hive-screen/              # The Hive's screen: the compiled scene on the console
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
│   ├── hive/                     # hive.q and what it compiles to (rules.toml, whitelist.toml)
│   └── screen/                   # screen.q and what it compiles to (screen.toml, font.png, art/)
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

CI (`.github/workflows/os.yml` at the repository root) runs `fmt`/`clippy`/`test`, the Hive lab's tapes and the VM lab's tapes on every pull request that touches `os/`. DruidOS's ISO build and release workflows were not brought over (a release workflow there would fire on Quantum's own tags); the ISO is built with `scripts/build-iso.sh` and the ISO lab below.

Cargo can't cross-compile this workspace from Windows; `bash scripts/test-on-forge.sh` runs `scripts/check.sh` on the Forge homelab host instead.

### The Hive's rules (`config/hive/hive.q`)

What the Hive offers on an event, and what the actuator may do, are declared in Quantum: `config/hive/hive.q` (`q:application type="hive"`, the `qh:` tags; `docs/targets/hive.md` at the repository's root is the reference). `python scripts/generate-hive-config.py` (from the repository's root) writes `config/hive/rules.toml`, which hive-synapse loads (`crates/hive-synapse/src/rules.rs`, which also embeds the committed file as its built-in rules), and `config/hive/whitelist.toml`, which hive-actuator loads. Both are committed as written and checked in CI (`tests/hive/`): edit `hive.q`, never them. A `{field}` is filled in from the event, never from the model's text; an offer the whitelist would refuse does not compile. A rule worth keeping has a tape in the Hive lab below.

### The Hive's screen (`config/screen/screen.q`)

What the console shows is declared in Quantum too: `config/screen/screen.q` (`q:application type="screen"`, the `qs:` tags; `docs/targets/screen.md` at the repository's root is the reference). The scene's vocabulary is the games' (sheets, animations, tweens with the same curves, the same particle presets); what moves it are the Hive's events, the same the rules are on, with the same `{field}`s (`hive_common::events` is the one table behind both, kept equal to `quantum/runtime/hive/schema.py` by a test). `python scripts/generate-screen-config.py` writes `config/screen/screen.toml` and `font.png` next to the art `scripts/art/hive_screen.py` draws (CC0, `config/screen/art/`; the cells of the comb are rounded, with a bevel and a 2-px shadow in their frames); all committed as written and checked in CI (`tests/screen/`): edit `screen.q`, never them. The scene is drawn in the look of the windows (window.rs's palette): a `qs:bar` at the top and one at the bottom span the scene (title in the accent, a text after it, a text at the right; the texts hold the screen's own `{field}`s, `{clock}`, `{level}`, `{cores}`, `{host}`, `{offers}`, which the daemon fills in from the kernel's hostname, the chooser's cores and the local time twice a second, `World::set_facts`, and which a test's screen leaves blank so its frames are the same everywhere; what a `qs:say` says takes the left of the bottom bar while it lasts, and the strip of its own only over a page), and a `qs:offers` or `qs:notices` with a `title=` is a panel with a bevelled frame, a shadow and a title bar, as tall as its rows. The observation says `bars` with the fields filled in. F1 opens the Hive's offers in a menu over whatever is on the screen (`World::toggle_menu`, drawn by `window::draw_menu` in the windows' look): a drawer that slides in from the bottom left in 8 ticks and pushes the comb 4 px aside, Up and Down choose, Enter approves, Del dismisses, Esc shuts it; while it is out the page does not hear the keys; the window's status bar says how many offers wait and the bottom bar shows the open page as a button; the observation says `menu`, the play protocol's `until` takes `menu`, and `tests/play.rs` keeps `menu.png`, `menu-drawer.png`, `menu-empty.png` and `window-offers.png`. A sprite named after a service is the one `{service}` reaches; an action the event cannot fill in, or whose target no sprite is named, is left out. `crates/hive-screen/tests/play.rs` plays the OS's screen and compares frames pixel for pixel with `tests/screens/` (`UPDATE_SCREENS=1` rewrites them); a behaviour worth keeping has a tape in the Hive lab (`screen-crash.jsonl`, `screen-page.jsonl`), which reads what the screen shows as data, never pixels. A page of a Quantum application on the screen (`quantum pixel`, `docs/guide/ui.md`) is not declared here: the scene is the Hive's, the page is the application's, and the screen draws both.

### Apps (`apps/`)

The applications installed with the Hive are Quantum project folders under `apps/`, shipped to `/usr/share/quantum-os/apps/` with the Quantum runtime itself (the repository's `quantum/` package in `/usr/lib/python3/dist-packages`, its needs as Ubuntu packages, `/usr/bin/quantum` running `quantum.cli.runner`; `scripts/build-iso.sh` for the ISO, `scripts/lab/vm/install-hive.sh` for the VM lab, the same way). `hive NAME` (`crates/hive-cli`) opens an app on the Hive's screen with `quantum pixel`, as the user who runs it; `hive apps` lists them. **Settings** (`apps/settings`, `hive settings`) is the machine's settings, read: five tabs of a `ui:tabpanel` (Machine, Network, Keyboard, Screen, Hive), each a service of `machine.py` (`settings.machine` and the others, `q:invoke`), which read what anyone may read (`/proc`, `/etc/default/keyboard`, `/etc/hive/whitelist.toml`, `ip -j addr`, `ip -j route`, `resolvectl status`, `systemctl is-active`) through doors (`run`, `run_any`, `read`) that a test replaces, and never raise: a machine with no `ip` or no screen reads as "not read". The Screen tab says what the screen told the page's runtime: the daemon sends a `status` event on the pixel socket when a runtime connects and whenever it changes (`Runtime::status`: the level and its name, whether it is pinned, the cores, whether pages move, the keyboard's layout, what a frame costs, the scene's size), the client (`ui_pixel.py`) waits half a second for it before the first page and keeps it for `screen_status()`. Reading is the app's and runs as the user. **A change goes through the Hive.** The page's "Ask the Hive" buttons call `settings.ask`, which runs `hive request set-hostname NAME | set-keyboard LAYOUT [MODEL] | set-screen-level auto|plain|effects|fine | set-network IFACE dhcp | set-network IFACE ADDR/PREFIX [via GATEWAY] [dns A,B]` (`crates/hive-cli`, the `hive` binary: it also opens the apps); that sends `HiveMessage::UserRequest { action, reason }` on cortex's user socket, which any local user may send and only for the settings actions (`Action::is_a_setting`: `SetHostname`, `SetKeyboard`, `SetScreenLevel`, `SetNetwork`). Cortex turns it into an offer in the user's name (`offer_request`: a `Notification` of kind `request`, title "druid asks: name the machine forge", fields `user`, `action`, `what`, `count`), stored as any suggestion; an administrator approves it on the screen (Enter, or F1 over a page) or the dashboard, and the actuator runs it through its whitelist (`<qh:allow action="set-hostname"/>` and the others in `hive.q`, two a minute each; `Whitelist::is_allowed` also refuses a value hostnamectl or localectl would not take). `SetHostname` runs `hostnamectl set-hostname` over D-Bus with polkit's leave for `_hive-act` (`config/polkit/61-druidos-hive-settings.rules`: the name, nothing else of hostnamed). `SetKeyboard` and `SetScreenLevel` write (or remove) `keyboard` (`br abnt2`) and `screen-level` under the actuator's `StateDirectory=hive/settings` (`/var/lib/hive/settings`, world-readable), no root: Ubuntu's `systemd-localed` refuses keymaps ("Setting X11 and console keymaps is not supported in Debian"), so the Hive never rewrites `/etc/default/keyboard`, which stays the installer's; the text console's keymap is not the Hive's to change. hive-screen follows both files as it runs, twice a second: `Layout::detect` reads `HIVE_SCREEN_KEYBOARD`, then the Hive's `keyboard` setting, then `/etc/default/keyboard` (`Keyboards::set_layout`, no restart), and the level is pinned or let go by `screen-level` (`HIVE_SCREEN_LEVEL` in the unit's environment still wins); it says so in its log and in the `status` it sends the page's runtime (`HIVE_SETTINGS_DIR` moves the folder for a test). On the screen a request is its own event, `qs:on event="request"` ("{user} asks: {what}"), listed in the Offers panel like any offer. Nothing runs on the asking. **The network** is the one setting that needs root and the one that is dangerous (`Action::is_dangerous`: a wrong address takes the machine off the network, so the screen asks for Enter twice and the dashboard for confirmation). `SetNetwork { interface, dhcp, address, gateway, dns }` is one interface by DHCP or at a fixed IPv4 address with its prefix, a gateway and up to four DNS servers (`is_valid_network`, checked by the CLI, the Settings page, the whitelist and again by the root step). The actuator has no root and netplan's D-Bus refuses anyone else, so it writes the setting as JSON to `network` under its settings folder, empties `network.result`, and starts `quantum-network-apply.service` (`config/systemd/quantum-network-apply.service`, a root oneshot the polkit manage-units rule already lets it start; `scripts/network-apply`, python3 stdlib, installed at `/usr/lib/quantum-os/network-apply`): that reads and checks the setting again, keeps `/etc/netplan/60-hive.yaml` as `60-hive.yaml.before`, writes `60-hive.yaml` for that interface only (mode 600; cloud-init's file for the same interface is merged under it by netplan, its match kept, its `dhcp4` overridden), runs `netplan generate` and `netplan apply`, and waits up to 20 s for the interface to have the fixed address, or any address by DHCP; when it does not, the file before comes back and is applied again, so a wrong address never leaves the machine off the network for want of a hand. The outcome goes to `network.result` ("ok: enp0s1 has 10.0.2.20/24" or "failed: ..."), which the actuator answers with. The Network tab's form (interface, source dhcp/static, address/prefix, gateway, DNS) starts from what the first interface has and asks through `settings.ask` (`set-network`, `value` the interface, then `mode`, `address`, `gateway`, `dns`); the flash says it takes Enter twice. `tests/apps/test_settings.py` reads a canned machine through the doors, asks through a replaced `ask` door, and runs the page in the browser, in the console and on the screen with the parity test's drivers; `request-hostname.jsonl` in the Hive lab follows a request to the actuator and refuses one that is not a setting; `settings.jsonl` in the VM lab opens the app on the real screen with `hive settings` and reads the view its server answers; `settings-hostname.jsonl` asks for the name, the keyboard and the level from a local user and approves each on the real keyboard: `hostname` and the two settings files change (`/etc/default/keyboard` does not), and the screen reads the keyboard and the level anew. `request-network.jsonl` in the Hive lab follows a fixed address and then DHCP to the actuator; `settings-network.jsonl` in the VM lab asks for 10.0.2.20/24 via 10.0.2.2, arms the offer with one Enter (nothing runs), approves it with the second, and `ip addr`, the default route and the netplan file follow, then back by DHCP with the file before kept.

### Hive Lab (the Hive in a box: seconds, no VM)

Start here for anything the Hive decides: rules, suggestions, notifications, approvals, what a user may send, and how grove, the dashboard and the screen show it (the real programs run in a pseudo-terminal and their screens are read as text; the real `hive-screen` runs with no display and is read through its play protocol). `crates/hive-lab` runs the real `hive-cortex` and `hive-synapse` and plays the nerves, the actuator (which records actions and runs none), grove and the dashboard, under the binary names and users cortex checks, in a private mount namespace (root, as in a container). See `crates/hive-lab/README.md`.

```bash
scripts/lab/hive-tapes.sh                        # every tape in crates/hive-lab/tapes/, ~4 s
sudo target/debug/hive-lab                       # by hand: {"op":"start"}, {"op":"crash",...}, {"op":"observe"}
sudo target/debug/hive-lab --record my.jsonl     # a session becomes a tape; --play runs it again
```

A behaviour worth keeping is a tape: add it to `crates/hive-lab/tapes/` and CI plays it. The same lab is an MCP server (`hive-lab` in the repository's `.mcp.json`: `hive_start`, `hive_request`, `hive_view`, `hive_tape`, `hive_end`).

### VM Lab (the real system, restored from a snapshot in a second)

For what only the running system shows: what the real nerves notice (the journal, the audit log, `/proc`), what the real actuator does through polkit and systemd, how the units, their sandboxes and users behave together. `scripts/lab/vm/vm.py` runs Ubuntu 24.04's minimal cloud image in QEMU (KVM when available, emulation otherwise), installs the Hive from the working tree's build as the ISO does, and saves snapshots: `base` (booted, with polkit, PackageKit and auditd) and `hive` (with this build installed). A tape restores `hive` in about a second; a new build is installed on `base` again. A guest agent answers over virtio-serial (no network, no SSH); the real dashboard and grove run in a terminal in the guest and are read as text with `hive-lab term`. See `scripts/lab/vm/README.md`.

```bash
cargo build --workspace
python3 scripts/lab/vm/vm.py --play              # every tape in scripts/lab/vm/tapes/
python3 scripts/lab/vm/vm.py                     # by hand: {"op":"start"}, {"op":"sh","sh":"..."}, {"op":"tui","app":"dashboard"}
```

Its MCP tools are in the same server: `vm_start`, `vm_request`, `vm_view`, `vm_tape`, `vm_end`. Use the ISO lab below only for the image itself: boot, the installer, ZFS on root.

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

### What a notice carries

`HiveMessage::Notification` carries, besides its title and body, the event behind it as the rules and the screen name it (`kind`: `service-crash`, `disk-low`, ..., `offer` for a suggestion with its `count`; `None` for a plain notice) and its `fields` (`service`, `port`, `mount`...), filled in by cortex from the observation through `hive_common::events::fields_of`. A client acts on what happened, not on the words; the dashboard still shows the words.

### Serialization

Use `bincode` for efficient binary serialization over Unix sockets.

## Coding Conventions

### Language

**Everything in `os/` is English**, as in the rest of the repository (`CODING.md`): code, identifiers, comments, what a screen, an app or a command says to its user (help lines, menus, tabs, buttons, messages), tests and their fixtures, tapes, this guide, `DEVLOG.md`, `STATUS.md` and the docs. Whoever asks for the work, in whatever language, the repository's text is English. Test data that only exists to exercise a character (`ç` on the Brazilian keyboard, `ñ` after a dead `~`) is data, not prose.

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
