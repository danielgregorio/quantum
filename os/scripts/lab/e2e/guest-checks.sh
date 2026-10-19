#!/usr/bin/env bash
# DruidOS end-to-end checks. Runs INSIDE an installed DruidOS guest, as root,
# pushed there over SSH by scripts/lab/harness.py (e2e command).
#
# Output is TAP-like - one "ok N - name" / "not ok N - name" line per check,
# with diagnostics on indented "#" lines - which the harness turns into
# result.json steps. Exit status is the number of failed checks.
#
# Checks are ordered so an early failure still lets later, independent
# checks report (no set -e).
set -uo pipefail

n=0
failures=0

pass() {
    n=$((n + 1))
    echo "ok $n - $1"
}

fail() {
    n=$((n + 1))
    failures=$((failures + 1))
    echo "not ok $n - $1"
    [ -n "${2:-}" ] && printf '%s\n' "$2" | tail -n 40 | sed 's/^/#   /'
}

# check NAME COMMAND... - passes when COMMAND exits 0; its output is the
# diagnostic shown on failure.
check() {
    local name=$1 out
    shift
    if out=$("$@" 2>&1); then
        pass "$name"
    else
        fail "$name" "$out"
    fi
}

HIVE_UNITS=(
    hive-cortex hive-synapse hive-actuator
    hive-nerve-process hive-nerve-journal hive-nerve-network hive-nerve-fs
)
BINARIES=("${HIVE_UNITS[@]}" hive-apt hive-zfs hive-dashboard grove)

journal_cursor() {
    journalctl --no-pager -n 0 --show-cursor | sed -n 's/^-- cursor: //p'
}

# Journal window the checks judge. Normally the whole boot; after a
# hot-swap (harness e2e --hotswap) only what happened since the swap, so
# the old binaries' failures don't count against the new ones.
if [ -n "${CHECK_CURSOR:-}" ]; then
    SINCE=(--after-cursor="$CHECK_CURSOR")
else
    SINCE=(-b)
fi
# The daemons' tracing output carries ANSI color codes into the journal;
# strip them so diagnostics stay readable.
jctl() {
    journalctl --no-pager -o cat "${SINCE[@]}" "$@" | sed 's/\x1b\[[0-9;]*m//g'
}

# The local model takes seconds per answer and queues bursts of requests.
# Checks that need a specific answer first wait for synapse to catch up:
# every request received has been answered or dropped.
wait_for_synapse_idle() {
    local received answered dropped
    for _ in $(seq 1 90); do
        received=$(jctl -u hive-synapse | grep -c "Received suggestion request")
        answered=$(jctl -u hive-synapse | grep -c "Sent suggestion response")
        dropped=$(jctl -u hive-synapse | grep -c "Busy: dropped suggestion request")
        [ $((received - answered - dropped)) -le 0 ] && return 0
        sleep 2
    done
    return 1
}

# ---------------------------------------------------------------- identity
check "os-release identifies DruidOS" grep -qx 'ID=druidos' /etc/os-release

check "hive binaries installed" bash -c '
    for b in "$@"; do test -x "/usr/bin/$b" || { echo "missing /usr/bin/$b"; exit 1; }; done
' _ "${BINARIES[@]}"

check "hive group and service users exist" bash -c '
    getent group hive || exit 1
    for u in _hive-ai _hive-sense _hive-act; do id "$u" || exit 1; done'

check "hive config installed" test -f /etc/hive/config.toml -a -f /etc/hive/whitelist.toml

# ---------------------------------------------------------------- units
# systemd-analyze verify re-parses the installed units on demand. (Grepping
# the journal for parse warnings misses them: PID 1 reports those while
# loading units early in boot, before journald is capturing.)
unit_warnings=$(systemd-analyze verify /etc/systemd/system/hive-*.service 2>&1 \
    | grep -E "hive-[a-z-]+\.service:[0-9]+:")
if [ -n "$unit_warnings" ]; then
    fail "hive unit files parse without warnings" "$unit_warnings"
else
    pass "hive unit files parse without warnings"
fi

# Give the stack time to settle: every unit active, or give up after 120s.
settled=false
for _ in $(seq 1 60); do
    all_active=true
    for unit in "${HIVE_UNITS[@]}"; do
        systemctl is-active --quiet "$unit" || all_active=false
    done
    if $all_active; then
        settled=true
        break
    fi
    sleep 2
done
# A crash-looping unit can look active between restarts (RestartSec=5):
# watch a little longer before trusting the restart counters.
$settled && sleep 12

for unit in "${HIVE_UNITS[@]}"; do
    # Compare as sorted Key=Value pairs: `systemctl show --value` prints
    # properties in systemd's own order, not the order they were requested.
    state=$(systemctl show "$unit" -p ActiveState -p SubState -p NRestarts | sort | paste -sd' ')
    if [[ "$state" == "ActiveState=active NRestarts=0 SubState=running" ]]; then
        pass "$unit active, no restarts"
    else
        fail "$unit active, no restarts" "$state
$(jctl -u "$unit" | tail -n 25)"
    fi
done

# ---------------------------------------------------------------- IPC
check "cortex socket is root:hive 0660" bash -c '
    got=$(stat -c "%F %a %U:%G" /run/hive/cortex.sock) || exit 1
    echo "$got"; [ "$got" = "socket 660 root:hive" ]'

cortex_log=$(jctl -u hive-cortex)
for component in Synapse Actuator NerveProcess NerveJournal NerveNetwork NerveFs; do
    if grep -qE "Registered connection [0-9]+ as $component\$" <<< "$cortex_log"; then
        pass "cortex registered $component"
    else
        fail "cortex registered $component" "$(tail -n 4 <<< "$cortex_log")"
    fi
done

if panics=$(jctl -u 'hive-*' | grep -i -B2 -A5 "panicked"); then
    fail "no panics in hive logs" "$panics"
else
    pass "no panics in hive logs"
fi

# ---------------------------------------------------------------- main flow
# Safe dangerous commands: a real `rm -rf` whose path normalizes to /etc but
# ends in "..", which the kernel can't resolve (the directory doesn't exist)
# and GNU rm refuses to remove anyway. The nerve must judge it by the
# normalized path; nothing is deleted.
flow_cursor=$(journal_cursor)
canary="druidos-e2e-canary-$$"
rm -rf "/etc/$canary/.." 2> /dev/null

