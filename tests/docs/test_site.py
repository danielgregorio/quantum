"""The website's structure: languages, the top nav's routes, and search in Chinese.

The site (docs/, VitePress) is English at the root with /pt/, /es/ and /zh/.
The build (`npm run docs:build`, run by CI) fails on a link to a page that
does not exist; these tests hold what the build does not check.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
VITEPRESS = DOCS / '.vitepress'


def test_every_language_has_its_home():
    for prefix in ('', 'pt/', 'es/', 'zh/'):
        assert (DOCS / prefix / 'index.md').is_file(), prefix


def test_the_top_nav_routes_exist():
    # Home · Docs (Guide, Tutorial, Reference, SPEC) · Showcase · Blog ·
    # Changelog · Status · Sponsor: other pages fill them, the routes are here.
    source = (VITEPRESS / 'locales.js').read_text(encoding='utf-8')
    links = set(re.findall(r"link: '(/[^']*)'", source))
    for link in links:
        page = DOCS / (link.strip('/') + ('/index.md' if link.endswith('/') else '.md'))
        assert page.is_file(), f'the nav links to {link}, and {page.relative_to(REPO)} does not exist'
    for route in ('/tutorial/', '/reference/', '/reference/spec', '/showcase/', '/blog/', '/changelog/',
                  '/status/', '/sponsor/'):
        assert route in links


def test_the_base_path_is_not_written_in_the_pages():
    # The site moved from /quantum/ to /: a page that spells the base breaks.
    offenders = [p.relative_to(REPO).as_posix() for p in DOCS.rglob('*.md')
                 if 'node_modules' not in p.parts and '.vitepress' not in p.parts
                 and re.search(r'\]\(/quantum/|href="/quantum/', p.read_text(encoding='utf-8'))]
    assert offenders == []


@pytest.mark.skipif(shutil.which('node') is None or not (REPO / 'node_modules' / 'minisearch').is_dir(),
                    reason='needs node and `npm ci`')
def test_search_finds_a_chinese_word_inside_a_sentence():
    result = subprocess.run(['node', str(VITEPRESS / 'search-tokenize.check.mjs')],
                            capture_output=True, text=True, encoding='utf-8', cwd=str(REPO), timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
