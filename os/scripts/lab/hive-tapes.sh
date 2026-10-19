#!/usr/bin/env bash
# Plays every tape of the Hive lab (crates/hive-lab/tapes/): the real
# hive-cortex and hive-synapse, with the nerves, the actuator, grove and the
# dashboard played by hive-lab. Seconds, no VM, no ISO.
#
# The lab needs root for its private mount namespace (its users never touch
# this machine's /etc/passwd); this script uses sudo when it is not root.
set -euo pipefail
cd "$(dirname "$0")/../.."

cargo build --workspace --bins --quiet
run=(target/debug/hive-lab)
[ "$(id -u)" = 0 ] || run=(sudo target/debug/hive-lab)

failed=0
for tape in crates/hive-lab/tapes/*.jsonl; do
  start=$(date +%s%N)
  if out=$("${run[@]}" --play "$tape" 2>&1); then
    echo "ok    $(basename "$tape")  $(( ($(date +%s%N) - start) / 1000000 )) ms"
  else
    echo "FAIL  $(basename "$tape")"
    echo "$out" | grep '"ok":false' || echo "$out" | tail -5
    failed=1
  fi
done
exit $failed
