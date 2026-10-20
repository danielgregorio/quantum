# Hive Stack - The Consciousness of DruidOS

## What It Is

The Hive Stack is the set of Rust daemons that form the "consciousness" of DruidOS. It is a local AI that **watches** what you do on the system and **offers smart suggestions**.

**Philosophy:** "The Swarm is watching. The Swarm is learning."

---

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER                                      │
│                     (terminal, commands)                            │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      hive-cortex (root)                             │
│                    CENTRAL ORCHESTRATOR                             │
│                                                                     │
│  - Receives events from all the nerves                              │
│  - Decides when to consult the AI                                   │
│  - Sends actions to the actuator                                    │
│  - Socket: /run/hive/cortex.sock                                    │
└────┬──────────┬──────────┬──────────┬──────────┬────────────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
│ nerve-  ││ nerve-  ││ nerve-  ││ nerve-  ││hive-    │
│ process ││ journal ││ network ││ fs      ││synapse  │
│         ││         ││         ││         ││         │
│Watches  ││Watches  ││Watches  ││Watches  ││BRAIN    │
│commands ││logs     ││ports    ││files    ││(AI/SLM) │
└─────────┘└─────────┘└─────────┘└─────────┘└────┬────┘
                                                  │
                                                  ▼
                                           ┌───────────┐
                                           │ Qwen 0.5B │
                                           │  (GGUF)   │
                                           │  469 MB   │
                                           └───────────┘
```

---

## The Components

### 1. hive-cortex (Orchestrator)
**Role:** Central brain that coordinates everything

```
User:    root
Socket:  /run/hive/cortex.sock
```

- Receives messages from all the other components via IPC
- Decides what to do with each event
- Keeps the context of the user's session
- Routes messages between components

**Example flow:**
```
nerve-process detects: "rm -rf /home/*"
       │
       ▼
cortex receives a "dangerous command" event
       │
       ▼
cortex sends to synapse: "user is going to delete home, what should we suggest?"
       │
       ▼
synapse answers: "Suggest a ZFS snapshot first"
       │
       ▼
cortex shows a notification to the user
```

---

### 2. hive-synapse (AI/Brain)
**Role:** Inference engine with a local language model

```
User:    _hive-ai (unprivileged)
Model:   Qwen 2.5 0.5B Instruct (Q4, 469MB)
```

- Runs a language model **100% locally** (no internet)
- Receives context from the cortex
- Generates suggestions in natural language
- Isolated in a sandbox (no network, no disk)

**Example:**
```
Input:  "User ran 'chmod 777 /etc/passwd'. History shows
         that they are trying to fix an SSH permission problem."

Output: "The chmod 777 command on /etc/passwd is dangerous and can
         break authentication. I suggest: chmod 644 /etc/passwd.
         For SSH, check ~/.ssh/authorized_keys with chmod 600."
```

---

### 3. hive-nerve-process (Command Observer)
**Role:** Monitors commands executed in the terminal

```
User:    _hive-sense (read-only)
```

- Intercepts commands before they run (via eBPF or auditd)
- Detects dangerous patterns: `rm -rf`, `chmod 777`, `dd if=/dev/zero`
- Sends events to the cortex

**Detected patterns:**
```yaml
- pattern: "rm -rf /"
  severity: critical
  action: block_and_warn

- pattern: "chmod 777"
  severity: high
  action: warn

- pattern: "curl | bash"
  severity: high
  action: warn
