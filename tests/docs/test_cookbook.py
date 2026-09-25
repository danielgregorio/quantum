"""The Cookbook: every recipe is tested, and what its page shows is what it does.

A recipe is a small app in examples/cookbook/<topic>/<name>/ with a
`quantum test` suite; its page in docs/cookbook/ imports the recipe's files,
and scripts/generate-cookbook.py writes what the page shows as a result by
running the recipe. This fails when a recipe's tests fail, when a shown result
or the index is stale, or when a page imports something that is not there.
"""

import importlib.util
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
IMPORT = re.compile(r'^<<< @/\.\./(?P<path>[^{\s]+)', re.M)


def _generator():
    spec = importlib.util.spec_from_file_location('generate_cookbook', REPO / 'scripts' / 'generate-cookbook.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_recipe_passes_and_what_the_pages_show_is_current():
    gen = _generator()
    files, failing = gen.expected()
    assert not failing, f'recipes whose tests fail: {failing}'
    stale = gen.stale(files)
    assert not stale, f'stale: {stale} — run python scripts/generate-cookbook.py'


def test_every_recipe_has_tests_and_a_page_that_imports_it():
    gen = _generator()
    for recipe in gen.recipes():
        rel = recipe.relative_to(REPO).as_posix()
        assert list((recipe / 'tests').glob('*.test.q')), f'{rel}: no tests/*.test.q'
        topic, name = recipe.parent.name, recipe.name
        page = REPO / 'docs' / 'cookbook' / topic / f'{name}.md'
        assert page.is_file(), f'{rel}: no page docs/cookbook/{topic}/{name}.md'
        imported = IMPORT.findall(page.read_text(encoding='utf-8'))
        assert any(p.startswith(rel + '/') for p in imported), f'{page.name} imports nothing from {rel}'


def test_every_import_on_the_site_points_to_a_file():
    for page in (REPO / 'docs').rglob('*.md'):
        if 'node_modules' in page.parts:
            continue
        for path in IMPORT.findall(page.read_text(encoding='utf-8')):
            assert (REPO / path).is_file(), f'{page.relative_to(REPO)}: imports {path}, which does not exist'
