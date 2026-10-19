#!/bin/bash
# =============================================================================
# BONSAI QEMU Run Script
# Boots DruidOS in QEMU with VirtIO devices
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

# VM Configuration
MEMORY="${MEMORY:-512}"
CPUS="${CPUS:-2}"
KERNEL="${KERNEL:-$OUTPUT_DIR/bonsai-kernel}"
INITRD="${INITRD:-$OUTPUT_DIR/bonsai-initramfs.img}"
DISK="${DISK:-}"
GRAPHICS="${GRAPHICS:-none}"
NETWORK="${NETWORK:-user}"

check_files() {
    if [ ! -f "$KERNEL" ]; then
        log_error "Kernel not found: $KERNEL"
        log_info "Build with: ./bonsai/scripts/build-kernel.sh"
        exit 1
    fi

    if [ ! -f "$INITRD" ]; then
        log_error "Initramfs not found: $INITRD"
        log_info "Build with: ./bonsai/scripts/build-initramfs.sh"
        exit 1
    fi

    log_success "Kernel: $KERNEL"
    log_success "Initrd: $INITRD"
}

run_qemu() {
    local qemu_cmd="qemu-system-x86_64"

    # Check for KVM support
    local kvm_flag=""
    if [ -w /dev/kvm ]; then
        kvm_flag="-enable-kvm -cpu host"
        log_info "KVM acceleration enabled"
    else
        kvm_flag="-cpu qemu64"
        log_warn "KVM not available, using software emulation"
    fi

    # Build QEMU command
    local cmd=(
        "$qemu_cmd"
        $kvm_flag
        -m "$MEMORY"
        -smp "$CPUS"

        # Kernel and initramfs
        -kernel "$KERNEL"
        -initrd "$INITRD"
        -append "console=ttyS0 quiet loglevel=3"

        # VirtIO devices
        -device virtio-rng-pci

        # Serial console
        -serial mon:stdio
        -nographic
    )

    # Add disk if specified
    if [ -n "$DISK" ]; then
        if [ ! -f "$DISK" ]; then
            log_warn "Disk image not found, creating: $DISK"
            qemu-img create -f qcow2 "$DISK" 1G
        fi
        cmd+=(
            -drive "file=$DISK,format=qcow2,if=virtio"
        )
        log_info "Disk: $DISK"
    fi

    # Network
    case "$NETWORK" in
        user)
            cmd+=(
                -netdev user,id=net0
                -device virtio-net-pci,netdev=net0
            )
            ;;
        none)
            cmd+=(-nic none)
            ;;
        *)
            log_warn "Unknown network type: $NETWORK"
            cmd+=(-nic none)
            ;;
    esac

    # Graphics
    case "$GRAPHICS" in
        none)
            # Already set -nographic above
            ;;
        virtio)
            # Remove -nographic and add virtio-gpu
            cmd=($(printf '%s\n' "${cmd[@]}" | grep -v nographic))
            cmd+=(
                -device virtio-gpu-pci
                -display gtk
            )
            ;;
        sdl)
            cmd=($(printf '%s\n' "${cmd[@]}" | grep -v nographic))
            cmd+=(-display sdl)
            ;;
    esac

    echo ""
    log_info "Starting QEMU..."
    echo ""
    echo "VM Configuration:"
    echo "  Memory: ${MEMORY}MB"
    echo "  CPUs:   $CPUS"
    echo "  Graphics: $GRAPHICS"
    echo "  Network:  $NETWORK"
    echo ""
    echo "Press Ctrl+A, X to exit QEMU"
    echo ""

    # Run QEMU
    exec "${cmd[@]}"
}

create_disk() {
    local disk_path="${1:-$OUTPUT_DIR/druidos.qcow2}"
    local size="${2:-2G}"

    log_info "Creating disk image: $disk_path ($size)"
    mkdir -p "$(dirname "$disk_path")"
    qemu-img create -f qcow2 "$disk_path" "$size"
    log_success "Disk created: $disk_path"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [COMMAND]

Commands:
    run         Run QEMU (default)
    disk        Create a disk image
    help        Show this help

Options:
    -m, --memory SIZE       Memory in MB (default: 512)
    -c, --cpus NUM          Number of CPUs (default: 2)
    -k, --kernel PATH       Kernel image path
    -i, --initrd PATH       Initramfs image path
    -d, --disk PATH         Disk image (optional)
    -g, --graphics MODE     Graphics mode: none, virtio, sdl (default: none)
    -n, --network MODE      Network mode: user, none (default: user)

Examples:
    $(basename "$0")                              # Basic boot, serial console
    $(basename "$0") -m 1024 -c 4                 # More resources
    $(basename "$0") -g virtio                    # With VirtIO GPU
    $(basename "$0") -d disk.qcow2                # With disk
    $(basename "$0") disk mydisk.qcow2 4G         # Create 4GB disk

Console shortcuts:
    Ctrl+A, X    Exit QEMU
    Ctrl+A, C    QEMU monitor
    Ctrl+A, H    Help
EOF
}

main() {
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--memory)
                MEMORY="$2"
                shift 2
                ;;
            -c|--cpus)
                CPUS="$2"
                shift 2
                ;;
            -k|--kernel)
                KERNEL="$2"
                shift 2
                ;;
            -i|--initrd)
                INITRD="$2"
                shift 2
                ;;
            -d|--disk)
                DISK="$2"
                shift 2
                ;;
            -g|--graphics)
                GRAPHICS="$2"
                shift 2
                ;;
            -n|--network)
                NETWORK="$2"
                shift 2
                ;;
            run)
                shift
                check_files
                run_qemu
                ;;
            disk)
                shift
                create_disk "$@"
                exit 0
                ;;
            help|--help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Default action: run
    check_files
    run_qemu
}

main "$@"
