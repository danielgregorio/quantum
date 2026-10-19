#!/usr/bin/env python3
"""DruidOS lab harness: drives QEMU/KVM guests for ISO boot and e2e tests.

Runs inside the druidos-lab container on Forge (scripts/lab/lab.Dockerfile),
launched by scripts/lab/remote.sh. Stdlib + Pillow + tesseract only.

Every wait has a timeout, and the run directory always keeps the evidence:
qemu.cmdline, qemu.log, serial.log, screens/ (one PNG + OCR text per
distinct screen seen), screen-final.png and result.json.
"""

import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time

from PIL import Image, ImageOps, ImageStat

# Text expected on screen at each boot milestone (matched against OCR
# output, case-insensitive). Loose enough for OCR noise, but specific to the
# milestone: a bare "Welcome" also matches systemd's early "Welcome to
# Ubuntu!" boot banner, long before Subiquity is up.
GRUB_MENU = r"Try or Install|GNU GRUB"
INSTALLER_UI = r"Use UP, DOWN and ENTER|select your language"


class StepFailed(Exception):
    pass


def log(msg):
    print(f"[harness {time.strftime('%H:%M:%S')}] {msg}", flush=True)


class Qmp:
    """Minimal QMP client: newline-delimited JSON over a unix socket."""

    def __init__(self, path, timeout=30):
        deadline = time.monotonic() + timeout
        while True:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.sock.connect(path)
                break
            except (FileNotFoundError, ConnectionRefusedError):
                self.sock.close()
                if time.monotonic() > deadline:
                    raise StepFailed(f"could not connect to QMP socket {path}")
                time.sleep(0.2)
        self.sock.settimeout(60)
        self.file = self.sock.makefile("rwb")
        self._read()  # greeting
        self.execute("qmp_capabilities")

    def _read(self):
        line = self.file.readline()
        if not line:
            raise StepFailed("QMP connection closed (QEMU exited?)")
        return json.loads(line)

    def execute(self, command, **arguments):
        msg = {"execute": command}
        if arguments:
            msg["arguments"] = arguments
        self.file.write(json.dumps(msg).encode() + b"\n")
        self.file.flush()
        while True:
            reply = self._read()
            if "return" in reply:
                return reply["return"]
            if "error" in reply:
                raise StepFailed(f"QMP {command} failed: {reply['error']}")
            # otherwise an asynchronous {"event": ...}; keep reading

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def find_ovmf():
    for code, vars_template in [
        ("/usr/share/OVMF/OVMF_CODE_4M.fd", "/usr/share/OVMF/OVMF_VARS_4M.fd"),
        ("/usr/share/OVMF/OVMF_CODE.fd", "/usr/share/OVMF/OVMF_VARS.fd"),
    ]:
        if os.path.exists(code) and os.path.exists(vars_template):
            return code, vars_template
    raise StepFailed("OVMF firmware not found (is the ovmf package installed?)")


