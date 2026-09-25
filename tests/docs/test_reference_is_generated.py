"""docs/reference/ is generated from the code and the SPEC, and committed as generated.

scripts/generate-reference.py writes the tags (quantum-lsp's schema, itself
checked against the parser), the expression functions (STDLIB), the command
line (build_parser), the configuration (web_config), the ui:* tags (what each
_parse_ui_* method reads) and SPEC.md with an anchor per rule. A page edited by hand, or code that changed without regenerating,
fails here: run `python scripts/generate-reference.py`.
"""

import importlib.util
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location('generate_reference', REPO / 'scripts' / 'generate-reference.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = generator()
PAGES = GEN.pages()


@pytest.mark.parametrize('name', sorted(PAGES))
def test_the_committed_page_is_what_the_generator_writes(name):
    committed = GEN.OUT / name
    assert committed.exists(), f'docs/reference/{name} is missing — run python scripts/generate-reference.py'
    assert committed.read_text(encoding='utf-8') == PAGES[name], \
        f'docs/reference/{name} is not current — run python scripts/generate-reference.py'


def test_no_page_in_the_reference_that_the_generator_does_not_write():
    extra = sorted(p.name for p in GEN.OUT.glob('*.md') if p.name not in PAGES)
    assert extra == [], f'docs/reference/ has pages the generator does not write: {extra}'


def test_every_rule_has_its_anchor_and_every_rule_link_exists():
    anchors = set(re.findall(r'<a id="([A-Z]+-\d+)"></a>', PAGES['spec.md']))
    assert anchors == set(GEN.RULES)
    linked = {m for text in PAGES.values() for m in re.findall(r'\./spec#([A-Z]+-\d+)\)', text)}
    assert linked <= set(GEN.RULES)


def test_the_ui_page_has_every_ui_tag_and_every_attribute_its_parser_reads():
    """The ui: page reads the parser's code; a plain-text reading of the same code must agree."""
    import ast
    from quantum.core.features.ui_engine.src.ast_nodes import CORE_TAGS
    from quantum.core.features.ui_engine.src.parser import UIParser
    source = GEN.UI_PARSER.read_text(encoding='utf-8')
    methods = GEN._ui_methods()
    page = PAGES['ui.md']
    core, experimental = page.split('<h1 class="reference-group">Experimental</h1>')
    for tag, name in UIParser.UI_TAG_MAP.items():
        section = re.search(r'<a id="ui-%s"></a>(.*?)(?=<a id=|\Z)' % re.escape(tag), page, re.S)
        assert section, f'ui:{tag} has no entry'
        assert (f'<a id="ui-{tag}">' in core) == (tag in CORE_TAGS), f'ui:{tag} is in the wrong group (UI-7)'
        body = ast.get_source_segment(source, methods[name])
        for attr in re.findall(r"element\.get\('([\w-]+)'", body):
            assert f'| `{attr}` |' in section.group(1), f'ui:{tag} reads {attr}= but its entry does not list it'
