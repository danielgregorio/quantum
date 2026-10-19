#!/bin/bash
#
# DruidOS ZFS Setup Script
# Creates the ZFS pool and dataset layout for DruidOS
#
# Usage:
#   sudo ./scripts/setup-zfs.sh /dev/vda
#
# WARNING: This will destroy all data on the target disk!
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
POOL_NAME="${POOL_NAME:-rpool}"
HOSTNAME="${HOSTNAME:-druidos}"

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
DruidOS ZFS Setup Script

Usage: sudo $(basename "$0") DISK [OPTIONS]

Arguments:
    DISK            Target disk (e.g., /dev/vda)

Options:
    --pool NAME     Pool name (default: rpool)
    --hostname NAME Hostname (default: druidos)
    --encrypt       Enable native ZFS encryption
    --mirror DISK2  Create mirrored pool with second disk
    --help          Show this help message

WARNING: This will DESTROY ALL DATA on the target disk(s)!

Examples:
    sudo ./scripts/setup-zfs.sh /dev/vda
    sudo ./scripts/setup-zfs.sh /dev/vda --encrypt
    sudo ./scripts/setup-zfs.sh /dev/vda --mirror /dev/vdb
EOF
    exit 0
}

DISK=""
DISK2=""
ENCRYPT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pool)
            POOL_NAME="$2"
            shift 2
            ;;
        --hostname)
            HOSTNAME="$2"
            shift 2
            ;;
        --encrypt)
            ENCRYPT=true
            shift
            ;;
        --mirror)
            DISK2="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        /dev/*)
            if [ -z "$DISK" ]; then
                DISK="$1"
            fi
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            ;;
    esac
done

if [ -z "$DISK" ]; then
    log_error "No disk specified. Usage: $0 /dev/vda"
fi

if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
fi

check_dependencies() {
    log_info "Checking dependencies..."

    local deps=(zpool zfs sgdisk)
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing[*]}

Install with:
    sudo apt install zfsutils-linux gdisk"
    fi
}

confirm_destruction() {
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                      WARNING                               ║${NC}"
    echo -e "${RED}║   This will DESTROY ALL DATA on the following disk(s):   ║${NC}"
    echo -e "${RED}║                                                            ║${NC}"
    echo -e "${RED}║   Primary: ${DISK}                                         ${NC}"
    if [ -n "$DISK2" ]; then
        echo -e "${RED}║   Mirror:  ${DISK2}                                         ${NC}"
    fi
    echo -e "${RED}║                                                            ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    read -p "Type 'yes' to continue: " confirm
    if [ "$confirm" != "yes" ]; then
        log_error "Aborted by user"
    fi
}

partition_disk() {
    local disk="$1"
    log_info "Partitioning $disk..."

    # Clear existing partition table
    sgdisk --zap-all "$disk"

    # Create partitions:
    # 1: EFI System Partition (512M)
    # 2: ZFS root (rest of disk)
    sgdisk -n 1:0:+512M -t 1:EF00 -c 1:"EFI" "$disk"
    sgdisk -n 2:0:0 -t 2:BF00 -c 2:"ZFS" "$disk"

    # Notify kernel of partition changes
    partprobe "$disk" 2>/dev/null || true
    sleep 2

    log_success "Partitioned $disk"
}

create_pool() {
    log_info "Creating ZFS pool: $POOL_NAME..."

    # Determine partition naming
    local part_suffix=""
    if [[ "$DISK" == *"nvme"* ]] || [[ "$DISK" == *"loop"* ]]; then
        part_suffix="p"
    fi

    local zfs_part="${DISK}${part_suffix}2"
    local pool_opts=""

    if [ -n "$DISK2" ]; then
        local part_suffix2=""
        if [[ "$DISK2" == *"nvme"* ]] || [[ "$DISK2" == *"loop"* ]]; then
            part_suffix2="p"
        fi
        local zfs_part2="${DISK2}${part_suffix2}2"
        pool_opts="mirror $zfs_part $zfs_part2"
    else
        pool_opts="$zfs_part"
    fi

    # ZFS pool creation options
    local create_opts=(
        -o ashift=12                    # 4K sectors
        -o autotrim=on                  # TRIM/discard
        -O acltype=posixacl             # POSIX ACLs
        -O canmount=off                 # Don't mount pool root
        -O compression=zstd             # Compression
        -O dnodesize=auto               # Automatic dnode sizing
        -O normalization=formD          # Unicode normalization
        -O relatime=on                  # Reduce atime writes
        -O xattr=sa                     # Extended attributes in inodes
        -O mountpoint=/                 # Root mountpoint
    )

    if [ "$ENCRYPT" = true ]; then
        log_info "Setting up ZFS native encryption..."
        create_opts+=(-O encryption=aes-256-gcm)
        create_opts+=(-O keylocation=prompt)
        create_opts+=(-O keyformat=passphrase)
    fi

    zpool create -f "${create_opts[@]}" "$POOL_NAME" $pool_opts

    log_success "ZFS pool created"
}

