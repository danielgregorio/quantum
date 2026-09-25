"""The repository's front door — README.md (what GitHub and PyPI show),
CONTRIBUTING.md, SECURITY.md, SUPPORT_TIERS.md, CODE_OF_CONDUCT.md — meets the
site's bar.

- README's Quantum examples are tested code: each `xml` block is a file of a
  Cookbook recipe, byte for byte (the recipes run in CI, tests/docs/test_cookbook.py),
  or the quick start's hello.q, which is run here and must print what README shows.
- Their quantum.config.yaml snippets load without errors or warnings.
- Their links to quantumframework.net go to published pages, and their links
  to files of the repository go to files that exist.

What they must not present as current (removed tags, old commands, counts
that age) is checked with the site's pages by test_no_deprecated_content.py.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.docs import docs_blocks
from tests.docs.test_no_deprecated_content import UNPUBLISHED

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
FRONT_DOOR = ['README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'SUPPORT_TIERS.md', 'CODE_OF_CONDUCT.md']
F = '`' * 3
README = (REPO / 'README.md').read_text(encoding='utf-8').replace('\r\n', '\n')
XML_BLOCKS = re.findall(F + r'xml\n(.*?)' + F, README, re.S)


def normalized(text):
    return text.replace('\r\n', '\n').strip('\n')


RECIPE_FILES = {normalized(p.read_text(encoding='utf-8')): p.relative_to(REPO).as_posix()
                for p in (REPO / 'examples' / 'cookbook').rglob('components/**/*.q')}


def hello_block():
    """The quick start's hello.q, and the output README shows after `quantum run hello.q`."""
    section = README[README.index('## Quick start'):]
    source = re.search(F + r'xml\n(.*?)' + F, section, re.S).group(1)
    shown = re.search(r'quantum run hello\.q\n' + F + r'\s*' + F + r'\n(.*?)' + F, section, re.S).group(1)
    return source, shown


def test_every_example_is_a_tested_recipe_file_or_the_quick_start():
    hello, _ = hello_block()
    untested = [block for block in XML_BLOCKS
                if normalized(block) not in RECIPE_FILES and block != hello]
    assert XML_BLOCKS and not untested, (
        'README examples that are not a Cookbook recipe file, byte for byte:\n\n'
        + '\n---\n'.join(untested))


def test_the_quick_start_prints_what_the_readme_shows(tmp_path):
    source, shown = hello_block()
    (tmp_path / 'hello.q').write_text(source, encoding='utf-8')
    result = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'run', 'hello.q'],
                            capture_output=True, text=True, cwd=tmp_path, timeout=120,
                            env={**__import__('os').environ, 'PYTHONPATH': str(REPO)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert normalized(shown) in result.stdout


def test_the_from_source_example_runs():
    # README and CONTRIBUTING: `quantum run examples/hello.q` prints Hello World!
    result = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'run', 'examples/hello.q'],
                            capture_output=True, text=True, cwd=REPO, timeout=120)
    assert result.returncode == 0 and 'Hello World!' in result.stdout, result.stdout + result.stderr


def config_snippets():
    import yaml
    from quantum.runtime.web_config import _KNOWN_SECTIONS
    for name in FRONT_DOOR:
        text = (REPO / name).read_text(encoding='utf-8')
        for m in docs_blocks.YAML_FENCE.finditer(text):
            data = yaml.safe_load(m['text'])
            if isinstance(data, dict) and set(data) & _KNOWN_SECTIONS:
                yield name, m['text']


@pytest.mark.parametrize('name,text', list(config_snippets()))
def test_a_config_snippet_loads_without_complaint(name, text, monkeypatch):
    assert docs_blocks.config_problem(text, monkeypatch) is None


def links(pattern):
    for name in FRONT_DOOR:
        text = (REPO / name).read_text(encoding='utf-8')
        for m in re.finditer(pattern, text):
            yield name, m.group(1)


def published(path):
    """The page quantumframework.net serves at /path, if it publishes one."""
    path = path.split('#')[0].strip('/')
    for candidate in ([f'{path}.md', f'{path}/index.md'] if path else ['index.md']):
        if (DOCS / candidate).is_file() and candidate not in UNPUBLISHED:
            return candidate
    return None


@pytest.mark.parametrize('name,path', sorted(set(links(r'https://quantumframework\.net/([^)\s]*)'))))
def test_a_site_link_goes_to_a_published_page(name, path):
    assert published(path), f'{name}: https://quantumframework.net/{path} is not a page of the site'


@pytest.mark.parametrize('name,path', sorted(set(
    list(links(r'https://github\.com/danielgregorio/quantum/blob/main/([^)\s#]+)'))
    + [(n, p) for n, p in links(r'\]\((?!https?:|#|mailto:)([^)\s#]+)\)')])))
def test_a_link_to_a_file_of_the_repository_exists(name, path):
    assert (REPO / path).exists(), f'{name}: {path} does not exist'
