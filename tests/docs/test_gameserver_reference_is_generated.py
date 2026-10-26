"""docs/targets/gameserver.md is generated from the game server's schema, and committed as generated.

scripts/generate-gameserver-reference.py writes the page from quantum/runtime/gameserver/schema.py (the table a world
is read against), the functions of rules.py, the server's protocol and the world of the tests. A page edited by
hand, or a tag added without regenerating, fails here: run `python scripts/generate-gameserver-reference.py`.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        'generate_gameserver_reference', REPO / 'scripts' / 'generate-gameserver-reference.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_gameserver_page_is_current():
    gen = generator()
    assert gen.OUT.read_text(encoding='utf-8') == gen.build(), (
        'docs/targets/gameserver.md is stale: run python scripts/generate-gameserver-reference.py')


def test_every_tag_and_function_is_on_the_page():
    """Every tag of the schema, and every function a world's expressions have besides the Core's stdlib."""
    from quantum.core.expression_stdlib import STDLIB
    from quantum.core.parser import QuantumParser
    from quantum.runtime.gameserver import World, read_world
    from quantum.runtime.gameserver.rules import FUNCTION_DOCS
    from quantum.runtime.gameserver.schema import TAGS
    yard = REPO / 'tests' / 'gameserver' / 'worlds' / 'yard' / 'yard.server.q'
    world = World(read_world(QuantumParser(use_cache=False).parse_file(str(yard)), str(yard)))
    functions = world.rules.evaluator.functions
    own = {name for name, fn in functions.items() if STDLIB.get(name) is not fn}
    assert own == {sig.split('(')[0] for sig in FUNCTION_DOCS}
    text = (REPO / 'docs' / 'targets' / 'gameserver.md').read_text(encoding='utf-8')
    assert not [t for t in TAGS if f'### `q:{t}`' not in text]
    assert not [sig for sig in FUNCTION_DOCS if f'`{sig}`' not in text]
