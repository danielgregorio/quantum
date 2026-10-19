#!/usr/bin/env bash
# DruidOS ISO lab - Forge side. Invoked over SSH by scripts/lab/lab.sh (which
# syncs the working tree first); can also be run by hand on Forge:
#
#   bash ~/druidos-test/scripts/lab/remote.sh <stage> [args]
#
# Every stage runs in a *detached* container so a dropped SSH session can't
# kill a 30-minute ISO build; `attach` re-follows it later. When a stage
# container finishes, its logs and exit code are saved into its run dir
# (~/druidos-lab/runs/<id>/<stage>.log|.exit) and the container is removed.
set -euo pipefail

SRC="$HOME/druidos-test"
LAB="$HOME/druidos-lab"
LAB_IMAGE=druidos-lab
BUILD_IMAGE=druidos-test
ISO_NAME=druidos-hive-amd64.iso
ISO="$LAB/iso/$ISO_NAME"
PREFIX=druidos-lab-

mkdir -p "$LAB/build" "$LAB/iso" "$LAB/runs"

log() {
    printf '[lab] %s\n' "$*"
}

new_run_dir() { # stage
    local id
    id="$(date +%Y%m%d-%H%M%S)-$1"
    mkdir -p "$LAB/runs/$id"
    ln -sfn "$id" "$LAB/runs/latest"
    echo "$LAB/runs/$id"
}

# Save a finished stage container's logs + exit code into its run dir, then
# remove it. Prints the exit code.
reap() { # container
    local name=$1 run_dir stage code
    run_dir=$(docker inspect -f '{{index .Config.Labels "lab.run_dir"}}' "$name")
    stage=$(docker inspect -f '{{index .Config.Labels "lab.stage"}}' "$name")
    code=$(docker inspect -f '{{.State.ExitCode}}' "$name")
    docker logs "$name" > "$run_dir/$stage.log" 2>&1 || true
    echo "$code" > "$run_dir/$stage.exit"
    docker rm "$name" > /dev/null
    echo "$code"
}

# Stage containers that finished while nobody was following them (SSH drop).
reap_finished() {
    local name
    for name in $(docker ps -a --filter "name=^$PREFIX" --filter status=exited --format '{{.Names}}'); do
        log "saved logs of $name, which finished unattended (exit $(reap "$name"))"
    done
}

follow() { # container - returns the container's exit code
    local name=$1 code
    docker logs -f "$name" 2>&1 || true
    docker wait "$name" > /dev/null
    code=$(reap "$name")
    log "$name finished with exit code $code"
    return "$code"
}

start_stage() { # stage run_dir docker-run-args... (image + command last)
    local stage=$1 run_dir=$2 name="$PREFIX$1"
    shift 2
    reap_finished
    if docker ps --filter "name=^$name\$" --format '{{.Names}}' | grep -q .; then
        log "$name is already running - use: lab.sh attach $stage"
        exit 3
    fi
    log "stage $stage -> $run_dir"
    docker run -d --name "$name" \
        --label "lab.stage=$stage" --label "lab.run_dir=$run_dir" \
        "$@" > /dev/null
    follow "$name"
}

stage_image() {
    log "building $BUILD_IMAGE image"
    docker build -q -t "$BUILD_IMAGE" -f "$SRC/scripts/forge-test.Dockerfile" "$SRC/scripts"
    log "building $LAB_IMAGE image"
    docker build -q -t "$LAB_IMAGE" -f "$SRC/scripts/lab/lab.Dockerfile" "$SRC/scripts/lab"
}

stage_build() {
    local run_dir
    run_dir=$(new_run_dir build)
    start_stage build "$run_dir" \
        -v "$SRC:/app" -w /app \
        -v druidos-cargo-registry:/usr/local/cargo/registry \
        -v druidos-cargo-git:/usr/local/cargo/git \
        "$BUILD_IMAGE" cargo build --workspace --release
}