flow_logs() {
    journalctl --no-pager -o cat --after-cursor="$flow_cursor" \
        -u hive-nerve-process -u hive-cortex -u hive-synapse | sed 's/\x1b\[[0-9;]*m//g'
}
detected=false
responded=false
for _ in $(seq 1 120); do
    flow_logs | grep -q "Detected dangerous command.*$canary" && detected=true
    $detected && flow_logs | grep -q "Sent suggestion response" && responded=true
    $responded && break
    sleep 1
done

if $detected; then
    pass "nerve-process detects a dangerous-looking command"
else
    fail "nerve-process detects a dangerous-looking command" "$(flow_logs | tail -n 20)"
fi
if $responded; then
    pass "synapse answers the resulting suggestion request"
else
    fail "synapse answers the resulting suggestion request" "$(flow_logs | tail -n 20)"
fi
if jctl -u hive-synapse | grep -qE "Generated [0-9]+ tokens in [0-9]+ ms with candle" \
    && ! jctl -u hive-synapse | grep -q "using mock inference"; then
    pass "synapse answers with the local model, not the mock"
else
    fail "synapse answers with the local model, not the mock" \
        "$(jctl -u hive-synapse | grep -iE "model|mock|candle|Generated|Inference" | tail -n 6)"
fi

# Real one-shot commands are over in a millisecond or two - far quicker than
# any /proc polling interval. Every single one must still be seen.
if auditctl -l 2> /dev/null | grep -q "key=hive-exec"; then
    pass "auditd loads the Hive's exec audit rule"
else
    fail "auditd loads the Hive's exec audit rule" "$(auditctl -l 2>&1 | head -n 5)"
fi
fast_cursor=$(journal_cursor)
fast_total=20
for i in $(seq 1 "$fast_total"); do
    rm -rf "/etc/druidos-e2e-fast-$$-$i/.." 2> /dev/null
done
sleep 5
fast_seen=$(journalctl --no-pager -o cat --after-cursor="$fast_cursor" -u hive-nerve-process \
    | grep -cE "(^|hive_nerve_process: )Detected dangerous command 'rm': rm -rf /etc/druidos-e2e-fast-$$-[0-9]+/\.\. \(")
if [ "$fast_seen" -eq "$fast_total" ]; then
    pass "nerve-process catches every fast one-shot dangerous command"
else
    fail "nerve-process catches every fast one-shot dangerous command" \
        "detected $fast_seen of $fast_total \`rm -rf\` runs"
fi

# Dangerous is judged on the program actually run and its parsed arguments,
# with paths resolved against its working directory - not on text found
# anywhere in a command line.
judge_cursor=$(journal_cursor)
(cd /etc && rm -rf "druidos-e2e-relative-$$/..") 2> /dev/null
grep -c "rm -rf /druidos-e2e-mention-$$" /dev/null > /dev/null
rm -rf "/tmp/druidos-e2e-scratch-$$"
sleep 4
judged() {
    journalctl --no-pager -o cat --after-cursor="$judge_cursor" -u hive-nerve-process | grep "$1"
}
if judged "druidos-e2e-relative-$$/\.\." > /dev/null; then
    pass "nerve-process resolves a relative rm -rf against its working directory"
else
    fail "nerve-process resolves a relative rm -rf against its working directory" \
        "$(journalctl --no-pager -o cat --after-cursor="$judge_cursor" -u hive-nerve-process | tail -n 5)"
fi
if flagged=$(judged "druidos-e2e-mention-$$"); then
    fail "a command merely mentioning rm -rf / is not flagged" "$flagged"
else
    pass "a command merely mentioning rm -rf / is not flagged"
fi
if flagged=$(judged "druidos-e2e-scratch-$$"); then
    fail "rm -rf of scratch space under /tmp is not flagged" "$flagged"
else
    pass "rm -rf of scratch space under /tmp is not flagged"
fi

# ---------------------------------------------------------------- nerve-fs
# Settings come from /etc/hive/config.toml ([nerves.filesystem] watches
# /etc and /home), and an unprivileged nerve must keep watching everything
# it can read even when some subdirectory (/etc/ssl/private, a 0750 home
# directory) is off limits.
fs_log=$(jctl -u hive-nerve-fs)
if grep -q "Failed to watch" <<< "$fs_log" \
    || ! grep -q "Watching /etc: " <<< "$fs_log" \
    || ! grep -q "Watching /home: " <<< "$fs_log" \
    || grep -q "/var/log" <<< "$fs_log"; then
    fail "nerve-fs watches the configured paths, skipping only unreadable dirs" \
        "$(grep -iE "watch|config" <<< "$fs_log" | tail -n 12)"
else
    pass "nerve-fs watches the configured paths, skipping only unreadable dirs"
fi

fs_cursor=$(journal_cursor)
# Under /etc/hive, not /etc itself: removing a whole top-level /etc entry
# with rm -rf is (rightly) a dangerous command, and cleanup shouldn't be one.
fs_canary_dir="/etc/hive/druidos-e2e-fs-$$"
echo "nested = true" > "/etc/hive/druidos-e2e-canary-$$.conf"
mkdir "$fs_canary_dir"
sleep 1 # the nerve adds watches for new directories as it sees them
echo "created = true" > "$fs_canary_dir/new-dir.conf"
fs_reported() {
    journalctl --no-pager -o cat --after-cursor="$fs_cursor" -u hive-nerve-fs \
        | grep -q "Config file modified: $1"
}
for _ in $(seq 1 15); do
    fs_reported "/etc/hive/druidos-e2e-canary-$$.conf" && fs_reported "$fs_canary_dir/new-dir.conf" && break
    sleep 1
done
for canary in "/etc/hive/druidos-e2e-canary-$$.conf" "$fs_canary_dir/new-dir.conf"; do
    if fs_reported "$canary"; then
        pass "nerve-fs reports a write to $(dirname "$canary")/*.conf"
    else
        fail "nerve-fs reports a write to $(dirname "$canary")/*.conf" \
            "$(journalctl --no-pager -o cat --after-cursor="$fs_cursor" -u hive-nerve-fs | tail -n 10)"
    fi
done
if journalctl --no-pager -o cat --after-cursor="$fs_cursor" -u hive-cortex \
    | grep -q "Notification from Some(NerveFs): Filesystem Event: Config file modified: /etc/hive/druidos-e2e-canary-$$.conf"; then
    pass "cortex accepts nerve-fs notifications"
else
    fail "cortex accepts nerve-fs notifications" \
        "$(journalctl --no-pager -o cat --after-cursor="$fs_cursor" -u hive-cortex | tail -n 10)"
