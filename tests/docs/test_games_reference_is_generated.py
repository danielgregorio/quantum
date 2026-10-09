"""docs/targets/games.md is generated from the game schema and the three games, and committed as generated.

scripts/generate-games-reference.py writes the page from
quantum/runtime/godot/schema.py (the table the compiler validates against)
and the sources of projects/hopper, keep and drift. A page edited by hand, a
tag added to the schema, or a game changed without regenerating fails here:
run `python scripts/generate-games-reference.py`.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        'generate_games_reference', REPO / 'scripts' / 'generate-games-reference.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_games_page_is_current():
    gen = generator()
    assert gen.OUT.read_text(encoding='utf-8') == gen.build(), (
        'docs/targets/games.md is stale: run python scripts/generate-games-reference.py')


def test_every_tag_of_the_schema_is_on_the_page():
    from quantum.runtime.godot.schema import TAGS
    text = (REPO / 'docs' / 'targets' / 'games.md').read_text(encoding='utf-8')
    missing = [t for t in TAGS if f'### `qg:{t}`' not in text]
    assert not missing, missing
