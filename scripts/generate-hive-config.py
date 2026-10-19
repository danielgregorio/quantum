#!/usr/bin/env python
"""Write os/config/hive/rules.toml and whitelist.toml from os/config/hive/hive.q. Never by hand.

    python scripts/generate-hive-config.py          # rewrite both files
    python scripts/generate-hive-config.py --check  # exit 1 when either is stale

hive.q is the Hive's rules in Quantum (quantum/runtime/hive): what
hive-synapse offers on an event, and what hive-actuator may do. The two
TOML files are what the daemons load; they are committed as generated, and
tests/hive/test_hive_config_is_generated.py fails when they are not this
script's output. hive-synapse embeds rules.toml as its built-in rules.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantum.core.parser import QuantumParser  # noqa: E402
from quantum.runtime.hive import read_hive, rules_toml, whitelist_toml  # noqa: E402

SOURCE = REPO / 'os' / 'config' / 'hive' / 'hive.q'
OUT = SOURCE.parent


def build() -> dict:
    """{file name: its text}, from hive.q."""
    hive = read_hive(QuantumParser(use_cache=False).parse_file(str(SOURCE)))
    return {'rules.toml': rules_toml(hive), 'whitelist.toml': whitelist_toml(hive)}


def main() -> int:
    files = build()
    if '--check' in sys.argv:
        stale = [name for name, text in files.items()
                 if not (OUT / name).is_file() or (OUT / name).read_text(encoding='utf-8') != text]
        if stale:
            print(f'stale: {", ".join(stale)} (run python scripts/generate-hive-config.py)')
            return 1
        print('os/config/hive/rules.toml and whitelist.toml are current')
        return 0
    for name, text in files.items():
        (OUT / name).write_text(text, encoding='utf-8')
        print(f'wrote {(OUT / name).relative_to(REPO)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