fi
rm -rf "/etc/hive/druidos-e2e-canary-$$.conf" "$fs_canary_dir"

# ---------------------------------------------------------------- nerve-journal
# A service logging a crash-like error gets reported...
journal_canary="druidos-e2e-journal-$$"
journal_cursor_before=$(journal_cursor)
# The logging process stays alive a moment: journald looks up the sender's
# cgroup (-> _SYSTEMD_UNIT) when it handles the entry, and a process that has
# already exited by then gets logged without a unit (flaky otherwise).
systemd-run --quiet --wait --unit="$journal_canary" \
    sh -c "(echo 'fatal error: e2e canary'; sleep 2) | systemd-cat -t $journal_canary -p err" > /dev/null
journal_reported_since() { # cursor
    journalctl --no-pager -o cat --after-cursor="$1" -u hive-nerve-journal \
        | grep -q "Reported service crash: $journal_canary.service"
}
for _ in $(seq 1 15); do
    journal_reported_since "$journal_cursor_before" && break
    sleep 1
done
if journal_reported_since "$journal_cursor_before"; then
    pass "nerve-journal reports a service logging a crash"
else
    fail "nerve-journal reports a service logging a crash" \
        "$(journalctl --no-pager -o cat --after-cursor="$journal_cursor_before" -u hive-nerve-journal | tail -n 10)"
fi
# ...but only once: a restarted nerve must not replay journal history.
journal_cursor_restart=$(journal_cursor)
systemctl restart hive-nerve-journal
sleep 5
if journal_reported_since "$journal_cursor_restart"; then
    fail "restarted nerve-journal does not re-report old entries" \
        "$(journalctl --no-pager -o cat --after-cursor="$journal_cursor_restart" -u hive-nerve-journal | tail -n 10)"
else
    pass "restarted nerve-journal does not re-report old entries"
fi

# ---------------------------------------------------------------- nerve-network
# One process listening on both IPv4 and IPv6 - what nginx does with
# `listen 80; listen [::]:80;` - is two LISTEN sockets on one port, and not
# a conflict. It stays up as the holder for the real conflict below.
net_port=8080
# Before the holder starts: the wait can outlast any fixed holder lifetime.
wait_for_synapse_idle
net_cursor=$(journal_cursor)
runuser -u nobody -- python3 - "$net_port" << 'EOF' &
import socket, sys, time
port = int(sys.argv[1])
v4 = socket.socket()
v4.bind(("0.0.0.0", port))
v4.listen()
v6 = socket.socket(socket.AF_INET6)
v6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
v6.bind(("::", port))
v6.listen()
time.sleep(600)  # killed explicitly once the checks are done
EOF
net_holder_pid=$!
sleep 12 # longer than the nerve's old 5s port poll
net_logs() { # cursor [units...]
    local cursor=$1
    shift
    journalctl --no-pager -o cat --after-cursor="$cursor" "${@/#/--unit=}" | sed 's/\x1b\[[0-9;]*m//g'
}
if net_logs "$net_cursor" hive-nerve-network | grep -q "port conflict on port $net_port"; then
    fail "nerve-network does not call a dual-stack listener a conflict" \
        "$(net_logs "$net_cursor" hive-nerve-network | tail -n 5)"
else
    pass "nerve-network does not call a dual-stack listener a conflict"
fi

# A real conflict: a service that can't bind the port because it's taken,
# failing the way nginx reports it on stderr.
conflict_cursor=$(journal_cursor)
systemd-run --quiet --wait --unit=druidos-e2e-binder python3 -c "
import socket, sys
try:
    socket.socket().bind(('0.0.0.0', $net_port))
except OSError as e:
    print(f'nginx: [emerg] bind() to 0.0.0.0:$net_port failed ({e.errno}: {e.strerror})', file=sys.stderr)
    sys.exit(1)
" 2> /dev/null
for _ in $(seq 1 120); do
    net_logs "$conflict_cursor" hive-synapse | grep -q "Suggesting 'Show listening ports'" && break
    sleep 1
done
conflict_report=$(net_logs "$conflict_cursor" hive-nerve-network | grep "Reported port conflict on port $net_port" | head -n 1)
if grep -q "druidos-e2e-binder.service" <<< "$conflict_report" && grep -q "held by user nobody" <<< "$conflict_report"; then
    pass "nerve-network reports a service failing to bind a taken port, and who holds it"
else
    fail "nerve-network reports a service failing to bind a taken port, and who holds it" \
        "report: ${conflict_report:-(none)}
$(net_logs "$conflict_cursor" hive-nerve-network | tail -n 5)"
fi
if net_logs "$conflict_cursor" hive-synapse | grep -q "Suggesting 'Show listening ports'"; then
    pass "a port conflict reaches synapse and gets an actionable suggestion"
else
    fail "a port conflict reaches synapse and gets an actionable suggestion" \
        "$(net_logs "$conflict_cursor" hive-cortex hive-synapse | tail -n 8)"
fi
kill "$net_holder_pid" 2> /dev/null
wait "$net_holder_pid" 2> /dev/null

# ---------------------------------------------------------------- logging
# Daemons write to the journal, not a terminal: no color escape codes.
# (-F: as a regex, the "[" would open an unterminated bracket expression,
# grep would exit 2, and the check would pass vacuously.)
if ansi=$(journalctl --no-pager -o cat "${SINCE[@]}" -u 'hive-*' | grep -F -m 3 $'\x1b['); then
    fail "hive logs are free of ANSI escape codes" "$(sed 's/\x1b/<ESC>/g' <<< "$ansi")"
else
    pass "hive logs are free of ANSI escape codes"
fi

# ---------------------------------------------------------------- log priorities
# A Hive warning must reach the journal as a warning, so `journalctl -p
# warning` and priority-based tooling see it. And once it does, nerve-journal
# (which watches warnings and worse) must not report the Hive's own logs back
# into the Hive - that would be a feedback loop.
# nerve-fs is pointed at five missing paths: five real warnings, enough for
# nerve-journal's anomaly threshold if it were listening to the Hive.
cp /etc/hive/config.toml /tmp/config.toml.orig
python3 - << 'EOF'
import re
path = "/etc/hive/config.toml"
text = open(path).read()
missing = "".join(f'\n    "/druidos-e2e-missing-{i}",' for i in range(1, 6))
text, count = re.subn(r"(\[nerves\.filesystem\][^\[]*?watch_paths = \[)", lambda m: m.group(1) + missing, text, count=1)
assert count == 1, "no [nerves.filesystem] watch_paths in config.toml"
open(path, "w").write(text)
EOF
prio_cursor=$(journal_cursor)
systemctl restart hive-nerve-fs
sleep 5
if journalctl --no-pager -o cat --after-cursor="$prio_cursor" -u hive-nerve-fs -p warning \
    | grep -q "Path does not exist, skipping: /druidos-e2e-missing"; then
    pass "Hive warnings carry warning priority in the journal"
