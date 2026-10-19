# DruidOS Security Model

This document describes the security architecture of the Hive Stack.

## Design Principles

1. **Least Privilege**: Each component runs with minimal permissions
2. **Defense in Depth**: Multiple layers of protection
3. **Transparency**: User can see what the Hive observes
4. **Escape Hatch**: Anonymous mode when privacy is needed

## System Users

The Hive Stack uses dedicated system users:

| User | UID | Component | Purpose |
|------|-----|-----------|---------|
| root | 0 | hive-cortex | System orchestration |
| _hive-ai | 990 | hive-synapse | AI inference |
| _hive-sense | 991 | hive-nerve-* | System observation |
| _hive-act | 992 | hive-actuator | Action execution |

## Component Security

### hive-cortex (root)

The only component running as root. Responsibilities:
- Socket management with proper permissions
- Peer credential authentication
- Message routing between components

**Restrictions**:
- Only accepts connections from known components
- Validates all incoming messages
- No direct command execution

### hive-synapse (_hive-ai)

The AI inference engine is heavily sandboxed:

**Restrictions**:
- No network access (network namespace)
- No filesystem access except model files
- Seccomp filter restricts syscalls
- Memory limited to 2GB
- CPU limited to prevent denial of service

**Seccomp Policy**:
```
Allowed syscalls:
- read, write, mmap, munmap (memory operations)
- futex, nanosleep (synchronization)
- clock_gettime (timing)
- exit, exit_group

Blocked syscalls:
- All network operations
- All filesystem operations except read
- fork, exec, clone
- ioctl, ptrace
```

### hive-nerve-* (_hive-sense)

Observer components with read-only access:

| Component | Access |
|-----------|--------|
| nerve-process | /proc (read) |
| nerve-journal | journald socket |
| nerve-network | /proc/net (read) |
| nerve-fs | inotify on specific paths |

**Restrictions**:
- Cannot modify observed files
- Cannot execute commands
- Limited to specific observation paths

### hive-actuator (_hive-act)

Action executor with strict whitelist:

**Whitelist Categories**:
1. Package management (apt install/remove)
2. Service control (systemctl start/stop/restart)
3. File operations (copy, move, delete in safe paths)
4. System commands (safe subset)

**Restrictions**:
- All actions must match whitelist
- Rate limiting (max 10 actions per minute)
- All actions logged to syslog
- No shell expansion or injection possible

## IPC Security

### Unix Socket Permissions

```
/run/hive/cortex.sock        the Hive's own components
  Owner: root
  Group: hive
  Permissions: 0660

/run/hive/user.sock          users (grove)
  Owner: root
  Group: hive
  Permissions: 0666
```

Any local user can connect to `user.sock`. A connection there is a shell
(allowed: `UserQuery`, `CommandNotFound`, `AnonymousModeEnter`/`Exit`,
`Ping`) unless it is `hive-dashboard` run by an administrator - root, or an
account in the sudo, admin or wheel group, looked up from the uid the kernel
reports (`SO_PEERCRED`), not from anything the process claims - which may
send `UserAction`, `UserDismiss` and `Ping`. A dashboard from anyone else is
refused. Everything else is dropped before routing. A shell can only make its own pid anonymous; it receives
answers to its own questions (text only, actions stripped) and system
notices, never suggestions, which can concern another user's commands.

### Peer Credential Verification

Every connection is authenticated using SO_PEERCRED:
- Component type is guessed from the process name (`/proc/{pid}/comm`),
  then cross-checked against the connection's real uid (`hive-cortex`'s
  `verify_component_identity`) — a claimed type that doesn't match the
  uid its systemd unit should be running as gets downgraded to `Unknown`
  rather than trusted.

### Message Validation

All messages are:
1. Length-prefixed (prevents buffer overflow)
2. Deserialized with strict typing (prevents injection)
3. Validated for required fields
4. Logged for audit

## Anonymous Mode

### Levels

| Level | Observation | Notifications | Logging |
|-------|-------------|---------------|---------|
| Quiet | Yes | No | Yes |
| Detach | No | No | No |
| Full | No | No | No (namespace) |

### Implementation

**Quiet Mode**:
- Suppresses notifications to the user (delivery mechanism TBD — no GUI
  overlay anymore; see "Open Questions" in CLAUDE.md)
- Observations still recorded internally
- Can be toggled per-session

**Detach Mode**:
- Process PID added to anonymous set
- Observations for PID are dropped
- Child processes inherit status

**Full Mode**:
- New user namespace created
- No connection to Hive Stack
- Completely isolated environment

### Entering Anonymous Mode

```bash
# Via environment variable, before launching your shell
HIVE_ANONYMOUS=quiet grove

# Via command
hive anonymous --level detach
```

(There is no dedicated terminal emulator or keyboard shortcut anymore — see CLAUDE.md. `HIVE_ANONYMOUS` is read at process start, same as before.)

## Action Whitelist

The real schema (`config/hive/whitelist.toml`, parsed by
`crates/hive-actuator/src/whitelist.rs`) corresponds directly to the
`Action` enum — one table per action family, matched by exact command +
positional args, or by glob (`*`) for paths/services/packages:

```toml
[run_command]
allowed = [
    { command = "systemctl", args = ["status", "*"] },
]

[service]
allowed = ["nginx", "postgresql"]
blocked = ["hive-*", "systemd-*", "sshd"]

[file_ops]
allowed_paths = ["/home/*", "/tmp/*"]
blocked_paths = ["/etc/*", "/usr/*", "/root/*"]
```

Everything not explicitly listed is denied — an empty or missing config
denies all actions (fail closed), not "allow with defaults."

### Confirmation Required

High-risk actions require user confirmation:
- Package removal
- Service stop/restart
- File deletion
- Any action matching `auto_snapshot: true`

## Audit Logging

All Hive Stack actions are logged:

```
/var/log/hive/audit.log
```

Log format:
```
timestamp | component | action | user | result | details
```

Example:
```
2024-01-15T10:30:00Z | actuator | install_package | druid | success | package=htop
2024-01-15T10:31:00Z | actuator | service_restart | druid | denied | service=sshd (blocked)
```

## Network Security

### hive-synapse Network Isolation

The synapse component runs in an isolated network namespace:

```bash
# Created at startup
ip netns add hive-synapse
ip netns exec hive-synapse ip link set lo up
```

No routes are configured, preventing any network access.

### No External Connections

The Hive Stack never makes external network connections:
- Models are loaded from local files
- Knowledge base is local YAML
- All inference is on-device

## Updates and Integrity

### Package Signing

All DruidOS packages are signed with GPG:
- Repository key: `/etc/apt/keyrings/druidos.gpg`
- Packages verified before installation

### Hive Binary Verification

Hive binaries can be verified:
```bash
sha256sum /usr/bin/hive-* | sha256sum -c /etc/hive/checksums.sha256
```

## Incident Response

### Suspicious Activity Detection

The Hive Stack monitors for:
- Unusual privilege escalation attempts
- Unauthorized file access
- Network anomalies
- Service crashes

### Automatic Responses

Low-risk responses (configurable):
- Create ZFS snapshot before risky operation
- Alert user to suspicious activity
- Log detailed information

### User Notification

Users are always notified of:
- Blocked actions
- Security-relevant observations
- Recommended security improvements

## Best Practices

1. **Keep anonymous mode available** - Users should always have an escape hatch
2. **Review audit logs** - Periodically check /var/log/hive/audit.log
3. **Update regularly** - Security fixes are distributed via apt
4. **Report issues** - Security vulnerabilities should be reported to security@druidos.org
