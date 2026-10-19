# Quantum OS

> **Experimental.** Quantum OS is a working directory, not a release: it may change in any commit.

Quantum OS is a Linux distribution for virtual machines. It remasters Ubuntu Server 24.04 without the third-party drivers a VM never needs. Its terminal shell, `grove`, is the interface, and the Hive watches the system and offers help.

The Hive is a set of Rust daemons:
- `hive-nerve-*` observe the system;
- `hive-cortex` routes what they see;
- `hive-synapse` suggests, with a small local model;
- `hive-actuator` runs only whitelisted, typed actions an administrator approved.

It starts as [DruidOS](https://github.com/danielgregorio/druidos), whose history stays in that repository. This directory begins at its commit `bbcf319`, plus `crates/hive-lab`. The names inside (`druidos-*` packages, `hive-*`, `grove`) are still DruidOS's.

## Why it lives in the Quantum repository

The two share an idea. In Quantum, a game is written in tags with no script, and the compiler refuses anything its schema does not declare. In Quantum OS, the Hive acts only through typed actions on a whitelist that fails closed, and the model's text never becomes an action.

They also share a way of working. Quantum's games have a play protocol, through which an agent plays a game and turns the session into a test. Quantum OS has two labs that do the same for the system, without ISO builds:
- the Hive lab (`crates/hive-lab`) runs the real hive-cortex and hive-synapse and plays the rest, in a fraction of a second;
- the VM lab (`scripts/lab/vm`) runs the whole system for real in a VM, restored from a snapshot in about a second.

Next is declaring the Hive's rules in Quantum and compiling them to what the daemons load.

## Working on it

```bash
cd os
cargo build --workspace
scripts/lab/hive-tapes.sh        # the Hive in a box: the real cortex and synapse, no VM, ~5 s
python3 scripts/lab/vm/vm.py --play   # the real system in a VM restored from a snapshot
./scripts/check.sh               # fmt, clippy, tests
```

- `CLAUDE.md` is the development guide: the architecture, the security model, the conventions and the labs.
- `crates/hive-lab/README.md` describes the Hive lab, and `scripts/lab/vm/README.md` the VM lab.
- `DEVLOG.md` and `STATUS.md` are DruidOS's history (in Portuguese); new entries go at the top of the DEVLOG.

## License

MIT, as DruidOS.
