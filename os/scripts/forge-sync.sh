#!/usr/bin/env bash
# Ship the current working tree (including uncommitted changes) to the Forge
# homelab host. Shared by scripts/test-on-forge.sh and scripts/lab/lab.sh.
#
# Requires: `forge` configured in ~/.ssh/config (key auth, no password).
set -euo pipefail

REMOTE=${REMOTE:-forge}
REMOTE_DIR=${REMOTE_DIR:-druidos-test}

cd "$(dirname "${BASH_SOURCE[0]}")/.."

ssh "$REMOTE" "mkdir -p $REMOTE_DIR"

git ls-files -z --cached --others --exclude-standard \
    | tar --null -T - -czf - \
    | ssh "$REMOTE" "tar xzf - -C $REMOTE_DIR"

# .gitattributes marks *.sh/*.py as eol=lf, but a Windows checkout with
# core.autocrlf=true still checks them out CRLF in the working tree (the
# committed blob is clean LF - only the local checkout is affected). The
# tar pipe above ships that working-tree copy as-is, so normalize on
# arrival rather than fighting autocrlf (never touch git config here).
ssh "$REMOTE" "find $REMOTE_DIR -path $REMOTE_DIR/target -prune -o \
    \( -name '*.sh' -o -name '*.py' \) -type f -exec sed -i 's/\r\$//' {} +"
