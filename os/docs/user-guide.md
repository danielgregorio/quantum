# DruidOS User Guide

Welcome to DruidOS! This guide will help you get started with your new AI-enhanced operating system.

## Introduction

DruidOS is a VM-first Linux distribution with an integrated Small Language Model (SLM) called the Hive. The Hive watches your system and provides intelligent suggestions and assistance.

**Tagline**: *"The Swarm is watching. The Swarm is learning."*

## Getting Started

### First Boot

DruidOS is terminal-only — there is no graphical desktop. After
installation you'll land in `grove`, the interactive shell that's your
primary interface to the system.

### Installing

Boot the ISO and pick **Try or Install DruidOS Server (ZFS)**: the
installer asks the usual questions (language, keyboard, network, your user)
and puts the system on ZFS across the whole disk, after asking you to
confirm. Choose **Install DruidOS Server - choose storage yourself** for
LVM, plain ext4 or your own partitions - without ZFS, the Hive can't take
safety snapshots.

### Logging In

Log in with the user and password you created in the installer.

## The Hive Stack

### What is the Hive?

The Hive is a collection of background services that:
1. **Observe** your system (processes, logs, network, filesystem)
2. **Analyze** patterns and detect issues
3. **Suggest** solutions and improvements
4. **Act** on your behalf (with permission)

### Hive Components

| Component | Description |
|-----------|-------------|
| hive-cortex | Central brain - coordinates everything |
| hive-synapse | Local AI - generates suggestions |
| hive-actuator | Action executor - does things for you |
| hive-nerve-* | Observers - watch system activity |
| hive-dashboard | Interactive panel - see and approve/dismiss suggestions |

### Notifications

Run `hive-dashboard` in a terminal (or a `tmux`/`screen` pane) to see what
the Hive is noticing, live:

```
┌ Hive Dashboard ─────────────────────────────┐
│ Port Conflict Detected — Kill process 1234  │
│ Log Anomaly — journalctl --vacuum-size=500M │
└──────────────────────────────────────────────┘
 Enter approve  d/Esc dismiss  q quit
```

Navigate with `↑`/`↓`, press `Enter` to approve the selected suggestion
(sends it to `hive-actuator` via `hive-cortex`), `d` or `Esc` to dismiss
it, `q` to quit the dashboard. `hive-dashboard` isn't a background
service — it only shows you things while it's running, same as `top`.

Approving what the Hive suggests is for administrators: root, or a member
of the `sudo`, `admin` or `wheel` group (the user created by the installer
is in `sudo`). For anyone else, `hive-dashboard` says so and exits.

### Missing Programs

Run a program that isn't installed, and if a package of that name is
available, grove tells you - and the Hive offers to install it:

```
[druid@druidos ~]$ htop
grove: htop: command not found
grove: the package htop would provide it; the Hive has offered to install it (an administrator can approve that in hive-dashboard)
```

In `hive-dashboard` the suggestion appears as "Install htop". Approving it
snapshots the system (on ZFS) and installs the package.

### Asking the Hive

In `grove`, start a line with `?` to ask the Hive in plain language:

```
[druid@druidos ~]$ ? how do I see which services failed
[hive] thinking... (the local model takes a moment; Ctrl-C stops waiting)
[hive] Run `systemctl --failed` to list services that failed.
```

The answer comes from a small model running locally (no network) and takes
10-20 seconds on a small VM. It can be wrong - check a command before you
run it. Answers are only ever text: nothing runs unless you run it.

Notices about the system - a service that crashed, a port conflict, a disk
filling up - appear above your next prompt.

## Anonymous Mode

Sometimes you want privacy. In `grove`:

```
[druid@druidos ~]$ anon
[hive] anonymous: the Hive won't act on or answer to what this shell runs until `anon off` ...
(anon) [druid@druidos ~]$ anon off
```

While `anon` is on, the Hive ignores the commands this shell runs, including
the programs they start. It lasts until `anon off` or until the shell exits.
The kernel's audit log (`/var/log/audit/audit.log`, readable only by root)
still records commands. Other levels - a global quiet mode, full isolation -
are planned but not implemented yet.

## Package Management

### Using hive-apt

