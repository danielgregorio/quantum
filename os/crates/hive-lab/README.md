# hive-lab: the Hive in a box

Most of what the Hive does is decided between its daemons. An event comes from a nerve, hive-cortex routes it and hive-synapse suggests. grove and the dashboard are told, an administrator approves, and the actuator is asked to act. None of that needs an ISO, an install or a VM.

hive-lab runs the **real hive-cortex and hive-synapse** and plays everything else:

| Role | Played as | What the lab does with it |
|---|---|---|
| a nerve | `hive-nerve-process`, user `_hive-sense` | injects what the system did: a crash, a port conflict, a full disk, a command |
| the actuator | `hive-actuator`, user `_hive-act` | receives the actions, **runs none of them**, answers "recorded, not executed" |
| grove | `grove`, user `druid` | asks questions, reports a missing program, goes anonymous |
| the dashboard | `hive-dashboard`, root | approves or dismisses suggestions |

Each role connects under the binary name and the user that hive-cortex checks, so the lab exercises the same identity rules as the system. The Hive's users exist only in the lab. Every daemon runs in a private mount namespace where the lab's own `/etc/passwd` and `/etc/group` are bound over the machine's, and the machine's files are never touched. This takes root, as in a container, a throwaway VM, or CI with sudo.

A session starts in about 0.2 s. The tapes below play in about 5 s together.

## Playing it by hand

The driver reads one JSON request per line on stdin and answers one JSON line per request:

```
$ cargo build --workspace
$ sudo target/debug/hive-lab
{"op":"start"}
{"op":"crash","service":"nginx.service","exit_code":1,"restarts":5}
{"op":"until","to":"dashboard","contains":"Restart nginx"}
{"op":"approve"}
{"op":"until","to":"actuator","type":"ActionRequest"}
{"op":"observe"}
{"op":"end"}
```

The ops:

| op | does |
|---|---|
| `start` (`synapse`: true) | hive-cortex, hive-synapse (mock inference when its model is absent; the rules that attach actions to events still apply) and the four roles |
| `crash`, `port_conflict`, `disk_low`, `command` | a nerve's observation, ready made |
| `inject` (`message`) | any `HiveMessage`, as JSON, from the nerve |
| `send` (`as`, `message`) | any message as any role, to check what a role may *not* do |
| `ask` (`text`), `not_found` (`command`, `package`), `anonymous` (`on`) | grove |
| `approve`, `dismiss` (`notification`, `suggestion`, `as`) | the dashboard; by default, the latest offer |
| `observe` | everything each role received since the last look |
| `until` (`to`, `type`, `contains`, `excludes`, `timeout`) | waits for a matching message; `excludes` is text it must not hold |
| `none` (`to`, `type`, `contains`, `within`) | nothing matching arrives, for example an action nobody approved |
| `tui` (`app`: dashboard or grove, `rows`, `cols`) | the **real** program in a pseudo-terminal: hive-dashboard as root, grove as the lab's user |
| `view` (`app`), `keys` (`app`, `keys`: ["Down", "Enter", "text"]), `until_screen` (`app`, `contains`, `excludes`) | its screen as text, through a terminal emulator: what a person sees, with no screenshot and no OCR |
| `log_until` (`daemon`, `contains`), `log` (`daemon`, `lines`) | the daemons' logs |
| `end` | stops everything and removes the lab's directory |

## As MCP tools

`os/scripts/lab/hive_mcp.py` serves the lab to an agent, declared in `.mcp.json` at the repository's root as `hive-lab`:

| Tool | Does |
|---|---|
| `hive_start` | starts the lab, building `os/` first if needed |
| `hive_request` | sends any request above |
| `hive_view` | shows the real dashboard's or grove's screen |
| `hive_tape` | saves the session's requests as a tape here, for CI to play |
| `hive_end` | stops the lab |

It runs the lab with `sudo -n` when it is not root. `python os/scripts/lab/hive_mcp.py --selftest` checks it end to end without an MCP client.

## Tapes

A tape is a file of requests, one per line, with `//` comments. `--play` runs it and exits 1 when a request fails, such as an `until` that times out or a `none` that sees something arrive. `--record FILE` turns a hand-played session into a tape.

```
scripts/lab/hive-tapes.sh            # builds, then plays every tape (sudo when not root)
sudo target/debug/hive-lab --play crates/hive-lab/tapes/crash-restart.jsonl
```

| Tape | What it holds the Hive to |
|---|---|
| `crash-restart` | a crash reaches grove and the dashboard; a restart is offered; nothing runs until approved; then the actuator is asked |
| `command-not-found` | a missing program gets an install offer; the install is asked only once approved |
| `port-conflict` | the shell is told who holds the port; listing the ports is offered |
| `disk-low` | a warning; `df -h` is offered |
| `question` | grove's question is answered as text, never as an action |
| `user-socket-boundary` | a user's shell cannot send an action, nor approve a suggestion |
| `dashboard-screen` | the real dashboard shows the crash and its offers, a plain notice is not shown as awaiting confirmation, Enter approves; a second dashboard's approval runs nothing again |
| `grove-screen` | the real grove runs a command, answers a question in plain language, and prints the crash notice at the next prompt |

`cargo test -p hive-lab` plays them too when it runs as root, and skips them otherwise, saying why.

## What it does not cover

The dashboard and grove are the real programs (`tui`), but they run against the lab's Hive. The nerves are not the real ones, so the lab does not test what they notice in a running system. The actuator runs nothing, so it does not test what an action does to the system. Both need the system itself. That is the job of a VM driven by a guest agent, which is the next layer, and, for boot and the installer, of the ISO lab in `scripts/lab/`.