stage_iso() {
    local run_dir
    run_dir=$(new_run_dir iso)
    # Build into a staging dir and only move the result into place on
    # success, so a boot stage never picks up a half-written ISO. The base
    # Ubuntu ISO stays cached in $LAB/build across runs.
    start_stage iso "$run_dir" --privileged \
        -v "$SRC:/app" -v "$LAB:/lab" \
        -e BUILD_DIR=/lab/build -e OUTPUT_DIR=/lab/iso/.staging -e ISO_NAME="$ISO_NAME" \
        -e MODEL_CACHE=/lab/cache/models \
        "$LAB_IMAGE" bash -c '
            set -euo pipefail
            rm -rf "$OUTPUT_DIR"
            bash /app/scripts/build-iso.sh
            cd "$OUTPUT_DIR"
            sha256sum "$ISO_NAME" > "$ISO_NAME.sha256"
            mv -f "$ISO_NAME" "$ISO_NAME.sha256" /lab/iso/'
    cp "$ISO.sha256" "$run_dir/"
}

stage_boot() { # [firmware list]
    local firmware=${1:-bios,uefi} run_dir
    if [ ! -f "$ISO" ]; then
        log "no ISO at $ISO - run the iso stage first"
        exit 1
    fi
    run_dir=$(new_run_dir boot)
    cp "$ISO.sha256" "$run_dir/" 2> /dev/null || true
    start_stage boot "$run_dir" --device /dev/kvm \
        -v "$SRC:/app:ro" -v "$LAB:/lab" \
        "$LAB_IMAGE" python3 -u /app/scripts/lab/harness.py boot-smoke \
        --iso "/lab/iso/$ISO_NAME" --firmware "$firmware" \
        --out "/lab/runs/$(basename "$run_dir")/boot"
}

# Golden installed disk for the current ISO + firmware (lab-relative path):
# golden/<first 16 hex of the ISO's sha256>-<firmware>-zfs. Keyed by ISO hash
# so a rebuilt ISO never gets tested against a disk installed from an older
# one; -zfs because the lab installs with the ZFS root layout (harness.py
# install --storage), which is what DruidOS's snapshots need.
golden_rel() { # firmware
    echo "golden/$(cut -c1-16 "$ISO.sha256")-$1-zfs"
}

require_iso() {
    if [ ! -f "$ISO" ] || [ ! -f "$ISO.sha256" ]; then
        log "no ISO at $ISO - run the iso stage first"
        exit 1
    fi
}

stage_install() { # [firmware]
    local firmware=${1:-uefi} run_dir golden
    require_iso
    golden=$(golden_rel "$firmware")
    run_dir=$(new_run_dir install)
    cp "$ISO.sha256" "$run_dir/"
    mkdir -p "$LAB/golden"
    start_stage install "$run_dir" --device /dev/kvm \
        -v "$SRC:/app:ro" -v "$LAB:/lab" \
        "$LAB_IMAGE" python3 -u /app/scripts/lab/harness.py install \
        --iso "/lab/iso/$ISO_NAME" --firmware "$firmware" \
        --out "/lab/runs/$(basename "$run_dir")/install" \
        --golden "/lab/$golden"
}

# The production install path: the ISO driven through its own UI with the
# default answers (no autoinstall seed), then the installed disk booted.
stage_install_interactive() { # [firmware] [harness options, e.g. --grub-entry 1]
    local firmware=${1:-uefi} run_dir
    shift || true
    require_iso
    run_dir=$(new_run_dir install-interactive)
    cp "$ISO.sha256" "$run_dir/"
    start_stage install-interactive "$run_dir" --device /dev/kvm \
        -v "$SRC:/app:ro" -v "$LAB:/lab" \
        "$LAB_IMAGE" python3 -u /app/scripts/lab/harness.py install-interactive \
        --iso "/lab/iso/$ISO_NAME" --firmware "$firmware" \
        --out "/lab/runs/$(basename "$run_dir")/install-interactive" "$@"
}

stage_test() { # [firmware] [hotswap]
    local firmware=${1:-uefi} hotswap=${2:-} run_dir golden
    require_iso
    golden=$(golden_rel "$firmware")
    if [ ! -f "$LAB/$golden/disk.qcow2" ]; then
        log "no installed disk for this ISO yet ($LAB/$golden) - running install first"
        stage_install "$firmware"
    fi
    run_dir=$(new_run_dir test)
    cp "$ISO.sha256" "$run_dir/"
    start_stage test "$run_dir" --device /dev/kvm \
        -v "$SRC:/app:ro" -v "$LAB:/lab" \
        "$LAB_IMAGE" python3 -u /app/scripts/lab/harness.py e2e \
        --golden "/lab/$golden" --firmware "$firmware" \
        --out "/lab/runs/$(basename "$run_dir")/e2e" \
        ${hotswap:+--hotswap /app}
}

