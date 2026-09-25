"""The site pages generated from the repository are up to date.

docs/changelog/ (from CHANGELOG.md), docs/status/ (from FEATURE_STATUS.md) and
the blog index and RSS feed (from docs/blog/posts/) are produced by
scripts/generate-site-pages.py. A change to one of the sources that is not
regenerated would publish a site that disagrees with the repository.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def _generator():
    spec = importlib.util.spec_from_file_location('generate_site_pages', REPO / 'scripts' / 'generate-site-pages.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_generated_site_pages_are_current():
    gen = _generator()
    stale = gen.stale(gen.pages())
    assert not stale, f'stale: {stale} — run python scripts/generate-site-pages.py'


def test_every_version_in_the_changelog_has_a_page_newest_first():
    gen = _generator()
    text = (REPO / 'CHANGELOG.md').read_text(encoding='utf-8')
    versions = [v for v, _ in gen.split_versions(text)]
    assert versions[0] == '1.0.0'
    index = gen.pages()['changelog/index.md']
    positions = [index.index(f'[{v}](./{gen.version_slug(v)}.md)') for v in versions]
    assert positions == sorted(positions)


def test_a_section_keeps_its_anchor():
    # Links to a version's section must not depend on the text around it.
    page = _generator().pages()['changelog/v1-0-0.md']
    assert '{#breaking}' in page and '{#added}' in page
