"""docs/targets/screen.md is generated from the screen schema and the OS's screen, and committed as generated.

scripts/generate-screen-reference.py writes the page from
quantum/runtime/screen/schema.py (the table the compiler validates against)
and os/config/screen/screen.q. A page edited by hand, a tag added to the
schema, or the OS's screen changed without regenerating fails here: run
`python scripts/generate-screen-reference.py`.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        'generate_screen_reference', REPO / 'scripts' / 'generate-screen-reference.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_screen_page_is_current():
    gen = generator()
    assert gen.OUT.read_text(encoding='utf-8') == gen.build(), (
        'docs/targets/screen.md is stale: run python scripts/generate-screen-reference.py')


def test_every_tag_and_event_of_the_schema_is_on_the_page():
    from quantum.runtime.screen.schema import EVENTS, TAGS
    text = (REPO / 'docs' / 'targets' / 'screen.md').read_text(encoding='utf-8')
    missing = [t for t in TAGS if f'### `qs:{t}`' not in text]
    missing += [e for e in EVENTS if f'### `{e}`' not in text]
    assert not missing, missing
