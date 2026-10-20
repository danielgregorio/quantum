# DruidOS - Development Status

**Date:** 2026-02-20
**Version:** 0.3.0-slm

---

## Executive Summary

DruidOS has reached its **first working SLM (Small Language Model)**: the user can ask questions in natural language through the `ask` command and get answers in Portuguese. The Qwen 2.5 0.5B model loads at boot and answers through an HTTP API.

```
/ # ask hi, how are you
Hello! I'm fine, thank you. How can I help?
```

We also have `hive-cortex` (the central orchestrator) running with an IPC socket at `/run/hive/cortex.sock`.

---

## What DruidOS Is

DruidOS is a VM-first Linux distribution that integrates a local AI called "The Hive" (A Colmeia). The system watches what the user does and offers smart suggestions.

- **Kernel**: Linux 6.8+ (currently using Ubuntu 6.8.0-100)
- **Stack**: 100% Rust (Hive Stack compiled, not integrated yet)
- **AI**: local SLM (Qwen 0.5B) - model downloaded, inference pending
- **Desktop**: Wayland/Hyprland - not integrated yet

---

## Distribution Files

### v0.3-slm (Current)
Location: `dist/v0.3-slm/`

| File | Size | Description |
|---------|---------|-----------|
| `bonsai-kernel` | 15 MB | Linux kernel 6.8.0-100-generic |
| `bonsai-initramfs.img` | ~470 MB | Initramfs with BusyBox + Hive + SLM |

**Note:** The initramfs is large because of the Qwen 2.5 0.5B model (469 MB).

### v0.2-cortex (Preserved)
Location: `dist/v0.2-cortex/`

| File | Size | Description |
|---------|---------|-----------|
| `bonsai-kernel` | 15 MB | Linux kernel 6.8.0-100-generic |
| `bonsai-initramfs.img` | 3.1 MB | Initramfs with BusyBox + hive-cortex |

### v0.1-minimal (Preserved)
Location: `dist/v0.1-minimal/`

| File | Size | Description |
|---------|---------|-----------|
| `druidos-bonsai.iso` | 27 MB | Bootable ISO with GRUB |
| `bonsai-kernel` | 15 MB | Linux kernel 6.8.0-100-generic |
| `bonsai-initramfs.img` | 700 KB | Minimal initramfs with BusyBox |

### Checksums (SHA256)
```
bonsai-kernel:        528d909745819a1464848a2c4d91c609db4f54b33ccae7069aad4178fb34606f
bonsai-initramfs.img: ef1abd44dfbdc9a8a37cece427491e5c0017a934b19297142ae685a30e4ed6b1
druidos-bonsai.iso:   8491747ba7a7d541ffbb57aa592a16fc3dccc853cae4b45e361756fb7500ddbe
```

---

## How to Boot

### v0.3-slm (With SLM - Needs more resources)
```bash
qemu-system-x86_64 \
    -m 4096 \
    -smp 4 \
    -machine pc \
    -cpu qemu64 \
    -kernel dist/v0.3-slm/bonsai-kernel \
    -initrd dist/v0.3-slm/bonsai-initramfs.img \
    -append "console=tty0 noapic nolapic" \
    -vnc :0
```
Connect via VNC at `localhost:5900`.

### Minimal Direct Boot (v0.1/v0.2)
```bash
qemu-system-x86_64 -m 512 \
    -kernel dist/v0.1-minimal/bonsai-kernel \
    -initrd dist/v0.1-minimal/bonsai-initramfs.img \
    -append "console=ttyS0 console=tty0 quiet" \
    -nographic
```

---

## Full Progress

### ✅ Phase 1: Build Environment
- [x] QEMU 10.2.0 on Windows
- [x] qemu-lab MCP working
- [x] Ubuntu 24.04 VM for compiling
- [x] Rust 1.93.1 on the VM

### ✅ Phase 2: Hive Stack (Compilation)
- [x] 12 hive-* binaries compiled
- [x] ~25MB total (release, LTO, stripped)
- [x] Tested on the Ubuntu VM

### ✅ Phase 3: Minimal Boot
- [x] Ubuntu 6.8.0 kernel extracted
- [x] Initramfs with BusyBox created
- [x] Working boot in ~1.5s
- [x] Bootable ISO with GRUB

### ⏳ Phase 4: Base System (Next)
- [ ] Persistent root filesystem
- [ ] User login (`druid`)
- [ ] Automatic networking (DHCP)
- [ ] Systemd as init

### ✅ Phase 5: Hive Integration (Partial)
- [x] hive-* binaries in the system (hive-cortex)
- [x] hive-cortex starting at boot
- [x] Working IPC socket (/run/hive/cortex.sock)
- [ ] Nerves connecting to the cortex

### ✅ Phase 6: AI (Partial)
- [x] Qwen 0.5B model in the system
- [x] llama-server with real inference (HTTP API)
- [x] `ask` command for natural-language interaction
- [ ] hive-synapse integrating with llama-server
- [ ] End-to-end suggestions