def ocr(png_path):
    """OCR a screendump. VGA text mode is 720x400 light-on-dark, which
    tesseract reads poorly as-is: normalize to dark-on-light and upscale.

    Two passes, texts joined: the plain inversion, and a threshold that
    keeps only bright pixels as ink - the inversion loses light text on a
    colored bar (Subiquity's orange title bar, its green focused button),
    which ends up mid-gray on mid-gray."""
    gray = Image.open(png_path).convert("L")
    inverted = ImageOps.invert(gray) if ImageStat.Stat(gray).mean[0] < 128 else gray
    bright_ink = gray.point(lambda v: 0 if v > 200 else 255)
    texts = []
    for i, img in enumerate((inverted, bright_ink)):
        if img.width < 1200:
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        prepared = f"{png_path}.ocr{i}.png"
        img.save(prepared)
        try:
            result = subprocess.run(
                ["tesseract", prepared, "stdout"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            os.remove(prepared)
        texts.append(result.stdout)
    return "\n".join(texts)


class Vm:
    def __init__(
        self,
        run_dir,
        firmware="bios",
        accel="kvm",
        memory_mb=4096,
        cpus=2,
        uefi_vars=None,
        ssh_port=None,
    ):
        if firmware not in ("bios", "uefi"):
            raise StepFailed(f"unknown firmware {firmware!r} (expected bios or uefi)")
        self.run_dir = run_dir
        self.firmware = firmware
        self.accel = accel
        self.memory_mb = memory_mb
        self.cpus = cpus
        # UEFI NVRAM file. Pass the one from an earlier boot to keep the boot
        # entries an installer wrote; by default a fresh copy is made.
        self.uefi_vars = uefi_vars or os.path.join(run_dir, "OVMF_VARS.fd")
        self.ssh_port = ssh_port
        self.proc = None
        self.qmp = None
        self.qemu_log = None
        self.qmp_path = os.path.join(run_dir, "qmp.sock")
        self.serial_log = os.path.join(run_dir, "serial.log")
        self.screens_dir = os.path.join(run_dir, "screens")
        self.last_screen_text = ""
        self.screen_count = 0
        os.makedirs(self.screens_dir, exist_ok=True)

    def start(self, extra_args):
        nic = "user,model=virtio-net-pci"
        if self.ssh_port:
            nic += f",hostfwd=tcp:127.0.0.1:{self.ssh_port}-:22"
        args = [
            "qemu-system-x86_64",
            "-machine", f"q35,accel={self.accel}",
            "-cpu", "host" if self.accel == "kvm" else "max",
            "-m", str(self.memory_mb),
            "-smp", str(self.cpus),
            "-display", "none",
            "-vga", "std",
            "-serial", f"file:{self.serial_log}",
            "-qmp", f"unix:{self.qmp_path},server=on,wait=off",
            "-nic", nic,
        ]
        if self.firmware == "uefi":
            code, vars_template = find_ovmf()
            if not os.path.exists(self.uefi_vars):
                shutil.copyfile(vars_template, self.uefi_vars)
            args += [
                "-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                "-drive", f"if=pflash,format=raw,file={self.uefi_vars}",
            ]
        args += extra_args

        with open(os.path.join(self.run_dir, "qemu.cmdline"), "w") as f:
            f.write(" ".join(args) + "\n")
        if os.path.exists(self.qmp_path):
            os.remove(self.qmp_path)
        self.qemu_log = open(os.path.join(self.run_dir, "qemu.log"), "wb")
        self.proc = subprocess.Popen(args, stdout=self.qemu_log, stderr=subprocess.STDOUT)

        deadline = time.monotonic() + 30
        while not os.path.exists(self.qmp_path):
            if self.proc.poll() is not None:
                raise StepFailed(f"QEMU exited during startup: {self.tail('qemu.log')}")
            if time.monotonic() > deadline:
                raise StepFailed("QEMU started but its QMP socket never appeared")
            time.sleep(0.2)
        self.qmp = Qmp(self.qmp_path)
        kvm = self.qmp.execute("query-kvm")
        return f"accel={self.accel} kvm={kvm}"

    def tail(self, name, max_bytes=2000):
        path = os.path.join(self.run_dir, name)
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                f.seek(max(0, f.tell() - max_bytes))
                return f.read().decode(errors="replace")
        except OSError:
            return ""

    def ensure_running(self, waiting_for):
        if self.proc.poll() is not None:
            raise StepFailed(
                f"QEMU exited (code {self.proc.returncode}) while waiting for {waiting_for}"
            )

    def screenshot(self, path):
        self.qmp.execute("screendump", filename=path, format="png")

    def send_key(self, key):
        self.qmp.execute("send-key", keys=[{"type": "qcode", "data": key}])

    def send_keys(self, keys, delay=0.08):
        for key in keys:
            self.send_key(key)
            time.sleep(delay)

    def type_text(self, text):
        """Type `text` on the guest keyboard (lowercase letters, digits, -)."""
        names = {"-": "minus", " ": "spc"}
        self.send_keys([names.get(ch, ch) for ch in text])

    def read_screen(self, label, regex=None):
        """Screendump + OCR the current screen; returns (text, match of
        `regex` or None).

        Each sufficiently different screen, and always one that matches, is
        saved under screens/ (PNG + OCR text), so a failure leaves a readable
        trail of what the guest showed.
        """
        current = os.path.join(self.run_dir, "screen-current.png")
        self.screenshot(current)
        text = ocr(current)
        match = regex.search(text) if regex else None
        normalized = " ".join(text.split())
        similarity = difflib.SequenceMatcher(None, normalized, self.last_screen_text).ratio()
        if match or similarity < 0.85:
            self.last_screen_text = normalized
            self.screen_count += 1
            suffix = "-match" if match else ""
            stem = os.path.join(self.screens_dir, f"{self.screen_count:03d}-{label}{suffix}")
            shutil.copyfile(current, stem + ".png")
            with open(stem + ".txt", "w") as f:
                f.write(text)
            log(f"screen {self.screen_count:03d} ({label}{suffix}): {normalized[:120]!r}")
        return text, match

    def wait_for_screen(self, pattern, timeout, label, interval=2.0):
        """Poll screendumps + OCR until `pattern` shows up on screen."""
        regex = re.compile(pattern, re.IGNORECASE)
        deadline = time.monotonic() + timeout
        while True:
            self.ensure_running(label)
            text, match = self.read_screen(label, regex)
            normalized = " ".join(text.split())
            if match:
                return f"matched {match.group(0)!r} (screen {self.screen_count:03d})"
            if time.monotonic() > deadline:
                raise StepFailed(
                    f"timed out after {timeout}s waiting for /{pattern}/ on screen; "
                    f"last screen: {normalized[:300]!r}"
                )
            time.sleep(interval)

    def wait_for_serial(self, pattern, timeout, label, interval=1.0):
        regex = re.compile(pattern)
        deadline = time.monotonic() + timeout
        while True:
            try:
                with open(self.serial_log, "rb") as f:
                    text = f.read().decode(errors="replace")
            except OSError:
                text = ""
            match = regex.search(text)
            if match:
                return f"serial matched {match.group(0)!r}"
            self.ensure_running(label)
            if time.monotonic() > deadline:
                raise StepFailed(
                    f"timed out after {timeout}s waiting for /{pattern}/ on serial; "
                    f"serial tail: {self.tail('serial.log', 500)!r}"
                )
            time.sleep(interval)

    def wait_for_exit(self, timeout, label, fail_pattern=None, screenshot_every=60):
        """Wait for the guest to power off (QEMU exits), e.g. at the end of
        an unattended install. Fails early if `fail_pattern` shows up on the
        serial console, and keeps a periodic screenshot trail meanwhile."""
        fail_regex = re.compile(fail_pattern) if fail_pattern else None
        deadline = time.monotonic() + timeout
        next_shot = time.monotonic() + screenshot_every
        offset = 0
        shots = 0
        while self.proc.poll() is None:
            if fail_regex:
                try:
                    with open(self.serial_log, "rb") as f:
                        f.seek(max(0, offset - 200))  # overlap: matches split across reads
                        chunk = f.read().decode(errors="replace")
                        offset = f.tell()
                    match = fail_regex.search(chunk)
                    if match:
                        raise StepFailed(f"failure on serial console during {label}: {match.group(0)!r}")
                except OSError:
                    pass
            if time.monotonic() > deadline:
                raise StepFailed(
                    f"guest still running after {timeout}s ({label}); "
                    f"serial tail: {self.tail('serial.log', 800)!r}"
                )
            if time.monotonic() > next_shot:
                shots += 1
                try:
                    self.screenshot(os.path.join(self.screens_dir, f"{label}-{shots:03d}.png"))
                except (StepFailed, OSError):
                    pass
                next_shot = time.monotonic() + screenshot_every
            time.sleep(3)
        return f"guest powered off, QEMU exit code {self.proc.returncode}"

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.screenshot(os.path.join(self.run_dir, "screen-final.png"))
            except (StepFailed, OSError):
                pass
            try:
                self.qmp.execute("quit")
            except (StepFailed, OSError):
                pass
            try:
                self.proc.wait(15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        if self.qmp:
            self.qmp.close()
        if self.qemu_log:
            self.qemu_log.close()
        for leftover in (self.qmp_path, os.path.join(self.run_dir, "screen-current.png")):
            if os.path.exists(leftover):
                os.remove(leftover)


class Run:
    """Records named steps with timings; writes result.json at the end."""

    def __init__(self, run_dir, name):
        self.run_dir = run_dir
        self.name = name
        self.steps = []
        self.started = time.monotonic()
        os.makedirs(run_dir, exist_ok=True)

    def step(self, name, fn):
        log(f"[step] {self.name}: {name}")
        t0 = time.monotonic()
        try:
            detail = fn()
        except StepFailed as e:
            self._record(name, False, t0, str(e))
            log(f"[FAIL] {self.name}: {name} ({time.monotonic() - t0:.0f}s): {e}")
            raise
        self._record(name, True, t0, detail)
        log(f"[ ok ] {self.name}: {name} ({time.monotonic() - t0:.0f}s) {detail or ''}")

    def _record(self, name, ok, t0, detail):
        self.steps.append(
            {"step": name, "ok": ok, "seconds": round(time.monotonic() - t0, 1), "detail": detail}
        )

    @property
    def ok(self):
        return bool(self.steps) and all(s["ok"] for s in self.steps)

    def finish(self):
        result = {
            "run": self.name,
            "ok": self.ok,
            "seconds": round(time.monotonic() - self.started, 1),
            "steps": self.steps,
        }
        with open(os.path.join(self.run_dir, "result.json"), "w") as f:
            json.dump(result, f, indent=2)
        return result


def cmd_boot_smoke(args):
    """Boot the ISO like a real CD and follow it to the installer UI.

    Proves the whole chain up to userspace: firmware finds the El Torito
    image, GRUB loads its menu, kernel + initrd boot, the live system
    starts Subiquity. Uses screens (not serial) because the ISO's GRUB and
    kernel command line don't enable a serial console.
    """
    if not os.path.isfile(args.iso):
        log(f"ISO not found: {args.iso}")
        return 1

    results = []
    for firmware in args.firmware.split(","):
        run_dir = os.path.join(args.out, firmware)
        run = Run(run_dir, f"boot-smoke/{firmware}")
        vm = None
        try:
            vm = Vm(run_dir, firmware=firmware, accel=args.accel)
            run.step(
                "qemu-start",
                lambda: vm.start(
                    ["-drive", f"file={args.iso},media=cdrom,readonly=on,format=raw", "-boot", "d"]
                ),
            )
            run.step("grub-menu", lambda: vm.wait_for_screen(GRUB_MENU, 120, "grub"))
            # Pick the default entry now instead of sitting out GRUB's timeout.
            vm.send_key("ret")
            run.step(
                "installer-ui",
                lambda: vm.wait_for_screen(INSTALLER_UI, args.timeout, "installer"),
            )
            # The ISO's kernel command line puts a console on ttyS0 too.
            run.step("serial-console", lambda: vm.wait_for_serial(r"Linux version \S+", 10, "serial"))
        except StepFailed:
            pass
        finally:
            if vm:
                vm.stop()
            results.append(run.finish())

    return summarize(results)


def summarize(results):
    log("summary:")
    for result in results:
        status = "PASS" if result["ok"] else "FAIL"
        steps = ", ".join(f"{s['step']}={'ok' if s['ok'] else 'FAIL'}({s['seconds']}s)" for s in result["steps"])
        log(f"  {status} {result['run']} in {result['seconds']}s: {steps}")
    return 0 if all(r["ok"] for r in results) else 1


def run_tool(args, timeout=300):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise StepFailed(f"{args[0]} failed ({result.returncode}): {result.stderr.strip()[-500:]}")
    return result.stdout


def iso_extract(iso, path_in_iso, dest):
    run_tool(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", path_in_iso, dest])
    return dest


def iso_kernel_args(grub_cfg):
    """Command line of the ISO's default GRUB entry (the first `linux` line),
    minus the kernel path - so a direct kernel boot sees exactly what GRUB
    would pass, including the console=/--- arguments the installed system
    inherits."""
    with open(grub_cfg) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "linux":
                return " ".join(parts[2:])
    raise StepFailed("no linux line in the ISO's grub.cfg")


# Unattended install answers. Test-only: a disposable user with an
# ephemeral SSH key and passwordless sudo. The production ISO never
# autoinstalls - only a direct kernel boot with `autoinstall` on the
# command line plus this CIDATA seed does.
USER_DATA = """#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  source:
    id: druidos
  identity:
    hostname: druidos-lab
    username: druid
    password: "{password_hash}"
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
      - "{public_key}"
  storage:
    layout:
      name: {storage_layout}
  late-commands:
    - echo 'druid ALL=(ALL) NOPASSWD:ALL' > /target/etc/sudoers.d/90-druidos-lab
    - chmod 0440 /target/etc/sudoers.d/90-druidos-lab
  shutdown: poweroff
"""

# Subiquity reports install problems on the console like this; seeing one
# means the install won't power off on its own, so don't wait out the timeout.
INSTALL_FAILURE = r"finish: subiquity/\S+: FAIL|An error occurred during installation|autoinstall config did not validate"

SSH_USER = "druid"


SSH_OPTIONS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "ConnectTimeout=5",
    "-o", "BatchMode=yes",
]

# What a hot-swap pushes into a running guest: the workspace's release
# binaries plus the unit files, i.e. everything a Rust or unit change
# touches, without rebuilding the ISO or reinstalling.
HIVE_UNITS = [
    "hive-cortex", "hive-synapse", "hive-actuator",
    "hive-nerve-process", "hive-nerve-journal", "hive-nerve-network", "hive-nerve-fs",
]
HOTSWAP_BINARIES = HIVE_UNITS + ["hive-apt", "hive-zfs", "hive-dashboard", "grove"]


def ssh(key, port, command, timeout=120, input=None):
    return subprocess.run(
        ["ssh", "-i", key, "-p", str(port), *SSH_OPTIONS, f"{SSH_USER}@127.0.0.1", command],
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input,
    )


def scp_to_guest(key, port, sources, dest):
    run_tool(["scp", "-i", key, "-P", str(port), *SSH_OPTIONS, *sources, f"{SSH_USER}@127.0.0.1:{dest}"])


def graceful_poweroff(vm, key, port, timeout=120):
    try:
        ssh(key, port, "sudo systemctl poweroff", timeout=20)
    except subprocess.TimeoutExpired:
        pass
    return vm.wait_for_exit(timeout, "poweroff")


def wait_for_ssh(vm, key, port, timeout):
    deadline = time.monotonic() + timeout
    while True:
        vm.ensure_running("ssh")
        try:
            result = ssh(key, port, "true", timeout=20)
            if result.returncode == 0:
                return "ssh login ok"
            last = result.stderr.strip()
        except subprocess.TimeoutExpired:
            last = "ssh timed out"
        if time.monotonic() > deadline:
            raise StepFailed(f"no SSH login after {timeout}s (last: {last!r})")
        time.sleep(5)


def guest_check(key, port, command, expect, label, evidence_dir):
    """Run `command` in the guest, save its output, require `expect` in it."""
    try:
        result = ssh(key, port, command)
    except subprocess.TimeoutExpired:
        raise StepFailed(f"{label}: guest command timed out: {command}")
    output = result.stdout + result.stderr
    with open(os.path.join(evidence_dir, f"{label}.txt"), "w") as f:
        f.write(f"$ {command}\n(exit {result.returncode})\n{output}")
    if result.returncode != 0 or not re.search(expect, output, re.MULTILINE):
        raise StepFailed(f"{label}: expected /{expect}/, got exit {result.returncode}: {output.strip()[-400:]!r}")
    return f"matched /{expect}/"


def cmd_install(args):
    """Unattended install of the ISO onto a fresh disk, then boot the result.

    GRUB is bypassed (boot-smoke covers the real boot path): the ISO's own
    kernel + initrd boot directly with `autoinstall` added, and a CIDATA
    seed disk carries the answers. Proves the installer actually installs
    DruidOS and that the installed disk boots on its own.
    """
    if not os.path.isfile(args.iso):
        log(f"ISO not found: {args.iso}")
        return 1

    install_dir = os.path.join(args.out, "install")
    firstboot_dir = os.path.join(args.out, "firstboot")
    run = Run(args.out, f"install/{args.firmware}")
    disk = os.path.join(args.out, "disk.qcow2")
    key = os.path.join(args.out, "id_ed25519")
    vms = []

    def prepare():
        os.makedirs(install_dir, exist_ok=True)
        run_tool(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "druidos-lab", "-f", key])
        with open(key + ".pub") as f:
            public_key = f.read().strip()
        password = os.urandom(12).hex()
        with open(os.path.join(args.out, "guest-password"), "w") as f:
            f.write(password + "\n")
        password_hash = run_tool(["openssl", "passwd", "-6", password]).strip()

        seed_dir = os.path.join(install_dir, "seed")
        os.makedirs(seed_dir, exist_ok=True)
        with open(os.path.join(seed_dir, "user-data"), "w") as f:
            f.write(
                USER_DATA.format(
                    password_hash=password_hash,
                    public_key=public_key,
                    storage_layout=args.storage,
                )
            )
        with open(os.path.join(seed_dir, "meta-data"), "w") as f:
            f.write(f"instance-id: druidos-lab-{int(time.time())}\n")
        run_tool([
            "genisoimage", "-quiet", "-output", os.path.join(install_dir, "cidata.iso"),
            "-volid", "CIDATA", "-joliet", "-rock",
            os.path.join(seed_dir, "user-data"), os.path.join(seed_dir, "meta-data"),
        ])

        iso_extract(args.iso, "/casper/vmlinuz", os.path.join(install_dir, "vmlinuz"))
        iso_extract(args.iso, "/casper/initrd", os.path.join(install_dir, "initrd"))
        iso_extract(args.iso, "/boot/grub/grub.cfg", os.path.join(install_dir, "grub.cfg"))
        run_tool(["qemu-img", "create", "-q", "-f", "qcow2", disk, args.disk_size])
        return f"kernel args: {iso_kernel_args(os.path.join(install_dir, 'grub.cfg'))}"

    def install():
        vm = Vm(install_dir, firmware=args.firmware, accel=args.accel)
        vms.append(vm)
        kernel_args = iso_kernel_args(os.path.join(install_dir, "grub.cfg"))
        vm.start([
            "-kernel", os.path.join(install_dir, "vmlinuz"),
            "-initrd", os.path.join(install_dir, "initrd"),
            "-append", f"autoinstall {kernel_args}",
            "-drive", f"file={args.iso},media=cdrom,readonly=on,format=raw",
            "-drive", f"file={os.path.join(install_dir, 'cidata.iso')},media=cdrom,readonly=on,format=raw",
            "-drive", f"file={disk},if=virtio,format=qcow2",
            "-no-reboot",
        ])
        detail = vm.wait_for_exit(args.timeout, "install", fail_pattern=INSTALL_FAILURE)
        vm.stop()
        if vm.proc.returncode != 0:
            raise StepFailed(detail)
        return detail

    def save_golden():
        # Assemble next to the destination, then swap it in, so a crash
        # mid-copy never leaves a half-written golden image behind.
        staging = args.golden.rstrip("/") + ".staging"
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging)
        shutil.move(disk, os.path.join(staging, "disk.qcow2"))
        for name in ("id_ed25519", "id_ed25519.pub"):
            shutil.copyfile(os.path.join(args.out, name), os.path.join(staging, name))
        if args.firmware == "uefi":
            shutil.copyfile(os.path.join(install_dir, "OVMF_VARS.fd"), os.path.join(staging, "OVMF_VARS.fd"))
        shutil.rmtree(args.golden, ignore_errors=True)
        os.rename(staging, args.golden)
        return f"golden image at {args.golden}"

    firstboot_vm = Vm(
        firstboot_dir,
        firmware=args.firmware,
        accel=args.accel,
        uefi_vars=os.path.join(install_dir, "OVMF_VARS.fd"),
        ssh_port=2222,
    )

    def firstboot():
        vms.append(firstboot_vm)
        return firstboot_vm.start(["-drive", f"file={disk},if=virtio,format=qcow2"])

    def check(label, command, expect=r""):
        return lambda: guest_check(key, 2222, command, expect, label, firstboot_dir)

    try:
        run.step("prepare", prepare)
        run.step("install", install)
        run.step("firstboot-start", firstboot)
        run.step("firstboot-ssh", lambda: wait_for_ssh(firstboot_vm, key, 2222, 300))
        run.step("serial-login-prompt", lambda: firstboot_vm.wait_for_serial(r"login:", 60, "serial login"))
        run.step("is-druidos", check("os-release", "cat /etc/os-release", r"^ID=druidos$"))
        run.step(
            "hive-binaries",
            check(
                "binaries",
                "missing=0; for b in hive-cortex hive-synapse hive-actuator hive-nerve-process "
                "hive-nerve-journal hive-nerve-network hive-nerve-fs hive-dashboard grove; "
                "do test -x /usr/bin/$b || { echo MISSING $b; missing=1; }; done; exit $missing",
            ),
        )
        run.step("serial-cmdline", check("cmdline", "cat /proc/cmdline", r"console=ttyS0"))
        if args.golden:
            # Keep the installed disk as the base image `e2e` boots from
            # (through throwaway overlays). Shut down cleanly first so the
            # image isn't left with a dirty filesystem.
            run.step("poweroff", lambda: graceful_poweroff(firstboot_vm, key, 2222))
            run.step("save-golden", save_golden)
    except StepFailed:
        pass
    finally:
        for vm in vms:
            vm.stop()
        result = run.finish()

    return summarize([result])


# The interactive installer, screen by screen, as a person would drive it:
# (screen pattern, keys, label, how many times it may fire). Patterns are
# each screen's body text from Subiquity's source (titles sit on a colored
# bar OCR reads unreliably). Checked in order, first match wins - overlays
# first, since the screen under them still shows. Keys follow Subiquity's
# focus rules: most screens focus their Done/Continue button; the
# confirmation overlay focuses "No"; forms that focus their first field are
# walked with Down past the last field to Back, then Up to Done. "enter" in
# a text field moves on to the next field.
PROFILE_PASSWORD = "druidos-lab"
DOWN_TO_DONE = ["down"] * 40 + ["up", "ret"]
INTERACTIVE_SCREENS = [
    (r"loss of data on the disks", ["down", "ret"], "confirm-destructive", 2),
    (r"remove the installation medium", ["ret"], "remove-medium", 3),
    # The progress screen's buttons are [View full log] [Reboot Now], focus on
    # the log button (or the event list above it); Down doesn't wrap, so a
    # few Downs always land on Reboot Now. Its log overlay has a Close button.
    (r"Full installer output", ["down"] * 3 + ["ret"], "close-log", 2),
    (r"Reboot Now", ["down"] * 3 + ["ret"], "reboot", 3),
    (r"username and password you will use", None, "profile", 1),  # typed, see below
    (r"install the OpenSSH server", DOWN_TO_DONE, "ssh", 3),
    (r"popular snaps in server|Loading server snaps", DOWN_TO_DONE, "snaps", 5),
    (r"Configure a guided storage layout", DOWN_TO_DONE, "guided-storage", 3),
    (r"FILE SYSTEM SUMMARY", ["ret"], "storage-summary", 3),
    (r"Ubuntu Pro", ["ret"], "ubuntu-pro", 3),
    (r"Continue without updating", ["ret"], "installer-update", 3),
    (r"select your keyboard layout|layout of the keyboard", ["ret"], "keyboard", 3),
    (r"base for the installation", ["ret"], "source", 3),
    # After "source": that screen has a "Search for third-party drivers" box.
    (r"third-party drivers are available|install third-party drivers", DOWN_TO_DONE, "drivers", 3),
    (r"Configure at least one interface", ["ret"], "network", 5),
    (r"requires a proxy", ["ret"], "proxy", 3),
    (r"alternative mirror", ["ret"], "mirror", 10),
    (r"select your language", ["ret"], "language", 3),
]
# A screen still showing this long after its keys were sent gets them again
# (a Done button that was still disabled, a slow screen change).
RESEND_AFTER = 20
# No known screen and nothing changing for this long: stuck somewhere the
# walker doesn't know - fail with the screen instead of waiting out the
# whole install timeout.
STALLED_AFTER = 240


def cmd_install_interactive(args):
    """Install from the ISO exactly as a user would: boot it like a CD, pick
    GRUB's default entry, answer the installer's screens with the default
    choice everywhere except the profile form, confirm, reboot. Then boot
    the installed disk and judge it from its serial console.

    This is the production path - no autoinstall seed, no direct kernel
    boot - so it proves what a real install gets by default (e.g. the
    storage layout), not just what the lab's autoinstall asks for.
    """
    if not os.path.isfile(args.iso):
        log(f"ISO not found: {args.iso}")
        return 1

    install_dir = os.path.join(args.out, "install")
    firstboot_dir = os.path.join(args.out, "firstboot")
    os.makedirs(install_dir, exist_ok=True)
    run = Run(args.out, f"install-interactive/{args.firmware}")
    disk = os.path.join(args.out, "disk.qcow2")
    vms = []

    def install():
        run_tool(["qemu-img", "create", "-q", "-f", "qcow2", disk, args.disk_size])
        vm = Vm(install_dir, firmware=args.firmware, accel=args.accel)
        vms.append(vm)
        vm.start([
            "-drive", f"file={args.iso},media=cdrom,readonly=on,format=raw",
            "-drive", f"file={disk},if=virtio,format=qcow2",
            "-boot", "d",
            "-no-reboot",
        ])
        vm.wait_for_screen(GRUB_MENU, 120, "grub")
        vm.send_keys(["down"] * args.grub_entry + ["ret"])

        rules = [(re.compile(p, re.IGNORECASE), keys, label, limit) for p, keys, label, limit in INTERACTIVE_SCREENS]
        fired = {}
        last_label, last_sent = None, 0.0
        previous, last_progress = "", time.monotonic()
        deadline = time.monotonic() + args.timeout
        while vm.proc.poll() is None:
            if time.monotonic() > deadline:
                raise StepFailed(
                    f"installer still running after {args.timeout}s; "
                    f"screens answered: {fired}; last screen: {vm.last_screen_text[:300]!r}"
                )
            try:
                text, _ = vm.read_screen("installer")
            except (StepFailed, OSError):
                break  # QMP gone: QEMU exited (the reboot, with -no-reboot)
            normalized = " ".join(text.split())
            if difflib.SequenceMatcher(None, normalized, previous).ratio() < 0.95:
                previous, last_progress = normalized, time.monotonic()
            elif time.monotonic() - max(last_progress, last_sent) > STALLED_AFTER:
                raise StepFailed(
                    f"installer screen unchanged for {STALLED_AFTER}s and not one the walker "
                    f"knows; screens answered: {fired}; screen: {normalized[:400]!r}"
                )
            for regex, keys, label, limit in rules:
                if not regex.search(text):
                    continue
                if label == last_label and time.monotonic() - last_sent < RESEND_AFTER:
                    break  # just answered; give the screen time to change
                if fired.get(label, 0) >= limit:
                    raise StepFailed(
                        f"screen {label!r} is still showing after {limit} answers: "
                        f"{' '.join(text.split())[:300]!r}"
                    )
                fired[label] = fired.get(label, 0) + 1
                log(f"answering screen {label} ({fired[label]})")
                if label == "profile":
                    for value in ("druid", "druidos", "druid", PROFILE_PASSWORD, PROFILE_PASSWORD):
                        vm.type_text(value)
                        vm.send_key("ret")
                    vm.send_key("ret")  # Done
                else:
                    vm.send_keys(keys)
                last_label, last_sent = label, time.monotonic()
                break
            time.sleep(2)
        if "reboot" not in fired:
            raise StepFailed(f"QEMU exited before the install completed; screens answered: {fired}")
        vm.stop()
        return f"screens answered: {fired}"

    firstboot_vm = Vm(
        firstboot_dir,
        firmware=args.firmware,
        accel=args.accel,
        uefi_vars=os.path.join(install_dir, "OVMF_VARS.fd"),
    )

    def firstboot():
        vms.append(firstboot_vm)
        detail = firstboot_vm.start(["-drive", f"file={disk},if=virtio,format=qcow2"])
        firstboot_vm.wait_for_serial(r"login:", 300, "firstboot login")
        return detail

    def kernel_command_line():
        with open(firstboot_vm.serial_log, "rb") as f:
            serial = f.read().decode(errors="replace")
        match = re.search(r"Command line: (.*)", serial)
        if not match:
            raise StepFailed("no kernel 'Command line:' on the installed system's serial console")
        return match.group(1).strip()

    def root_filesystem():
        cmdline = kernel_command_line()
        with open(os.path.join(firstboot_dir, "cmdline.txt"), "w") as f:
            f.write(cmdline + "\n")
        root = re.search(r"\broot=(\S+)", cmdline)
        if not root or not re.match(args.expect_root, root.group(1)):
            raise StepFailed(
                f"expected root /{args.expect_root}/, installed system boots with: {cmdline!r}"
            )
        return f"root={root.group(1)}"

    try:
        run.step("install", install)
        run.step("firstboot", firstboot)
        run.step("root-filesystem", root_filesystem)
    except StepFailed:
        pass
    finally:
        for vm in vms:
            vm.stop()
        result = run.finish()

    return summarize([result])


class GuestSession:
    """An installed DruidOS booted from a throwaway overlay of a golden disk
    (written by `install --golden`), reachable over SSH on port 2222."""

    PORT = 2222

    def __init__(self, golden, out, firmware, accel):
        self.golden_disk = os.path.join(golden, "disk.qcow2")
        if not os.path.isfile(self.golden_disk):
            raise StepFailed(f"no golden disk at {self.golden_disk} - run the install stage first")
        os.makedirs(out, exist_ok=True)
        self.overlay = os.path.join(out, "overlay.qcow2")
        self.key = os.path.join(out, "id_ed25519")
        shutil.copyfile(os.path.join(golden, "id_ed25519"), self.key)
        os.chmod(self.key, 0o600)
        uefi_vars = os.path.join(out, "OVMF_VARS.fd")
        if firmware == "uefi":
            shutil.copyfile(os.path.join(golden, "OVMF_VARS.fd"), uefi_vars)
        self.vm = Vm(out, firmware=firmware, accel=accel, uefi_vars=uefi_vars, ssh_port=self.PORT)
        # Journal cursor from just before a hot-swap, if one happened.
        self.cursor = None

    def ssh(self, command, **kwargs):
        return ssh(self.key, self.PORT, command, **kwargs)

    def boot(self):
        run_tool(["qemu-img", "create", "-q", "-f", "qcow2", "-b", self.golden_disk, "-F", "qcow2", self.overlay])
        return self.vm.start(["-drive", f"file={self.overlay},if=virtio,format=qcow2"])

    def wait_for_ssh(self):
        return wait_for_ssh(self.vm, self.key, self.PORT, 300)

    def hotswap(self, src):
        """Replace the installed Hive binaries, unit files, polkit rules and
        /etc/hive config with the ones from source tree `src` (installed the
        way build-iso.sh installs them), and restart the stack."""
        release = os.path.join(src, "target", "release")
        binaries = [os.path.join(release, b) for b in HOTSWAP_BINARIES]
        missing = [b for b in binaries if not os.path.isfile(b)]
        if missing:
            raise StepFailed(f"missing release binaries: {missing}")
        units = config_files(src, "systemd", ".service")
        timers = config_files(src, "systemd", ".timer")
        polkit_rules = config_files(src, "polkit", ".rules")
        hive_config = [os.path.join(src, "config", "hive", f) for f in ("default.toml", "whitelist.toml")]
        stage = "/tmp/druidos-hotswap"
        result = self.ssh(f"rm -rf {stage} && mkdir -p {stage}")
        if result.returncode != 0:
            raise StepFailed(f"could not prepare {stage}: {result.stderr}")
        scp_to_guest(self.key, self.PORT, binaries + units + timers + polkit_rules + hive_config, stage + "/")
        # Journal cursor taken before the swap: checks judge only what
        # happens after it.
        cursor = self.ssh("journalctl -n 0 --show-cursor --no-pager | sed -n 's/^-- cursor: //p'")
        self.cursor = cursor.stdout.strip()
        install_rules = (
            "mkdir -p /etc/polkit-1/rules.d; install -m 0644 *.rules /etc/polkit-1/rules.d/; "
            if polkit_rules else ""
        )
        install_timers = "install -m 0644 *.timer /etc/systemd/system/; " if timers else ""
        # A timer new to this install isn't enabled yet; the ISO enables them.
        enable_timers = (
            f"systemctl enable --now {' '.join(os.path.basename(t) for t in timers)}; "
            if timers else ""
        )
        swap = self.ssh(
            "sudo sh -ec '"
            f"systemctl stop {' '.join(HIVE_UNITS)}; "
            f"cd {stage}; install -m 0755 {' '.join(HOTSWAP_BINARIES)} /usr/bin/; "
            "install -m 0644 *.service /etc/systemd/system/; "
            f"{install_timers}"
            f"{install_rules}"
            "install -m 0644 default.toml /etc/hive/config.toml; "
            "install -m 0644 whitelist.toml /etc/hive/whitelist.toml; "
            f"systemctl daemon-reload; systemctl reset-failed {' '.join(HIVE_UNITS)} || true; "
            f"{enable_timers}"
            f"systemctl start --no-block {' '.join(HIVE_UNITS)}'",
            timeout=180,
        )
        if swap.returncode != 0:
            raise StepFailed(f"hot-swap failed: {swap.stdout}{swap.stderr}")
        return (
            f"swapped {len(binaries)} binaries, {len(units)} units, "
            f"{len(polkit_rules)} polkit rules, /etc/hive config"
        )

    def stop(self):
        self.vm.stop()


def config_files(src, subdir, suffix):
    directory = os.path.join(src, "config", subdir)
    if not os.path.isdir(directory):
        return []
    return sorted(os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(suffix))


def cmd_e2e(args):
    """Boot an installed DruidOS (throwaway overlay on a golden disk from
    `install`) and run scripts/lab/e2e/guest-checks.sh inside it.

    With --hotswap, the source tree's current release binaries, unit files
    and polkit rules replace the installed ones first - the fast loop for
    Rust/unit changes, no ISO rebuild or reinstall needed.
    """
    run = Run(args.out, f"e2e/{args.firmware}" + ("+hotswap" if args.hotswap else ""))
    session = None
    state = {}

    def guest_checks():
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e", "guest-checks.sh")) as f:
            script = f.read()
        pushed = session.ssh("cat > /tmp/guest-checks.sh", input=script)
        if pushed.returncode != 0:
            raise StepFailed(f"could not push guest-checks.sh: {pushed.stderr}")
        env = f"CHECK_CURSOR='{session.cursor}' " if session.cursor else ""
        try:
            result = session.ssh(f"sudo {env}bash /tmp/guest-checks.sh", timeout=900)
        except subprocess.TimeoutExpired:
            raise StepFailed("guest-checks.sh timed out")
        with open(os.path.join(args.out, "guest-checks.txt"), "w") as f:
            f.write(result.stdout + result.stderr)
        state["checks"] = result
        return f"guest-checks.sh exit {result.returncode}"

    try:
        session = GuestSession(args.golden, args.out, args.firmware, args.accel)
        run.step("boot", session.boot)
        run.step("ssh", session.wait_for_ssh)
        if args.hotswap:
            run.step("hotswap", lambda: session.hotswap(args.hotswap))
        run.step("guest-checks-run", guest_checks)
        record_tap(run, state["checks"].stdout)
    except StepFailed as e:
        if not run.steps:
            log(str(e))
    finally:
        if session:
            session.stop()
        result = run.finish()

    return summarize([result])


def cmd_exec(args):
    """Boot an installed DruidOS, optionally hot-swap, run one shell command
    as root, print its output. For poking at a real install by hand."""
    session = None
    try:
        session = GuestSession(args.golden, args.out, args.firmware, args.accel)
        session.boot()
        session.wait_for_ssh()
        if args.hotswap:
            log(session.hotswap(args.hotswap))
        # Let the stack settle, the way a real boot would have.
        time.sleep(args.settle)
        result = session.ssh(f"sudo bash -c {shlex.quote(args.cmd)}", timeout=args.timeout)
        sys.stdout.write(result.stdout)
        sys.stdout.write(result.stderr)
        return result.returncode
    except (StepFailed, subprocess.TimeoutExpired) as e:
        log(f"exec failed: {e}")
        return 1
    finally:
        if session:
            session.stop()


def record_tap(run, output):
    """Turn guest-checks.sh's TAP-like output into one result step per check."""
    current = None
    count = 0
    for line in output.splitlines():
        m = re.match(r"^(ok|not ok) \d+ - (.*)$", line)
        if m:
            count += 1
            current = {"step": m.group(2), "ok": m.group(1) == "ok", "seconds": 0, "detail": ""}
            run.steps.append(current)
            log(f"[{' ok ' if current['ok'] else 'FAIL'}] {run.name}: {current['step']}")
        elif line.startswith("#   ") and current is not None and not current["ok"]:
            current["detail"] += line[4:] + "\n"
            log(f"         {line[4:]}")
    if count == 0:
        run.steps.append({
            "step": "guest-checks-output", "ok": False, "seconds": 0,
            "detail": f"no TAP lines in output: {output[-500:]!r}",
        })


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    boot = sub.add_parser("boot-smoke", help="boot an ISO until its installer UI shows")
    boot.add_argument("--iso", required=True)
    boot.add_argument("--out", required=True, help="run directory")
    boot.add_argument("--firmware", default="bios,uefi", help="comma-separated: bios,uefi")
    boot.add_argument("--accel", default="kvm", choices=["kvm", "tcg"])
    boot.add_argument("--timeout", type=int, default=420, help="seconds to reach the installer UI")

    inst = sub.add_parser("install", help="autoinstall the ISO to a disk and boot it")
    inst.add_argument("--iso", required=True)
    inst.add_argument("--out", required=True, help="run directory (disk.qcow2 is kept here)")
    inst.add_argument("--firmware", default="uefi", choices=["bios", "uefi"])
    inst.add_argument("--accel", default="kvm", choices=["kvm", "tcg"])
    inst.add_argument("--disk-size", default="20G")
    inst.add_argument(
        "--storage",
        default="zfs",
        choices=["zfs", "direct"],
        help="installer storage layout: zfs root (DruidOS's default) or plain ext4",
    )
    inst.add_argument("--timeout", type=int, default=1800, help="seconds for the install to power off")
    inst.add_argument("--golden", help="on success, keep the installed disk here for e2e runs")

    inter = sub.add_parser(
        "install-interactive", help="install the ISO through its UI with default answers, boot it"
    )
    inter.add_argument("--iso", required=True)
    inter.add_argument("--out", required=True, help="run directory")
    inter.add_argument("--firmware", default="uefi", choices=["bios", "uefi"])
    inter.add_argument("--accel", default="kvm", choices=["kvm", "tcg"])
    inter.add_argument("--disk-size", default="20G")
    inter.add_argument("--timeout", type=int, default=1800, help="seconds for the whole install")
    inter.add_argument(
        "--grub-entry", type=int, default=0, help="which ISO boot menu entry to pick (0 = default)"
    )
    inter.add_argument(
        "--expect-root",
        default=r"ZFS=rpool/ROOT/",
        help="regex the installed system's root= kernel argument must match",
    )

    e2e = sub.add_parser("e2e", help="boot a golden install and run the guest checks")
    e2e.add_argument("--golden", required=True, help="directory written by install --golden")
    e2e.add_argument("--out", required=True, help="run directory")
    e2e.add_argument("--firmware", default="uefi", choices=["bios", "uefi"])
    e2e.add_argument("--accel", default="kvm", choices=["kvm", "tcg"])
    e2e.add_argument("--hotswap", metavar="SRC", help="push SRC's release binaries + units first")

    exe = sub.add_parser("exec", help="boot a golden install and run one command as root")
    exe.add_argument("--golden", required=True, help="directory written by install --golden")
    exe.add_argument("--out", required=True, help="run directory")
    exe.add_argument("--firmware", default="uefi", choices=["bios", "uefi"])
    exe.add_argument("--accel", default="kvm", choices=["kvm", "tcg"])
    exe.add_argument("--hotswap", metavar="SRC", help="push SRC's release binaries + units first")
    exe.add_argument("--settle", type=int, default=5, help="seconds to wait before running")
    exe.add_argument("--timeout", type=int, default=600)
    exe.add_argument("cmd", help="shell command, run with sudo bash -c")

    args = parser.parse_args()
    if args.command == "boot-smoke":
        return cmd_boot_smoke(args)
    if args.command == "install":
        return cmd_install(args)
    if args.command == "install-interactive":
        return cmd_install_interactive(args)
    if args.command == "e2e":
        return cmd_e2e(args)
    if args.command == "exec":
        return cmd_exec(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