create_datasets() {
    log_info "Creating ZFS datasets..."

    # Root dataset
    zfs create -o canmount=off -o mountpoint=none "$POOL_NAME/ROOT"
    zfs create -o canmount=noauto -o mountpoint=/ "$POOL_NAME/ROOT/$HOSTNAME"

    # Home (separate snapshots)
    zfs create -o mountpoint=/home "$POOL_NAME/home"

    # Var hierarchy
    zfs create -o canmount=off -o mountpoint=/var "$POOL_NAME/var"

    # Logs (no snapshots, grows indefinitely)
    zfs create -o com.sun:auto-snapshot=false "$POOL_NAME/var/log"

    # Cache (no snapshots)
    zfs create -o com.sun:auto-snapshot=false "$POOL_NAME/var/cache"

    # Lib subdirectories
    zfs create -o canmount=off "$POOL_NAME/var/lib"

    # Hive data directory
    zfs create -o mountpoint=/var/lib/hive "$POOL_NAME/var/lib/hive"

    # Docker/containers (if needed)
    zfs create -o com.sun:auto-snapshot=false "$POOL_NAME/var/lib/docker"

    # Reserved space for emergencies
    zfs create -o refreservation=1G -o mountpoint=none "$POOL_NAME/reserved"

    # Set boot filesystem
    zpool set bootfs="$POOL_NAME/ROOT/$HOSTNAME" "$POOL_NAME"

    log_success "Datasets created"
}

format_esp() {
    log_info "Formatting EFI System Partition..."

    local part_suffix=""
    if [[ "$DISK" == *"nvme"* ]] || [[ "$DISK" == *"loop"* ]]; then
        part_suffix="p"
    fi

    local esp_part="${DISK}${part_suffix}1"

    mkfs.vfat -F 32 -n "EFI" "$esp_part"

    log_success "ESP formatted"
}

show_summary() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║         DruidOS ZFS Setup Complete                        ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    log_info "Pool status:"
    zpool status "$POOL_NAME"

    echo ""
    log_info "Dataset layout:"
    zfs list -r "$POOL_NAME"

    echo ""
    log_info "Next steps:"
    echo "  1. Export the pool:"
    echo "     zpool export $POOL_NAME"
    echo ""
    echo "  2. Mount for installation:"
    echo "     zpool import -N -R /mnt $POOL_NAME"
    echo "     zfs mount $POOL_NAME/ROOT/$HOSTNAME"
    echo "     zfs mount -a"
    echo "     mkdir -p /mnt/boot/efi"
    echo "     mount ${DISK}${part_suffix}1 /mnt/boot/efi"
    echo ""
    echo "  3. Install DruidOS base system to /mnt"
    echo ""
    echo "  4. Install bootloader:"
    echo "     bootctl --path=/mnt/boot/efi install"
    echo ""

    if [ "$ENCRYPT" = true ]; then
        echo -e "${YELLOW}NOTE: ZFS encryption is enabled.${NC}"
        echo "      You will need to enter the passphrase at each boot."
        echo ""
    fi
}

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║         DruidOS ZFS Setup                                 ║"
    echo "║         Pool: $POOL_NAME                                  "
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    check_dependencies
    confirm_destruction

    # Partition disks
    partition_disk "$DISK"
    if [ -n "$DISK2" ]; then
        partition_disk "$DISK2"
    fi

    # Create ZFS pool and datasets
    create_pool
    create_datasets

    # Format ESP
    format_esp

    # Show results
    show_summary
}

main "$@"
