#!/usr/bin/env bash
# Sync the current working tree (including uncommitted changes) to the
# Forge homelab host and run scripts/check.sh there inside a prebuilt Rust
# container. Native Linux, no WSL, no local cross-compile toolchain needed.
#
# Requires: `forge` configured in ~/.ssh/config (key auth, no password).
set -euo pipefail

REMOTE=forge
REMOTE_DIR=druidos-test
IMAGE=druidos-test

bash "$(dirname "${BASH_SOURCE[0]}")/forge-sync.sh"

ssh "$REMOTE" "docker build -q -t $IMAGE -f $REMOTE_DIR/scripts/forge-test.Dockerfile $REMOTE_DIR/scripts"

ssh "$REMOTE" "docker run --rm \
    -v \$HOME/$REMOTE_DIR:/app \
    -v druidos-cargo-registry:/usr/local/cargo/registry \
    -v druidos-cargo-git:/usr/local/cargo/git \
    $IMAGE bash scripts/check.sh"
