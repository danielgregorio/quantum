"""Every ```xml block on the site is real Quantum (tests/docs/docs_blocks.py).

The site taught tags that do not exist (ui:tabs, q:validate, q:job-queue) and
attributes the parser refuses; 121 of 607 blocks failed the real parser. Each
block is now parsed as what the page says it is — a whole file, the body of a
component, a fragment inside a named context, or an error on purpose — and the
guide's examples with a result are also run (test_guide_examples_run.py).
"""

import pytest

import docs_blocks

BLOCKS = [b for b in docs_blocks.blocks() if b.path not in docs_blocks.UNDER_REVIEW]


@pytest.mark.parametrize('block', BLOCKS, ids=[f'{b.path}:{b.line}' for b in BLOCKS])
def test_the_block_is_what_the_page_says(block):
    problem = docs_blocks.check(block)
    assert problem is None, f'docs/{block.path}:{block.line}: {problem}'


def test_the_pages_under_review_say_so_and_the_list_only_shrinks():
    marked = {p.relative_to(docs_blocks.DOCS).as_posix()
              for p in docs_blocks.DOCS.rglob('*.md')
              if 'node_modules' not in p.parts
              and docs_blocks.NOTICE in p.read_text(encoding='utf-8')}
    assert marked == docs_blocks.UNDER_REVIEW, (
        f'notice without being listed: {sorted(marked - docs_blocks.UNDER_REVIEW)}; '
        f'listed without the notice (fixed? take it off the list): '
        f'{sorted(docs_blocks.UNDER_REVIEW - marked)}')


def test_a_fragment_names_a_known_context():
    for b in docs_blocks.blocks():
        if b.fragment:
            assert b.fragment in docs_blocks.CONTEXTS, f'docs/{b.path}:{b.line}: fragment={b.fragment}'


GUARDED = [b for b in docs_blocks.blocks()]


@pytest.mark.parametrize('block', GUARDED, ids=[f'{b.path}:{b.line}' for b in GUARDED])
def test_quantum_code_on_the_site_is_tested(block):
    # The guard: see THE GUARD in docs_blocks.py.
    problem = docs_blocks.guard(block)
    assert problem is None, f'docs/{block.path}:{block.line}: {problem}'


def test_the_parse_only_list_only_shrinks():
    unused = docs_blocks.PARSE_ONLY_PAGES - docs_blocks.parse_only_pages_in_use()
    assert not unused, f'no parse-only block left on {sorted(unused)}: take them off PARSE_ONLY_PAGES'


CONFIGS = list(docs_blocks.config_snippets())


@pytest.mark.parametrize('path,line,text', CONFIGS, ids=[f'{p}:{n}' for p, n, _ in CONFIGS])
def test_a_config_snippet_loads_without_complaint(path, line, text, monkeypatch):
    problem = docs_blocks.config_problem(text, monkeypatch)
    assert problem is None, f'docs/{path}:{line}: {problem}'
