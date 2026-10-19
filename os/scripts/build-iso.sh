#!/bin/bash
# ============================================================================
# DruidOS ISO Builder
# Creates a bootable ISO image for installation
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${BUILD_DIR:-/tmp/druidos-iso-build}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/output}"
ISO_NAME="${ISO_NAME:-druidos-0.1.0-amd64.iso}"
VOLUME_ID="DRUIDOS_INSTALL"

# Base system
BASE_DISTRO="ubuntu"
BASE_VERSION="24.04"
# Ubuntu only keeps the current point release live at the numbered path
# (e.g. 24.04.4, not bare 24.04) and removes old point-release filenames
# as they're superseded, so this needs bumping periodically — if the
# download 404s, check https://releases.ubuntu.com/${BASE_VERSION}/ for
# the current filename.
BASE_POINT_RELEASE="${BASE_POINT_RELEASE:-24.04.4}"
BASE_ARCH="amd64"
BASE_ISO_URL="https://releases.ubuntu.com/${BASE_VERSION}/ubuntu-${BASE_POINT_RELEASE}-live-server-${BASE_ARCH}.iso"

# Customization
INCLUDE_MODEL="${INCLUDE_MODEL:-true}"
MODEL_CACHE="${MODEL_CACHE:-$BUILD_DIR/models}"

# hive-synapse's local model: Qwen2.5 0.5B Instruct as a Q4_K_M GGUF, plus
# its tokenizer. Pinned by sha256 - the GGUF's is the LFS hash Hugging Face
# publishes for it - and downloaded once into MODEL_CACHE.
MODEL_FILES=(
    "qwen2.5-0.5b-instruct-q4_k_m.gguf|https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf|74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
    "qwen2.5-0.5b-instruct-tokenizer.json|https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/resolve/main/tokenizer.json|c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}==>${NC} ${CYAN}$1${NC}"
}

print_banner() {
    echo -e "${BLUE}"
    cat << 'EOF'
    ____             _     __  ____  _____
   / __ \_______  __(_)___/ / / __ \/ ___/
  / / / / ___/ / / / / __  / / / / /\__ \
 / /_/ / /  / /_/ / / /_/ / / /_/ /___/ /
/_____/_/   \__,_/_/\__,_/  \____//____/

          ISO Builder Script

"The Swarm is watching. The Swarm is learning."
EOF
    echo -e "${NC}"
}

check_dependencies() {
    log_step "Checking dependencies"

    local deps=(
        "xorriso"
        "squashfs-tools"  # mksquashfs
        "genisoimage"
        "wget"
        "unsquashfs"
        "chroot"
    )

    local missing=()
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            # Check for package name variations
            case "$dep" in
                "squashfs-tools")
                    if ! command -v mksquashfs &> /dev/null; then
                        missing+=("squashfs-tools")
                    fi
                    ;;
                "unsquashfs")
                    if ! command -v unsquashfs &> /dev/null; then
                        missing+=("squashfs-tools")
                    fi
                    ;;
                *)
                    missing+=("$dep")
                    ;;
            esac
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        log_info "Install with: sudo apt install ${missing[*]}"
        exit 1
    fi

    # Check for root
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root"
        log_info "Run with: sudo $0 $*"
        exit 1
    fi

    log_success "All dependencies satisfied"
}

check_disk_space() {
    log_step "Checking disk space"

    local required_gb=15
    local available_gb

    available_gb=$(df -BG "$BUILD_DIR" 2>/dev/null | awk 'NR==2 {print $4}' | tr -d 'G' || echo "0")

    if [ -z "$available_gb" ] || [ "$available_gb" -lt "$required_gb" ]; then
        # Try parent directory
        mkdir -p "$BUILD_DIR"
        available_gb=$(df -BG "$BUILD_DIR" | awk 'NR==2 {print $4}' | tr -d 'G')
    fi

    if [ "$available_gb" -lt "$required_gb" ]; then
        log_error "Insufficient disk space. Need ${required_gb}GB, have ${available_gb}GB"
        exit 1
    fi

    log_success "Disk space OK (${available_gb}GB available)"
}

