#!/bin/bash
# DruidOS Image Builder
# Creates bootable VM images for QEMU/KVM
#
# Usage: ./build-image.sh [options]
#
# Options:
#   --output FILE    Output image file (default: druidos.qcow2)
#   --size SIZE      Image size (default: 20G)
#   --format FMT     Image format: qcow2, raw (default: qcow2)
#   --zfs            Use ZFS root filesystem (default)
#   --ext4           Use ext4 root filesystem
#   --minimal        Currently a no-op (DruidOS is TUI-only, no desktop
#                    package set exists to skip) — kept for compatibility
#   --help           Show this help

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[BUILD]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# Default configuration
OUTPUT="druidos.qcow2"
SIZE="20G"
FORMAT="qcow2"
FILESYSTEM="zfs"
MINIMAL=false

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build"
KERNEL_DIR="${PROJECT_ROOT}/kernel"
INITRAMFS="${BUILD_DIR}/initramfs.img"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --size)
            SIZE="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --zfs)
            FILESYSTEM="zfs"
            shift
            ;;
        --ext4)
            FILESYSTEM="ext4"
            shift
            ;;
        --minimal)
            MINIMAL=true
            shift
            ;;
        --help)
            head -20 "$0" | tail -16
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Check dependencies
check_deps() {
    local deps=(qemu-img qemu-nbd parted mkfs.fat)

    if [[ "$FILESYSTEM" == "zfs" ]]; then
        deps+=(zpool zfs)
    else
        deps+=(mkfs.ext4)
    fi

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            error "Missing dependency: $dep"
        fi
    done

    # Check for root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
}

# Create the disk image
create_image() {
    log "Creating ${SIZE} ${FORMAT} image: ${OUTPUT}"

    mkdir -p "$(dirname "$OUTPUT")"

    qemu-img create -f "$FORMAT" "$OUTPUT" "$SIZE"

    log "Image created successfully"
}

# Setup NBD device
setup_nbd() {
    log "Loading NBD module..."
    modprobe nbd max_part=16

    # Find free NBD device
    for i in /dev/nbd*; do
        if [[ -b "$i" ]] && ! lsblk "$i" &>/dev/null 2>&1; then
            NBD_DEV="$i"
            break
        fi
    done

    [[ -z "${NBD_DEV:-}" ]] && error "No free NBD device found"

    log "Connecting image to ${NBD_DEV}..."
    qemu-nbd --connect="$NBD_DEV" "$OUTPUT"

    # Wait for device
    sleep 2
}

# Cleanup NBD
cleanup_nbd() {
    if [[ -n "${NBD_DEV:-}" ]]; then
        log "Disconnecting NBD device..."
        qemu-nbd --disconnect "$NBD_DEV" 2>/dev/null || true
    fi
}

# Partition the disk (GPT + UEFI)
partition_disk() {
    log "Partitioning disk (GPT)..."

    parted -s "$NBD_DEV" mklabel gpt

    # EFI System Partition (512MB)
    parted -s "$NBD_DEV" mkpart ESP fat32 1MiB 513MiB
    parted -s "$NBD_DEV" set 1 esp on

    # Boot partition for /boot (1GB)
    parted -s "$NBD_DEV" mkpart boot ext4 513MiB 1537MiB

    # Root partition (rest)
    parted -s "$NBD_DEV" mkpart root 1537MiB 100%

    # Refresh partition table
    partprobe "$NBD_DEV"
    sleep 2

    log "Partitions created"
}

# Format partitions
format_partitions() {
    log "Formatting partitions..."

    # EFI partition
    mkfs.fat -F32 -n EFI "${NBD_DEV}p1"

    # Boot partition
    mkfs.ext4 -L boot "${NBD_DEV}p2"

    # Root partition
    if [[ "$FILESYSTEM" == "zfs" ]]; then
        log "Creating ZFS pool..."

        # Create ZFS pool
        zpool create -f \
            -o ashift=12 \
            -o autotrim=on \
            -O acltype=posixacl \
            -O compression=zstd \
            -O dnodesize=auto \
            -O normalization=formD \
            -O relatime=on \
            -O xattr=sa \
            -O mountpoint=none \
            rpool "${NBD_DEV}p3"

        # Create datasets
        zfs create -o mountpoint=none rpool/ROOT
        zfs create -o mountpoint=/ rpool/ROOT/druidos
        zfs create -o mountpoint=/home rpool/home
        zfs create -o mountpoint=/var -o canmount=off rpool/var
        zfs create rpool/var/log
        zfs create rpool/var/cache
        zfs create -o mountpoint=/var/lib/hive rpool/var/lib/hive

        # Reserved space
        zfs create -o refreservation=1G -o mountpoint=none rpool/reserved

        log "ZFS pool and datasets created"
    else
        mkfs.ext4 -L root "${NBD_DEV}p3"
    fi
}

