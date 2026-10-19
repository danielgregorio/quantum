#!/usr/bin/env python3
"""The VM lab: Quantum OS's real system in a light VM, restored from a
snapshot in about a second.

Layer 1, the Hive lab (crates/hive-lab), runs the real hive-cortex and
hive-synapse and plays everything else. This layer runs everything for real:
the nerves watch a running system, the actuator acts through polkit and
systemd, grove and the dashboard run in a terminal. It still needs no ISO, no
installer and no OCR:

- the guest is Ubuntu's minimal cloud image (the release Quantum OS remasters),
  on a copy-on-write overlay;
- an agent in the guest (agent.py) speaks JSON lines over a virtio-serial
  port: commands, files, the journal, programs in a terminal;
- the guest boots once. Snapshots keep it booted ("base") and with the Hive
  installed from the working tree ("hive"); restoring one takes a second;
- the working tree reaches the guest over a read-only 9p share.

    python3 vm.py                 # the driver: one JSON request per line on stdin
    python3 vm.py --play TAPE...  # plays tapes, exit 1 on the first failure

Needs qemu-system-x86_64, qemu-img and genisoimage (or cloud-localds); KVM
when /dev/kvm is usable, plain emulation otherwise (slower to build the
base, as fast to restore).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
OS_DIR = HERE.parents[2]
CACHE = Path(os.environ.get('QUANTUM_LAB_CACHE', Path.home() / '.cache' / 'quantum-os-lab')).expanduser()

RELEASE = 'noble'
IMAGE_DIR = f'https://cloud-images.ubuntu.com/minimal/releases/{RELEASE}/release/'
IMAGE_NAME = 'ubuntu-24.04-minimal-cloudimg-amd64.img'


class LabError(Exception):
    pass


def log(msg: str) -> None:
    print(f'[vm {time.strftime("%H:%M:%S")}] {msg}', file=sys.stderr, flush=True)


def kvm_usable() -> bool:
    return os.access('/dev/kvm', os.R_OK | os.W_OK)


# ------------------------------------------------------------------ the image

def cloud_image() -> Path:
    """Ubuntu's minimal cloud image, downloaded once and checked against the
    release's SHA256SUMS."""
    path = CACHE / IMAGE_NAME
    if path.is_file():
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    log(f'downloading {IMAGE_DIR}{IMAGE_NAME}')
    sums = urllib.request.urlopen(IMAGE_DIR + 'SHA256SUMS', timeout=60).read().decode()
    expected = next((line.split()[0] for line in sums.splitlines()
                     if line.split()[-1].lstrip('*') == IMAGE_NAME), None)
    if not expected:
        raise LabError(f'{IMAGE_NAME} is not in the release SHA256SUMS')
    part = path.with_suffix('.part')
    digest = hashlib.sha256()
    with urllib.request.urlopen(IMAGE_DIR + IMAGE_NAME, timeout=60) as r, open(part, 'wb') as f:
        while chunk := r.read(1 << 20):
            digest.update(chunk)
            f.write(chunk)
    if digest.hexdigest() != expected:
        part.unlink()
        raise LabError(f'{IMAGE_NAME}: checksum mismatch')
    part.rename(path)
    return path


AGENT_UNIT = """[Unit]
Description=Quantum OS VM lab agent (virtio-serial)
After=dev-virtio\\x2dports-org.quantum.lab.device
Wants=dev-virtio\\x2dports-org.quantum.lab.device

[Service]
ExecStart=/usr/bin/python3 /usr/local/lib/quantum-lab/agent.py
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
"""


def seed_iso(out: Path) -> Path:
    """The cloud-init seed of the base image: the agent, its unit and the
    lab's user. The rest of the base is provisioned through the agent."""
    agent = (HERE / 'agent.py').read_bytes()
    user_data = {
        'hostname': 'quantum-lab',
        'users': [{'name': 'druid', 'uid': 1000, 'shell': '/bin/bash', 'lock_passwd': True}],
        'write_files': [
            {'path': '/usr/local/lib/quantum-lab/agent.py', 'permissions': '0755',
             'encoding': 'b64', 'content': base64.b64encode(agent).decode()},
            {'path': '/etc/systemd/system/quantum-lab-agent.service', 'content': AGENT_UNIT},
        ],
        'runcmd': [
            ['systemctl', 'daemon-reload'],
            ['systemctl', 'enable', '--now', 'quantum-lab-agent.service'],
        ],
    }
    seed = out / 'seed'
    seed.mkdir(parents=True, exist_ok=True)
    (seed / 'user-data').write_text('#cloud-config\n' + json.dumps(user_data, indent=1) + '\n')
    (seed / 'meta-data').write_text('instance-id: quantum-lab\nlocal-hostname: quantum-lab\n')
    iso = out / 'seed.iso'
    if shutil.which('genisoimage'):
        subprocess.run(['genisoimage', '-quiet', '-output', str(iso), '-volid', 'cidata', '-joliet',
                        '-rock', str(seed / 'user-data'), str(seed / 'meta-data')], check=True)
    else:
        subprocess.run(['cloud-localds', str(iso), str(seed / 'user-data'), str(seed / 'meta-data')],
                       check=True)
    return iso