setup_build_dirs() {
    log_step "Setting up build directories"

    # Wipe the extraction/build subdirs but keep any already-downloaded
    # base.iso around (a full rm -rf here ran before download_base_iso()
    # ever got a chance to see it, so its cache check was previously dead
    # code - every run re-downloaded the ~3GB base ISO).
    rm -rf "$BUILD_DIR/iso" "$BUILD_DIR/squashfs" "$BUILD_DIR/chroot" "$BUILD_DIR/mnt"
    mkdir -p "$BUILD_DIR"/{iso,squashfs,chroot}
    mkdir -p "$OUTPUT_DIR"

    log_success "Build directories created"
}

download_base_iso() {
    log_step "Downloading base Ubuntu ISO"

    local iso_path="$BUILD_DIR/base.iso"

    if [ -f "$iso_path" ]; then
        log_info "Using cached base ISO"
        return 0
    fi

    log_info "Downloading from: $BASE_ISO_URL"
    wget --progress=bar:force -O "$iso_path" "$BASE_ISO_URL"

    log_success "Base ISO downloaded"
}

extract_iso() {
    log_step "Extracting ISO contents"

    local iso_path="$BUILD_DIR/base.iso"
    local iso_dir="$BUILD_DIR/iso"

    # Mount and copy ISO contents
    local mount_point="$BUILD_DIR/mnt"
    mkdir -p "$mount_point"

    mount -o loop "$iso_path" "$mount_point"
    cp -a "$mount_point"/* "$iso_dir/" || true
    cp -a "$mount_point"/.* "$iso_dir/" 2>/dev/null || true
    umount "$mount_point"

    # Make writable
    chmod -R u+w "$iso_dir"

    log_success "ISO extracted"
}

# unsquashfs -ignore-errors still exits 2 (its documented code for
# "non-fatal errors occurred") rather than 0 when it skips something, and
# this script runs under `set -e` - without this wrapper that non-fatal
# exit code would abort the whole build. Exit 1 (genuinely fatal, e.g.
# filesystem corruption) still propagates.
run_unsquashfs_tolerant() {
    local rc=0
    unsquashfs "$@" || rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then
        return "$rc"
    fi
    return 0
}

extract_squashfs() {
    log_step "Extracting squashfs filesystem"

    local casper_dir="$BUILD_DIR/iso/casper"
    local chroot_dir="$BUILD_DIR/chroot"

    if [ -f "$casper_dir/filesystem.squashfs" ]; then
        # Older casper layout (Desktop ISOs, older Server ISOs): a single
        # squashfs already is the complete rootfs.
        run_unsquashfs_tolerant -f -ignore-errors -d "$chroot_dir" "$casper_dir/filesystem.squashfs"
        log_success "Squashfs extracted (single filesystem.squashfs)"
        return 0
    fi

    # Ubuntu 24.04 Server's Subiquity installer ships several *layered*
    # squashfs images meant to be overlaid at boot, not one flat rootfs:
    #   ubuntu-server-minimal.squashfs                        - base layer
    #   ubuntu-server-minimal.ubuntu-server.squashfs          - server pkgs
    #   ubuntu-server-minimal.ubuntu-server.installer*.squashfs - the live
    #     installer environment itself (Subiquity/curtin), NOT part of the
    #     installed target system.
    # Extract just the two non-installer layers, in order, into the same
    # dir (later extraction wins on conflicts) to reconstruct the target
    # rootfs. This is a plain "last write wins" merge, not a true
    # overlayfs union (no whiteout/deletion handling) - good enough for
    # adding the Hive Stack on top, not meant to byte-for-byte match a
    # live-booted casper session.
    local -a layers=()
    for name in ubuntu-server-minimal.squashfs ubuntu-server-minimal.ubuntu-server.squashfs; do
        if [ -f "$casper_dir/$name" ]; then
            layers+=("$casper_dir/$name")
        fi
    done

    if [ ${#layers[@]} -eq 0 ]; then
        log_error "Could not find a base rootfs squashfs under $casper_dir"
        log_info "Found: $(find "$casper_dir" -iname '*.squashfs' 2>/dev/null | tr '\n' ' ')"
        exit 1
    fi

    for squashfs_path in "${layers[@]}"; do
        log_info "Layering in $(basename "$squashfs_path")"
        # -ignore-errors: some Ubuntu Server layers contain dummy
        # character-device placeholders (e.g. /etc/dpkg/dpkg.cfg.d/excludes,
        # a build-time trick to no-op doc/man installation) that mknod(2)
        # can fail to recreate depending on the host's container/mount
        # restrictions (CAP_MKNOD present but still EPERM in some Docker+
        # containerd configurations). None of that is load-bearing for
        # DruidOS, so skip past it instead of aborting the whole extract.
        run_unsquashfs_tolerant -f -ignore-errors -d "$chroot_dir" "$squashfs_path"
    done

    log_success "Squashfs layers extracted (${#layers[@]} layer(s))"
}

prepare_chroot() {
    log_step "Preparing chroot environment"

    local chroot_dir="$BUILD_DIR/chroot"

    # Mount required filesystems
    mount --bind /dev "$chroot_dir/dev"
    mount --bind /dev/pts "$chroot_dir/dev/pts"
    mount -t proc proc "$chroot_dir/proc"
    mount -t sysfs sysfs "$chroot_dir/sys"

    # Copy resolv.conf for network access
    cp /etc/resolv.conf "$chroot_dir/etc/resolv.conf"

    log_success "Chroot environment prepared"
}

cleanup_chroot() {
    log_step "Cleaning up chroot"

    local chroot_dir="$BUILD_DIR/chroot"

    # Unmount in reverse order
    umount "$chroot_dir/sys" 2>/dev/null || true
    umount "$chroot_dir/proc" 2>/dev/null || true
    umount "$chroot_dir/dev/pts" 2>/dev/null || true
    umount "$chroot_dir/dev" 2>/dev/null || true

    log_success "Chroot cleaned up"
}

run_in_chroot() {
    chroot "$BUILD_DIR/chroot" /bin/bash -c "$1"
}

install_hive_stack() {
    log_step "Installing Hive Stack"

    local chroot_dir="$BUILD_DIR/chroot"
    local release_dir="$PROJECT_ROOT/target/release"

    # Everything the ISO ships from the workspace. An ISO without the real
    # binaries isn't DruidOS, so a missing one is a hard error (this used to
    # fall back to placeholder scripts, and its `cp hive-*` glob also copied
    # cargo's hive-*.d dep-info files into /usr/bin while skipping grove).
    local -a binaries=(
        hive-cortex hive-synapse hive-actuator
        hive-nerve-process hive-nerve-journal hive-nerve-network hive-nerve-fs
        hive-apt hive-zfs hive-dashboard
        grove
    )
    local -a missing=()
    local binary
    for binary in "${binaries[@]}"; do
        [ -x "$release_dir/$binary" ] || missing+=("$binary")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing release binaries in $release_dir: ${missing[*]}"
        log_info "Build them first with: cargo build --workspace --release"
        exit 1
    fi

    log_info "Installing release binaries"
    for binary in "${binaries[@]}"; do
        install -m 0755 "$release_dir/$binary" "$chroot_dir/usr/bin/$binary"
    done

    # Install systemd services
    log_info "Installing systemd services"
    mkdir -p "$chroot_dir/etc/systemd/system"
    cp "$PROJECT_ROOT/config/systemd/"*.service "$PROJECT_ROOT/config/systemd/"*.timer \
        "$chroot_dir/etc/systemd/system/"

    # Install configuration. The units point HIVE_CONFIG at
    # /etc/hive/config.toml; the tracked template for it is default.toml
    # (a config.toml in the source tree is a local, untracked override and
    # must not leak into the image).
    log_info "Installing configuration"
    mkdir -p "$chroot_dir/etc/hive"
    install -m 0644 "$PROJECT_ROOT/config/hive/default.toml" "$chroot_dir/etc/hive/config.toml"
    install -m 0644 "$PROJECT_ROOT/config/hive/whitelist.toml" "$chroot_dir/etc/hive/whitelist.toml"
    install -m 0644 "$PROJECT_ROOT/config/hive/rules.toml" "$chroot_dir/etc/hive/rules.toml"

    # hive-actuator runs unprivileged; polkit is what lets it control
    # services (within the rule's own ceiling - see the rules file).
    log_info "Installing polkit rules"
    mkdir -p "$chroot_dir/etc/polkit-1/rules.d"
    install -m 0644 "$PROJECT_ROOT/config/polkit/"*.rules "$chroot_dir/etc/polkit-1/rules.d/"

    # The exec audit rule hive-nerve-process reads commands from.
    log_info "Installing audit rules"
    mkdir -p "$chroot_dir/etc/audit/rules.d"
    install -m 0640 "$PROJECT_ROOT/config/audit/"*.rules "$chroot_dir/etc/audit/rules.d/"

    # Install knowledge base
    log_info "Installing knowledge base"
    mkdir -p "$chroot_dir/var/lib/hive/knowledge"
    cp -r "$PROJECT_ROOT/knowledge/"* "$chroot_dir/var/lib/hive/knowledge/"

    # Create hive users
    log_info "Creating system users"
    run_in_chroot "
        groupadd -r hive 2>/dev/null || true
        useradd -r -g hive -s /usr/sbin/nologin -d /nonexistent _hive-ai 2>/dev/null || true
        useradd -r -g hive -s /usr/sbin/nologin -d /nonexistent _hive-sense 2>/dev/null || true
        useradd -r -g hive -s /usr/sbin/nologin -d /nonexistent _hive-act 2>/dev/null || true
    "

    # Enable every shipped unit that has an [Install] section (enable only
    # creates symlinks, so it works in a chroot without a running systemd).
    # The rest are started by something else: hive-zfs-prune.service by its
    # timer.
    log_info "Enabling services"
    local units
    units=$(cd "$PROJECT_ROOT/config/systemd" && grep -l '^\[Install\]' *.service *.timer | xargs)
    run_in_chroot "systemctl enable $units"

    log_success "Hive Stack installed"
}

configure_serial_console() {
    log_step "Configuring serial console"

    # DruidOS is VM-first and terminal-only: the installed system's GRUB
    # menu should be reachable over a serial console too (Proxmox
    # `qm terminal`, `virsh console`, the lab harness). The kernel
    # console= arguments come from the ISO's GRUB command line instead
    # (see update_boot_config) - curtin carries everything after `---`
    # over into the installed system's GRUB_CMDLINE_LINUX_DEFAULT.
    local chroot_dir="$BUILD_DIR/chroot"
    mkdir -p "$chroot_dir/etc/default/grub.d"
    cat > "$chroot_dir/etc/default/grub.d/40-druidos-serial.cfg" << 'EOF'
GRUB_TERMINAL="console serial"
GRUB_SERIAL_COMMAND="serial --unit=0 --speed=115200"
EOF

    log_success "Serial console configured"
}

install_zfs() {
    log_step "Installing ZFS support"

    run_in_chroot "
        export DEBIAN_FRONTEND=noninteractive

        apt-get update
        apt-get install -y --no-install-recommends \
            zfsutils-linux \
            zfs-initramfs \
            || true

        apt-get clean
        rm -rf /var/lib/apt/lists/*
    "

    log_success "ZFS installed"
}

install_audit() {
    log_step "Installing the audit daemon"

    # auditd loads /etc/audit/rules.d/ at boot, including the Hive's exec
    # rule (installed by install_hive_stack) that hive-nerve-process reads
    # program executions from. Unlike ZFS this is not optional: without it
    # the nerve falls back to polling and misses short-lived commands.
    run_in_chroot "
        export DEBIAN_FRONTEND=noninteractive

        apt-get update
        apt-get install -y --no-install-recommends auditd

        apt-get clean
        rm -rf /var/lib/apt/lists/*
    "

    log_success "Audit daemon installed"
}

customize_branding() {
    log_step "Applying DruidOS branding"

    local chroot_dir="$BUILD_DIR/chroot"

    # OS release info
    cat > "$chroot_dir/etc/os-release" << 'EOF'
NAME="DruidOS"
VERSION="0.1.0"
ID=druidos
ID_LIKE=ubuntu
PRETTY_NAME="DruidOS 0.1.0"
VERSION_ID="0.1"
HOME_URL="https://druidos.org"
SUPPORT_URL="https://druidos.org/support"
BUG_REPORT_URL="https://github.com/druidos/druidos/issues"
LOGO=druidos
EOF

    # Issue
    cat > "$chroot_dir/etc/issue" << 'EOF'

  ____             _     __  ____  _____
 / __ \_______  __(_)___/ / / __ \/ ___/
/ / / / ___/ / / / / __  / / / / /\__ \
/ /_/ / /  / /_/ / / /_/ / / /_/ /___/ /
/_____/_/   \__,_/_/\__,_/  \____//____/

"The Swarm is watching. The Swarm is learning."

DruidOS \n \l

EOF

    # MOTD
    cat > "$chroot_dir/etc/motd" << 'EOF'
Welcome to DruidOS!

The Hive is active and monitoring your system.
'grove' is your shell — it's already running.

Documentation: /usr/share/doc/druidos/
Online: https://druidos.org/docs

EOF

    # Hostname
    echo "druidos" > "$chroot_dir/etc/hostname"

    log_success "Branding applied"
}

install_installer() {
    log_step "Installing DruidOS installer"

    local chroot_dir="$BUILD_DIR/chroot"

    # Copy installer binary if built (installer/ is a workspace member, so
    # it lands in the workspace's target/, not installer/target/)
    if [ -f "$PROJECT_ROOT/target/release/druidos-installer" ]; then
        install -m 0755 "$PROJECT_ROOT/target/release/druidos-installer" "$chroot_dir/usr/bin/"
    else
        log_warn "Installer not built. Run 'cargo build --workspace --release'"
    fi

    # Create installer launcher
    cat > "$chroot_dir/usr/bin/install-druidos" << 'EOF'
#!/bin/bash
if command -v druidos-installer &> /dev/null; then
    exec druidos-installer "$@"
else
    echo "DruidOS Installer"
    echo ""
    echo "The TUI installer is not available."
    echo "Please use the manual installation method:"
    echo ""
    echo "1. Partition your disk (fdisk/parted)"
    echo "2. Create ZFS pool: zpool create rpool /dev/sdX"
    echo "3. Create datasets: zfs create rpool/ROOT/druidos"
    echo "4. Install base system: debootstrap noble /mnt"
    echo "5. Copy DruidOS packages"
    echo ""
    echo "See: https://druidos.org/docs/installation"
fi
EOF
    chmod +x "$chroot_dir/usr/bin/install-druidos"

    log_success "Installer installed"
}

include_model() {
    if [ "$INCLUDE_MODEL" != "true" ]; then
        log_warn "Skipping the local model (INCLUDE_MODEL=false): hive-synapse will answer with mock suggestions"
        return 0
    fi

    log_step "Including the local model"

    local model_dir="$BUILD_DIR/chroot/var/lib/hive/models"
    mkdir -p "$MODEL_CACHE" "$model_dir"

    local entry name url sha256 cached
    for entry in "${MODEL_FILES[@]}"; do
        IFS='|' read -r name url sha256 <<< "$entry"
        cached="$MODEL_CACHE/$name"
        if ! echo "$sha256  $cached" | sha256sum --check --status 2>/dev/null; then
            log_info "Downloading $name"
            wget -q -O "$cached.part" "$url"
            mv "$cached.part" "$cached"
            if ! echo "$sha256  $cached" | sha256sum --check --status; then
                log_error "$name does not match its pinned sha256"
                exit 1
            fi
        fi
        install -m 0644 "$cached" "$model_dir/$name"
    done

    log_success "Local model included ($(du -sh "$model_dir" | cut -f1))"
}

rebuild_squashfs() {
    log_step "Rebuilding squashfs filesystem"

    local chroot_dir="$BUILD_DIR/chroot"
    local squashfs_path="$BUILD_DIR/iso/casper/filesystem.squashfs"

    # Remove old squashfs
    rm -f "$squashfs_path"

    # Create new squashfs
    mksquashfs "$chroot_dir" "$squashfs_path" \
        -comp xz \
        -b 1M \
        -Xdict-size 100% \
        -noappend

    # Update filesystem.size
    du -sx --block-size=1 "$chroot_dir" | cut -f1 > "$BUILD_DIR/iso/casper/filesystem.size"

    log_success "Squashfs rebuilt"
}

register_install_source() {
    log_step "Registering DruidOS as the installer's install source"

    # Subiquity (and curtin under it) installs whatever
    # casper/install-sources.yaml points at - the rebuilt
    # filesystem.squashfs is invisible to it otherwise, and the installer
    # would silently lay down stock Ubuntu Server. Make DruidOS the only
    # choice. The original Ubuntu layer squashfs files stay on the ISO: the
    # live installer environment itself is overlaid on top of them.
    #
    # type fsimage = one self-contained rootfs image (our merged chroot), as
    # opposed to fsimage-layered, which stacks on lower layers by filename.
    local casper_dir="$BUILD_DIR/iso/casper"
    local size
    size=$(cat "$casper_dir/filesystem.size")

    cat > "$casper_dir/install-sources.yaml" << EOF
- default: true
  description:
    en: Ubuntu Server base with the DruidOS Hive Stack preinstalled.
  id: druidos
  locale_support: locale-only
  name:
    en: DruidOS
  path: filesystem.squashfs
  size: $size
  type: fsimage
  variant: server
EOF

    log_success "Install source registered (id: druidos, $size bytes)"
}

configure_installer_defaults() {
    log_step "Configuring installer defaults (ZFS root)"

    # DruidOS installs onto ZFS by default: the Hive snapshots the system
    # before changing packages, and refuses to change them without one.
    # Subiquity's own storage screen offers only LVM or a plain partition,
    # and ignores an autoinstall layout for its defaults when interactive -
    # so the default install answers storage itself (ZFS on the largest
    # disk) and keeps every other screen interactive. The installer still
    # asks "Confirm destructive action" before touching the disk. Subiquity
    # picks this file up from the ISO root (/cdrom/autoinstall.yaml); it is
    # never a full autoinstall (no `autoinstall` on the kernel command line).
    local iso_dir="$BUILD_DIR/iso"
    cat > "$iso_dir/autoinstall.yaml" << 'EOF'
# DruidOS installer defaults - see scripts/build-iso.sh
autoinstall:
  version: 1
  interactive-sections:
    - locale
    - refresh-installer
    - keyboard
    - source
    - network
    - proxy
    - apt
    - identity
    - ubuntu-pro
    - ssh
    - snaps
  storage:
    layout:
      name: zfs
EOF

    # The "choose storage yourself" boot entry (see update_boot_config):
    # the stock fully interactive installer - LVM, plain ext4, manual
    # partitioning. No ZFS there, so no safety snapshots either.
    mkdir -p "$iso_dir/druidos"
    cat > "$iso_dir/druidos/manual-storage.yaml" << 'EOF'
# DruidOS installer, storage chosen by hand - see scripts/build-iso.sh
autoinstall:
  version: 1
  interactive-sections:
    - "*"
EOF

    log_success "Installer defaults: ZFS on the whole disk (manual storage in the boot menu)"
}

update_boot_config() {
    log_step "Updating boot configuration"

    local iso_dir="$BUILD_DIR/iso"
    local grub_cfg="$iso_dir/boot/grub/grub.cfg"

    # Update GRUB config
    if [ -f "$grub_cfg" ]; then
        sed -i 's/Ubuntu/DruidOS/g' "$grub_cfg"
        sed -i 's/ubuntu/druidos/g' "$grub_cfg"

        # Serial console: GRUB menu on both screen and ttyS0, and the kernel
        # on both (tty0 last, so it stays /dev/console and the installer
        # still comes up on the normal screen). Args after `---` are also
        # carried into the installed system by curtin.
        sed -i '1i serial --unit=0 --speed=115200\nterminal_input console serial\nterminal_output console serial\n' "$grub_cfg"
        sed -i -E 's|^(\s*linux\s+\S+\s+---)\s*$|\1 console=ttyS0,115200n8 console=tty0|' "$grub_cfg"

        # The default entry installs onto ZFS (configure_installer_defaults);
        # a second one keeps the stock storage screen for anyone who wants
        # LVM, ext4 or their own partitions. Installer-only arguments go
        # before `---` - after it they'd be carried into the installed system.
        sed -i 's/^menuentry "Try or Install DruidOS Server" {/menuentry "Try or Install DruidOS Server (ZFS)" {/' "$grub_cfg"
        awk '
            { print }
            !added && /^}/ {
                print "menuentry \"Install DruidOS Server - choose storage yourself (no ZFS snapshots)\" {"
                print "\tset gfxpayload=keep"
                print "\tlinux\t/casper/vmlinuz subiquity.autoinstallpath=/cdrom/druidos/manual-storage.yaml --- console=ttyS0,115200n8 console=tty0"
                print "\tinitrd\t/casper/initrd"
                print "}"
                added = 1
            }' "$grub_cfg" > "$grub_cfg.new"
        mv "$grub_cfg.new" "$grub_cfg"
    fi

    # Update isolinux config (legacy BIOS)
    if [ -f "$iso_dir/isolinux/txt.cfg" ]; then
        sed -i 's/Ubuntu/DruidOS/g' "$iso_dir/isolinux/txt.cfg"
    fi

    log_success "Boot configuration updated"
}

create_iso() {
    log_step "Creating ISO image"

    local iso_dir="$BUILD_DIR/iso"
    local output_iso="$OUTPUT_DIR/$ISO_NAME"
    local base_iso="$BUILD_DIR/base.iso"

    # Generate MD5 sums
    cd "$iso_dir"
    find . -type f -exec md5sum {} \; > md5sum.txt 2>/dev/null || true
    cd - > /dev/null

    # Ubuntu 24.04's Server ISO boots via GRUB2 + a hybrid MBR/GPT layout
    # with an *appended* (not file-tree-visible) EFI system partition -
    # not the older isolinux+isohybrid scheme this used to assume. That
    # old path silently fell through to a completely boot-less fallback
    # whenever /usr/lib/ISOLINUX/isohdpfx.bin didn't exist (it doesn't on
    # a plain Debian/Ubuntu box without the isolinux package), producing
    # an ISO with no El Torito boot catalog at all ("No bootable device"
    # in a VM). Fix: ask xorriso to report the exact boot-image recipe it
    # used for the original base.iso, and replay those same flags against
    # our rebuilt file tree. Re-derived every build (not hardcoded)
    # because the byte offsets it contains are specific to this exact
    # base ISO and shift between Ubuntu point releases.
    if [ ! -f "$base_iso" ]; then
        log_error "base.iso not found at $base_iso - can't derive the boot image layout"
        exit 1
    fi

    local -a boot_args=()
    while IFS= read -r line; do
        # Skip the volume-id/mod-date lines - we set our own -V below.
        case "$line" in
            -V\ *|--modification-date=*|"") continue ;;
        esac
        eval "boot_args+=($line)"
    done < <(xorriso -indev "$base_iso" -report_el_torito as_mkisofs 2>/dev/null)

    if [ ${#boot_args[@]} -eq 0 ]; then
        log_error "Could not derive a boot image recipe from $base_iso"
        exit 1
    fi

    xorriso -as mkisofs \
        -r -V "$VOLUME_ID" \
        -o "$output_iso" \
        -J -joliet-long \
        "${boot_args[@]}" \
        "$iso_dir"

    log_success "ISO created: $output_iso"

    # Show ISO info
    echo ""
    echo "ISO Details:"
    echo "============"
    ls -lh "$output_iso"
    echo ""
    echo "SHA256: $(sha256sum "$output_iso" | cut -d' ' -f1)"
}

cleanup() {
    log_step "Cleaning up"

    cleanup_chroot
    # Optionally remove build directory
    # rm -rf "$BUILD_DIR"

    log_success "Cleanup complete"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Build a bootable DruidOS ISO image.

Options:
    -o, --output DIR      Output directory (default: ./output)
    -n, --name NAME       ISO filename (default: druidos-0.1.0-amd64.iso)
    -m, --include-model   Include AI model in ISO (increases size by ~500MB)
    -b, --build-dir DIR   Build directory (default: /tmp/druidos-iso-build)
    -c, --clean           Clean build directory before starting
    -h, --help            Show this help message

Environment Variables:
    BUILD_DIR            Override build directory
    OUTPUT_DIR           Override output directory
    ISO_NAME             Override ISO filename
    INCLUDE_MODEL        'false' to leave out the local model (default: true)
    MODEL_CACHE          Where the model is downloaded to once (default: BUILD_DIR/models)

Examples:
    sudo $(basename "$0")                          # Build standard ISO
    sudo $(basename "$0") --include-model          # Include AI model
    sudo $(basename "$0") -o /path/to/output       # Custom output directory

Requirements:
    - Root privileges
    - ~15GB free disk space
    - Internet connection (for base ISO download)
    - Packages: xorriso, squashfs-tools, genisoimage, wget

EOF
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -n|--name)
                ISO_NAME="$2"
                shift 2
                ;;
            -m|--include-model)
                INCLUDE_MODEL="true"
                shift
                ;;
            -b|--build-dir)
                BUILD_DIR="$2"
                shift 2
                ;;
            -c|--clean)
                rm -rf "$BUILD_DIR"
                shift
                ;;
            -h|--help)
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

    print_banner

    # Trap for cleanup on exit
    trap cleanup EXIT

    check_dependencies
    check_disk_space
    setup_build_dirs
    download_base_iso
    extract_iso
    extract_squashfs
    prepare_chroot

    # Customization
    install_zfs
    install_audit
    install_hive_stack
    install_installer
    configure_serial_console
    customize_branding
    include_model

    # Cleanup chroot before rebuilding
    cleanup_chroot

    # Build ISO
    rebuild_squashfs
    register_install_source
    configure_installer_defaults
    update_boot_config
    create_iso

    echo ""
    log_success "DruidOS ISO build complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Test in VM: qemu-system-x86_64 -cdrom $OUTPUT_DIR/$ISO_NAME -m 4G"
    echo "  2. Write to USB: sudo dd if=$OUTPUT_DIR/$ISO_NAME of=/dev/sdX bs=4M status=progress"
    echo ""
}

main "$@"
