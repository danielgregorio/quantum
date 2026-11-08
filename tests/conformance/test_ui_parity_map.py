"""UI_PARITY.md is the map of every `ui:*` tag against every renderer (UI-7, UI-21), written from
quantum/runtime/ui_parity.py. The renderers' side — that each says "not drawn" for exactly what the map says —
is checked on a page with every tag in tests/apps/test_ui_parity_script.py (test_every_tag_*)."""

from pathlib import Path

from quantum.runtime import ui_parity

ROOT = Path(__file__).resolve().parents[2]


def test_the_map_is_written_from_the_table():
    # UI-21
    assert (ROOT / 'UI_PARITY.md').read_text(encoding='utf-8') == ui_parity.markdown(), \
        'UI_PARITY.md is out of date: python -m quantum.runtime.ui_parity > UI_PARITY.md'


def test_every_tag_the_parser_knows_is_in_the_map():
    # UI-7: a new tag is placed in the map, never left out of it
    text = (ROOT / 'UI_PARITY.md').read_text(encoding='utf-8')
    assert [t for t in ui_parity.all_tags() if f'`ui:{t}`' not in text] == []


def test_a_tag_is_core_when_every_renderer_draws_it():
    # UI-7: the Core set is what every renderer draws; what one does not draw is Experimental
    for tag in ui_parity.all_tags():
        everywhere = all(ui_parity.status(tag, r).startswith('drawn') for r in ui_parity.RENDERERS)
        assert (ui_parity.tier(tag) == 'Core') == everywhere, tag
