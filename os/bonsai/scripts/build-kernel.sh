#!/bin/bash
# =============================================================================
# BONSAI Kernel Build Script
# Builds a minimal paravirtualized Linux kernel for DruidOS
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
KERNEL_VERSION="${KERNEL_VERSION:-6.12.6}"
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz"
JOBS="${JOBS:-$(nproc)}"

print_banner() {
    echo -e "${GREEN}"
    cat << 'EOF'
    ____                        _
   / __ )____  ____  _________ (_)
  / __  / __ \/ __ \/ ___/ __ `/ /
 / /_/ / /_/ / / / (__  ) /_/ / /
/_____/\____/_/ /_/____/\__,_/_/

     Minimal Paravirtualized Kernel
EOF
    echo -e "${NC}"
}

check_dependencies() {
    log_info "Checking build dependencies..."

    local deps=(
        "gcc"
        "make"
        "flex"
        "bison"
        "bc"
        "libelf-dev:pkg-config --exists libelf"
        "libssl-dev:pkg-config --exists openssl"
        "wget"
        "xz"
    )

    local missing=()

    for dep in "${deps[@]}"; do
        local name="${dep%%:*}"
        local check="${dep##*:}"

        if [ "$name" = "$check" ]; then
            # Simple command check
            if ! command -v "$name" &>/dev/null; then
                missing+=("$name")
            fi
        else
            # Custom check
            if ! eval "$check" &>/dev/null; then
                missing+=("$name")
            fi
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        log_info "Install with: sudo apt install build-essential flex bison bc libelf-dev libssl-dev wget xz-utils"
        exit 1
    fi

    log_success "All dependencies satisfied"
}

download_kernel() {
    local kernel_dir="$BUILD_DIR/linux-${KERNEL_VERSION}"

    if [ -d "$kernel_dir" ]; then
        log_info "Kernel source already exists: $kernel_dir"
        return 0
    fi

    log_info "Downloading Linux ${KERNEL_VERSION}..."
    mkdir -p "$BUILD_DIR"

    local tarball="$BUILD_DIR/linux-${KERNEL_VERSION}.tar.xz"

    if [ ! -f "$tarball" ]; then
        wget --progress=bar:force -O "$tarball" "$KERNEL_URL"
    fi

    log_info "Extracting kernel source..."
    tar -xf "$tarball" -C "$BUILD_DIR"

    log_success "Kernel source ready: $kernel_dir"
}

configure_kernel() {
    local kernel_dir="$BUILD_DIR/linux-${KERNEL_VERSION}"

    log_info "Configuring kernel with Bonsai config..."

    cd "$kernel_dir"

    # Copy our defconfig directly to kernel configs
    if [ -f "$BONSAI_DIR/config/bonsai_defconfig" ]; then
        log_info "Installing Bonsai defconfig..."
        cp "$BONSAI_DIR/config/bonsai_defconfig" arch/x86/configs/bonsai_defconfig
    else
        log_error "Bonsai defconfig not found!"
        exit 1
    fi

    # Use our defconfig directly
    log_info "Applying Bonsai defconfig..."
    make ARCH=x86_64 bonsai_defconfig

    # Show config stats
    log_info "Config stats:"
    grep -c "=y" .config || true
    grep -c "=m" .config || true

    log_success "Kernel configured"
}

build_kernel() {
    local kernel_dir="$BUILD_DIR/linux-${KERNEL_VERSION}"

    log_info "Building kernel with $JOBS jobs..."

    cd "$kernel_dir"

    # Build kernel image
    make -j"$JOBS" ARCH=x86_64 bzImage

    # Copy result
    mkdir -p "$BUILD_DIR/output"
    cp arch/x86/boot/bzImage "$BUILD_DIR/output/bonsai-kernel"

    local size
    size=$(du -h "$BUILD_DIR/output/bonsai-kernel" | cut -f1)

    log_success "Kernel built: $BUILD_DIR/output/bonsai-kernel ($size)"

    # Check size
    local size_bytes
    size_bytes=$(stat -c%s "$BUILD_DIR/output/bonsai-kernel")

    if [ "$size_bytes" -lt 15000000 ]; then
        log_success "✓ Kernel size under 15MB target!"
    else
        log_warn "Kernel size exceeds 15MB target. Consider further reduction."
    fi
}

show_config_summary() {
    local kernel_dir="$BUILD_DIR/linux-${KERNEL_VERSION}"

    if [ -f "$kernel_dir/.config" ]; then
        echo ""
        echo "Configuration Summary:"
        echo "======================"
        echo "VirtIO Block:   $(grep -q 'CONFIG_VIRTIO_BLK=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo "VirtIO Net:     $(grep -q 'CONFIG_VIRTIO_NET=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo "VirtIO GPU:     $(grep -q 'CONFIG_DRM_VIRTIO_GPU=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo "VirtIO Input:   $(grep -q 'CONFIG_VIRTIO_INPUT=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo "VirtIO Console: $(grep -q 'CONFIG_VIRTIO_CONSOLE=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo "KVM Guest:      $(grep -q 'CONFIG_KVM_GUEST=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo "Paravirt:       $(grep -q 'CONFIG_PARAVIRT=y' "$kernel_dir/.config" && echo '✓' || echo '✗')"
        echo ""
        echo "Disabled features:"
        echo "  USB:          $(grep -q '# CONFIG_USB is not set\|# CONFIG_USB_SUPPORT is not set' "$kernel_dir/.config" && echo '✓ disabled' || echo '✗ enabled')"
        echo "  ACPI:         $(grep -q '# CONFIG_ACPI is not set' "$kernel_dir/.config" && echo '✓ disabled' || echo '✗ enabled')"
        echo "  Sound:        $(grep -q '# CONFIG_SOUND is not set' "$kernel_dir/.config" && echo '✓ disabled' || echo '✗ enabled')"
        echo "  Bluetooth:    $(grep -q '# CONFIG_BT is not set' "$kernel_dir/.config" && echo '✓ disabled' || echo '✗ enabled')"
        echo ""
    fi
}

clean() {
    log_info "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    log_success "Clean complete"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND]

Commands:
    build       Download, configure, and build kernel (default)
    configure   Configure kernel only
    download    Download kernel source only
    clean       Remove build directory
    help        Show this help

Environment Variables:
    KERNEL_VERSION  Linux kernel version (default: 6.12.6)
    BUILD_DIR       Build directory (default: ./build)
    JOBS            Parallel jobs (default: nproc)

Examples:
    $(basename "$0")                          # Full build
    KERNEL_VERSION=6.11 $(basename "$0")      # Build specific version
    $(basename "$0") clean && $(basename "$0") # Clean rebuild
EOF
}

main() {
    local command="${1:-build}"

    print_banner

    case "$command" in
        build)
            check_dependencies
            download_kernel
            configure_kernel
            build_kernel
            show_config_summary

            echo ""
            log_success "Bonsai kernel ready!"
            echo ""
            echo "Next steps:"
            echo "  1. Build initramfs: ./scripts/build-initramfs.sh"
            echo "  2. Run in QEMU:     ./scripts/run-qemu.sh"
            ;;
        configure)
            download_kernel
            configure_kernel
            show_config_summary
            ;;
        download)
            download_kernel
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