else
    fail "Hive warnings carry warning priority in the journal" \
        "priorities of hive-nerve-fs's lines since restart: $(journalctl --no-pager -o json --after-cursor="$prio_cursor" -u hive-nerve-fs \
            | grep -o '"PRIORITY":"[0-9]"' | sort | uniq -c | tr '\n' ' ')"
fi
if own=$(journalctl --no-pager -o cat --after-cursor="$prio_cursor" -u hive-nerve-journal | grep "hive-nerve-fs"); then
    fail "nerve-journal does not report the Hive's own warnings" "$own"
else
    pass "nerve-journal does not report the Hive's own warnings"
fi
cp /tmp/config.toml.orig /etc/hive/config.toml
systemctl restart hive-nerve-fs

# ---------------------------------------------------------------- interfaces
check "grove executes a builtin from stdin" bash -c '
    out=$(printf "echo grove-e2e-ok\nexit\n" | timeout 10 grove 2>&1); echo "$out"
    grep -q grove-e2e-ok <<< "$out"'

# grove is the only user-facing shell: it has to run real programs.
check "grove runs programs through pipes and redirections" bash -c '
    out=$(timeout 10 grove -c "grep ^ID= /etc/os-release | cut -d= -f2 > /tmp/grove-e2e-id; cat /tmp/grove-e2e-id" 2>&1)
    echo "$out"; [ "$out" = "druidos" ]'
# Interactive: Ctrl-C stops the running program, not the shell.
tmux new-session -d -s e2e-grove -x 120 -y 30 grove
sleep 1
tmux send-keys -t e2e-grove "sleep 3$$" Enter
sleep 1
tmux send-keys -t e2e-grove C-c
sleep 1
tmux send-keys -t e2e-grove "echo grove-survived-$$" Enter
sleep 1
grove_screen=$(tmux capture-pane -p -t e2e-grove 2> /dev/null)
tmux kill-session -t e2e-grove 2> /dev/null
# The marker shows up twice when grove ran it: the typed line and its output.
if [ "$(grep -c "grove-survived-$$" <<< "$grove_screen")" -ge 2 ] && ! pgrep -x -f "sleep 3$$" > /dev/null; then
    pass "Ctrl-C in grove stops the program and leaves the shell running"
else
    fail "Ctrl-C in grove stops the program and leaves the shell running" "$(grep -v '^\s*$' <<< "$grove_screen" | tail -n 8)"
fi

# ...and whatever it runs is observed like any other command.
grove_cursor=$(journal_cursor)
timeout 10 grove -c "rm -rf /etc/druidos-e2e-grove-$$/.." > /dev/null 2>&1
sleep 3
if journalctl --no-pager -o cat --after-cursor="$grove_cursor" -u hive-nerve-process \
    | grep -q "druidos-e2e-grove-$$/\.\."; then
    pass "a dangerous command run from grove is observed by the Hive"
else
    fail "a dangerous command run from grove is observed by the Hive" \
        "$(journalctl --no-pager -o cat --after-cursor="$grove_cursor" -u hive-nerve-process | tail -n 5)"
fi

# ---------------------------------------------------------------- grove and the Hive
# grove is where users are, so the Hive has to be reachable from it - by any
# local user, not just root: questions in plain language (`? ...`), notices
# about the system at the prompt, and `anon` to go unobserved. Through a
# socket of its own that only takes those user messages; the component
# socket stays root:hive.
check "cortex user socket is open to local users, component socket is not" bash -c '
    user=$(stat -c "%F %a %U:%G" /run/hive/user.sock) || exit 1
    comp=$(stat -c "%F %a %U:%G" /run/hive/cortex.sock) || exit 1
    echo "user: $user / component: $comp"
    [ "$user" = "socket 666 root:hive" ] && [ "$comp" = "socket 660 root:hive" ]'

grove_user=$(getent passwd 1000 | cut -d: -f1)
wait_for_synapse_idle
ask_cursor=$(journal_cursor)
ask_out=$(runuser -u "$grove_user" -- timeout 150 grove -c "? how do I see which services failed" 2>&1)
if grep -q "^\[hive\] ." <<< "$ask_out" \
    && journalctl --no-pager -o cat --after-cursor="$ask_cursor" -u hive-cortex \
        | grep -q "Question from uid $(id -u "$grove_user")"; then
    pass "an unprivileged user asks the Hive a question from grove and gets an answer"
else
    fail "an unprivileged user asks the Hive a question from grove and gets an answer" \
        "grove output:
$ask_out
--- cortex/synapse:
$(journalctl --no-pager -o cat --after-cursor="$ask_cursor" -u hive-cortex -u hive-synapse | sed 's/\x1b\[[0-9;]*m//g' | tail -n 10)"
fi

# Notices: a service crashing shows up in a user's grove at the next prompt.
tmux new-session -d -s e2e-notice -x 200 -y 50 runuser -u "$grove_user" -- grove
sleep 2
notice_unit="druidos-e2e-notice-$$"
notice_cursor=$(journal_cursor)
systemd-run --quiet --wait --unit="$notice_unit" \
    sh -c "(echo 'fatal error: e2e notice'; sleep 2) | systemd-cat -t $notice_unit -p err" > /dev/null
for _ in $(seq 1 20); do
    journalctl --no-pager -o cat --after-cursor="$notice_cursor" -u hive-nerve-journal \
        | grep -q "Reported service crash: $notice_unit.service" && break
    sleep 1
done
sleep 2
tmux send-keys -t e2e-notice Enter
sleep 2
notice_screen=$(tmux capture-pane -p -t e2e-notice 2> /dev/null)
if grep -q "\[hive\] Service Crashed: $notice_unit.service" <<< "$notice_screen"; then
    pass "grove shows a Hive notice about the system at the prompt"
else
    fail "grove shows a Hive notice about the system at the prompt" \
        "$(grep -v '^\s*$' <<< "$notice_screen" | tail -n 8)"
fi

