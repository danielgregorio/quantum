# The VM lab: the real system, restored in a second

The Hive lab (`crates/hive-lab`) runs the real hive-cortex and hive-synapse and plays everything else, in a fraction of a second. It cannot show what only the running system does: what the nerves notice in the journal, the audit log and `/proc`; what the actuator does through polkit and systemd; how the units, their sandboxes and their users behave together. This lab runs all of it for real, and still needs no ISO, no installer, no SSH and no OCR.

| | |
|---|---|
| the guest | Ubuntu 24.04's minimal cloud image (the release Quantum OS remasters), on a copy-on-write overlay |
| the agent | `agent.py`, in the guest: JSON lines over a virtio-serial port (commands, files, the journal, programs in a terminal) |
| the build | the working tree's binaries (debug sections stripped) and `config/`, over a read-only 9p share, installed by `install-hive.sh` as the ISO installs them |
| packages | the guest's only package source is a signed repository in the guest, made by the host, with what a test may install (`REPO_PACKAGES`: htop): an approved install goes through PackageKit as on the real system, with no network |
| the speed | the guest boots once. The snapshot `base` keeps it booted with its packages, and `hive` keeps it with the Hive installed from the build. Restoring one takes about a second, with or without KVM |
| the screens | the real hive-dashboard and grove run in a terminal in the guest. `hive-lab term` renders them with the same terminal emulator as the Hive lab |

## Playing it

```bash
cargo build --workspace
python3 scripts/lab/vm/vm.py --play                  # every tape in scripts/lab/vm/tapes/
python3 scripts/lab/vm/vm.py --play scripts/lab/vm/tapes/crash-restart.jsonl
python3 scripts/lab/vm/vm.py                         # the driver: one JSON request per line on stdin
```

It needs `qemu-system-x86_64`, `qemu-img`, `genisoimage` and `gpg`. It uses KVM when `/dev/kvm` is usable and plain emulation otherwise. The first run downloads the cloud image (260 MB) and makes `base`. On a host without KVM this takes a few minutes, mostly the first boot. The guest's missing packages (polkit, PackageKit and pkcon, auditd, and the repository's) are downloaded by the host's apt for the guest's own dpkg status, so the guest needs no network; this needs an Ubuntu 24.04 host. After that:

- an unchanged build restores `hive` (about a second);
- a changed build restores `hive`, installs what changed and saves `hive` again;
- a new base (its packages, the image) installs everything on `base`.

Only what changed is installed: when nothing but binaries changed, they are copied and their units restarted (measured without KVM: grove 6 s, a nerve 9 s, hive-cortex 20 s, a full install 60 s).

| Measured | without KVM (this lab's container) | with KVM (CI) |
|---|---|---|
| making the base (once) | ~5 min | 18 s |
| restoring `hive` | ~2 s | under a second |
| the five tapes | ~95 s | ~40 s, the first install included |

Everything lives in `~/.cache/quantum-os-lab`, or `QUANTUM_LAB_CACHE`. A run's evidence is in `run/` there: `serial.log`, `qemu.cmdline`.

## The requests

The same shape as the Hive lab's: `{"op": ...}` in, `{"ok": true, ...}` or `{"ok": false, "error": ...}` out.

| op | does |
|---|---|
| `start` | a fresh Hive: restores `hive`, installing first when the build changed |
| `restore` (`snapshot`: hive), `save` (`snapshot`) | go back to a snapshot; keep one of your own to try something and come back |
| `install` | after `cargo build`: installs what changed, as `start` does |
| `sh` (`sh`, `user`, `timeout`; expects `code`: 0 or null for any, `contains`, `excludes`) | a command in the guest, as root or `user` |
| `until_sh` (same, `timeout`: 10) | runs it again until it meets the expectations |
| `journal` (`units`) | the journal since the last look |
| `until_journal` (`unit`, `contains`, `excludes`, `timeout`: 10) | waits for an entry; the next look starts after it |
| `none_journal` (`unit`, `contains`, `within`: 1) | nothing like it shows up |
| `tui` (`app`: dashboard or grove, `rows`, `cols`) | the real program in a terminal: the dashboard as root, grove as the user `druid` |
| `view` (`app`), `keys` (`app`, `keys`) | its screen as text, typing (`Enter`, `Down`, `Esc`, ... or text) |
| `until_screen` (`app`, `contains`, `excludes`, `count`, `timeout`: 5) | waits until the screen shows it (exactly `count` times, if given) |
| `keys_until` (`app`, `keys`, `contains`, `max`: 20) | presses keys until the screen shows the text: moves a selection to a row by what it says |
| `end` | stops the VM |

## Tapes

| Tape | What it holds the system to |
|---|---|
| `crash-restart` | a real unit crashes: the journal nerve sees it, the real dashboard offers a restart, nothing runs on its own, and the real actuator restarts it through polkit once it is approved with the keyboard |
| `crash-loop` | a unit crashing again and again (`Restart=on-failure`) is shown, and its restart offered, once |
| `install-on-request` | a user reaches for a missing program: grove says which package provides it, the dashboard offers it, and the approval has the unprivileged actuator install it through PackageKit and polkit; the user's next try runs it |
| `port-conflict` | a real process holds a port and a unit keeps failing to bind it: the network nerve names both, once; listing the ports runs once approved |
| `dangerous-command` | a logged-in user's `rm -rf /srv` goes from the kernel's audit log through the process nerve to the real dashboard, whose advice claims nothing was done; a routine delete and a daemon's own commands are not reported |

A user's commands (`sh` with `user`, grove) carry a login uid, as a real login gives them: the audit rule the process nerve reads records only programs of someone who logged in. A failing tape prints the guest's journal since it started, for failures seen where nobody can look into the guest afterwards (CI).

`--play` runs tapes one after the other on one VM. Each tape's `start` restores a fresh Hive.

## What it found

- A unit in a restart loop flooded the Hive. Every crash reached the model, and each one stacked "Service Crashed" and its offers on every dashboard again. hive-cortex now passes a problem on once every five minutes, and says how many reports it held (`router.rs`, `news`).
- The network nerve's own five-minute window never held anything: its key held the pid, which changes with every retry. It is now the unit.
- After `rm -rf /srv`, the dashboard said "A ZFS snapshot has been created for safety", on a system without ZFS: synapse's mock text claimed something nothing does. The line is gone.
- A failed service action reached the dashboard as "(failed)" and the journal as an exit code: systemctl's own words were dropped. They are now the action's output.
- The druidos-hive package did not depend on what the Hive runs: an approved install failed with "Failed to run pkcon" on a system without `packagekit-tools`. The ISO happened to ship it. `debian/control` now depends on polkitd, packagekit, packagekit-tools and auditd.

## And the ISO lab

`scripts/lab/lab.sh` builds the ISO and installs it, and remains the test for what this lab skips: the image, the installer, the boot, ZFS on root. This lab starts from Ubuntu's own image, so it does not see what the remaster changes.
