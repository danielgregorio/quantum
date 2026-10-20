<!--
  The Hive's rules, in Quantum: what the Hive offers when something happens,
  and what the actuator may do at all. `quantum run hive.q` (from the
  repository's root: python scripts/generate-hive-config.py) writes
  rules.toml, which hive-synapse loads, and whitelist.toml, which
  hive-actuator loads. Both are committed next to this file and checked
  against it in CI; edit this file, never them.

  A {field} is filled in by hive-synapse from the event itself, never from
  the model's text. An offer this file's own whitelist would refuse does not
  compile. docs/targets/hive.md is the reference.
-->
<q:application id="hive" type="hive">

  <!-- ================================================================ offers -->

  <qh:on event="service-crash">
    <qh:offer title="Restart {service}"
              description="{unit} stopped unexpectedly. Run `systemctl restart {service}`."
              action="restart-service" service="{service}" />
    <qh:offer title="Show recent logs for {service}"
              description="The last 50 journal lines from {service}, to see why it failed."
              action="run-command" cmd="journalctl" args="-n 50 -u {service}" />
  </qh:on>

  <qh:on event="log-anomaly">
    <qh:offer title="Show recent logs for {service}"
              description="The last 50 journal lines from {service}, to see why it failed."
              action="run-command" cmd="journalctl" args="-n 50 -u {service}" />
  </qh:on>

  <qh:on event="disk-low">
    <qh:offer title="Show disk usage"
              description="See how full {mount} and the other mounts are."
              action="run-command" cmd="df" args="-h" />
  </qh:on>

  <qh:on event="command-not-found">
    <qh:offer title="Install {package}"
              description="`{command}` isn't installed; the {package} package provides it."
              action="install-package" package="{package}" />
  </qh:on>

  <qh:on event="port-conflict">
    <qh:offer title="Show listening ports"
              description="See which process is holding port {port}."
              action="run-command" cmd="ss" args="-tlnp" />
  </qh:on>

  <!-- ============================================================= whitelist -->
  <!-- Commands: each matched argument for argument; `*` is any one argument. -->

  <qh:allow command="df" args="-h" />
  <qh:allow command="free" args="-h" />
  <qh:allow command="uptime" />
  <qh:allow command="whoami" />
  <qh:allow command="id" />
  <qh:allow command="uname" args="-a" />
  <qh:allow command="ss" args="-tlnp" />
  <qh:allow command="ip" args="addr" />
  <qh:allow command="ip" args="route" />
  <qh:allow command="systemctl" args="status *" />
  <qh:allow command="systemctl" args="is-active *" />
  <qh:allow command="journalctl" args="-n 50 -u *" />

  <!-- The machine's settings a user asks for through the Ajustes app
       (hive request) and an administrator approves on the screen: its name
       (hostnamectl), its keyboard (us or br), its screen's level, an
       interface's address (netplan; dangerous: Enter twice).
       Two a minute each: a setting is not something to flap. -->
  <qh:allow action="set-hostname" />
  <qh:allow action="set-keyboard" />
  <qh:allow action="set-screen-level" />
  <qh:allow action="set-network" />
  <qh:limit action="set-hostname" per-minute="2" />
  <qh:limit action="set-keyboard" per-minute="2" />
  <qh:limit action="set-screen-level" per-minute="2" />
  <qh:limit action="set-network" per-minute="2" />
  <qh:allow command="zpool" args="status" />
  <qh:allow command="zfs" args="list" />
  <qh:allow command="zfs" args="list -t snapshot" />

  <!-- Services the actuator may start, stop, restart, reload, enable and
       disable; a block wins over an allow, and the Hive and the units that
       keep the machine reachable are never touched. -->
  <qh:allow service="nginx apache2 postgresql mysql mariadb redis-server mongodb docker containerd
                     NetworkManager cups bluetooth" />
  <qh:block service="hive-* systemd-* dbus sshd" />

  <!-- Packages: any valid name may be installed (the per-minute limit below
       bounds it); these are never removed. -->
  <qh:block package="systemd linux-image-* grub-* hive-* zfs-* libc6 apt dpkg" />

  <!-- Files: where they may be created, moved, copied, deleted and have their
       permissions changed, and where never. -->
  <qh:allow path="/home/* /tmp/* /var/tmp/*" />
  <qh:block path="/home/*/.ssh/* /home/*/.gnupg/* /etc/* /usr/* /bin/* /sbin/* /lib/* /boot/* /root/*" />

  <!-- ZFS: the datasets it may snapshot, and the snapshots it may destroy
       (only the Hive's own). -->
  <qh:allow dataset="rpool/ROOT/* rpool/home/*" />
  <qh:allow delete-snapshot="hive-*" />

  <!-- Permissions with no list behind them. Rebooting, shutting down and
       suspending have no switch: never. -->
  <qh:allow action="kill-port-process" />
  <qh:allow action="open-url" />

  <!-- At most this many a minute, under the actuator's overall limit. -->
  <qh:limit action="kill-port-process" per-minute="10" />
  <qh:limit action="install-package" per-minute="5" />
  <qh:limit action="remove-package" per-minute="3" />
  <qh:limit action="create-directory" per-minute="20" />
  <qh:limit action="move-file" per-minute="20" />
  <qh:limit action="copy-file" per-minute="20" />
  <qh:limit action="delete-file" per-minute="20" />
  <qh:limit action="change-permissions" per-minute="20" />
  <qh:limit action="create-snapshot" per-minute="10" />
  <qh:limit action="restore-snapshot" per-minute="10" />
  <qh:limit action="delete-snapshot" per-minute="10" />

</q:application>