# anon: the Hive stops acting on what this shell runs, and resumes after.
anon_cursor=$(journal_cursor)
tmux send-keys -t e2e-notice "anon" Enter
sleep 2
tmux send-keys -t e2e-notice "rm -rf /etc/druidos-e2e-anon-hidden-$$/.." Enter
sleep 4
tmux send-keys -t e2e-notice "anon off" Enter
sleep 2
tmux send-keys -t e2e-notice "rm -rf /etc/druidos-e2e-anon-seen-$$/.." Enter
sleep 4
anon_screen=$(tmux capture-pane -p -t e2e-notice 2> /dev/null)
tmux kill-session -t e2e-notice 2> /dev/null
anon_logs() { # units...
    journalctl --no-pager -o cat --after-cursor="$anon_cursor" "${@/#/--unit=}" | sed 's/\x1b\[[0-9;]*m//g'
}
if anon_logs hive-nerve-process | grep -q "druidos-e2e-anon-hidden-$$" \
    && anon_logs hive-cortex | grep -q "Skipping observation for anonymous process" \
    && ! anon_logs hive-cortex hive-synapse | grep -q "druidos-e2e-anon-hidden-$$"; then
    pass "anon in grove keeps the Hive from acting on what the shell runs"
else
    fail "anon in grove keeps the Hive from acting on what the shell runs" \
        "$(anon_logs hive-nerve-process hive-cortex | grep -iE "anon|druidos-e2e-anon" | tail -n 8)
--- grove:
$(grep -v '^\s*$' <<< "$anon_screen" | tail -n 8)"
fi
if anon_logs hive-cortex | grep -q "Anonymous mode exited" \
    && [ "$(anon_logs hive-cortex | grep -c "Skipping observation for anonymous process")" -eq 1 ]; then
    pass "anon off in grove lets the Hive observe the shell again"
else
    fail "anon off in grove lets the Hive observe the shell again" \
        "$(anon_logs hive-cortex | grep -iE "anon" | tail -n 8)"
fi

# hive-dashboard is a full-screen TUI: give it a pseudo-terminal via
# script(1), and judge it by cortex's side of the connection rather than by
# scraping the screen.
dash_cursor=$(journal_cursor)
timeout 6 script -qfec hive-dashboard /dev/null > /dev/null 2>&1 < /dev/null
check "hive-dashboard connects and registers with cortex" bash -c "
    journalctl --no-pager -o cat --after-cursor='$dash_cursor' -u hive-cortex | grep -E 'Registered connection [0-9]+ as Dashboard\$'"

# The approval loop, driven like a user would: the dashboard running in a
# real terminal (tmux), a suggestion arriving for a dangerous-looking command,
# Enter on it. Cortex must receive the UserAction.
if command -v tmux > /dev/null; then
    wait_for_synapse_idle
    approve_cursor=$(journal_cursor)
    tmux new-session -d -s e2e-dashboard -x 160 -y 50 hive-dashboard
    sleep 2
    rm -rf "/etc/druidos-e2e-approve-$$/.." 2> /dev/null
    for _ in $(seq 1 120); do
        journalctl --no-pager -o cat --after-cursor="$approve_cursor" -u hive-synapse \
            | grep -q "Sent suggestion response" && break
        sleep 1
    done
    sleep 1
    tmux send-keys -t e2e-dashboard Enter
    accepted=false
    for _ in $(seq 1 10); do
        if journalctl --no-pager -o cat --after-cursor="$approve_cursor" -u hive-cortex \
            | grep -q "User accepted suggestion"; then
            accepted=true
            break
        fi
        sleep 1
    done
    tmux send-keys -t e2e-dashboard q
    sleep 1
    tmux kill-session -t e2e-dashboard 2> /dev/null
    if $accepted; then
        pass "approving a suggestion in hive-dashboard reaches cortex"
    else
        fail "approving a suggestion in hive-dashboard reaches cortex" \
            "$(journalctl --no-pager -o cat --after-cursor="$approve_cursor" -u hive-cortex -u hive-synapse | sed 's/\x1b\[[0-9;]*m//g' | tail -n 15)"
    fi
else
    fail "approving a suggestion in hive-dashboard reaches cortex" "tmux is not installed in the guest"
fi

# ---------------------------------------------------------------- acting on a suggestion
# The whole loop the Hive exists for: a service crashes -> nerve-journal
# attributes the failure to that unit -> synapse offers "Restart" with a
# typed RestartService action -> the user approves it in hive-dashboard ->
# hive-actuator (as _hive-act, through polkit) restarts the service. The
# approving user is an administrator who isn't root (in the sudo group), the
# way a real install's first user is.
#
# The test service is whitelisted the way an admin would whitelist their
# own service. It crashes on its first start and keeps running once
# restarted, and nothing but hive-actuator restarts it (no Restart=).
crasher=druidos-e2e-crasher
cp /etc/hive/whitelist.toml /tmp/whitelist.toml.orig
python3 - "$crasher" << 'EOF'
import sys
path, name = "/etc/hive/whitelist.toml", sys.argv[1]
text = open(path).read()
marker = "[service]\nallowed = [\n"
assert marker in text, "whitelist.toml has no [service] allowed list"
open(path, "w").write(text.replace(marker, f'{marker}    "{name}",\n', 1))
EOF
cat > "/etc/systemd/system/$crasher.service" << EOF
[Unit]
Description=DruidOS e2e: crashes on first start, runs once restarted
[Service]
ExecStart=/bin/sh -c 'if [ -e /run/$crasher.restarted ]; then exec sleep 600; fi; touch /run/$crasher.restarted; echo "crashing on purpose" >&2; exit 1'
EOF
systemctl daemon-reload
systemctl restart hive-actuator # reload the whitelist
sleep 3 # let nerve-fs's reports of the edits above drain before the dashboard starts

wait_for_synapse_idle
tmux new-session -d -s e2e-act -x 200 -y 50 runuser -u "$grove_user" -- hive-dashboard
sleep 2
act_cursor=$(journal_cursor)
systemctl start "$crasher" 2> /dev/null
act_logs() { # units...
    journalctl --no-pager -o cat --after-cursor="$act_cursor" "${@/#/--unit=}" | sed 's/\x1b\[[0-9;]*m//g'
}
for _ in $(seq 1 120); do
    act_logs hive-synapse | grep -q "Sent suggestion response" && break
    sleep 1
done
sleep 1
# Rows: the "Service Crashed" alert first, then the suggestions (actions first).
tmux send-keys -t e2e-act Down Enter
restarted=false
for _ in $(seq 1 20); do
    if systemctl is-active --quiet "$crasher"; then
        restarted=true
        break
    fi
    sleep 1
