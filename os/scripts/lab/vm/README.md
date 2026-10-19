# The VM lab: the real system, restored in a second

The Hive lab (`crates/hive-lab`) runs the real hive-cortex and hive-synapse and plays everything else, in a fraction of a second. It cannot show what only the running system does: what the nerves notice in the journal, the audit log and `/proc`; what the actuator does through polkit and systemd; how the units, their sandboxes and their users behave together. This lab runs all of it for real, and still needs no ISO, no installer, no SSH and no OCR.

| | |
|---|---|
| the guest | Ubuntu 24.04's minimal cloud image (the release Quantum OS remasters), on a copy-on-write overlay |
| the agent | `agent.py`, in the guest: JSON lines over a virtio-serial port (commands, files, the journal, programs in a terminal) |
| the build | the working tree's binaries (debug sections stripped) and `config/`, over a read-only 9p share, installed by `install-hive.sh` as the ISO installs them |
| the speed | the guest boots once. The snapshot `base` keeps it booted with its packages, and `hive` keeps it with the Hive installed from the build. Restoring one takes about a second, with or without KVM |
| the screens | the real hive-dashboard and grove run in a terminal in the guest. `hive-lab term` renders them with the same terminal emulator as the Hive lab |

## Playing it

```bash
cargo build --workspace
python3 scripts/lab/vm/vm.py --play                  # every tape in scripts/lab/vm/tapes/
python3 scripts/lab/vm/vm.py --play scripts/lab/vm/tapes/crash-restart.jsonl
python3 scripts/lab/vm/vm.py                         # the driver: one JSON request per line on stdin
```

It needs `qemu-system-x86_64`, `qemu-img` and `genisoimage`. It uses KVM when `/dev/kvm` is usable and plain emulation otherwise. The first run downloads the cloud image (260 MB) and makes `base`. On a host without KVM this takes a few minutes, mostly the first boot. The guest's missing packages (polkit, PackageKit, auditd) are downloaded by the host's apt for the guest's own dpkg status, so the guest needs no network; this needs an Ubuntu 24.04 host. After that:

- an unchanged build restores `hive` (about a second);
- a changed build (any binary, `config/`, `install-hive.sh`) restores `base`, installs and saves `hive` again.

Everything lives in `~/.cache/quantum-os-lab`, or `QUANTUM_LAB_CACHE`. A run's evidence is in `run/` there: `serial.log`, `qemu.cmdline`.

## The requests

The same shape as the Hive lab's: `{"op": ...}` in, `{"ok": true, ...}` or `{"ok": false, "error": ...}` out.

| op | does |
|---|---|
| `start` | a fresh Hive: restores `hive`, installing first when the build changed |
| `restore` (`snapshot`: hive), `save` (`snapshot`) | go back to a snapshot; keep one of your own to try something and come back |
| `install` | stage the build again and install it in place (the fast loop after `cargo build`) |
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
| `crash-restart` | a unit in a real restart loop is seen by the journal nerve, shown once on the real dashboard, and restarted by the real actuator through polkit only once someone approves it with the keyboard |
| `port-conflict` | a real process holds a port and a unit keeps failing to bind it: the network nerve names both, once; listing the ports runs once approved |

`--play` runs tapes one after the other on one VM. Each tape's `start` restores a fresh Hive.

## What it found

- A unit in a restart loop flooded the Hive. Every crash reached the model, and each one stacked "Service Crashed" and its offers on every dashboard again. hive-cortex now passes a problem on once every five minutes, and says how many reports it held (`router.rs`, `news`).
- The network nerve's own five-minute window never held anything: its key held the pid, which changes with every retry. It is now the unit.

## And the ISO lab

`scripts/lab/lab.sh` builds the ISO and installs it, and remains the test for what this lab skips: the image, the installer, the boot, ZFS on root. This lab starts from Ubuntu's own image, so it does not see what the remaster changes.