# Mount filesystems
mount_filesystems() {
    log "Mounting filesystems..."

    MOUNT_DIR="${BUILD_DIR}/mnt"
    mkdir -p "$MOUNT_DIR"

    if [[ "$FILESYSTEM" == "zfs" ]]; then
        # Export and reimport with altroot
        zpool export rpool
        zpool import -R "$MOUNT_DIR" rpool
    else
        mount "${NBD_DEV}p3" "$MOUNT_DIR"
    fi

    # Mount boot
    mkdir -p "${MOUNT_DIR}/boot"
    mount "${NBD_DEV}p2" "${MOUNT_DIR}/boot"

    # Mount EFI
    mkdir -p "${MOUNT_DIR}/boot/efi"
    mount "${NBD_DEV}p1" "${MOUNT_DIR}/boot/efi"
}

# Unmount filesystems
unmount_filesystems() {
    log "Unmounting filesystems..."

    MOUNT_DIR="${BUILD_DIR}/mnt"

    umount "${MOUNT_DIR}/boot/efi" 2>/dev/null || true
    umount "${MOUNT_DIR}/boot" 2>/dev/null || true

    if [[ "$FILESYSTEM" == "zfs" ]]; then
        zpool export rpool 2>/dev/null || true
    else
        umount "$MOUNT_DIR" 2>/dev/null || true
    fi
}

# Install base system
install_base() {
    log "Installing base system..."

    # Use debootstrap for Ubuntu base
    debootstrap --arch=amd64 noble "$MOUNT_DIR" http://archive.ubuntu.com/ubuntu/

    # Configure apt sources
    cat > "${MOUNT_DIR}/etc/apt/sources.list" << 'EOF'
deb http://archive.ubuntu.com/ubuntu/ noble main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ noble-security main restricted universe multiverse
EOF

    # Mount virtual filesystems for chroot
    mount --bind /dev "${MOUNT_DIR}/dev"
    mount --bind /proc "${MOUNT_DIR}/proc"
    mount --bind /sys "${MOUNT_DIR}/sys"

    log "Base system installed"
}

# Install packages
install_packages() {
    log "Installing packages..."

    # Essential packages
    local packages=(
        linux-image-generic
        linux-headers-generic
        systemd
        systemd-boot
        dbus
        networkmanager
        sudo
        vim
        curl
        wget
        git
        build-essential
        pkg-config
        # the Quantum runtime's needs (`quantum pixel`, the apps installed
        # with the Hive: scripts/lab/vm/vm.py keeps the same list)
        python3
        python3-flask
        python3-yaml
        python3-sqlparse
        python3-requests
        python3-bcrypt
    )

    # ZFS packages
    if [[ "$FILESYSTEM" == "zfs" ]]; then
        packages+=(
            zfsutils-linux
            zfs-initramfs
        )
    fi

    # DruidOS is TUI-only (no desktop package set) — $MINIMAL is currently
    # a no-op, kept for CLI compatibility in case a GUI target comes back.

    chroot "$MOUNT_DIR" apt-get update
    chroot "$MOUNT_DIR" apt-get install -y "${packages[@]}"

    log "Packages installed"
}

# Install Hive Stack
install_hive() {
    log "Installing Hive Stack..."

    # Copy Hive binaries
    local hive_bins=(
        hive-cortex
        hive-synapse
        hive-actuator
        hive-nerve-process
        hive-nerve-journal
        hive-nerve-network
        hive-nerve-fs
        hive-apt
        hive-zfs
        grove
    )

    mkdir -p "${MOUNT_DIR}/usr/bin"

    for bin in "${hive_bins[@]}"; do
        if [[ -f "${PROJECT_ROOT}/target/release/${bin}" ]]; then
            cp "${PROJECT_ROOT}/target/release/${bin}" "${MOUNT_DIR}/usr/bin/"
            chmod 755 "${MOUNT_DIR}/usr/bin/${bin}"
        else
            warn "Binary not found: ${bin}"
        fi
    done

    # Copy configuration
    mkdir -p "${MOUNT_DIR}/etc/hive"
    cp -r "${PROJECT_ROOT}/config/hive/"* "${MOUNT_DIR}/etc/hive/" 2>/dev/null || true

    # Copy knowledge base
    mkdir -p "${MOUNT_DIR}/var/lib/hive/knowledge"
    cp -r "${PROJECT_ROOT}/knowledge/"* "${MOUNT_DIR}/var/lib/hive/knowledge/" 2>/dev/null || true

    # Create systemd services
    create_systemd_services

    log "Hive Stack installed"
}

