#!/bin/bash
#
# DruidOS Initramfs Build Script
# Creates a minimal initramfs for early boot
#
# Usage:
#   ./scripts/build-initramfs.sh [--output PATH] [--kernel VERSION]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-$(uname -r)}"
OUTPUT="${OUTPUT:-$ROOT_DIR/build/output/initramfs-${KERNEL_VERSION}-druidos.img}"
WORK_DIR="${WORK_DIR:-$ROOT_DIR/build/initramfs-work}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

usage() {
    cat << EOF
DruidOS Initramfs Build Script

Usage: $(basename "$0") [OPTIONS]

Options:
    --output PATH       Output path for initramfs image
    --kernel VERSION    Kernel version to build for
    --clean            Clean work directory before building
    --help             Show this help message

Environment Variables:
    KERNEL_VERSION     Kernel version (default: current running kernel)
    OUTPUT             Output path
    WORK_DIR           Working directory for build

Examples:
    ./scripts/build-initramfs.sh
    ./scripts/build-initramfs.sh --kernel 6.12.6-druidos --output /boot/initramfs.img
EOF
    exit 0
}

CLEAN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --kernel)
            KERNEL_VERSION="$2"
            shift 2
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            ;;
    esac
done

check_dependencies() {
    log_info "Checking dependencies..."

    local deps=(cpio gzip busybox)
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing[*]}

Install with:
    sudo apt install cpio gzip busybox-static"
    fi
}

create_structure() {
    log_info "Creating initramfs structure..."

    if [ "$CLEAN" = true ] && [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi

    mkdir -p "$WORK_DIR"/{bin,sbin,etc,proc,sys,dev,run,mnt,lib,lib64,usr/{bin,sbin}}

    # Create essential device nodes
    cd "$WORK_DIR"
    mknod -m 622 dev/console c 5 1 2>/dev/null || true
    mknod -m 666 dev/null c 1 3 2>/dev/null || true
    mknod -m 666 dev/zero c 1 5 2>/dev/null || true
    mknod -m 666 dev/tty c 5 0 2>/dev/null || true
}

install_busybox() {
    log_info "Installing busybox..."

    # Use static busybox
    local busybox_path
    busybox_path=$(which busybox)

    if [ ! -f "$busybox_path" ]; then
        log_error "busybox not found"
    fi

    cp "$busybox_path" "$WORK_DIR/bin/busybox"
    chmod +x "$WORK_DIR/bin/busybox"

    # Create symlinks for common utilities
    cd "$WORK_DIR/bin"
    for cmd in sh ash cat echo ls mount umount mkdir sleep switch_root; do
        ln -sf busybox "$cmd"
    done

    cd "$WORK_DIR/sbin"
    for cmd in modprobe insmod; do
        ln -sf ../bin/busybox "$cmd"
    done
}

install_modules() {
    log_info "Installing kernel modules..."

    local mod_dir="/lib/modules/${KERNEL_VERSION}"
    local dest_dir="$WORK_DIR/lib/modules/${KERNEL_VERSION}"

    if [ ! -d "$mod_dir" ]; then
        log_warn "Module directory not found: $mod_dir"
        log_warn "Skipping module installation (built-in drivers assumed)"
        return 0
    fi

    mkdir -p "$dest_dir"

    # For VirtIO-only kernel, we need minimal modules
    # Most VirtIO drivers should be built-in, but include any modules just in case
    local modules=(
        "virtio.ko"
        "virtio_pci.ko"
        "virtio_blk.ko"
        "virtio_ring.ko"
    )

    for mod in "${modules[@]}"; do
        local mod_path
        mod_path=$(find "$mod_dir" -name "$mod" 2>/dev/null | head -1)
        if [ -n "$mod_path" ]; then
            local rel_path="${mod_path#$mod_dir/}"
            mkdir -p "$dest_dir/$(dirname "$rel_path")"
            cp "$mod_path" "$dest_dir/$rel_path"
        fi
    done

    # Copy modules.dep and related files
    for f in modules.dep modules.dep.bin modules.alias modules.alias.bin; do
        if [ -f "$mod_dir/$f" ]; then
            cp "$mod_dir/$f" "$dest_dir/"
        fi
    done
}

install_zfs() {
    log_info "Checking for ZFS support..."

    # Check if ZFS tools are available
    if ! command -v zpool &> /dev/null; then
        log_warn "ZFS tools not found, skipping ZFS support"
        return 0
    fi

    log_info "Installing ZFS support..."

    # Copy ZFS binaries
    mkdir -p "$WORK_DIR/sbin"
    for bin in zpool zfs; do
        if [ -f "/sbin/$bin" ]; then
            cp "/sbin/$bin" "$WORK_DIR/sbin/"
        fi
    done

    # Copy ZFS modules
    local mod_dir="/lib/modules/${KERNEL_VERSION}"
    local zfs_mod_dir="$WORK_DIR/lib/modules/${KERNEL_VERSION}/extra"
    mkdir -p "$zfs_mod_dir"

    local zfs_modules=(zfs spl zavl zcommon zlua znvpair zunicode icp)
    for mod in "${zfs_modules[@]}"; do
        local mod_path
        mod_path=$(find "$mod_dir" -name "${mod}.ko*" 2>/dev/null | head -1)
        if [ -n "$mod_path" ]; then
            cp "$mod_path" "$zfs_mod_dir/"
        fi
    done

    # Copy required libraries
    mkdir -p "$WORK_DIR/lib/x86_64-linux-gnu"
    for lib in libuuid.so.1 libblkid.so.1 libudev.so.1 libz.so.1 libm.so.6 libc.so.6 libpthread.so.0 libdl.so.2; do
        local lib_path
        lib_path=$(find /lib /lib64 /usr/lib -name "$lib*" 2>/dev/null | head -1)
        if [ -n "$lib_path" ]; then
            cp -L "$lib_path" "$WORK_DIR/lib/x86_64-linux-gnu/" 2>/dev/null || true
        fi
    done

    # Copy ld-linux
    if [ -f "/lib64/ld-linux-x86-64.so.2" ]; then
        cp -L "/lib64/ld-linux-x86-64.so.2" "$WORK_DIR/lib64/"
    fi
}

create_init() {
    log_info "Creating init script..."

    cat > "$WORK_DIR/init" << 'INIT_EOF'
#!/bin/sh
#
# DruidOS Initramfs Init Script
# Minimal init for VirtIO-based systems with optional ZFS support
#

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

# Kernel command line parsing
INIT="/sbin/init"
ROOT=""
ROOTFSTYPE=""
ROOTFLAGS=""

for param in $(cat /proc/cmdline); do
    case "$param" in
        root=*)
            ROOT="${param#root=}"
            ;;
        rootfstype=*)
            ROOTFSTYPE="${param#rootfstype=}"
            ;;
        rootflags=*)
            ROOTFLAGS="${param#rootflags=}"
            ;;
        init=*)
            INIT="${param#init=}"
            ;;
        rd.break)
            echo "Dropping to emergency shell..."
            exec /bin/sh
            ;;
    esac