### ⏳ Phase 7: Desktop
- [ ] Wayland/Hyprland
- [ ] hive-shell overlay
- [ ] hive-term terminal
- [ ] hive-dock

---

## Compiled Hive Binaries

All in `target/release/` (Linux ELF 64-bit):

| Binary | Size | Role | Status |
|--------|---------|--------|--------|
| hive-cortex | 2.2M | Central orchestrator | Compiled |
| hive-synapse | 2.2M | AI engine | Compiled |
| hive-actuator | 2.3M | Action executor | Compiled |
| hive-apt | 1.1M | Smart APT | Compiled |
| hive-zfs | 2.2M | ZFS snapshots | Compiled |
| hive-nerve-process | 2.7M | Process monitor | Compiled |
| hive-nerve-journal | 2.8M | Log monitor | Compiled |
| hive-nerve-network | 2.1M | Network monitor | Compiled |
| hive-nerve-fs | 2.0M | Filesystem monitor | Compiled |
| hive-shell | 2.2M | Desktop overlay | Compiled |
| hive-dock | 2.0M | Dock bar | Compiled |
| hive-term | 2.2M | Terminal | Compiled |

---

## Development Environment

### Build VM
- **OS**: Ubuntu 24.04 LTS
- **ID**: vm-ubuntu-test-60eefea9
- **Disk**: 26 GB
- **SSH**: Port 2222 (via QEMU user networking)
- **Key**: `qemu-workspace/keys/id_ed25519`

### Connecting to the Build VM
```bash
# Windows (Git Bash)
ssh -i qemu-workspace/keys/id_ed25519 -p 2222 lab@127.0.0.1

# Start the VM first
start "" "C:\Program Files\qemu\qemu-system-x86_64.exe" \
    -m 2048 -smp 1 \
    -hda qemu-workspace/vms/vm-ubuntu-test-60eefea9/disk-overlay.qcow2 \
    -cdrom qemu-workspace/vms/vm-ubuntu-test-60eefea9/seed.iso \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device virtio-net-pci,netdev=net0 \
    -display none -machine pc -cpu qemu64
```

---

## Project Structure

```
druidos/
├── dist/                          # DISTRIBUTION
│   ├── druidos-bonsai.iso         # Bootable ISO (27MB)
│   ├── bonsai-kernel              # Kernel (15MB)
│   ├── bonsai-initramfs.img       # Initramfs (700KB)
│   └── README.md                  # Documentation
│
├── build/output/                  # Temporary build
│   ├── bonsai-kernel
│   └── bonsai-initramfs.img
│
├── crates/                        # Hive Stack source code
│   ├── hive-common/
│   ├── hive-cortex/
│   ├── hive-synapse/
│   └── ...
│
├── bonsai/                        # Kernel/initramfs build scripts
│   ├── scripts/
│   │   ├── build-initramfs.sh
│   │   ├── build-kernel.sh
│   │   ├── build-iso.sh
│   │   └── run-qemu.sh
│   └── config/
│       └── bonsai_defconfig
│
├── qemu-workspace/                # VMs and QEMU artifacts
│   ├── keys/id_ed25519            # SSH key
│   ├── vms/                       # VM disks
│   └── base-images/               # Cloud images
│
├── scripts/                       # Build scripts (legacy)
├── config/                        # Configuration
├── knowledge/                     # Knowledge base
│
├── Cargo.toml                     # Rust workspace
├── CLAUDE.md                      # Guide for the AI
├── STATUS.md                      # THIS FILE
└── DEVLOG.md                      # Development log
```

---

## What Is Missing for a Complete System

### 1. Base System
The current initramfs is only BusyBox. For a complete system:
- Root filesystem (squashfs or ext4)
- Systemd as init
- User `druid` with login
- Configured networking

### 2. Hive Stack
The binaries are compiled but not integrated:
- Copy to /usr/bin
- Create systemd services
- Configure /etc/hive/config.toml
- Start the cortex at boot

### 3. AI
Model working via llama-server:
- Qwen 2.5 0.5B loads at boot
- The `ask` command allows interaction
- **Next**: Integrate hive-synapse with the llama-server API
- **Next**: Connect the nerves to the cortex for contextual suggestions

### 4. Desktop
Not integrated yet:
- Wayland/Hyprland
- Graphical session
- hive-shell overlay

---

## Architectural Decisions

1. **Direct Boot vs ISO**: We support both. Direct boot is faster for dev.
2. **Ubuntu Kernel**: Using Ubuntu's precompiled kernel for convenience.
3. **Static BusyBox**: We download a precompiled binary (musl) to avoid compilation problems.
4. **Build on the VM**: Compilation on the Ubuntu VM, not cross-compiling from Windows.

---

## Known Problems

1. **Nested Virtualization**: Boot can be slow without KVM/WHPX (~1 token/s for inference)
2. **VNC vs Serial**: For v0.3-slm use VNC (requires a graphical console)
3. **llama.cpp AVX**: The precompiled binary fails with "Illegal instruction" - it needs to be compiled without AVX
4. **Loopback Network**: The initramfs needs to configure `ifconfig lo 127.0.0.1 up` for local HTTP
3. **Line Endings**: Scripts copied from Windows need `sed -i 's/\r$//'`

