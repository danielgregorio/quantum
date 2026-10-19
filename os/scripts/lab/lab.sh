#!/usr/bin/env bash
# DruidOS ISO lab: build ISOs and boot/test them under QEMU+KVM on Forge.
#
#   scripts/lab/lab.sh <stage> [args]
#
# Stages (all execute on Forge, see scripts/lab/remote.sh):
#   sync               ship the working tree (incl. uncommitted edits) to Forge
#   image              (re)build the druidos-test and druidos-lab Docker images
#   build              cargo build --workspace --release
#   iso                scripts/build-iso.sh -> ~/druidos-lab/iso/ on Forge
#   boot [bios,uefi]   smoke-boot the ISO under KVM until the installer UI shows
#   install [uefi|bios] unattended install to a fresh disk, boot it, SSH in,
#                      keep it as the golden disk for this ISO
#   install-interactive [uefi|bios]
#                      install through the ISO's own UI with default answers
#                      (the production path), boot it, check its root fs
#   test [uefi|bios] [hotswap]
#                      boot an overlay of the golden disk, run the e2e checks
#                      (installs first if this ISO has no golden disk yet);
#                      hotswap = push current release binaries + units first
#   dev [uefi|bios]    fast loop for Rust/unit changes: sync, build, test hotswap
#   exec [--hotswap] 'CMD'
#                      boot a throwaway copy of the installed system, run CMD
#                      as root, print its output (poke at a real install)
#   all                sync, image, build, iso, boot, install-interactive, install, test
#   attach [stage]     re-follow a stage still running (e.g. after SSH dropped)
#   status             running stages, current ISO, recent runs + exit codes
#   fetch [run]        copy a run's evidence to qemu-workspace/runs/ (default: latest)
#   prune [keep]       delete all but the newest N runs (default 20) and golden
#                      disks installed from ISOs other than the current one
#
# Stages that use the source tree sync it first; LAB_NO_SYNC=1 skips that.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
REMOTE=${REMOTE:-forge}

remote() {
    ssh "$REMOTE" "bash druidos-test/scripts/lab/remote.sh $*"
}

sync_tree() {
    [ "${LAB_NO_SYNC:-}" = 1 ] || bash "$PROJECT_ROOT/scripts/forge-sync.sh"
}

stage=${1:-help}
shift || true

case "$stage" in
    sync)
        bash "$PROJECT_ROOT/scripts/forge-sync.sh"
        ;;
    image|build|iso|boot|install|install-interactive|test)
        sync_tree
        remote "$stage" "$@"
        ;;
    dev)
        sync_tree
        remote build
        remote test "${1:-uefi}" hotswap
        ;;
    exec)
        hotswap=no
        if [ "${1:-}" = --hotswap ]; then
            hotswap=yes
            shift
        fi
        [ $# -eq 1 ] || { echo "usage: lab.sh exec [--hotswap] 'command'" >&2; exit 2; }
        sync_tree
        # base64: the command survives the local shell, ssh and remote shell intact.
        remote exec uefi "$hotswap" "$(printf '%s' "$1" | base64 -w0)"
        ;;
    all)
        sync_tree
        for s in image build iso boot install-interactive install test; do
            remote "$s"
        done
        ;;
    attach|status|prune)
        remote "$stage" "$@"
        ;;
    fetch)
        run=$(ssh "$REMOTE" "cd druidos-lab/runs && basename \"\$(readlink -f '${1:-latest}')\"")
        mkdir -p "$PROJECT_ROOT/qemu-workspace/runs"
        scp -rq "$REMOTE:druidos-lab/runs/$run" "$PROJECT_ROOT/qemu-workspace/runs/"
        echo "$PROJECT_ROOT/qemu-workspace/runs/$run"
        ;;
    *)
        # Print this file's header comment.
        awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
        [ "$stage" = help ]
        ;;
esac