done

# Load VirtIO modules if present (should be built-in for DruidOS)
if [ -d /lib/modules ]; then
    for mod in virtio virtio_pci virtio_blk virtio_ring; do
        modprobe "$mod" 2>/dev/null || true
    done
fi

# Wait for root device
echo "Waiting for root device: $ROOT"
count=0
while [ ! -e "$ROOT" ] && [ $count -lt 30 ]; do
    sleep 0.5
    count=$((count + 1))

    # Handle PARTUUID
    if echo "$ROOT" | grep -q "PARTUUID="; then
        partuuid="${ROOT#PARTUUID=}"
        ROOT=$(blkid -t PARTUUID="$partuuid" -o device 2>/dev/null || echo "$ROOT")
    fi

    # Handle UUID
    if echo "$ROOT" | grep -q "UUID="; then
        uuid="${ROOT#UUID=}"
        ROOT=$(blkid -t UUID="$uuid" -o device 2>/dev/null || echo "$ROOT")
    fi
done

if [ ! -e "$ROOT" ]; then
    echo "ERROR: Root device not found: $ROOT"
    echo "Available block devices:"
    ls -la /dev/vd* /dev/sd* 2>/dev/null || echo "No block devices found"
    echo ""
    echo "Dropping to emergency shell..."
    exec /bin/sh
fi

# Check if root is ZFS
if echo "$ROOT" | grep -q "^zfs:"; then
    POOL="${ROOT#zfs:}"

    echo "Importing ZFS pool: $POOL"

    # Load ZFS modules
    for mod in spl zfs; do
        modprobe "$mod" 2>/dev/null || true
    done

    # Import pool
    zpool import -N -R /mnt "$POOL" || {
        echo "ERROR: Failed to import ZFS pool"
        exec /bin/sh
    }

    # Mount root dataset
    mount -t zfs "$POOL" /mnt || {
        echo "ERROR: Failed to mount ZFS root"
        exec /bin/sh
    }
else
    # Standard block device mount
    echo "Mounting root filesystem..."

    MOUNT_OPTS=""
    [ -n "$ROOTFSTYPE" ] && MOUNT_OPTS="-t $ROOTFSTYPE"
    [ -n "$ROOTFLAGS" ] && MOUNT_OPTS="$MOUNT_OPTS -o $ROOTFLAGS"

    mount $MOUNT_OPTS "$ROOT" /mnt || {
        echo "ERROR: Failed to mount root filesystem"
        echo "Trying with defaults..."
        mount "$ROOT" /mnt || {
            echo "ERROR: Mount failed completely"
            exec /bin/sh
        }
    }
fi

# Verify init exists
if [ ! -x "/mnt${INIT}" ]; then
    echo "ERROR: Init not found or not executable: /mnt${INIT}"
    echo "Available inits:"
    ls -la /mnt/sbin/init /mnt/lib/systemd/systemd 2>/dev/null || true
    exec /bin/sh
fi

# Cleanup
umount /proc /sys /dev 2>/dev/null || true

# Switch to real root
echo "Switching to real root filesystem..."
exec switch_root /mnt "$INIT"

# If we get here, something went wrong
echo "ERROR: switch_root failed"
exec /bin/sh
INIT_EOF

    chmod +x "$WORK_DIR/init"
}

build_initramfs() {
    log_info "Building initramfs image..."

    mkdir -p "$(dirname "$OUTPUT")"

    cd "$WORK_DIR"
    find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 > "$OUTPUT"

    log_success "Initramfs created: $OUTPUT"
    ls -lh "$OUTPUT"
}

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║         DruidOS Initramfs Build System                    ║"
    echo "║         Kernel: ${KERNEL_VERSION}                         "
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    check_dependencies
    create_structure
    install_busybox
    install_modules
    install_zfs
    create_init
    build_initramfs

    echo ""
    log_success "Initramfs build complete!"
    echo ""
    echo "To use with kernel:"
    echo "  initrd /initramfs-${KERNEL_VERSION}-druidos.img"
    echo ""
}

main "$@"
