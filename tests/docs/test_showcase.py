"""docs/showcase/index.md is what scripts/generate-showcase.py measures in projects/.

The page lists, per proving app, its size, tags, SPEC rules and tests. Those
are counted from the apps' files, so an app that grows, gains a tag or loses a
test changes the page, or this test fails until the page is regenerated.
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('generate_showcase', REPO / 'scripts' / 'generate-showcase.py')
showcase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(showcase)


def test_the_page_is_what_the_script_generates():
    assert showcase.PAGE.read_text(encoding='utf-8') == showcase.render(), (
        'docs/showcase/index.md is out of date: run python scripts/generate-showcase.py')


def test_every_app_has_its_screenshot():
    for app, *_ in showcase.APPS:
        assert (REPO / 'docs' / 'public' / 'showcase' / f'{app}.png').is_file(), (
            f'{app}: run python scripts/showcase-screenshots.py {app}')


def test_no_app_needs_javascript():
    for app, *_ in showcase.APPS:
        assert showcase.facts(app)['js'] == 0, app


def test_every_app_is_tested():
    for app, *_ in showcase.APPS:
        f = showcase.facts(app)
        assert f['tests'] or f['suites'], app
