"""The playground (docs/playground/): the Cookbook's recipes, run by the real Quantum.

The browser runs docs/public/playground/bridge.py in Pyodide, over the
quantum-framework the site documents. Here the same bridge runs under CPython,
over this repository's quantum/: every recipe the playground offers builds, its
first page answers, and its links, forms and tests work through the bridge.
scripts/check-playground.mjs (CI, docs job) runs it in Pyodide itself.
"""

import json
import re
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PUBLIC = REPO / 'docs' / 'public' / 'playground'


def _load(name, path):
    # Compiled here, not imported: an import would leave a __pycache__ in
    # docs/public/, and the site would publish it.
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
    return module


def _recipes():
    data = json.loads((PUBLIC / 'recipes.json').read_text(encoding='utf-8'))
    return [r for topic in data['topics'] for r in topic['recipes']]


@pytest.fixture
def playground(tmp_path):
    bridge = _load('playground_bridge', PUBLIC / 'bridge.py')
    pg = bridge.Playground(tmp_path / 'project')
    yield pg
    pg.close()


def test_the_examples_are_the_cookbook_as_it_is_now():
    generator = _load('generate_playground', REPO / 'scripts' / 'generate-playground.py')
    assert (PUBLIC / 'recipes.json').read_text(encoding='utf-8') == generator.build(), \
        'stale: run python scripts/generate-playground.py'
    ids = {r['id'] for r in _recipes()}
    cookbook = {p.parent.relative_to(REPO / 'examples' / 'cookbook').as_posix()
                for p in (REPO / 'examples' / 'cookbook').glob('*/*/quantum.config.yaml')}
    assert ids == {i for i in cookbook if not i.startswith('ai/')}, 'every recipe but the AI ones'


@pytest.mark.parametrize('recipe', _recipes(), ids=lambda r: r['id'])
def test_every_example_builds_and_its_first_page_answers(playground, recipe):
    assert playground.load(recipe['files']) == {'ok': True}
    page = playground.request('GET', recipe['start'])
    expected = (200, 404) if recipe['view'] == 'tests' else (200,)
    assert page['status'] in expected, page['html'][:500]
    assert 'href="/static/' not in page['html'], 'the preview has no server: its assets are inlined'


def _recipe(recipe_id):
    return next(r for r in _recipes() if r['id'] == recipe_id)


def test_a_form_saves_follows_the_redirect_and_the_tests_run(playground):
    recipe = _recipe('forms-and-actions/edit-a-row')
    playground.load(recipe['files'])
    page = playground.request('GET', '/book/2')
    assert page['status'] == 200
    saved = playground.request('POST', '/book/2', {'title': 'Edited in the playground', 'genre': 'poetry',
                                                   '_action': 'save'})
    assert saved['status'] == 200 and saved['path'] == '/'
    assert 'Saved: Edited in the playground' in saved['html']
    result = playground.test()
    assert result['code'] == 0 and re.search(r'4 passed, 0 failed', result['report'])
    assert str(playground.root) not in result['report'], 'paths are the project\'s own'


def test_a_broken_project_says_why_instead_of_failing(playground):
    recipe = _recipe('forms-and-actions/edit-a-row')
    files = dict(recipe['files'])
    files['migrations/V001_books.sql'] = 'CREATE TABLE ('
    result = playground.load(files)
    assert 'error' in result and 'migrations' in result['error']
    assert playground.request('GET', '/')['status'] == 0


def test_a_file_must_stay_inside_the_project(playground):
    result = playground.load({'../outside.q': '<q:component name="X"/>'})
    assert 'inside the project' in result['error']


def test_the_page_offers_it_in_every_language():
    assert (REPO / 'docs' / 'playground' / 'index.md').is_file()
    locales = (REPO / 'docs' / '.vitepress' / 'locales.js').read_text(encoding='utf-8')
    assert "{ text: t.playground, link: '/playground/' }" in locales
    assert locales.count('playground: ') == 4