done
dashboard_screen=$(tmux capture-pane -p -t e2e-act 2> /dev/null | grep '[[:alnum:]]' | head -n 20)
tmux send-keys -t e2e-act q
sleep 1
tmux kill-session -t e2e-act 2> /dev/null

if act_logs hive-nerve-journal | grep -q "Reported service crash: $crasher.service"; then
    pass "nerve-journal attributes a unit's failure to that unit"
else
    fail "nerve-journal attributes a unit's failure to that unit" "$(act_logs hive-nerve-journal | tail -n 5)"
fi
if act_logs hive-synapse | grep -q "RestartService { name: \"$crasher\" }"; then
    pass "synapse offers a RestartService action for a crashed service"
else
    fail "synapse offers a RestartService action for a crashed service" "$(act_logs hive-synapse | tail -n 8)"
fi
if $restarted && act_logs hive-actuator | grep -q "Action completed with exit code Some(0)"; then
    pass "approving the restart in hive-dashboard makes hive-actuator restart the service"
else
    fail "approving the restart in hive-dashboard makes hive-actuator restart the service" \
        "$crasher active: $restarted
$(act_logs hive-cortex hive-actuator | tail -n 12)
--- dashboard screen:
$dashboard_screen"
fi

# The polkit rule is a security boundary under hive-actuator's whitelist:
# whatever the actuator is tricked into asking for, the OS must still refuse
# anything outside the rule's ceiling.
polkit_refuses() { # systemctl args...
    local out
    if out=$(runuser -u _hive-act -- systemctl --no-ask-password "$@" 2>&1); then
        fail "polkit refuses _hive-act: systemctl $*" "unexpectedly allowed: $out"
    elif grep -qiE "authentication required|access denied" <<< "$out"; then
        pass "polkit refuses _hive-act: systemctl $*"
    else
        # Failed, but not on authorization (unit missing?) - proves nothing.
        fail "polkit refuses _hive-act: systemctl $*" "failed for another reason: $out"
    fi
}
polkit_refuses restart hive-nerve-network.service
polkit_refuses restart ssh.service
polkit_refuses restart getty@tty1.service
polkit_refuses enable "$crasher.service"
polkit_refuses start multi-user.target

# Acting on the Hive's suggestions is for administrators - root, and members
# of sudo, admin or wheel. Anyone else is turned away, and told why.
guest=druidos-e2e-guest
useradd --system --no-create-home --shell /usr/sbin/nologin "$guest" 2> /dev/null
refuse_cursor=$(journal_cursor)
guest_out=$(runuser -u "$guest" -- timeout 10 hive-dashboard < /dev/null 2>&1)
guest_status=$?
if journalctl --no-pager -o cat --after-cursor="$refuse_cursor" -u hive-cortex \
        | grep -q "Refusing hive-dashboard for uid $(id -u "$guest")" \
    && grep -qi "administrator" <<< "$guest_out" && [ "$guest_status" -ne 0 ] && [ "$guest_status" -ne 124 ]; then
    pass "hive-dashboard turns away a user who isn't an administrator"
else
    fail "hive-dashboard turns away a user who isn't an administrator" \
        "exit $guest_status: $guest_out
$(journalctl --no-pager -o cat --after-cursor="$refuse_cursor" -u hive-cortex | tail -n 5)"
fi
userdel "$guest" 2> /dev/null

systemctl stop "$crasher" 2> /dev/null
rm -f "/etc/systemd/system/$crasher.service" "/run/$crasher.restarted"
cp /tmp/whitelist.toml.orig /etc/hive/whitelist.toml
systemctl daemon-reload
systemctl restart hive-actuator

# ---------------------------------------------------------------- ZFS safety snapshots
# DruidOS installs onto ZFS so the system can be snapshotted before it gets
# changed. The installer names the datasets (rpool/ROOT/ubuntu_<random>, and
# /boot in a pool of its own); the Hive has to find them, and the snapshot
# has to really hold the state from before the change - including child
# datasets like /var/lib/dpkg.
root_ds=$(findmnt -n -o SOURCE -t zfs /)
boot_ds=$(findmnt -n -o SOURCE -t zfs /boot)
system_ds=()
[ -n "$root_ds" ] && system_ds+=("$root_ds")
[ -n "$boot_ds" ] && system_ds+=("$boot_ds")
if [ -n "$root_ds" ]; then
    pass "the root filesystem is a ZFS dataset"
else
    fail "the root filesystem is a ZFS dataset" "/ is: $(findmnt -n -o SOURCE,FSTYPE /)"
fi

if [ -n "$root_ds" ]; then
    hive_snapshots() {
        zfs list -H -t snapshot -o name -d 1 "${system_ds[@]}" 2> /dev/null | grep "@hive-" | sort
    }

    if jctl -u hive-actuator | grep -qF "Snapshots before package changes: ${system_ds[*]}"; then
        pass "hive-actuator finds the system datasets to snapshot"
    else
        fail "hive-actuator finds the system datasets to snapshot" \
            "expected: ${system_ds[*]}
$(jctl -u hive-actuator | grep -iE "snapshot|zfs" | tail -n 5)"
    fi

    # hive-actuator runs as _hive-act: ZFS delegation lets it snapshot the
    # system, and nothing else - no destroying, no rolling back.
    probe="hive-e2e-delegation-$$"
    # One call per dataset: ZFS won't snapshot two pools (rpool, bpool) in one.
    if out=$(for ds in "${system_ds[@]}"; do runuser -u _hive-act -- zfs snapshot -r "$ds@$probe" || exit 1; done 2>&1); then
        pass "_hive-act may snapshot the system datasets"
    else
        fail "_hive-act may snapshot the system datasets" "$out
