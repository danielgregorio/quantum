#!/usr/bin/env python
"""Expressions drawn from the grammar, run by the interpreter and by the Rust engine's machine (PLAN_WORLD_ENGINE.md,
E2): how many agree, and the first that do not.

    python scripts/bytecode-fuzz.py --draws 1000000 --seed 1

Each draw is an expression of the Core's operators and stdlib over a context of numbers, texts (numeric ones too),
lists, records, true, false and null (tests/gameserver/test_gameserver_bytecode.py's Drawer). Two kinds are told
apart and counted, not compared: a whole number past 64 bits (Python's have no end, the engine's are 64 bits) and a
complex number ((-8) ** 0.5 is one to Python; no world keeps it). Needs the engine (pip install ./native/world).
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / 'tests' / 'gameserver')]

import test_gameserver_bytecode as bytecode_tests  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--draws', type=int, default=1_000_000)
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    began = time.monotonic()
    differences, tally = bytecode_tests.draw(args.draws, args.seed)
    print(json.dumps({'draws': args.draws, 'seed': args.seed, 'seconds': round(time.monotonic() - began),
                      'differences': len(differences), **tally}, indent=2))
    for expression, context, theirs, mine in differences[:10]:
        print(f'{expression}\n  context:     {context}\n  interpreter: {theirs}\n  machine:     {mine}')
    return 1 if differences else 0


if __name__ == '__main__':
    raise SystemExit(main())