The `hive-apt` wrapper provides intelligent package management:

```bash
# Install with Hive suggestions
hive-apt install nginx

# Output:
# 📦 Installing nginx
#
# ℹ️  Notes:
#   - Default port: 80
#   - Config: /etc/nginx/nginx.conf
#
# ⚠️  Warnings:
#   - Will listen on all interfaces by default
#   - Consider firewall rules
#
# 💡 Suggestions:
#   - Also install: nginx-extras for additional modules
#
# Continue? [Y/n]
```

### ZFS Snapshots

DruidOS installs onto ZFS and snapshots the system before packages change:
`hive-apt install`/`remove`/`upgrade`/`autoremove`, and package actions
approved in `hive-dashboard`. A snapshot covers `/` with its child datasets
(`/var/lib/dpkg` included) and `/boot`, and is named after the change. If the
snapshot can't be taken, the package change doesn't happen.

```bash
# The Hive's snapshots (the dataset names come from the installer)
zfs list -t snapshot -o name,creation | grep @hive-

# What changed on / since a snapshot
sudo zfs diff rpool/ROOT/ubuntu_ab12cd@hive-before-install-nginx-20260910-170509

# A file as it was before the change
ls /.zfs/snapshot/hive-before-install-nginx-20260910-170509/etc/
```

Rolling the whole system back (`zfs rollback -r` on the root and boot
datasets) is best done from the installer's live environment rather than on
the running system. Old snapshots are pruned daily: the Hive's own
`hive-*` snapshots older than 14 days go, except the 3 newest (`[zfs]` in
`/etc/hive/config.toml`). Snapshots you name yourself are never touched.

## Customization

### Configuration Files

| File | Purpose |
|------|---------|
| `/etc/hive/config.toml` | Main Hive configuration |
| `/etc/hive/whitelist.toml` | Actuator action whitelist |

## Troubleshooting

### Hive Not Responding

Check if services are running:

```bash
systemctl status hive-cortex
systemctl status hive-synapse
```

Restart if needed:

```bash
sudo systemctl restart hive-cortex
```

### High CPU Usage

hive-synapse may use CPU during inference. This is normal but should be brief.

If persistent:
```bash
# Check synapse status
journalctl -u hive-synapse -f

# Restart if stuck
sudo systemctl restart hive-synapse
```

### ZFS Issues

```bash
# Check pool status
zpool status

# Scrub for errors
sudo zpool scrub rpool
```

## Advanced Usage

### Custom Knowledge Base

Add your own package knowledge:

```bash
# Create custom package file
cat > ~/.config/hive/knowledge/packages/myapp.yaml << 'EOF'
package: myapp
description: "My custom application"

install_notes:
  - "Requires port 8080"
  - "Config at ~/.myapp/config"

common_issues:
  - pattern: "connection refused"
    solution: "Check if myapp service is running"
EOF
```

### Extending the Whitelist

System administrators can extend `/etc/hive/whitelist.toml` directly —
each table maps to an `Action` variant, e.g. to allow one more command:

```toml
[run_command]
allowed = [
    { command = "/usr/local/bin/my-safe-script", args = [] },
]
```

Anything not listed is denied by default — see `docs/security-model.md`.

### API Access

Developers can connect to hive-cortex:

```rust
use hive_common::ipc::IpcSocket;
use hive_common::messages::HiveMessage;

async fn connect() -> Result<()> {
    let socket = IpcSocket::connect("/run/hive/cortex.sock").await?;
    socket.send(&HiveMessage::Ping { timestamp: Utc::now() }).await?;
    Ok(())
}
```

## Getting Help

- **Manual**: `man hive-cortex`, `man hive-apt`, etc.
- **Online**: https://druidos.org/docs
- **Community**: https://github.com/druidos/druidos/discussions

## Tips

1. **Let the Hive learn** - The more you use it, the better suggestions become
2. **Use anonymous mode wisely** - It's there when you need it
3. **Check suggestions** - The Hive often catches issues before they become problems
4. **Keep snapshots** - ZFS snapshots are your safety net
5. **Report bugs** - Help improve the Hive for everyone

---

*The Swarm is watching. The Swarm is learning. The Swarm is helping.*