# ------------------------------------------------------------------ the machine

class Qmp:
    def __init__(self, path: Path, timeout: float = 30):
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.sock = socket.socket(socket.AF_UNIX)
                self.sock.connect(str(path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                self.sock.close()
                if time.monotonic() > deadline:
                    raise LabError(f'no QMP socket at {path}')
                time.sleep(0.1)
        self.file = self.sock.makefile('rwb')
        self.file.readline()
        self.execute('qmp_capabilities')

    def execute(self, command: str, **arguments) -> dict:
        self.file.write((json.dumps({'execute': command, 'arguments': arguments}) + '\n').encode())
        self.file.flush()
        while True:
            line = self.file.readline()
            if not line:
                raise LabError('QEMU closed its QMP socket')
            msg = json.loads(line)
            if 'error' in msg:
                raise LabError(f'{command}: {msg["error"].get("desc")}')
            if 'return' in msg:
                return msg['return']

    def hmp(self, command_line: str) -> str:
        out = self.execute('human-monitor-command', **{'command-line': command_line})
        # HMP reports failure as text, not as a QMP error
        if re.search(r'^Error', out, re.M):
            raise LabError(f'{command_line}: {out.strip()}')
        return out


def lab_machine(run: Path, disk: Path) -> 'Machine':
    """The lab's machine, always with the same devices: a snapshot restores
    only on the machine it was saved on (the cloud-init seed stays attached,
    and both shares are there whether used or not)."""
    (run / 'debs').mkdir(parents=True, exist_ok=True)
    return Machine(run, disk, shares={'lab': OS_DIR, 'debs': run / 'debs'}, seed=run / 'seed.iso')


class Machine:
    """One QEMU process: the disk, the agent's port, QMP, the shares."""

    def __init__(self, run: Path, disk: Path, shares: Optional[dict] = None,
                 seed: Optional[Path] = None, memory: int = 2048, cpus: int = 2):
        self.run, self.disk, self.shares, self.seed = run, disk, shares or {}, seed
        self.memory, self.cpus = memory, cpus
        self.qmp: Optional[Qmp] = None
        self.port: Optional[socket.socket] = None
        self.buf = b''
        self.next_id = 0

    def cmdline(self, loadvm: Optional[str] = None) -> list:
        accel = ['-accel', 'kvm', '-cpu', 'host'] if kvm_usable() else \
            ['-accel', 'tcg,thread=multi', '-cpu', 'max']
        cmd = ['qemu-system-x86_64', '-name', 'quantum-lab', '-machine', 'q35', *accel,
               '-smp', str(self.cpus), '-m', str(self.memory), '-nodefaults',
               '-drive', f'file={self.disk},if=virtio,format=qcow2,cache=unsafe',
               '-netdev', 'user,id=net0', '-device', 'virtio-net-pci,netdev=net0',
               '-device', 'virtio-rng-pci',
               '-device', 'virtio-serial-pci',
               '-chardev', f'socket,id=agent,path={self.run / "agent.sock"},server=on,wait=off',
               '-device', 'virtserialport,chardev=agent,name=org.quantum.lab',
               '-qmp', f'unix:{self.run / "qmp.sock"},server=on,wait=off',
               '-display', 'none', '-serial', f'file:{self.run / "serial.log"}',
               '-pidfile', str(self.run / 'qemu.pid'), '-daemonize']
        for tag, path in self.shares.items():
            cmd += ['-virtfs', f'local,path={path},mount_tag={tag},security_model=none,readonly=on']
        if self.seed:
            cmd += ['-drive', f'file={self.seed},if=virtio,media=cdrom,readonly=on']
        if loadvm:
            cmd += ['-loadvm', loadvm]
        return cmd

    def start(self, loadvm: Optional[str] = None) -> None:
        self.run.mkdir(parents=True, exist_ok=True)
        for name in ('agent.sock', 'qmp.sock'):
            (self.run / name).unlink(missing_ok=True)
        cmd = self.cmdline(loadvm)
        (self.run / 'qemu.cmdline').write_text(' '.join(cmd) + '\n')
        done = subprocess.run(cmd, capture_output=True, text=True)
        if done.returncode != 0:
            raise LabError(f'QEMU did not start: {done.stderr.strip()}')
        self.qmp = Qmp(self.run / 'qmp.sock')
        self.port = socket.socket(socket.AF_UNIX)
        self.port.connect(str(self.run / 'agent.sock'))
        self.buf = b''

    def alive(self) -> bool:
        try:
            pid = int((self.run / 'qemu.pid').read_text())
            os.kill(pid, 0)
            return True
        except (FileNotFoundError, ValueError, ProcessLookupError):
            return False

    def stop(self) -> None:
        if self.qmp:
            try:
                self.qmp.execute('quit')
            except (LabError, OSError):
                pass
        deadline = time.monotonic() + 10
        while self.alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if self.alive():
            os.kill(int((self.run / 'qemu.pid').read_text()), 9)
        self.qmp = None
        if self.port:
            self.port.close()
            self.port = None

    def agent(self, req: dict, timeout: float = 60) -> dict:
        """One request to the guest agent, its answer. Answers to earlier
        requests (one that timed out, or one from before a snapshot was
        restored) are skipped by their id."""
        assert self.port
        self.next_id += 1
        req = {**req, 'id': self.next_id}
        self.port.sendall((json.dumps(req) + '\n').encode())
        deadline = time.monotonic() + timeout
        while True:
            while b'\n' in self.buf:
                line, self.buf = self.buf.split(b'\n', 1)
                try:
                    answer = json.loads(line)
                except ValueError:
                    continue
                if answer.get('id') == self.next_id:
                    answer.pop('id')
                    return answer
            left = deadline - time.monotonic()
            if left <= 0:
                raise LabError(f'the guest agent did not answer {req["op"]} in {timeout:g} s')
            self.port.settimeout(left)
            try:
                chunk = self.port.recv(1 << 16)
            except socket.timeout:
                continue
            if not chunk:
                raise LabError('the agent port closed (QEMU stopped?)')
            self.buf += chunk

    def wait_agent(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            if not self.alive():
                raise LabError(f'QEMU stopped; see {self.run / "serial.log"}')
            try:
                return self.agent({'op': 'ping'}, timeout=3)
            except LabError:
                if time.monotonic() > deadline:
                    raise LabError(f'the guest agent never answered; see {self.run / "serial.log"}')

    def sh(self, command: str, timeout: float = 120, check: bool = True, **kw) -> dict:
        answer = self.agent({'op': 'exec', 'sh': command, 'timeout': timeout, **kw}, timeout + 10)
        if check and (not answer.get('ok') or answer.get('code') != 0):
            raise LabError(f'`{command}` failed: {answer}')
        return answer

    def save(self, name: str) -> None:
        assert self.qmp
        self.qmp.hmp(f'savevm {name}')

    def restore(self, name: str) -> None:
        assert self.qmp
        self.qmp.hmp(f'loadvm {name}')
        self.buf = b''
        self.agent({'op': 'clock', 'epoch': time.time()}, timeout=10)

    def snapshots(self) -> list:
        assert self.qmp
        out = self.qmp.hmp('info snapshots')
        return [line.split()[1] for line in out.splitlines()[2:] if len(line.split()) > 1]


# ------------------------------------------------------------------ the base

# What the Hive needs from the system that the minimal image lacks: polkit
# (the actuator acts through it), PackageKit and its pkcon (installs) and
# auditd (the process nerve reads program executions from the audit log).
PACKAGES = ['polkitd', 'packagekit', 'packagekit-tools', 'auditd']

# Timers that would act on their own during a test: a test must see only
# what it caused.
QUIET = ['apt-daily.timer', 'apt-daily-upgrade.timer', 'motd-news.timer', 'dpkg-db-backup.timer',
         'e2scrub_all.timer', 'fstrim.timer', 'systemd-tmpfiles-clean.timer']


# What a user may reach for and the Hive may offer to install: served by a
# signed repository in the guest, its only package source, so that grove
# finds them with apt and an approved install goes through PackageKit as on
# the real system, with no network.
REPO_PACKAGES = ['htop']

# Bumped when make_base changes what the base holds.
BASE_VERSION = 3


def base_fingerprint() -> str:
    """What the base snapshot was made from: when it changes, the base is
    made again. The machine's accelerator is part of it, since a snapshot
    saved under emulation does not restore under KVM. The agent is not: each
    install brings the working tree's."""
    h = hashlib.sha256()
    h.update(json.dumps([BASE_VERSION, IMAGE_DIR, IMAGE_NAME, AGENT_UNIT, PACKAGES, QUIET,
                         REPO_PACKAGES, kvm_usable()]).encode())
    return h.hexdigest()[:16]


def fetch_debs(guest_status: Path, out: Path, packages: list) -> list:
    """Downloads, on the host, the packages the guest lacks, with the
    guest's own dpkg status: apt works out what to fetch for the guest. The
    host must run the guest's release (CI and this lab's containers do); the
    guest itself needs no network nor any proxy."""
    release = Path('/etc/os-release').read_text()
    if f'VERSION_CODENAME={RELEASE}' not in release:
        raise LabError(f'making the base needs an Ubuntu {RELEASE} host (it downloads the guest\'s packages)')
    (out / 'partial').mkdir(parents=True, exist_ok=True)
    cmd = ['apt-get', '-q', '-y', '--download-only', '--no-install-recommends',
           '-o', f'Dir::State::status={guest_status}', '-o', f'Dir::Cache::archives={out}',
           '-o', 'Debug::NoLocking=1', 'install', *packages]
    if os.geteuid() != 0:
        cmd = ['sudo', '-n', *cmd]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise LabError(f'apt-get could not download {packages}: {done.stdout[-500:]}{done.stderr[-500:]}')
    return sorted(out.glob('*.deb'))


def make_repo(repo: Path) -> None:
    """A flat apt repository of the .debs in `repo`, signed with a key made
    for it (the key goes in the guest; no one else trusts it)."""
    entries = []
    for deb in sorted(repo.glob('*.deb')):
        control = subprocess.run(['dpkg-deb', '-f', str(deb)], capture_output=True, text=True,
                                 check=True).stdout.rstrip('\n')
        data = deb.read_bytes()
        entries.append(f'{control}\nFilename: ./{deb.name}\nSize: {len(data)}\n'
                       f'SHA256: {hashlib.sha256(data).hexdigest()}\n')
    packages = '\n'.join(entries).encode()
    (repo / 'Packages').write_bytes(packages)
    date = time.strftime('%a, %d %b %Y %H:%M:%S UTC', time.gmtime())
    (repo / 'Release').write_text(
        f'Origin: quantum-lab\nLabel: quantum-lab\nSuite: lab\nDate: {date}\nArchitectures: amd64 all\n'
        f'SHA256:\n {hashlib.sha256(packages).hexdigest()} {len(packages)} Packages\n')
    gnupg = repo / '.gnupg'
    gnupg.mkdir(mode=0o700)
    gpg = ['gpg', '--batch', '--quiet', '--homedir', str(gnupg), '--pinentry-mode', 'loopback', '--passphrase', '']
    subprocess.run([*gpg, '--quick-gen-key', 'Quantum OS VM lab <lab@quantum.invalid>', 'ed25519', 'sign',
                    'never'], check=True, capture_output=True)
    subprocess.run([*gpg, '--clearsign', '--output', str(repo / 'InRelease'), str(repo / 'Release')],
                   check=True, capture_output=True)
    subprocess.run([*gpg, '--output', str(repo / 'quantum-lab.gpg'), '--export'], check=True, capture_output=True)
    shutil.rmtree(gnupg)


REPO_SOURCE = """Types: deb
URIs: file:/var/lib/quantum-lab/repo
Suites: ./
Signed-By: /etc/apt/keyrings/quantum-lab.gpg
"""


def make_base(disk: Path, run: Path) -> None:
    """The base: the cloud image booted once, with the agent, the packages
    and the quiet timers, saved booted as the snapshot "base"."""
    started = time.monotonic()
    disk.unlink(missing_ok=True)
    subprocess.run(['qemu-img', 'create', '-q', '-f', 'qcow2', '-F', 'qcow2', '-b', str(cloud_image()),
                    str(disk), '12G'], check=True)
    debs = run / 'debs'
    shutil.rmtree(debs, ignore_errors=True)
    debs.mkdir(parents=True)
    seed_iso(run)
    machine = lab_machine(run, disk)
    machine.start()
    try:
        log('first boot of the cloud image (cloud-init installs the agent)')
        machine.wait_agent(900)
        status = run / 'guest-dpkg-status'
        status.write_bytes(base64.b64decode(machine.agent({'op': 'get', 'path': '/var/lib/dpkg/status'})['data']))
        names = [d.name for d in fetch_debs(status, debs, PACKAGES)]
        log(f'installing {len(names)} packages: {", ".join(PACKAGES)} and what they need')
        machine.agent({'op': 'mount', 'tag': 'debs'})
        machine.sh('DEBIAN_FRONTEND=noninteractive dpkg -i /mnt/debs/*.deb', timeout=900)
        machine.agent({'op': 'umount', 'tag': 'debs'})
        # the repository: what the guest lacks for REPO_PACKAGES, once the
        # packages above are in (packagekitd is stopped after: its cache
        # would predate the repository)
        status.write_bytes(base64.b64decode(machine.agent({'op': 'get', 'path': '/var/lib/dpkg/status'})['data']))
        fetch_debs(status, debs / 'repo', REPO_PACKAGES)
        make_repo(debs / 'repo')
        log(f'a signed repository in the guest, its only package source: {", ".join(REPO_PACKAGES)}')
        machine.agent({'op': 'mount', 'tag': 'debs'})
        machine.agent({'op': 'put', 'path': '/etc/apt/sources.list.d/quantum-lab.sources',
                       'data': base64.b64encode(REPO_SOURCE.encode()).decode()})
        machine.sh('mkdir -p /var/lib/quantum-lab/repo /etc/apt/keyrings && '
                   'cp /mnt/debs/repo/*.deb /mnt/debs/repo/Packages /mnt/debs/repo/Release '
                   '/mnt/debs/repo/InRelease /var/lib/quantum-lab/repo/ && '
                   'install -m 0644 /mnt/debs/repo/quantum-lab.gpg /etc/apt/keyrings/ && '
                   'mv /etc/apt/sources.list.d/ubuntu.sources /etc/apt/ubuntu.sources.offline && '
                   'apt-get update -q && systemctl stop packagekit', timeout=300)
        machine.agent({'op': 'umount', 'tag': 'debs'})
        machine.sh(f'systemctl mask --now {" ".join(QUIET)}')
        # a guest that waits for nothing at the next restore
        machine.sh('cloud-init status --wait >/dev/null 2>&1 || true; sync')
        machine.save('base')
    finally:
        machine.stop()
    (run / 'base.json').write_text(json.dumps({'fingerprint': base_fingerprint()}))
    log(f'base made in {time.monotonic() - started:.0f} s')


# ------------------------------------------------------------------ the Hive

BINARIES = ['hive-cortex', 'hive-synapse', 'hive-actuator', 'hive-nerve-process', 'hive-nerve-journal',
            'hive-nerve-network', 'hive-nerve-fs', 'hive-apt', 'hive-zfs', 'hive-dashboard', 'grove',
            'hive-lab']

# Who registers with hive-cortex when the Hive is up (its log names them so).
COMPONENTS = ['Synapse', 'Actuator', 'NerveProcess', 'NerveJournal', 'NerveNetwork', 'NerveFs']


def stage(profile: str = 'debug') -> dict:
    """Copies the workspace's binaries, without their debug sections, to
    target/vm-lab/bin, where the guest installs them from (what the ISO
    ships is a release build; debug sections would only slow the copy).
    Answers a digest of every file the guest installs, by path: what changed
    since the snapshot "hive" was saved is all that needs installing."""
    src = OS_DIR / 'target' / profile
    out = OS_DIR / 'target' / 'vm-lab' / 'bin'
    out.mkdir(parents=True, exist_ok=True)
    missing = [b for b in BINARIES if not (src / b).is_file()]
    if missing:
        raise LabError(f'missing in {src}: {", ".join(missing)} (cargo build --workspace)')
    files = {}
    for b in BINARIES:
        built, staged = src / b, out / b
        if not staged.is_file() or staged.stat().st_mtime < built.stat().st_mtime:
            subprocess.run(['objcopy', '--strip-debug', str(built), str(staged)], check=True)
        files[f'bin/{b}'] = hashlib.sha256(staged.read_bytes()).hexdigest()
    for f in sorted([*(OS_DIR / 'config').rglob('*'), *(OS_DIR / 'knowledge').rglob('*'),
                     HERE / 'install-hive.sh', HERE / 'agent.py']):
        if f.is_file():
            files[str(f.relative_to(OS_DIR))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return files


class Lab:
    """A session: the machine, a fresh Hive in it, and what was looked at."""

    def __init__(self, profile: str = 'debug'):
        self.profile = profile
        self.run = CACHE / 'run'
        self.disk = CACHE / 'lab.qcow2'
        self.machine: Optional[Machine] = None
        self.cursor: Optional[str] = None
        self.apps: dict = {}
        self.lock = None

    # -- the session

    def start(self) -> dict:
        """A fresh Hive, from the snapshot "hive" when the working tree's
        build is the one it holds, else installed again on "base"."""
        started = time.monotonic()
        self.run.mkdir(parents=True, exist_ok=True)
        if self.lock is None:
            import fcntl
            self.lock = open(self.run / 'lock', 'w')
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.lock = None
                raise LabError('another VM lab is using this cache (QUANTUM_LAB_CACHE)')
        base = self.run / 'base.json'
        if not self.disk.is_file() or not base.is_file() or \
                json.loads(base.read_text()).get('fingerprint') != base_fingerprint():
            if self.machine:
                self.machine.stop()
                self.machine = None
            make_base(self.disk, self.run)
            (self.run / 'hive.json').unlink(missing_ok=True)
        files = stage(self.profile)
        hive = self.run / 'hive.json'
        held = json.loads(hive.read_text()).get('files', {}) if hive.is_file() else {}
        if held:
            # the snapshot "hive" and what changed since: the binaries are
            # the bulk of an install, so only the changed ones are copied
            changed = [b for b in BINARIES if files[f'bin/{b}'] != held.get(f'bin/{b}')]
            others = any(files[f] != held.get(f) for f in files if not f.startswith('bin/'))
            snapshot = 'hive'
        else:
            changed, others, snapshot = list(BINARIES), True, 'base'
        if self.machine and self.machine.alive():
            self.machine.restore(snapshot)
        else:
            self.machine = lab_machine(self.run, self.disk)
            self.machine.start(loadvm=snapshot)
            self.machine.wait_agent(60)
            self.machine.agent({'op': 'clock', 'epoch': time.time()})
        how = 'restored'
        if changed or others:
            self.install(changed, only_binaries=snapshot == 'hive' and not others)
            hive.write_text(json.dumps({'files': files}))
            how = f'installed {", ".join(changed)}' if changed and snapshot == 'hive' else 'installed'
        self.apps = {}
        self.cursor = self.machine.agent({'op': 'journal', 'lines': 0})['cursor']
        self.machine.agent({'op': 'exec', 'sh': 'date "+%Y-%m-%d %H:%M:%S" > /run/lab-tape-start'})
        return {'hive': how, 'seconds': round(time.monotonic() - started, 2)}

    def install(self, binaries: list, only_binaries: bool = False) -> None:
        """Installs the staged Hive (as the ISO does; of the binaries, only
        `binaries`), waits until every component has registered with
        hive-cortex, saves "hive". With `only_binaries`, nothing but those
        binaries changed: they are copied and their units restarted."""
        m = self.m
        env = {'HIVE_ONLY_BINARIES' if only_binaries else 'HIVE_BINARIES': ' '.join(binaries)}
        m.agent({'op': 'mount', 'tag': 'lab'})
        try:
            done = m.agent({'op': 'exec', 'sh': 'sh /mnt/lab/scripts/lab/vm/install-hive.sh /mnt/lab',
                            'env': env, 'timeout': 600}, 610)
            if done.get('code') != 0:
                raise LabError(f'install-hive.sh failed: {done.get("stderr") or done.get("error")}')
            if not only_binaries:
                m.sh('cmp -s /mnt/lab/scripts/lab/vm/agent.py /usr/local/lib/quantum-lab/agent.py || '
                     'install -m 0755 /mnt/lab/scripts/lab/vm/agent.py /usr/local/lib/quantum-lab/agent.py')
        finally:
            m.agent({'op': 'umount', 'tag': 'lab'})
        if not only_binaries:
            m.agent({'op': 'restart'})
            m.wait_agent(30)
        deadline = time.monotonic() + 120
        while True:
            log_text = m.sh('journalctl -u hive-cortex --no-pager -o cat '
                            '_SYSTEMD_INVOCATION_ID=$(systemctl show -p InvocationID --value hive-cortex)',
                            check=False)['stdout']
            missing = [c for c in COMPONENTS if f' as {c}' not in log_text]
            if not missing:
                break
            if time.monotonic() > deadline:
                raise LabError(f'never registered with hive-cortex: {missing}')
            time.sleep(0.5)
        m.save('hive')

    @property
    def m(self) -> Machine:
        if not self.machine:
            raise LabError('no VM: start first')
        return self.machine

    def end(self) -> dict:
        if self.machine:
            self.machine.stop()
            self.machine = None
        return {}

    # -- the requests

    def handle(self, req: dict) -> dict:
        op = req.get('op')
        fn = getattr(self, f'op_{op}', None)
        if not fn:
            raise LabError(f'unknown op {op!r}')
        return fn(req)

    def op_start(self, req):
        return self.start()

    def op_end(self, req):
        return self.end()

    def op_restore(self, req):
        name = req.get('snapshot', 'hive')
        started = time.monotonic()
        self.m.restore(name)
        self.apps = {}
        self.cursor = self.m.agent({'op': 'journal', 'lines': 0})['cursor']
        return {'seconds': round(time.monotonic() - started, 2)}

    def op_save(self, req):
        name = req['snapshot']
        if name in ('base', 'hive'):
            raise LabError(f'"{name}" belongs to the lab; save under another name')
        self.m.save(name)
        return {}

    def op_install(self, req):
        """After a rebuild: what `start` does, which installs what changed
        (the snapshot "hive" follows)."""
        return self.start()

    def op_sh(self, req):
        """A command as root (or `user`). Expects exit code `code` (0; null
        for any), output that `contains` / `excludes` text."""
        answer = self.m.agent({'op': 'exec', 'sh': req['sh'], 'user': req.get('user'),
                               'timeout': req.get('timeout', 60)}, req.get('timeout', 60) + 10)
        if not answer.get('ok'):
            return answer
        out = answer['stdout'] + answer['stderr']
        problem = expectation(req, answer.get('code'), out)
        result = {'code': answer.get('code'), 'stdout': answer['stdout'], 'stderr': answer['stderr']}
        return {**result, 'ok': False, 'error': problem} if problem else result

    def op_put(self, req):
        """Writes `text` to `path` in the guest (`mode`: 644)."""
        return self.m.agent({'op': 'put', 'path': req['path'], 'mode': req.get('mode', '644'),
                             'data': base64.b64encode(req['text'].encode()).decode()})

    def op_until_sh(self, req):
        """Runs `sh` until it meets the expectations of op_sh, within
        `timeout` seconds (10)."""
        deadline = time.monotonic() + req.get('timeout', 10)
        while True:
            answer = self.op_sh({**req, 'timeout': 30})
            if answer.get('ok', True):
                return answer
            if time.monotonic() > deadline:
                return answer
            time.sleep(req.get('every', 0.5))

    def journal_since(self, units=None) -> list:
        answer = self.m.agent({'op': 'journal', 'cursor': self.cursor, 'units': units or []})
        return answer['entries'], answer['cursor']

    def op_journal(self, req):
        """The journal since the last look (of `units`, if given)."""
        entries, self.cursor = self.journal_since(req.get('units'))
        return {'entries': entries}

    def op_until_journal(self, req):
        """Waits for a journal entry (of `unit`, if given) that `contains`
        text and not `excludes`; the next look starts after it."""
        deadline = time.monotonic() + req.get('timeout', 10)
        units = [req['unit']] if req.get('unit') else []
        while True:
            answer = self.m.agent({'op': 'journal', 'cursor': self.cursor, 'units': units})
            for e in answer['entries']:
                text = f'{e["unit"]}: {e["message"]}'
                if req['contains'] in text and not (req.get('excludes') and req['excludes'] in text):
                    self.cursor = e['cursor']
                    return {'entry': e}
            if time.monotonic() > deadline:
                return {'ok': False, 'error': f'the journal never showed {req["contains"]!r}',
                        'seen': [f'{e["unit"]}: {e["message"]}' for e in answer['entries']][-15:]}
            time.sleep(0.3)

    def op_none_journal(self, req):
        """Nothing in the journal (of `unit`) `contains` text for `within`
        seconds (1)."""
        time.sleep(req.get('within', 1))
        units = [req['unit']] if req.get('unit') else []
        entries, self.cursor = self.journal_since(units)
        hits = [f'{e["unit"]}: {e["message"]}' for e in entries if req['contains'] in f'{e["unit"]}: {e["message"]}']
        if hits:
            return {'ok': False, 'error': f'the journal showed {req["contains"]!r}', 'seen': hits[:10]}
        return {}

    # -- the real dashboard and grove, in a terminal in the guest

    # app -> (who logged in, the program)
    APPS = {
        'dashboard': (None, ['/usr/bin/hive-dashboard']),
        'grove': ('druid', ['runuser', '-l', 'druid', '-c', '/usr/bin/grove']),
    }

    def op_tui(self, req):
        app = req['app']
        if app not in self.APPS:
            raise LabError(f'tui app: one of {", ".join(self.APPS)}')
        login, program = self.APPS[app]
        argv = ['/usr/local/lib/quantum-lab/hive-lab', 'term', '--rows', str(req.get('rows', 30)),
                '--cols', str(req.get('cols', 100)), '--', *program]
        answer = self.m.agent({'op': 'proc_start', 'name': app, 'argv': argv, 'login': login})
        if answer.get('ok'):
            self.apps[app] = True
        return answer

    def term(self, app: str, req: dict, timeout: float = 30) -> dict:
        if app not in self.apps:
            raise LabError(f'{app} is not running: {{"op":"tui","app":"{app}"}} first')
        answer = self.m.agent({'op': 'proc_call', 'name': app, 'line': json.dumps(req),
                               'timeout': timeout}, timeout + 10)
        return json.loads(answer['line']) if answer.get('ok') else answer

    def op_view(self, req):
        return self.term(req['app'], {'op': 'view'})

    def op_keys(self, req):
        return self.term(req['app'], {'op': 'keys', 'keys': req.get('keys', [])})

    def op_until_screen(self, req):
        """Waits until the screen shows `contains` (and not `excludes`; and
        exactly `count` times, if given)."""
        t = req.get('timeout', 5)
        if 'count' not in req:
            return self.term(req['app'], {'op': 'until', 'contains': req['contains'],
                                          'excludes': req.get('excludes'), 'timeout': t}, t + 5)
        deadline = time.monotonic() + t
        while True:
            screen = self.term(req['app'], {'op': 'view'}).get('screen', '')
            seen = screen.count(req['contains'])
            if seen == req['count']:
                return {'screen': screen}
            if time.monotonic() > deadline:
                return {'ok': False, 'screen': screen,
                        'error': f'the screen shows {req["contains"]!r} {seen} times, not {req["count"]}'}
            time.sleep(0.2)

    def op_keys_until(self, req):
        """Presses `keys` until the screen shows `contains` (at most `max`
        times, 20): to move a selection to a row by what the row says."""
        for _ in range(req.get('max', 20)):
            screen = self.term(req['app'], {'op': 'view'}).get('screen', '')
            if req['contains'] in screen:
                return {'screen': screen}
            self.term(req['app'], {'op': 'keys', 'keys': req['keys']})
            time.sleep(0.1)
        return {'ok': False, 'error': f'the screen never showed {req["contains"]!r}', 'screen': screen}


def expectation(req: dict, code, out: str) -> Optional[str]:
    want = req.get('code', 0)
    if want is not None and code != want:
        return f'exit code {code}, expected {want}'
    if req.get('contains') and req['contains'] not in out:
        return f'the output does not show {req["contains"]!r}'
    if req.get('excludes') and req['excludes'] in out:
        return f'the output shows {req["excludes"]!r}'
    return None


# ------------------------------------------------------------------ the driver

def answer_line(lab: Lab, line: str) -> dict:
    try:
        req = json.loads(line)
    except ValueError as e:
        return {'ok': False, 'error': f'not JSON: {e}'}
    try:
        answer = lab.handle(req)
        answer = {'ok': True, **answer} if 'ok' not in answer else answer
    except (LabError, KeyError, OSError, subprocess.CalledProcessError) as e:
        answer = {'ok': False, 'error': f'{type(e).__name__}: {e}' if not isinstance(e, LabError) else str(e)}
    if isinstance(req, dict) and 'id' in req:
        answer['id'] = req['id']
    return answer


def evidence(lab: Lab) -> str:
    """What the guest's journal says since the tape started, for a failure
    seen where nobody can look into the guest afterwards (CI)."""
    if not lab.machine or not lab.machine.alive():
        return '      (no VM to ask)'
    try:
        answer = lab.machine.agent({'op': 'exec', 'sh': (
            "journalctl --no-pager -o short-precise --since \"$(cat /run/lab-tape-start 2>/dev/null || echo '-2min')\" "
            "| grep -v -e quantum-lab-agent -e 'kernel:' | tail -n 80")}, 30)
        return '      the guest\'s journal:\n' + '\n'.join(
            '        ' + line for line in answer.get('stdout', '').splitlines())
    except LabError as e:
        return f'      (the guest did not answer: {e})'


def play(lab: Lab, tapes: list) -> int:
    """Plays tapes one after the other on one machine: each starts from a
    fresh Hive (its `start` restores "hive"), and the machine stops after
    the last."""
    failed = 0
    try:
        for tape in tapes:
            started = time.monotonic()
            for n, line in enumerate(Path(tape).read_text().splitlines(), 1):
                if not line.strip() or line.lstrip().startswith('//'):
                    continue
                if json.loads(line).get('op') == 'end':
                    continue
                answer = answer_line(lab, line)
                if not answer.get('ok'):
                    print(f'FAIL  {Path(tape).name}:{n}  {line.strip()}\n      {json.dumps(answer)[:2000]}')
                    print(evidence(lab))
                    failed += 1
                    break
            else:
                print(f'ok    {Path(tape).name}  {time.monotonic() - started:.1f} s')
    finally:
        lab.end()
    return 1 if failed else 0


def main() -> int:
    args = sys.argv[1:]
    profile = 'debug'
    if '--release' in args:
        args.remove('--release')
        profile = 'release'
    lab = Lab(profile)
    if args[:1] == ['--play']:
        tapes = args[1:] or sorted(str(p) for p in (HERE / 'tapes').glob('*.jsonl'))
        return play(lab, tapes)
    if args:
        print(__doc__)
        return 2
    try:
        for line in sys.stdin:
            if line.strip():
                print(json.dumps(answer_line(lab, line)), flush=True)
    finally:
        lab.end()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