# Create systemd services for Hive
create_systemd_services() {
    # hive-cortex.service
    cat > "${MOUNT_DIR}/etc/systemd/system/hive-cortex.service" << 'EOF'
[Unit]
Description=Hive Cortex - Central Orchestrator
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/hive-cortex
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # hive-synapse.service
    cat > "${MOUNT_DIR}/etc/systemd/system/hive-synapse.service" << 'EOF'
[Unit]
Description=Hive Synapse - SLM Inference
After=hive-cortex.service
Requires=hive-cortex.service

[Service]
Type=simple
User=_hive-ai
ExecStart=/usr/bin/hive-synapse
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # hive-actuator.service
    cat > "${MOUNT_DIR}/etc/systemd/system/hive-actuator.service" << 'EOF'
[Unit]
Description=Hive Actuator - Action Executor
After=hive-cortex.service
Requires=hive-cortex.service

[Service]
Type=simple
User=_hive-act
ExecStart=/usr/bin/hive-actuator
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Enable services
    chroot "$MOUNT_DIR" systemctl enable hive-cortex
    chroot "$MOUNT_DIR" systemctl enable hive-synapse
    chroot "$MOUNT_DIR" systemctl enable hive-actuator
}

# Configure system
configure_system() {
    log "Configuring system..."

    # Hostname
    echo "druidos" > "${MOUNT_DIR}/etc/hostname"

    # Hosts
    cat > "${MOUNT_DIR}/etc/hosts" << EOF
127.0.0.1   localhost
127.0.1.1   druidos

::1         localhost ip6-localhost ip6-loopback
EOF

    # Timezone
    chroot "$MOUNT_DIR" ln -sf /usr/share/zoneinfo/UTC /etc/localtime

    # Locale
    echo "en_US.UTF-8 UTF-8" > "${MOUNT_DIR}/etc/locale.gen"
    chroot "$MOUNT_DIR" locale-gen
    echo "LANG=en_US.UTF-8" > "${MOUNT_DIR}/etc/default/locale"

    # Create hive users
    chroot "$MOUNT_DIR" useradd -r -s /usr/sbin/nologin _hive-ai
    chroot "$MOUNT_DIR" useradd -r -s /usr/sbin/nologin _hive-sense
    chroot "$MOUNT_DIR" useradd -r -s /usr/sbin/nologin _hive-act

    # Create default user
    chroot "$MOUNT_DIR" useradd -m -s /bin/bash -G sudo,audio,video druid
    echo "druid:druid" | chroot "$MOUNT_DIR" chpasswd

    log "System configured"
}

# Install bootloader
install_bootloader() {
    log "Installing bootloader..."

    # Install systemd-boot
    chroot "$MOUNT_DIR" bootctl install

    # Create loader config
    cat > "${MOUNT_DIR}/boot/efi/loader/loader.conf" << EOF
default druidos.conf
timeout 3
editor no
EOF

    # Create boot entry
    cat > "${MOUNT_DIR}/boot/efi/loader/entries/druidos.conf" << EOF
title DruidOS
linux /vmlinuz
initrd /initrd.img
options root=ZFS=rpool/ROOT/druidos rw quiet splash
EOF

    log "Bootloader installed"
}

# Cleanup chroot
cleanup_chroot() {
    log "Cleaning up chroot..."

    umount "${MOUNT_DIR}/sys" 2>/dev/null || true
    umount "${MOUNT_DIR}/proc" 2>/dev/null || true
    umount "${MOUNT_DIR}/dev" 2>/dev/null || true
}

# Main build process
main() {
    log "DruidOS Image Builder"
    log "====================="
    log "Output: ${OUTPUT}"
    log "Size: ${SIZE}"
    log "Format: ${FORMAT}"
    log "Filesystem: ${FILESYSTEM}"
    log "Minimal: ${MINIMAL}"
    echo

    check_deps

    # Cleanup on exit
    trap 'cleanup_chroot; unmount_filesystems; cleanup_nbd' EXIT

    # Build steps
    create_image
    setup_nbd
    partition_disk
    format_partitions
    mount_filesystems
    install_base
    install_packages
    install_hive
    configure_system
    install_bootloader
    cleanup_chroot
    unmount_filesystems
    cleanup_nbd

    log "Build complete: ${OUTPUT}"
    log ""
    log "To test the image:"
    log "  qemu-system-x86_64 -enable-kvm -m 4G -cpu host \\"
    log "    -drive file=${OUTPUT},format=${FORMAT} \\"
    log "    -bios /usr/share/ovmf/OVMF.fd"
}

main "$@"