---

## Next Session

> **Note (the Hive's screen, 2026-10):** the console gained a screen, `hive-screen`, declared in Quantum (`config/screen/screen.q`) and drawn on the CPU, with no engine, no compositor and no GPU. It is not the archived graphics track coming back: it is a small daemon, like the others. See the DEVLOG.
>
> **Note (target pivot):** the project was redefined as TUI-only — no GUI.
> bark/spore/hive-shell/hive-dock/hive-term were moved to `archive/`.
> See `DEVLOG.md` (most recent entry) and `CLAUDE.md`. The old "Option B:
> Minimal Desktop" no longer applies.

### Option A: v0.4 - Nerves Integration
1. Connect hive-nerve-process to the cortex
2. The nerve watches executed commands
3. The cortex sends context to the SLM
4. Automatic suggestions based on commands

### Option B: Persistence
1. Root filesystem (squashfs or ext4)
2. User login (druid)
3. Automatic networking (DHCP)

### Option C: Grove UX
1. Define the Hive's notification mechanism without a GUI (inline in Grove vs a separate TUI panel — still open)
2. Integrate Grove with hive-cortex as the "Shell" component

## Version History

| Version | Date | Description |
|--------|------|-----------|
| v0.1 | 2026-02-20 | Minimal boot (BusyBox) |
| v0.2 | 2026-02-20 | hive-cortex working |
| v0.3 | 2026-02-20 | SLM working (ask) |
| v0.4-fb | 2026-02-20 | Framebuffer test (IN DEVELOPMENT) |

---

## v0.4-fb - Framebuffer (ARCHIVED)

> The project's target was redefined as TUI-only (no GUI). `bark` and `spore`
> were moved to `archive/bark` and `archive/spore`, outside the active
> workspace. The fixes described below remain in the archived code; they are
> just no longer compiled/tested by default. Section kept as a historical
> record.

### Status
- `/dev/fb0` appears with `vga=0x31B` (1280x1024x24bpp)
- `fb-test` opens the framebuffer successfully
- **PROBLEM**: Segfault in mmap

### Root Cause
The code in `bark/src/framebuffer.rs` uses `MmapMut::map_mut(&file)`, which does not work for device files. It needs to specify an explicit size.

### Applied Fixes (NOT COMPILED)

#### Fix 1: mmap with explicit size (line ~169)
```rust
// BEFORE (broken):
let mmap = unsafe {
    MmapMut::map_mut(&file)
        .map_err(|e| BarkError::MmapFailed(...))?
};

// AFTER (fix):
let mmap = unsafe {
    memmap2::MmapOptions::new()
        .len(size)
        .map_mut(&file)
        .map_err(|e| BarkError::MmapFailed(...))?
};
```

#### Fix 2: flush() with 24bpp support (line ~312)
The `flush()` method was rewritten to convert the u32 backbuffer to:
- 32bpp: direct copy
- 24bpp: converts to BGR (3 bytes per pixel)
- 16bpp: converts to RGB565

### How to Test DruidOS v0.4
```powershell
# Start DruidOS with the framebuffer (VNC port 5901)
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -m 512 `
    -kernel "C:\projetos\druidos\dist\v0.4-fb\bonsai-kernel" `
    -initrd "C:\projetos\druidos\dist\v0.4-fb\bonsai-initramfs.img" `
    -append "console=tty0 noapic nolapic vga=0x31B" `
    -vga std -vnc :1

# Connect VNC: localhost:5901
# Run: fb-test
```

### Helper Scripts
- `C:\projetos\druidos\run-fb.ps1` - Starts DruidOS with the framebuffer
- `C:\projetos\druidos\kill-all-qemu.ps1` - Kills all QEMU processes
- `C:\projetos\druidos\build-fb-test.sh` - Compiles fb-test (run on Linux)

### Next Step: Compile fb-test

**Option 1: WSL Ubuntu (Recommended)**
```powershell
wsl --install -d Ubuntu
# Restart Windows
# Then:
cd /mnt/c/projetos/druidos
bash build-fb-test.sh
```

**Option 2: External VM**
Copy the project to any Linux machine and run `build-fb-test.sh`

### Problem with the Ubuntu Build VM
The current Ubuntu VM (vm-ubuntu-build-529bc657) has a kernel panic:
```
Kernel panic - not syncing: IO-APIC + timer doesn't work!
Boot with the 'noapic' option.
```
- The disk was expanded (+5GB) but that does not help
- WHPX does not work: "No space left on device"
- GRUB needs to be modified to add `noapic`

### VESA Parameters
| vga | Resolution | bpp | /dev/fb0 |
|-----|-----------|-----|----------|
| 0x31B | 1280x1024 | 24 | YES |
| 0x318 | 1024x768 | 24 | ? |
| 0x118 | 1024x768 | 32 | NO |
| 0x11B | 1280x1024 | 32 | ? |
