# DruidOS Kernel Configuration

This directory contains the minimal kernel configuration for DruidOS, optimized for VirtIO-based virtual machines.

## Philosophy

DruidOS is **VM-first**, meaning we explicitly exclude support for physical hardware. This results in:

- **Smaller kernel** (~4-6 MB bzImage vs ~12+ MB for generic distros)
- **Fewer modules** (~50 vs ~5000+ for generic distros)
- **Faster boot** (less hardware probing)
- **Reduced attack surface** (no unused drivers)

## Target Module Count: ~50

### VirtIO Stack (Essential - ~10 modules)

| Module | Purpose |
|--------|---------|
| `virtio` | Core VirtIO framework |
| `virtio_pci` | PCI transport layer |
| `virtio_blk` | Block device (disk) |
| `virtio_net` | Network interface |
| `virtio_console` | Serial/console |
| `virtio_balloon` | Memory ballooning |
| `virtio_gpu` | Graphics/display |
| `virtio_input` | Keyboard/mouse |
| `virtio_fs` | Filesystem sharing (9p replacement) |
| `virtio_rng` | Random number generation |

### Networking (~15 modules)

| Module | Purpose |
|--------|---------|
| `bridge` | Container networking |
| `veth` | Virtual ethernet pairs |
| `vxlan` | Overlay networks |
| `tun` | VPN/tunneling |
| `nf_conntrack` | Connection tracking |
| `nf_nat` | NAT for containers |
| `nft_*` | nftables rules |
| `vsock` | VM socket communication |

### Filesystems (~10 modules)

| Module | Purpose |
|--------|---------|
| `ext4` | Built-in (primary root FS option) |
| `xfs` | Alternative filesystem |
| `btrfs` | Copy-on-write filesystem |
| `overlay` | Container layers |
| `fuse` | Userspace filesystems |
| `squashfs` | Read-only images |
| ZFS | **External** (OpenZFS DKMS) |

### Other (~15 modules)

| Module | Purpose |
|--------|---------|
| `loop` | Loop devices |
| `dm_*` | Device mapper (LVM) |
| `snd_virtio` | VirtIO sound |
| `usb_storage` | USB passthrough |
| `usbhid` | USB input devices |
| Various crypto | Required by systemd |

## What's Excluded

These subsystems are **intentionally disabled** for VMs:

### Hardware Drivers (Not needed in VMs)
- ❌ SATA/AHCI/NVMe controllers (use virtio_blk)
- ❌ Physical NICs (Intel, Realtek, etc.)
- ❌ Physical GPUs (Intel, AMD, NVIDIA)
- ❌ Wireless/WiFi (no radios in VMs)
- ❌ Bluetooth
- ❌ Sound cards (use virtio_snd)
- ❌ Hardware sensors/HWMON
- ❌ Laptop features (backlight, hotkeys)

### Legacy Subsystems
- ❌ ISA/ISAPNP
- ❌ PCMCIA
- ❌ Parallel ports
- ❌ Floppy drives

### Power Management (Host handles this)
- ❌ CPU frequency scaling
- ❌ Thermal management
- ❌ Hibernation

## ZFS Support

ZFS is **not** built into the kernel. Instead:

1. The kernel provides necessary hooks (SPL compatibility)
2. OpenZFS is installed as a DKMS module
3. This allows ZFS to be updated independently

```bash
# After kernel is installed
apt install zfsutils-linux zfs-dkms
```

## Building

### Prerequisites

```bash
# Debian/Ubuntu
sudo apt install build-essential flex bison libelf-dev libssl-dev bc

# Fedora
sudo dnf install gcc make flex bison elfutils-libelf-devel openssl-devel bc
```

### Build Process

```bash
# From repository root
./scripts/build-kernel.sh

# With options
./scripts/build-kernel.sh --clean --version 6.12.6

# Install to system
sudo ./scripts/build-kernel.sh --install
```

### Build Output

```
build/
├── linux-6.12.6/           # Kernel source (downloaded)
└── output/
    ├── vmlinuz-6.12.6-druidos
    ├── System.map-6.12.6-druidos
    ├── config-6.12.6-druidos
    └── lib/modules/6.12.6-druidos/
```

## Bootloader Configuration

### systemd-boot (Recommended)

```
# /boot/loader/entries/druidos.conf
title   DruidOS
linux   /vmlinuz-6.12.6-druidos
options root=PARTUUID=xxxx-xxxx rw quiet
```

### GRUB (Alternative)

```
# /etc/grub.d/40_custom
menuentry "DruidOS" {
    linux /boot/vmlinuz-6.12.6-druidos root=PARTUUID=xxxx-xxxx rw quiet
}
```

Then run `update-grub`.

## Customization

The config uses a merge-based approach:

1. `make tinyconfig` - Start with minimal base
2. Merge `druidos.config` - Add our requirements
3. `make olddefconfig` - Resolve dependencies

To add features:

```bash
cd build/linux-6.12.6
make menuconfig           # Interactive configuration
cp .config ../druidos.config.new
```

## Kernel Command Line Options

Recommended boot parameters:

```
root=PARTUUID=xxxx rw quiet console=tty0 console=ttyS0,115200
```

| Parameter | Purpose |
|-----------|---------|
| `quiet` | Reduce boot messages |
| `console=tty0` | Primary console |
| `console=ttyS0,115200` | Serial console (for debugging) |

## Verification

After booting, verify the minimal configuration:

```bash
# Module count (should be ~50)
lsmod | wc -l

# Kernel size
ls -lh /boot/vmlinuz-*-druidos

# VirtIO devices
lspci | grep -i virtio
ls /dev/vd*
```

## Troubleshooting

### Boot fails with kernel panic

1. Ensure VirtIO drivers are built-in (not modules) for root disk
2. Check that `virtio_pci` is compiled in
3. Verify root partition UUID matches kernel parameters

### No network

1. Verify `virtio_net` is loaded: `lsmod | grep virtio_net`
2. Check `ip link` for interface
3. VM hypervisor must use VirtIO NIC (not e1000/rtl8139)

### No display

1. Fallback to serial console: `console=ttyS0,115200`
2. Verify `virtio-gpu` is exposed by hypervisor
3. Check `dmesg | grep -i drm`
