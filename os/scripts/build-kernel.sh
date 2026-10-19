#!/bin/bash
#
# DruidOS Kernel Build Script
# Builds a minimal VirtIO-only kernel for VM-first operation
#
# Usage:
#   ./scripts/build-kernel.sh [--clean] [--install]
#
# Requirements:
#   - Linux kernel source (downloaded automatically if not present)
#   - Build dependencies: gcc, make, flex, bison, libelf-dev, libssl-dev, bc
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.12.6}"
KERNEL_MAJOR="${KERNEL_VERSION%%.*}"
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_MAJOR}.x/linux-${KERNEL_VERSION}.tar.xz"

BUILD_DIR="${BUILD_DIR:-$ROOT_DIR/build}"
KERNEL_SRC="$BUILD_DIR/linux-${KERNEL_VERSION}"
KERNEL_CONFIG="$ROOT_DIR/kernel/druidos.config"
OUTPUT_DIR="$BUILD_DIR/output"

JOBS="${JOBS:-$(nproc)}"
CLEAN=false
INSTALL=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

usage() {
    cat << EOF
DruidOS Kernel Build Script

Usage: $(basename "$0") [OPTIONS]

Options:
    --clean         Clean build directory before building
    --install       Install kernel to /boot after building
    --version VER   Specify kernel version (default: ${KERNEL_VERSION})
    --jobs N        Number of parallel jobs (default: $(nproc))
    --help          Show this help message

Environment Variables:
    KERNEL_VERSION  Kernel version to build
    BUILD_DIR       Build directory (default: ./build)
    JOBS            Number of parallel jobs

Examples:
    ./scripts/build-kernel.sh
    ./scripts/build-kernel.sh --clean --version 6.12.6
    JOBS=8 ./scripts/build-kernel.sh --install
EOF
    exit 0
}

check_dependencies() {
    log_info "Checking build dependencies..."

    local deps=(gcc make flex bison bc perl)
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    # Check for development headers
    if ! pkg-config --exists libelf 2>/dev/null; then
        missing+=("libelf-dev")
    fi

    if ! pkg-config --exists openssl 2>/dev/null; then
        missing+=("libssl-dev")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing[*]}

Install with:
    sudo apt install build-essential flex bison libelf-dev libssl-dev bc"
    fi

    log_success "All dependencies satisfied"
}

download_kernel() {
    if [ -d "$KERNEL_SRC" ]; then
        log_info "Kernel source already exists at $KERNEL_SRC"
        return 0
    fi

    log_info "Downloading Linux ${KERNEL_VERSION}..."
    mkdir -p "$BUILD_DIR"

    local tarball="$BUILD_DIR/linux-${KERNEL_VERSION}.tar.xz"

    if [ ! -f "$tarball" ]; then
        curl -L -o "$tarball" "$KERNEL_URL" || \
            wget -O "$tarball" "$KERNEL_URL" || \
            log_error "Failed to download kernel source"
    fi

    log_info "Extracting kernel source..."
    tar -xf "$tarball" -C "$BUILD_DIR"

    log_success "Kernel source ready at $KERNEL_SRC"
}

configure_kernel() {
    log_info "Configuring kernel..."

    cd "$KERNEL_SRC"

    # Start with tinyconfig for minimal base
    make tinyconfig

    # Merge our VirtIO config
    if [ -f "$KERNEL_CONFIG" ]; then
        log_info "Merging DruidOS configuration..."
        ./scripts/kconfig/merge_config.sh .config "$KERNEL_CONFIG"
    else
        log_error "DruidOS kernel config not found at $KERNEL_CONFIG"
    fi

    # Ensure all dependencies are resolved
    make olddefconfig

    log_success "Kernel configured"
}

build_kernel() {
    log_info "Building kernel with $JOBS parallel jobs..."

    cd "$KERNEL_SRC"

    # Build kernel and modules
    make -j"$JOBS" bzImage modules

    log_success "Kernel build complete"

    # Show size statistics
    log_info "Kernel image size:"
    ls -lh arch/x86/boot/bzImage

    log_info "Module count:"
    find . -name "*.ko" | wc -l
}

install_output() {
    log_info "Copying build artifacts to $OUTPUT_DIR..."

    mkdir -p "$OUTPUT_DIR"

    cd "$KERNEL_SRC"

    # Copy kernel image
    cp arch/x86/boot/bzImage "$OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-druidos"

    # Copy System.map
    cp System.map "$OUTPUT_DIR/System.map-${KERNEL_VERSION}-druidos"

    # Install modules to output directory
    make INSTALL_MOD_PATH="$OUTPUT_DIR" modules_install

    # Copy config for reference
    cp .config "$OUTPUT_DIR/config-${KERNEL_VERSION}-druidos"

    log_success "Build artifacts in $OUTPUT_DIR"

    # Summary
    echo ""
    log_info "Build Summary:"
    echo "  Kernel: $OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-druidos"
    echo "  Modules: $OUTPUT_DIR/lib/modules/${KERNEL_VERSION}-druidos/"
    echo "  Config: $OUTPUT_DIR/config-${KERNEL_VERSION}-druidos"
}

install_system() {
    if [ "$EUID" -ne 0 ]; then
        log_error "System installation requires root privileges. Run with sudo."
    fi

    log_info "Installing kernel to /boot..."

    cp "$OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-druidos" /boot/
    cp "$OUTPUT_DIR/System.map-${KERNEL_VERSION}-druidos" /boot/
    cp "$OUTPUT_DIR/config-${KERNEL_VERSION}-druidos" /boot/

    log_info "Installing modules to /lib/modules..."
    cp -r "$OUTPUT_DIR/lib/modules/${KERNEL_VERSION}-druidos" /lib/modules/

    # Run depmod
    depmod "${KERNEL_VERSION}-druidos"

    log_success "Kernel installed. Update your bootloader configuration."

    echo ""
    log_info "For systemd-boot, add to /boot/loader/entries/druidos.conf:"
    cat << EOF
title   DruidOS
linux   /vmlinuz-${KERNEL_VERSION}-druidos
options root=PARTUUID=xxx rw quiet
EOF
}

clean_build() {
    log_info "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    log_success "Build directory cleaned"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --clean)
            CLEAN=true
            shift
            ;;
        --install)
            INSTALL=true
            shift
            ;;
        --version)
            KERNEL_VERSION="$2"
            KERNEL_MAJOR="${KERNEL_VERSION%%.*}"
            KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_MAJOR}.x/linux-${KERNEL_VERSION}.tar.xz"
            KERNEL_SRC="$BUILD_DIR/linux-${KERNEL_VERSION}"
            shift 2
            ;;
        --jobs)
            JOBS="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            ;;
    esac
done

# Main build process
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║         DruidOS Kernel Build System                       ║"
    echo "║         Target: Linux ${KERNEL_VERSION} (VirtIO-only)             ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    if [ "$CLEAN" = true ]; then
        clean_build
    fi

    check_dependencies
    download_kernel
    configure_kernel
    build_kernel
    install_output

    if [ "$INSTALL" = true ]; then
        install_system
    fi

    echo ""
    log_success "DruidOS kernel build complete!"
    echo ""
}

main "$@"