stage_exec() { # firmware hotswap(yes|no) base64-command
    local firmware=$1 hotswap=$2 cmd run_dir golden
    cmd=$(echo "$3" | base64 -d)
    require_iso
    golden=$(golden_rel "$firmware")
    run_dir=$(new_run_dir exec)
    # Short and interactive: runs in the foreground, not as a detached stage.
    docker run --rm --device /dev/kvm \
        -v "$SRC:/app:ro" -v "$LAB:/lab" \
        "$LAB_IMAGE" python3 -u /app/scripts/lab/harness.py exec \
        --golden "/lab/$golden" --firmware "$firmware" \
        --out "/lab/runs/$(basename "$run_dir")/exec" \
        $([ "$hotswap" = yes ] && echo "--hotswap /app") \
        "$cmd"
}

stage_attach() { # [stage]
    local names name
    reap_finished
    names=$(docker ps --filter "name=^$PREFIX${1:-}" --format '{{.Names}}')
    if [ -z "$names" ]; then
        log "nothing running"
        return 0
    fi
    for name in $names; do
        follow "$name"
    done
}

stage_status() {
    local d f result
    reap_finished
    echo "running:"
    docker ps --filter "name=^$PREFIX" --format '  {{.Names}} ({{.Status}})'
    echo "iso:"
    if [ -f "$ISO" ]; then
        echo "  $(date -r "$ISO" '+%F %T')  $(cut -d' ' -f1 "$ISO.sha256" 2> /dev/null)"
    else
        echo "  (none)"
    fi
    echo "recent runs:"
    for d in $(ls -1t "$LAB/runs" | grep -v '^latest$' | head -n 10); do
        result=""
        for f in "$LAB/runs/$d"/*.exit; do
            [ -f "$f" ] && result+="$(basename "$f" .exit)=exit $(cat "$f") "
        done
        echo "  $d  ${result:-(running or interrupted)}"
    done
}

stage_prune() { # [keep]
    local keep=${1:-20} old stale="" current=""
    old=$(ls -1t "$LAB/runs" | grep -v '^latest$' | tail -n +$((keep + 1)) || true)
    # Golden disks (~4GB each) installed from an ISO other than the current one.
    [ -f "$ISO.sha256" ] && current=$(cut -c1-16 "$ISO.sha256")
    if [ -d "$LAB/golden" ]; then
        stale=$(ls -1 "$LAB/golden" | grep -v "^$current-" || true)
    fi
    if [ -z "$old" ] && [ -z "$stale" ]; then
        log "nothing to prune"
        return 0
    fi
    # Both hold root-owned files written by the stage containers.
    # shellcheck disable=SC2086
    docker run --rm -v "$LAB:/lab" -w /lab "$LAB_IMAGE" rm -rf \
        $(for r in $old; do echo "runs/$r"; done) \
        $(for g in $stale; do echo "golden/$g"; done)
    log "pruned $(echo "$old" | grep -c . || true) run(s), $(echo "$stale" | grep -c . || true) stale golden disk(s)"
}

stage=${1:-help}
shift || true

case "$stage" in
    image) stage_image ;;
    build) stage_build ;;
    iso) stage_iso ;;
    boot) stage_boot "$@" ;;
    install) stage_install "$@" ;;
    install-interactive) stage_install_interactive "$@" ;;
    test) stage_test "$@" ;;
    exec) stage_exec "$@" ;;
    attach) stage_attach "$@" ;;
    status) stage_status ;;
    prune) stage_prune "$@" ;;
    *)
        echo "usage: remote.sh image|build|iso|boot [bios,uefi]|install [uefi|bios]|install-interactive [uefi|bios]|test [uefi|bios] [hotswap]|attach [stage]|status|prune [keep]"
        exit 2
        ;;
esac
