#!/bin/bash
# =============================================================================
# BONSAI ISO Builder
# Creates a bootable ISO image for testing in VirtualBox/VMware/online VMs
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
OUTPUT_DIR="$BUILD_DIR/output"
ISO_DIR="$BUILD_DIR/iso"

check_dependencies() {
    log_info "Checking dependencies..."

    local missing=()
    for cmd in xorriso mtools; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_warn "Missing: ${missing[*]}"
        log_info "Install with: sudo apt install xorriso mtools"
        log_info "Trying alternative method with genisoimage..."

        if ! command -v genisoimage &>/dev/null && ! command -v mkisofs &>/dev/null; then
            log_error "Need xorriso, genisoimage, or mkisofs"
            exit 1
        fi
    fi

    log_success "Dependencies OK"
}

check_kernel() {
    if [ ! -f "$OUTPUT_DIR/bonsai-kernel" ]; then
        log_error "Kernel not found: $OUTPUT_DIR/bonsai-kernel"
        log_info "Build with: ./bonsai/scripts/build-kernel.sh"
        exit 1
    fi

    if [ ! -f "$OUTPUT_DIR/bonsai-initramfs.img" ]; then
        log_error "Initramfs not found: $OUTPUT_DIR/bonsai-initramfs.img"
        log_info "Build with: ./bonsai/scripts/build-initramfs.sh"
        exit 1
    fi

    log_success "Kernel and initramfs found"
}

download_syslinux() {
    local syslinux_dir="$BUILD_DIR/syslinux"

    if [ -d "$syslinux_dir" ] && [ -f "$syslinux_dir/bios/core/isolinux.bin" ]; then
        log_info "Syslinux already exists"
        return 0
    fi

    log_info "Downloading Syslinux..."
    mkdir -p "$BUILD_DIR"

    local version="6.03"
    local url="https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/syslinux-${version}.tar.xz"
    local tarball="$BUILD_DIR/syslinux-${version}.tar.xz"

    if [ ! -f "$tarball" ]; then
        # Try curl first, fallback to wget
        if command -v curl &>/dev/null; then
            log_info "Downloading with curl..."
            curl -L -f -o "$tarball" "$url" || {
                log_error "Failed to download syslinux with curl"
                exit 1
            }
        else
            log_info "Downloading with wget..."
            wget --progress=bar:force -O "$tarball" "$url" || {
                log_error "Failed to download syslinux with wget"
                exit 1
            }
        fi
    fi

    log_info "Extracting syslinux..."
    tar -xf "$tarball" -C "$BUILD_DIR" || {
        log_error "Failed to extract syslinux"
        exit 1
    }
    mv "$BUILD_DIR/syslinux-${version}" "$syslinux_dir"

    # Verify extraction
    if [ ! -f "$syslinux_dir/bios/core/isolinux.bin" ]; then
        log_error "Syslinux extraction incomplete - isolinux.bin not found"
        exit 1
    fi

    log_success "Syslinux ready"
}

create_iso_structure() {
    log_info "Creating ISO structure..."

    rm -rf "$ISO_DIR"
    mkdir -p "$ISO_DIR/boot/isolinux"

    # Verify source files exist
    local syslinux_dir="$BUILD_DIR/syslinux"

    log_info "Checking required files..."
    for f in "$OUTPUT_DIR/bonsai-kernel" "$OUTPUT_DIR/bonsai-initramfs.img" \
             "$syslinux_dir/bios/core/isolinux.bin" \
             "$syslinux_dir/bios/com32/elflink/ldlinux/ldlinux.c32"; do
        if [ ! -f "$f" ]; then
            log_error "Required file not found: $f"
            exit 1
        fi
    done

    # Copy kernel and initramfs
    log_info "Copying kernel and initramfs..."
    cp "$OUTPUT_DIR/bonsai-kernel" "$ISO_DIR/boot/vmlinuz"
    cp "$OUTPUT_DIR/bonsai-initramfs.img" "$ISO_DIR/boot/initrd.img"

    # Copy syslinux files
    log_info "Copying syslinux files..."
    cp "$syslinux_dir/bios/core/isolinux.bin" "$ISO_DIR/boot/isolinux/"
    cp "$syslinux_dir/bios/com32/elflink/ldlinux/ldlinux.c32" "$ISO_DIR/boot/isolinux/"
    cp "$syslinux_dir/bios/com32/lib/libcom32.c32" "$ISO_DIR/boot/isolinux/" 2>/dev/null || true
    cp "$syslinux_dir/bios/com32/libutil/libutil.c32" "$ISO_DIR/boot/isolinux/" 2>/dev/null || true

    # Create isolinux config
    cat > "$ISO_DIR/boot/isolinux/isolinux.cfg" << 'EOF'
DEFAULT druidos
TIMEOUT 30
PROMPT 1

LABEL druidos
    MENU LABEL DruidOS Bonsai
    LINUX /boot/vmlinuz
    INITRD /boot/initrd.img
    APPEND console=tty0 console=ttyS0,115200

LABEL druidos-serial
    MENU LABEL DruidOS Bonsai (Serial Console)
    LINUX /boot/vmlinuz
    INITRD /boot/initrd.img
    APPEND console=ttyS0,115200
EOF

    log_success "ISO structure created"
}

build_iso() {
    log_info "Building ISO..."

    local iso_file="$OUTPUT_DIR/druidos-bonsai.iso"

    if command -v xorriso &>/dev/null; then
        xorriso -as mkisofs \
            -o "$iso_file" \
            -isohybrid-mbr "$BUILD_DIR/syslinux/bios/mbr/isohdpfx.bin" \
            -c boot/isolinux/boot.cat \
            -b boot/isolinux/isolinux.bin \
            -no-emul-boot \
            -boot-load-size 4 \
            -boot-info-table \
            "$ISO_DIR"
    elif command -v genisoimage &>/dev/null; then
        genisoimage \
            -o "$iso_file" \
            -b boot/isolinux/isolinux.bin \
            -c boot/isolinux/boot.cat \
            -no-emul-boot \
            -boot-load-size 4 \
            -boot-info-table \
            -J -R \
            "$ISO_DIR"
    else
        mkisofs \
            -o "$iso_file" \
            -b boot/isolinux/isolinux.bin \
            -c boot/isolinux/boot.cat \
            -no-emul-boot \
            -boot-load-size 4 \
            -boot-info-table \
            -J -R \
            "$ISO_DIR"
    fi

    local size
    size=$(du -h "$iso_file" | cut -f1)

    log_success "ISO created: $iso_file ($size)"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND]

Commands:
    build       Build bootable ISO (default)
    clean       Clean ISO build files
    help        Show this help

The ISO can be used with:
    - VirtualBox
    - VMware
    - QEMU: qemu-system-x86_64 -cdrom druidos-bonsai.iso -m 512
    - Online VM services

Requirements:
    - bonsai-kernel and bonsai-initramfs.img in build/output/
    - xorriso or genisoimage
EOF
}

main() {
    local command="${1:-build}"

    case "$command" in
        build)
            check_dependencies
            check_kernel
            download_syslinux
            create_iso_structure
            build_iso

            echo ""
            log_success "DruidOS ISO ready!"
            echo ""
            echo "Test with:"
            echo "  qemu-system-x86_64 -cdrom build/output/druidos-bonsai.iso -m 512"
            echo ""
            echo "Or upload to VirtualBox/VMware/online VM service"
            ;;
        clean)
            log_info "Cleaning ISO build..."
            rm -rf "$ISO_DIR"
            rm -f "$OUTPUT_DIR/druidos-bonsai.iso"
            log_success "Clean complete"
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
