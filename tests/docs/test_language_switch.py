"""The language switcher's map (docs/.vitepress/translated-paths.js).

The switcher (docs/.vitepress/theme/langs.js) goes to the same page in the other
language when the map says that language has it, and to the language's home
otherwise. The map is built from TRANSLATED in locales.js, so a wrong entry there
would send readers to a 404: every route must be a page, and every translated
page must be reachable.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
NODE = shutil.which('node')

pytestmark = pytest.mark.skipif(not NODE, reason='node is needed to run the site config')


@pytest.fixture(scope='module')
def paths():
    out = subprocess.run([NODE, str(DOCS / '.vitepress' / 'translated-paths.js')],
                         capture_output=True, text=True, check=True, cwd=REPO).stdout
    return json.loads(out)


def page_file(lang, route):
    base = DOCS / lang / route.lstrip('/')
    return base / 'index.md' if route.endswith('/') else base.with_suffix('.md')


def test_every_route_in_the_map_is_a_page(paths):
    missing = [f'{lang}{route}' for lang, routes in paths.items() for route in routes
               if not page_file(lang, route).is_file()]
    assert not missing, f'the switcher would link pages that do not exist: {missing}'


def test_every_translated_page_is_in_the_map(paths):
    unreachable = []
    for lang, routes in paths.items():
        for page in sorted((DOCS / lang).rglob('*.md')):
            rel = page.relative_to(DOCS / lang).as_posix()
            route = '/' + (rel[:-len('index.md')] if rel.endswith('index.md') else rel[:-3])
            if route not in routes:
                unreachable.append(f'{lang}{route}')
    assert not unreachable, f'translated, but the switcher does not know it: {unreachable}'


def test_the_map_has_every_language_and_its_home(paths):
    assert set(paths) == {'pt', 'es', 'zh'}
    assert all('/' in routes for routes in paths.values())