$(zfs allow "$root_ds" 2>&1)"
    fi
    zfs_refuses() { # zfs args...
        local out
        if out=$(runuser -u _hive-act -- zfs "$@" 2>&1); then
            fail "zfs refuses _hive-act: zfs $*" "unexpectedly allowed: $out"
        elif grep -qi "permission denied" <<< "$out"; then
            pass "zfs refuses _hive-act: zfs $*"
        else
            fail "zfs refuses _hive-act: zfs $*" "failed for another reason: $out"
        fi
    }
    zfs snapshot "$root_ds@$probe-root" 2> /dev/null # something to try destroying and rolling back to
    zfs_refuses destroy "$root_ds@$probe-root"
    zfs_refuses rollback "$root_ds@$probe-root"
    for ds in "${system_ds[@]}"; do
        zfs destroy -r "$ds@$probe" 2> /dev/null
    done
    zfs destroy "$root_ds@$probe-root" 2> /dev/null

    # hive-apt, the user's way to change packages: a snapshot first, taken
    # before apt touches anything. A local .deb keeps it offline.
    dummy=druidos-e2e-dummy
    pkg_dir=$(mktemp -d)
    chmod 755 "$pkg_dir" # readable by apt's _apt sandbox user
    mkdir -p "$pkg_dir/$dummy/DEBIAN" "$pkg_dir/$dummy/usr/share/$dummy"
    printf 'Package: %s\nVersion: 1.0\nArchitecture: all\nMaintainer: DruidOS e2e <e2e@druidos.invalid>\nDescription: DruidOS e2e test package\n' \
        "$dummy" > "$pkg_dir/$dummy/DEBIAN/control"
    echo installed > "$pkg_dir/$dummy/usr/share/$dummy/marker"
    dpkg-deb --build --root-owner-group "$pkg_dir/$dummy" "$pkg_dir/$dummy.deb" > /dev/null

    # What a snapshot holds of the package: its file, and dpkg's record of
    # it (in the dpkg child dataset, on the installer's layout). Read through
    # read-only mounts: the .zfs/snapshot automount fails with ELOOP on child
    # datasets.
    dpkg_ds=$(findmnt -n -o SOURCE -T /var/lib/dpkg)
    snap_mnt=/run/druidos-e2e-snapshot
    mkdir -p "$snap_mnt/root" "$snap_mnt/dpkg"
    package_state() { # root dir, dpkg dir
        local file=no dpkg=no
        [ -e "$1/usr/share/$dummy/marker" ] && file=yes
        [ -f "$2/status" ] || dpkg=unreadable
        grep -q "^Package: $dummy$" "$2/status" 2> /dev/null && dpkg=yes
        echo "file:$file dpkg:$dpkg"
    }
    snapshot_package_state() { # snapshot name
        local dpkg_dir="$snap_mnt/root/var/lib/dpkg" state
        mount -t zfs -o ro "$root_ds@$1" "$snap_mnt/root" 2> /dev/null || { echo "unmountable"; return; }
        if [ "$dpkg_ds" != "$root_ds" ]; then
            dpkg_dir="$snap_mnt/dpkg"
            mount -t zfs -o ro "$dpkg_ds@$1" "$dpkg_dir" 2> /dev/null
        fi
        state=$(package_state "$snap_mnt/root" "$dpkg_dir")
        umount "$snap_mnt/dpkg" 2> /dev/null
        umount "$snap_mnt/root"
        echo "$state"
    }

    snaps_before=$(hive_snapshots)
    apt_out=$(hive-apt -y install "$pkg_dir/$dummy.deb" 2>&1)
    snaps_after_install=$(hive_snapshots)
    install_snap=$(comm -13 <(echo "$snaps_before") <(echo "$snaps_after_install") \
        | grep -m 1 "^$root_ds@hive-before-install-$dummy-" | cut -d@ -f2)
    live_state=$(package_state / /var/lib/dpkg)
    snap_state=$([ -n "$install_snap" ] && snapshot_package_state "$install_snap")
    # Installed on the live system; neither file nor dpkg record in the
    # snapshot; and /boot's pool snapshotted under the same name.
    if [ "$live_state" = "file:yes dpkg:yes" ] && [ "$snap_state" = "file:no dpkg:no" ] \
        && { [ -z "$boot_ds" ] || grep -qx "$boot_ds@$install_snap" <<< "$snaps_after_install"; }; then
        pass "hive-apt snapshots the whole system before installing a package"
    else
        fail "hive-apt snapshots the whole system before installing a package" \
            "live system: $live_state (want file:yes dpkg:yes)
snapshot ${install_snap:-(none)}: ${snap_state:-(none)} (want file:no dpkg:no)
new snapshots:
$(comm -13 <(echo "$snaps_before") <(echo "$snaps_after_install"))
--- hive-apt:
$(tail -n 12 <<< "$apt_out")"
    fi

    apt_out=$(hive-apt -y remove "$dummy" 2>&1)
    remove_snap=$(comm -13 <(echo "$snaps_after_install") <(hive_snapshots) \
        | grep -m 1 "^$root_ds@hive-before-remove-$dummy-" | cut -d@ -f2)
    live_state=$(package_state / /var/lib/dpkg)
    snap_state=$([ -n "$remove_snap" ] && snapshot_package_state "$remove_snap")
    if [ "$live_state" = "file:no dpkg:no" ] && [ "$snap_state" = "file:yes dpkg:yes" ]; then
        pass "hive-apt snapshots the system before removing a package"
    else
        fail "hive-apt snapshots the system before removing a package" \
            "live system: $live_state (want file:no dpkg:no)
snapshot ${remove_snap:-(none)}: ${snap_state:-(none)} (want file:yes dpkg:yes)
--- hive-apt:
$(tail -n 12 <<< "$apt_out")"
    fi

    dpkg --purge "$dummy" > /dev/null 2>&1
    rm -rf "$pkg_dir" "$snap_mnt"
    for snap in $install_snap $remove_snap; do
        for ds in "${system_ds[@]}"; do
            zfs destroy -r "$ds@$snap" 2> /dev/null
        done
    done
fi

# ---------------------------------------------------------------- installing what a user reached for
# A user runs a program that isn't installed, and a package of that name is
# available: grove says so, the Hive offers to install it, an administrator
# approves in hive-dashboard, and hive-actuator - unprivileged, through
# PackageKit and polkit - snapshots the system and installs it. Offline:
# the package comes from a local repository.
pkg=druidos-e2e-hello
repo=/srv/druidos-e2e-repo
pkg_root_ds=$(findmnt -n -o SOURCE -t zfs /)
mkdir -p "$repo/build/$pkg/DEBIAN" "$repo/build/$pkg/usr/bin"
printf 'Package: %s\nVersion: 1.0\nArchitecture: all\nMaintainer: DruidOS e2e <e2e@druidos.invalid>\nDescription: DruidOS e2e test package\n' \
    "$pkg" > "$repo/build/$pkg/DEBIAN/control"
printf '#!/bin/sh\necho hello from the e2e package\n' > "$repo/build/$pkg/usr/bin/$pkg"
chmod 755 "$repo/build/$pkg/usr/bin/$pkg"
dpkg-deb --build --root-owner-group "$repo/build/$pkg" "$repo/$pkg.deb" > /dev/null
(cd "$repo" && apt-ftparchive packages . > Packages)
echo "deb [trusted=yes] file:$repo ./" > /etc/apt/sources.list.d/druidos-e2e.list
apt-get update -qq -o Dir::Etc::sourcelist=sources.list.d/druidos-e2e.list \
    -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0 > /dev/null 2>&1
