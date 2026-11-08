"""Which `ui:*` tag each renderer draws: the map behind UI_PARITY.md (UI-7, UI-21).

One table, written here: every tag the parser knows, its tier, and what each renderer of a page does with it —
the browser, the console (Textual), the Hive's screen (hive-screen) and the TUI drawn by Godot. The desktop is
the browser in a window of its own (UI-4). UI_PARITY.md is this table written out (`python -m
quantum.runtime.ui_parity > UI_PARITY.md`), and tests/conformance/test_ui_parity_map.py keeps both true: the file
says what the table says, and a page with every tag, laid out by each renderer, says "not drawn" for exactly the
tags the table says it does not draw (UI-7: never something else in their place).
"""

from __future__ import annotations

from typing import Dict, List, Optional

RENDERERS = ('browser', 'console', 'screen', 'tui')
TITLES = {'browser': 'Browser', 'console': 'Console', 'screen': "Hive's screen", 'tui': 'TUI'}

# The tags the console, the screen and the TUI do not draw yet: they say "[ui:kind is not drawn ...]". None since
# Platforms Phase 4: a kind a renderer does not know (a newer server's) still says so (UI-7).
NOT_DRAWN: frozenset = frozenset()

# Tags that are a part of another and drawn by it.
PART_OF = {'tab': 'tabpanel', 'column': 'table', 'option': 'select', 'item': 'list', 'card-header': 'card',
           'card-body': 'card', 'card-footer': 'card', 'breadcrumb-item': 'breadcrumb', 'slide': 'carousel',
           'step': 'stepper', 'color': 'theme'}

# Tags that are not elements of a page: what they do, in every renderer the same (UI-21).
NOT_ELEMENTS = {
    'validator': 'a rule of its form, checked by the server when the form is sent (the error comes back by '
                 'its field, UI-9)',
    'theme': "the page's colours: the browser's CSS variables, the console's and the TUI's colours; the "
             "Hive's screen keeps its palette",
    'color': "one of its ui:theme's colours",
}

# What the browser's page does with a tag whose standalone build runs a script a page does not have.
BROWSER_IN_A_PAGE: Dict[str, str] = {}

# How a renderer draws a tag in the form it can, where that is worth saying.
NOTES: Dict[str, Dict[str, str]] = {
    'markdown': {'screen': 'its emphasis as plain text (the font has one face)'},
    'chart': {'console': 'bars of characters', 'screen': 'bars', 'tui': 'bars of characters'},
    'loading': {'screen': 'a still mark'},
    'skeleton': {'console': 'shaded lines', 'tui': 'shaded lines'},
    'image': {'console': '[its alt]', 'screen': '[its alt]'},
    'input': {'console': 'a file field says to attach from the browser (UI-14)'},
    'tooltip': {'screen': 'its tip on the status line while it has the focus'},
    'calendar': {'screen': 'the days of the months around it left blank',
                 'tui': 'the days of the months around it left blank'},
}


def all_tags() -> List[str]:
    from quantum.core.features.ui_engine.src.parser import UIParser
    return list(UIParser.UI_TAG_MAP)


def tier(tag: str) -> str:
    from quantum.core.features.ui_engine.src.ast_nodes import CORE_TAGS
    return 'Core' if tag in CORE_TAGS else 'Experimental'


def status(tag: str, renderer: str) -> str:
    """'drawn', 'not drawn', or how it is drawn ('drawn: ...')."""
    if tag in ('validator', 'theme', 'color'):
        if tag == 'validator':
            return 'drawn: checked by the server'
        return 'drawn: the screen keeps its palette' if renderer == 'screen' else 'drawn: its colours'
    if tag in PART_OF:
        return status(PART_OF[tag], renderer)
    if renderer == 'browser':
        return f'drawn: {BROWSER_IN_A_PAGE[tag]}' if tag in BROWSER_IN_A_PAGE else 'drawn'
    if tag in NOT_DRAWN:
        return 'not drawn'
    note = NOTES.get(tag, {}).get(renderer)
    return f'drawn: {note}' if note else 'drawn'


def not_drawn(renderer: str) -> set:
    """The tags `renderer` says it does not draw, as a page's view names them (no hyphen), the parts of
    another left out (the one they are part of says it)."""
    return {t.replace('-', '') for t in all_tags()
            if t not in PART_OF and status(t, renderer) == 'not drawn'}


def _cell(text: str) -> str:
    if text == 'drawn':
        return '✓'
    if text == 'not drawn':
        return '— says so'
    return '✓ ' + text[len('drawn: '):]


def markdown() -> str:
    lines = [
        '# UI parity: every `ui:*` tag in every renderer',
        '',
        '<!-- Written by `python -m quantum.runtime.ui_parity > UI_PARITY.md` from quantum/runtime/ui_parity.py;',
        '     tests/conformance/test_ui_parity_map.py fails when they differ, or when a renderer does not do',
        '     what the table says. -->',
        '',
        'What each renderer of a page does with each tag (SPEC.md UI-7, UI-21): ✓ drawn, with what is worth',
        'saying about the form it takes; "— says so" not drawn yet, and the renderer says',
        '`[ui:kind is not drawn ...]` in its place, never something else (UI-7). The desktop is the browser in',
        'a window of its own (UI-4). A tag enters the Core set when every renderer draws it.',
        '',
        '| Tag | Tier | ' + ' | '.join(TITLES[r] for r in RENDERERS) + ' |',
        '|---|---|' + '---|' * len(RENDERERS),
    ]
    for tag in sorted(all_tags()):
        part = f' (part of `ui:{PART_OF[tag]}`)' if tag in PART_OF else ''
        lines.append(f'| `ui:{tag}`{part} | {tier(tag)} | '
                     + ' | '.join(_cell(status(tag, r)) for r in RENDERERS) + ' |')
    lines += ['', '## Not elements of a page', '']
    for tag, what in NOT_ELEMENTS.items():
        lines.append(f'- `ui:{tag}`: {what}.')
    drawn_everywhere = sum(1 for t in all_tags() if all(status(t, r).startswith('drawn') for r in RENDERERS))
    lines += ['', f'{drawn_everywhere} of {len(all_tags())} tags are drawn by every renderer.', '']
    return '\n'.join(lines)


def main(argv: Optional[list] = None) -> int:
    print(markdown(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
