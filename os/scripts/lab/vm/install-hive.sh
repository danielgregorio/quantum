#!/bin/sh
# Installs the Hive from the working tree into the VM lab's guest, the way
# scripts/build-iso.sh (install_hive_stack) installs it into the ISO: the
# binaries in /usr/bin, the units, /etc/hive, the polkit and audit rules, the
# knowledge base, the service users, every unit with an [Install] section
# enabled. Then it (re)starts the Hive.
#
#   install-hive.sh SRC     # SRC: the os/ directory, as the guest sees it
#
# The binaries come from SRC/target/vm-lab/bin, where the host stages them
# (without debug sections: what the ISO ships is a release build).
#
# The lab installs incrementally on a guest that has the Hive already:
# with HIVE_BINARIES set, only those binaries are copied (everything else is
# installed every time); with HIVE_ONLY_BINARIES instead, only those are
# copied and only the units that run them restarted, nothing else.
set -eu

SRC=${1:-/mnt/lab}
BIN=$SRC/target/vm-lab/bin
ALL="hive-cortex hive-synapse hive-actuator hive-nerve-process hive-nerve-journal
hive-nerve-network hive-nerve-fs hive-apt hive-zfs hive-dashboard grove hive-lab"

copy() {
    case $1 in
        hive-lab) install -m 0755 "$BIN/hive-lab" /usr/local/lib/quantum-lab/hive-lab ;;
        *) install -m 0755 "$BIN/$1" "/usr/bin/$1" ;;
    esac
}

if [ -n "${HIVE_ONLY_BINARIES-}" ]; then
    restart=""
    for b in $HIVE_ONLY_BINARIES; do
        copy "$b"
        if [ -f "/etc/systemd/system/$b.service" ]; then
            restart="$restart $b.service"
        fi
    done
    # Type=notify: this returns once each unit is ready again (restarting
    # hive-cortex restarts the rest of the Hive with it: PartOf)
    if [ -n "$restart" ]; then
        systemctl restart $restart
    fi
    exit 0
fi

units=$(cd "$SRC/config/systemd" && grep -l '^\[Install\]' *.service *.timer | xargs)

# a reinstall replaces a running Hive
systemctl stop hive-cortex.service $units 2>/dev/null || true

for b in ${HIVE_BINARIES-$ALL}; do
    copy "$b"
done

install -m 0644 "$SRC"/config/systemd/*.service "$SRC"/config/systemd/*.timer /etc/systemd/system/
mkdir -p /etc/hive
install -m 0644 "$SRC/config/hive/default.toml" /etc/hive/config.toml
install -m 0644 "$SRC/config/hive/whitelist.toml" /etc/hive/whitelist.toml
install -m 0644 "$SRC/config/hive/rules.toml" /etc/hive/rules.toml
mkdir -p /etc/polkit-1/rules.d /etc/audit/rules.d
install -m 0644 "$SRC"/config/polkit/*.rules /etc/polkit-1/rules.d/
install -m 0640 "$SRC"/config/audit/*.rules /etc/audit/rules.d/
mkdir -p /var/lib/hive/knowledge
cp -r "$SRC"/knowledge/* /var/lib/hive/knowledge/

groupadd -r hive 2>/dev/null || true
useradd -r -g hive -s /usr/sbin/nologin -d /nonexistent _hive-ai 2>/dev/null || true
useradd -r -g hive -s /usr/sbin/nologin -d /nonexistent _hive-sense 2>/dev/null || true
useradd -r -g hive -s /usr/sbin/nologin -d /nonexistent _hive-act 2>/dev/null || true

# the audit rule hive-nerve-process reads commands from, loaded now rather
# than at the next boot
if command -v augenrules >/dev/null; then
    augenrules --load >/dev/null 2>&1 || true
fi

systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true
systemctl enable $units >/dev/null 2>&1
systemctl start hive-cortex.service
systemctl start --no-block $units
