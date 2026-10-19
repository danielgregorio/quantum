#!/bin/bash
# =============================================================================
# BONSAI Initramfs Build Script
# Creates a minimal initramfs for DruidOS
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BONSAI_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BONSAI_DIR")"
BUILD_DIR="${BUILD_DIR:-$PROJECT_ROOT/build}"
INITRAMFS_DIR="$BUILD_DIR/initramfs"
OUTPUT_DIR="$BUILD_DIR/output"

# Busybox version
BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
BUSYBOX_URL="https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2"

print_banner() {
    echo -e "${GREEN}"
    cat << 'EOF'
    ____                        _    ____            __  ___
   / __ )____  ____  _________ (_)  /  _/___  ___  / /_/ _ \____ _____ ___
  / __  / __ \/ __ \/ ___/ __ `/ /   / // __ \/ _ \/ __/  __/ __ `/ __ `__ \
 / /_/ / /_/ / / / (__  ) /_/ / /  _/ // / / /  __/ /_/ /  / /_/ / / / / / /
/_____/\____/_/ /_/____/\__,_/_/  /___/_/ /_/\___/\__/_/   \__,_/_/ /_/ /_/

                    Minimal Initramfs Builder
EOF
    echo -e "${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."

    local missing=()
    for cmd in gcc make cpio gzip; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing: ${missing[*]}"
        exit 1
    fi

    log_success "Dependencies OK"
}

download_busybox() {
    local busybox_dir="$BUILD_DIR/busybox-${BUSYBOX_VERSION}"

    # Skip if busybox binary already exists (e.g., from apt package)
    if [ -f "$busybox_dir/busybox" ]; then
        log_info "Busybox binary already exists"
        return 0
    fi

    if [ -d "$busybox_dir" ] && [ -f "$busybox_dir/Makefile" ]; then
        log_info "Busybox source exists"
        return 0
    fi

    log_info "Downloading Busybox ${BUSYBOX_VERSION}..."
    mkdir -p "$BUILD_DIR"

    local tarball="$BUILD_DIR/busybox-${BUSYBOX_VERSION}.tar.bz2"
    if [ ! -f "$tarball" ]; then
        # Try curl first, fallback to wget
        if command -v curl &>/dev/null; then
            log_info "Downloading with curl..."
            curl -L -f -o "$tarball" "$BUSYBOX_URL" || {
                log_error "Failed to download busybox with curl"
                exit 1
            }
        else
            log_info "Downloading with wget..."
            wget --progress=bar:force -O "$tarball" "$BUSYBOX_URL" || {
                log_error "Failed to download busybox with wget"
                exit 1
            }
        fi
    fi

    log_info "Extracting busybox..."
    tar -xf "$tarball" -C "$BUILD_DIR" || {
        log_error "Failed to extract busybox"
        exit 1
    }
    log_success "Busybox source ready"
}

build_busybox() {
    local busybox_dir="$BUILD_DIR/busybox-${BUSYBOX_VERSION}"

    # Skip build if binary already exists (e.g., from apt package)
    if [ -x "$busybox_dir/busybox" ]; then
        log_info "Busybox binary already built/provided"
        return 0
    fi

    log_info "Building Busybox (static)..."

    cd "$busybox_dir"

    # Configure for static build
    make defconfig

    # Enable static linking
    sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config

    # Disable features we don't need
    sed -i 's/CONFIG_FEATURE_PREFER_APPLETS=y/# CONFIG_FEATURE_PREFER_APPLETS is not set/' .config
    sed -i 's/CONFIG_FEATURE_SH_STANDALONE=y/# CONFIG_FEATURE_SH_STANDALONE is not set/' .config

    # Build
    make -j"$(nproc)"

    log_success "Busybox built"
}

create_initramfs_structure() {
    log_info "Creating initramfs structure..."

    rm -rf "$INITRAMFS_DIR"
    mkdir -p "$INITRAMFS_DIR"/{bin,sbin,etc,proc,sys,dev,tmp,run,var,usr/bin,usr/sbin}
    mkdir -p "$INITRAMFS_DIR"/mnt/root

    # Install busybox
    local busybox_dir="$BUILD_DIR/busybox-${BUSYBOX_VERSION}"
    cp "$busybox_dir/busybox" "$INITRAMFS_DIR/bin/"
    chmod +x "$INITRAMFS_DIR/bin/busybox"

    # Create symlinks for busybox applets
    cd "$INITRAMFS_DIR/bin"
    for applet in sh ash bash mount umount ls cat echo mkdir rm cp mv ln \
                  sleep ps kill grep sed awk cut head tail sort uniq \
                  chmod chown chroot dmesg poweroff reboot halt \
                  ip ifconfig route ping hostname; do
        ln -sf busybox "$applet"
    done

    cd "$INITRAMFS_DIR/sbin"
    for applet in init mdev; do
        ln -sf ../bin/busybox "$applet"
    done

    # Install Grove shell if available
    local grove_bin="$PROJECT_ROOT/target/x86_64-unknown-linux-musl/release/grove"
    if [ -f "$grove_bin" ]; then
        log_info "Installing Grove shell..."
        cp "$grove_bin" "$INITRAMFS_DIR/bin/grove"
        chmod +x "$INITRAMFS_DIR/bin/grove"
        log_success "Grove installed"
    else
        log_warn "Grove binary not found at $grove_bin"
        log_warn "Build with: cargo build --release --target x86_64-unknown-linux-musl -p grove"
    fi

    log_success "Initramfs structure created"
}

create_init_script() {
    log_info "Creating init script..."

    cat > "$INITRAMFS_DIR/init" << 'INIT_SCRIPT'
#!/bin/sh
# DruidOS Bonsai Init - Minimal Debug Version

# Mount essential filesystems
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t devtmpfs devtmpfs /dev 2>/dev/null || true

# Create minimal device nodes
/bin/busybox mknod -m 622 /dev/console c 5 1 2>/dev/null || true
/bin/busybox mknod -m 666 /dev/null c 1 3 2>/dev/null || true
/bin/busybox mknod -m 666 /dev/tty c 5 0 2>/dev/null || true
/bin/busybox mknod -m 666 /dev/tty0 c 4 0 2>/dev/null || true
/bin/busybox mknod -m 666 /dev/tty1 c 4 1 2>/dev/null || true

# Print boot message
echo ""
echo "================================"
echo "  DruidOS Bonsai - Booting...   "
echo "================================"
echo ""

# Show basic info
echo "Init running!"
echo ""

# Start shell directly
echo "Starting shell..."
exec /bin/busybox sh
INIT_SCRIPT

    chmod +x "$INITRAMFS_DIR/init"
    log_success "Init script created"
}

create_etc_files() {
    log_info "Creating /etc files..."

    # /etc/passwd
    cat > "$INITRAMFS_DIR/etc/passwd" << 'EOF'
root:x:0:0:root:/root:/bin/sh
EOF

    # /etc/group
    cat > "$INITRAMFS_DIR/etc/group" << 'EOF'
root:x:0:
EOF

    # /etc/profile
    cat > "$INITRAMFS_DIR/etc/profile" << 'EOF'
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/root
export PS1='\[\033[1;32m\]druidos\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]# '
alias ll='ls -la'
alias q='poweroff'
EOF

    # /etc/hostname
    echo "druidos" > "$INITRAMFS_DIR/etc/hostname"

    # /etc/os-release
    cat > "$INITRAMFS_DIR/etc/os-release" << 'EOF'
NAME="DruidOS"
VERSION="1.0"
ID=druidos
PRETTY_NAME="DruidOS 1.0 (Bonsai)"
VERSION_ID="1.0"
HOME_URL="https://druidos.org"
EOF

    log_success "/etc files created"
}

pack_initramfs() {
    log_info "Packing initramfs..."

    mkdir -p "$OUTPUT_DIR"

    cd "$INITRAMFS_DIR"
    find . | cpio -o -H newc 2>/dev/null | gzip -9 > "$OUTPUT_DIR/bonsai-initramfs.img"

    local size
    size=$(du -h "$OUTPUT_DIR/bonsai-initramfs.img" | cut -f1)

    log_success "Initramfs created: $OUTPUT_DIR/bonsai-initramfs.img ($size)"
}

clean() {
    log_info "Cleaning initramfs build..."
    rm -rf "$INITRAMFS_DIR"
    rm -f "$OUTPUT_DIR/bonsai-initramfs.img"
    log_success "Clean complete"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND]

Commands:
    build       Build initramfs (default)
    clean       Clean build files
    help        Show this help

Environment Variables:
    BUILD_DIR        Build directory (default: ./build)
    BUSYBOX_VERSION  Busybox version (default: 1.36.1)

The initramfs includes:
    - Busybox (static)
    - Basic shell utilities
    - Init script with VirtIO support
    - Device node creation
EOF
}

main() {
    local command="${1:-build}"

    print_banner

    case "$command" in
        build)
            check_dependencies
            download_busybox
            build_busybox
            create_initramfs_structure
            create_init_script
            create_etc_files
            pack_initramfs

            echo ""
            log_success "Initramfs ready!"
            echo ""
            echo "Next: ./scripts/run-qemu.sh"
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
