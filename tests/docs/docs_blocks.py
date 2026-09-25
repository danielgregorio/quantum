"""Every ```xml block in docs/, and how each one is checked.

A block is checked with the real parser — or run, when the page shows its
result (**Output:** / **Error:** right after it; tests/docs/
test_guide_examples_run.py runs the guide's, this runs the rest). What a
block is, is said by the page, never guessed from failure:

- A whole file (`<q:component>`, `<q:application>`, `<q:job>`) parses as is.
- Anything else is the body of a `<q:component>` — the common case: a few
  statements or some markup.
- A `.test.q` file (`<q:test>`) is parsed as one; `test:` steps alone go
  inside a `<q:test>`.
- A fragment that only makes sense inside something else says so in the
  fence: ```xml fragment=action — see CONTEXTS for the names.
- A block that must NOT parse is followed by **Error:** `part of the message`
  (the guide's convention), or says ```xml error="part of the message".
- A block that is not Quantum at all is not ```xml: use ```text or ```html.

Pages listed in UNDER_REVIEW say on the page that their examples are not
checked; they are being replaced, and are reported, not checked.
"""

import pathlib
import re
from dataclasses import dataclass
from typing import Optional

REPO = pathlib.Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
NS = 'xmlns:q="https://quantum.lang/ns"'
F = '`' * 3

# Pages that document things that do not exist (ui:tabs, q:validate,
# q:job-queue…) carry a visible "Under review" notice and are replaced by tested
# examples (the Cookbook) or a generated reference. They are listed here so the
# list can only shrink: test_docs_xml_blocks.py fails if a page gains the
# notice without being listed, or keeps it after leaving the list.
UNDER_REVIEW = {
    'ui/overview.md', 'ui/layout.md', 'ui/forms.md', 'ui/data-display.md', 'ui/feedback.md',
    'ui/navigation.md', 'ui/overlays.md', 'ui/advanced-components.md',
    'features/animations.md', 'features/theming.md', 'features/form-validation.md',
    'examples/advanced.md', 'examples/agents.md', 'examples/conditionals.md',
    'examples/forms-actions.md', 'examples/games.md', 'examples/queries.md', 'examples/ui-theming.md',
    'targets/html.md', 'targets/mobile.md', 'targets/terminal.md',
    'extensibility/plugins.md',
}
NOTICE = '::: danger Under review'

# fragment=<name>: the context a fragment is parsed in. {body} is the block.
CONTEXTS = {
    'action': f'<q:component name="Doc" {NS}><q:action name="doc">{{body}}</q:action></q:component>',
    'knowledge': f'<q:component name="Doc" {NS}><q:knowledge name="doc">{{body}}</q:knowledge></q:component>',
    'agent': (f'<q:component name="Doc" {NS}><q:agent name="doc" model="phi3">'
              f'<q:instruction>x</q:instruction>{{body}}<q:execute task="x"/></q:agent></q:component>'),
    'llm': f'<q:component name="Doc" {NS}><q:llm name="doc" model="phi3">{{body}}</q:llm></q:component>',
    'game': f'<q:application id="doc" type="game" {NS}>{{body}}</q:application>',
    'scene': f'<q:application id="doc" type="game" {NS}><qg:scene name="doc">{{body}}</qg:scene></q:application>',
    'terminal': f'<q:application id="doc" type="terminal" {NS}>{{body}}</q:application>',
    'ui-app': f'<q:application id="doc" type="ui" {NS}>{{body}}</q:application>',
    'test': '<q:test name="doc" page="/">{body}</q:test>',
}

FENCE = re.compile(r'^' + F + r'xml(?P<meta>[^\n]*)\n(?P<xml>.*?)^' + F + r'[ \t]*$', re.S | re.M)
AFTER = re.compile(r'\s*\*\*(?P<kind>Output|Error|Shows):\*\*[ \t]*(?:`(?P<inline>[^`\n]+)`)?')


@dataclass
class Block:
    path: str            # relative to docs/
    line: int
    xml: str
    fragment: Optional[str]
    error: Optional[str]  # the block must fail with this text
    shown: Optional[str]  # Output / Shows: the page shows its result


def blocks():
    for doc in sorted(DOCS.rglob('*.md')):
        if 'node_modules' in doc.parts or '.vitepress' in doc.parts:
            continue
        rel = doc.relative_to(DOCS).as_posix()
        text = doc.read_text(encoding='utf-8')
        for m in FENCE.finditer(text):
            meta = m['meta']
            frag = re.search(r'\bfragment=([\w-]+)', meta)
            err = re.search(r'\berror="([^"]+)"', meta)
            after = AFTER.match(text, m.end())
            error = err.group(1) if err else None
            shown = None
            if after and after['kind'] == 'Error':
                error = error or after['inline'] or ''
            elif after:
                shown = after['kind']
            yield Block(rel, text[:m.start()].count('\n') + 1, m['xml'],
                        frag.group(1) if frag else None, error, shown)


def source(block: Block) -> str:
    body = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', block.xml.strip())
    if block.fragment:
        if block.fragment not in CONTEXTS:
            raise ValueError(f'unknown fragment={block.fragment} (known: {", ".join(CONTEXTS)})')
        return CONTEXTS[block.fragment].format(body=body)
    head = re.sub(r'^(?:\s*<!--.*?-->)*\s*', '', body, flags=re.S)
    if re.match(r'<q:(component|application|job)\b', head):
        return body
    if head.startswith('<q:test') or head.startswith('<test:'):
        return body if head.startswith('<q:test') else CONTEXTS['test'].format(body=body)
    return f'<q:component name="Doc" {NS}>\n{body}\n</q:component>'


def parse(block: Block):
    from quantum.core.parser import QuantumParser
    text = source(block)
    if re.match(r'(?:\s*<!--.*?-->)*\s*<q:test\b', text, re.S):
        from quantum.core.features.native_testing.src.parser import parse_test_source
        return parse_test_source(text)
    return QuantumParser(use_cache=False).parse(text)


def check(block: Block) -> Optional[str]:
    """None when the block is what the page says it is; otherwise the problem."""
    if block.path in UNDER_REVIEW:
        return None
    try:
        parse(block)
    except Exception as exc:  # noqa: BLE001 — any failure is the finding
        message = str(exc)
        if block.error is not None:
            if block.error in message:
                return None
            return f'fails, but not with {block.error!r}: {message.splitlines()[0][:100]}'
        return message.splitlines()[0]
    if block.error is not None and not runs_elsewhere(block):
        return f'parses, but the page says it fails with {block.error!r}'
    return None


def runs_elsewhere(block: Block) -> bool:
    """The guide's examples with a result are RUN by test_guide_examples_run.py.

    There an **Error:** is usually a run-time error (a failed validation, a
    missing table) — the block parses, and that test checks it fails as shown.
    """
    return block.path.startswith('guide/') and (block.error is not None or block.shown is not None)