```

---

### 4. hive-nerve-journal (Log Observer)
**Role:** Monitors system logs in real time

```
User:    _hive-sense
Source:  journald (systemd)
```

- Detects errors and anomalies in the logs
- Correlates them with the user's actions
- Examples:
  - "nginx: bind() to 0.0.0.0:80 failed - Address already in use"
  - "sshd: Failed password for root from 192.168.1.100"

---

### 5. hive-nerve-network (Network Observer)
**Role:** Monitors ports and connections

```
User:    _hive-sense
```

- Detects port conflicts
- Monitors suspicious connections
- Example: "Port 3000 is already in use by the node process (PID 1234)"

---

### 6. hive-nerve-fs (Filesystem Observer)
**Role:** Monitors changes to critical files

```
User:    _hive-sense
Paths:   /etc, /var/log, /home
```

- Uses inotify to detect changes
- Alerts about modifications to configuration files
- Example: "/etc/nginx/nginx.conf was modified"

---

### 7. hive-actuator (Action Executor)
**Role:** Executes actions approved by the user

```
User:    _hive-act
```

- The only component that can DO things (not just watch)
- Whitelist of allowed actions
- Rate-limited for safety
- Examples of actions:
  - Create a ZFS snapshot
  - Restart a service
  - Fix a permission

---

### 8. hive-dashboard (Notification Panel)
**Role:** Shows suggestions/notifications and lets the user approve or dismiss them

```
Run manually by the user (like `top`) — no systemd service
```

- Connects to the cortex like any other component
- Each suggestion of a `Notification` becomes a navigable line
- Approving (Enter) sends `UserAction` — the cortex builds the `ActionRequest` and dispatches it to the actuator
- Dismissing (`d`/Esc) sends `UserDismiss`

---

## Complete Flow: A Real Example

```
1. User types: rm -rf /var/log/*

2. nerve-process detects a dangerous command
   └─> Sends to cortex: CommandObserved {
         cmd: "rm -rf /var/log/*",
         severity: high
       }

3. cortex analyzes and consults synapse
   └─> SuggestionRequest {
         context: "user wants to delete logs",
         history: [...latest commands...]
       }

4. synapse processes it with the local AI
   └─> SuggestionResponse {
         message: "Deleting /var/log can break logging.
                   Consider: journalctl --vacuum-size=500M",
         alternatives: ["logrotate -f", "truncate logs"]
       }

5. cortex stores the suggestions and notifies hive-dashboard
   (running in a separate terminal, like `top`)
   ┌────────────────────────────────────────┐
   │ Hive Dashboard                         │
   │ Log Anomaly — journalctl --vacuum-size │
   │ [Enter] approve  [d] dismiss           │
   └────────────────────────────────────────┘

6. User approves (Enter) → dashboard sends UserAction → cortex builds
   the real ActionRequest and dispatches it to the actuator
   └─> ActionRequest {
         action: CreateSnapshot { dataset: "rpool/var" }
       }
```

---

## Security

### Principle of Least Privilege

| Component | User | Can read | Can write | Network |
|------------|---------|----------|---------------|------|
| cortex | root | everything | IPC socket | no |
| synapse | _hive-ai | nothing | nothing | **no** |
| nerve-* | _hive-sense | logs, processes | nothing | no |
| actuator | _hive-act | nothing | whitelisted actions | no |
| dashboard | logged-in user | notifications | IPC socket | no |

### Synapse Isolation
```
- No network access (cannot "phone home")
- No disk access (cannot read your files)
- Only receives text from the cortex
- Only returns text to the cortex
- Restricted seccomp
```

---

## IPC Protocol

Communication via Unix sockets with bincode serialization:

```rust
pub enum HiveMessage {
    // Nerve -> Cortex
    CommandObserved { pid: u32, cmd: String, cwd: PathBuf },
    LogAnomaly { service: String, message: String },
    PortConflict { port: u16, process: String },
    FileChanged { path: PathBuf, action: FileAction },

    // Cortex -> Synapse
    SuggestionRequest { context: Context, query: Option<String> },

    // Synapse -> Cortex
    SuggestionResponse { suggestions: Vec<Suggestion> },

    // Cortex -> Actuator
    ActionRequest { action: Action, confirm: bool },

    // Actuator -> Cortex
    ActionResult { success: bool, output: String },
}
```

---

## Anonymous Mode

When the user wants privacy:

```bash
hive --quiet      # The Hive watches but does not show notifications
hive --detach     # This terminal is invisible to the Hive
hive --anonymous  # Isolated namespace, no logging
```

---

## Desktop Components (Archived)

The project's target was redefined as TUI-only. hive-shell, hive-dock and
hive-term (along with bark and spore, the framebuffer stack that
supported them) were moved to `archive/`, outside the active workspace.
The code remains in the git history in case the GUI becomes a priority again.

The role of "warning the user" that hive-shell fulfilled was taken over by
`hive-dashboard` — a separate TUI panel (ratatui), run manually
by the user, not a graphical overlay. See section 8 above.

---

## Current Status

| Component | Code | Compiled | Tested | Integrated |
|------------|--------|-----------|---------|-----------|
| hive-cortex | ✅ | ✅ | ✅ | ❌ |
| hive-synapse | ✅ | ✅ | ⚠️ mock | ❌ |
| hive-nerve-process | ✅ | ✅ | ✅ | ❌ |
| hive-nerve-journal | ✅ | ✅ | ✅ | ❌ |
| hive-nerve-network | ✅ | ✅ | ✅ | ❌ |
| hive-nerve-fs | ✅ | ✅ | ✅ | ❌ |
| hive-actuator | ✅ | ✅ | ✅ | ❌ |
| hive-dashboard | ✅ | ✅ | ✅ | ❌ |
| hive-shell | 📦 archived | - | - | - |
| hive-dock | 📦 archived | - | - | - |
| hive-term | 📦 archived | - | - | - |

**Legend:**
- ✅ Complete
- ⚠️ Partial (mock or limited)
- ❌ Not done
- 📦 Archived (code in `archive/`, outside the current scope)

---

## To Integrate into DruidOS

1. Copy the binaries to `/usr/bin/hive-*`
2. Create users: `_hive-ai`, `_hive-sense`, `_hive-act`
3. Create systemd services
4. Configure `/etc/hive/config.toml`
5. Copy the model to `/var/lib/hive/models/`
6. Enable the services at boot