systemctl stop packagekit 2> /dev/null # its cache predates the repository
sleep 3 # let nerve-fs's reports of the edits above drain before the dashboard starts

wait_for_synapse_idle
tmux new-session -d -s e2e-pkg -x 200 -y 50 runuser -u "$grove_user" -- hive-dashboard
sleep 2
pkg_cursor=$(journal_cursor)
pkg_logs() { # units...
    journalctl --no-pager -o cat --after-cursor="$pkg_cursor" "${@/#/--unit=}" | sed 's/\x1b\[[0-9;]*m//g'
}
reach_out=$(runuser -u "$grove_user" -- timeout 20 grove -c "$pkg" 2>&1)
for _ in $(seq 1 150); do
    pkg_logs hive-synapse | grep -q "Suggesting 'Install $pkg'" \
        && pkg_logs hive-synapse | grep -q "Sent suggestion response" && break
    sleep 1
done
sleep 2
tmux send-keys -t e2e-pkg Enter
installed=false
for _ in $(seq 1 120); do
    if dpkg-query -W -f='${db:Status-Status}' "$pkg" 2> /dev/null | grep -qx installed; then
        installed=true
        break
    fi
    sleep 1
done
sleep 2
pkg_screen=$(tmux capture-pane -p -t e2e-pkg 2> /dev/null | grep '[[:alnum:]]' | head -n 20)
tmux send-keys -t e2e-pkg q
sleep 1
tmux kill-session -t e2e-pkg 2> /dev/null

if grep -q "$pkg: command not found" <<< "$reach_out" && grep -q "package $pkg" <<< "$reach_out"; then
    pass "grove says which package would provide a missing program"
else
    fail "grove says which package would provide a missing program" "$reach_out"
fi
if pkg_logs hive-synapse | grep -q "Suggesting 'Install $pkg': InstallPackage { name: \"$pkg\""; then
    pass "synapse offers to install the package a user reached for"
else
    fail "synapse offers to install the package a user reached for" \
        "$(pkg_logs hive-cortex hive-synapse | tail -n 10)"
fi
if $installed \
    && pkg_logs hive-actuator | grep -q "Created snapshot: $pkg_root_ds@hive-before-install-$pkg-" \
    && pkg_logs hive-actuator | grep -q "Action completed with exit code Some(0)"; then
    pass "approving the install in hive-dashboard installs it via hive-actuator, after a safety snapshot"
else
    fail "approving the install in hive-dashboard installs it via hive-actuator, after a safety snapshot" \
        "installed: $installed
$(pkg_logs hive-cortex hive-actuator | tail -n 12)
--- dashboard screen:
$pkg_screen"
fi

dpkg --purge "$pkg" > /dev/null 2>&1
rm -f /etc/apt/sources.list.d/druidos-e2e.list /var/lib/apt/lists/_srv_druidos-e2e-repo_*
rm -rf "$repo"
systemctl stop packagekit 2> /dev/null
for snap in $(zfs list -H -t snapshot -o name -d 1 "$pkg_root_ds" 2> /dev/null | grep "@hive-before-install-$pkg-" | cut -d@ -f2); do
    for ds in "${system_ds[@]}"; do
        zfs destroy -r "$ds@$snap" 2> /dev/null
    done
done

# ---------------------------------------------------------------- old safety snapshots
# The Hive's snapshots don't pile up forever: a daily timer prunes hive-*
# snapshots past the configured age (keeping the newest few whatever their
# age), across the system datasets and their children - and never touches
# anyone else's snapshots.
if [ -n "$root_ds" ]; then
    if systemctl is-enabled --quiet hive-zfs-prune.timer && systemctl is-active --quiet hive-zfs-prune.timer; then
        pass "the Hive's snapshot pruning is scheduled"
    else
        fail "the Hive's snapshot pruning is scheduled" \
            "$(systemctl status hive-zfs-prune.timer 2>&1 | head -n 5)"
    fi

    now_stamp=$(date -u +%Y%m%d-%H%M%S)
    old_snap="hive-before-install-e2e-old-20200101-000000"
    admin_snap="e2e-admin-snapshot-20200101"
    for ds in "${system_ds[@]}"; do
        zfs snapshot -r "$ds@$old_snap"
        for i in 1 2 3; do
            zfs snapshot -r "$ds@hive-before-install-e2e-recent$i-$now_stamp"
        done
    done
    zfs snapshot "$root_ds@$admin_snap"
    prune_cursor=$(journal_cursor)
    systemctl start hive-zfs-prune.service
    all_snaps=$(zfs list -H -t snapshot -o name -r "${system_ds[@]}" 2> /dev/null)
    if ! grep -q "@$old_snap$" <<< "$all_snaps" \
        && [ "$(grep -c "^$root_ds@hive-before-install-e2e-recent[123]-$now_stamp$" <<< "$all_snaps")" -eq 3 ] \
        && grep -q "^$root_ds/var/lib/dpkg@hive-before-install-e2e-recent1-$now_stamp$" <<< "$all_snaps" \
        && grep -qx "$root_ds@$admin_snap" <<< "$all_snaps" \
        && { [ -z "$boot_ds" ] || grep -qx "$boot_ds@hive-before-install-e2e-recent1-$now_stamp" <<< "$all_snaps"; }; then
        pass "pruning removes old Hive snapshots everywhere, keeps recent ones and the admin's own"
    else
        fail "pruning removes old Hive snapshots everywhere, keeps recent ones and the admin's own" \
            "$(grep -E "e2e-|$admin_snap" <<< "$all_snaps")
--- prune:
$(journalctl --no-pager -o cat --after-cursor="$prune_cursor" -u hive-zfs-prune | tail -n 8)"
    fi
    for ds in "${system_ds[@]}"; do
        for snap in $old_snap hive-before-install-e2e-recent1-$now_stamp hive-before-install-e2e-recent2-$now_stamp hive-before-install-e2e-recent3-$now_stamp; do
            zfs destroy -r "$ds@$snap" 2> /dev/null
        done
    done
    zfs destroy "$root_ds@$admin_snap" 2> /dev/null
fi

# ---------------------------------------------------------------- summary
echo "1..$n"
echo "# $failures of $n checks failed"
exit "$failures"
