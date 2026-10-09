"""The expression compiler agrees with the Core evaluator, in Godot.

A game whose scene sets one variable per expression as it is entered is
built, replayed for a tick, and its state compared with what
quantum/core/expressions.py computes for the same expressions — the
conformance table of PLAN_GAMES_2.md, run by the real engine.
"""

import json

import pytest

from quantum.core.expressions import ExpressionEvaluator
from quantum.runtime.godot_replay import replay

CONTEXT = {'coins': 7, 'lives': 3, 'ratio': 2.5, 'word': 'hopper', 'items': [1, 2, 3, 4], 'empty': [],
           'bag': {'a': 1, 'b': 2}}

EXPRESSIONS = [
    'coins + 1', 'coins - lives', 'coins * ratio', 'coins / 2', 'coins // 2', 'coins % 4', '-coins % 4',
    'coins ** 2', '-coins', 'coins > 1 and lives < 5', 'not (coins == 7) or true', '1 < lives <= 3',
    'coins if lives else 0', 'len(word)', 'len(items)', 'len(bag)', 'max(coins, 10)', 'min(coins, 10)',
    'abs(-ratio)', 'round(ratio)', 'floor(ratio)', 'ceil(ratio)', 'int(ratio)', 'float(coins)', 'str(coins)',
    "word + '!'", "'p' in word", "2 in items", "9 not in items", "'a' in bag", 'items[0]', 'items[-1]',
    'items[1:3]', 'items[:2]', 'items[2:]', 'items[-2:]', 'items[5:9]', 'word[0:3]', 'word[3:]', 'word[-2:]',
    'bag.a + bag.b', '[coins, lives]', 'empty', 'coins == 7.0', 'ratio * 2 == 5',
]


def gd_value(v):
    """What GDScript's JSON makes of the Core value (every number is a float)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return float(v)
    if isinstance(v, list):
        return [gd_value(x) for x in v]
    return v


@pytest.fixture(scope='module')
def built(godot, tmp_path_factory):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    sets = '\n'.join(f'      <q:set name="r{i}" value="{{{e}}}" />' for i, e in enumerate(EXPRESSIONS))
    declares = '\n'.join(f'    <q:set name="r{i}" value="" />' for i in range(len(EXPRESSIONS)))
    ctx = '\n'.join(f'    <q:set name="{k}" value="{json.dumps(v) if not isinstance(v, str) else v}" '
                    f'type="{"array" if isinstance(v, (list, dict)) else "number" if isinstance(v, (int, float)) else "string"}" />'
                    for k, v in CONTEXT.items() if not isinstance(v, dict))
    source = f'''<q:application id="expr" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:scene name="main">
{ctx}
    <q:set name="bag" value="" />
{declares}
    <q:if condition="{{true}}">
      <q:set name="bag" value="{{{{'a': 1, 'b': 2}}}}" />
{sets}
    </q:if>
  </qg:scene>
</q:application>
'''
    src = tmp_path_factory.mktemp('expr') / 'expr.q'
    src.write_text(source, encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(src))
    from pathlib import Path
    out = compile_game(app, str(src.parent / 'godot'), source_dir=str(Path(__file__).resolve().parents[2]))
    return replay(out, 1, binary=godot)['main']


@pytest.mark.parametrize('i,expression', list(enumerate(EXPRESSIONS)), ids=EXPRESSIONS)
def test_godot_computes_what_the_core_evaluator_computes(built, i, expression):
    expected = ExpressionEvaluator().evaluate(expression, dict(CONTEXT))
    assert built[f'r{i}'] == gd_value(expected)
