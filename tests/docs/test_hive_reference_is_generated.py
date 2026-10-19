"""docs/targets/hive.md is generated from the hive schema and the OS's rules, and committed as generated.

scripts/generate-hive-reference.py writes the page from
quantum/runtime/hive/schema.py (the table the compiler validates against)
and os/config/hive/hive.q. A page edited by hand, a tag added to the
schema, or the OS's rules changed without regenerating fails here: run
`python scripts/generate-hive-reference.py`.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        'generate_hive_reference', REPO / 'scripts' / 'generate-hive-reference.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_hive_page_is_current():
    gen = generator()
    assert gen.OUT.read_text(encoding='utf-8') == gen.build(), (
        'docs/targets/hive.md is stale: run python scripts/generate-hive-reference.py')


def test_every_tag_event_and_action_of_the_schema_is_on_the_page():
    from quantum.runtime.hive.schema import ACTIONS, EVENTS, TAGS
    text = (REPO / 'docs' / 'targets' / 'hive.md').read_text(encoding='utf-8')
    missing = [t for t in TAGS if f'### `qh:{t}`' not in text]
    missing += [e for e in EVENTS if f'### `{e}`' not in text]
    missing += [a for a in ACTIONS if f'### `{a}`' not in text]
    assert not missing, missing
