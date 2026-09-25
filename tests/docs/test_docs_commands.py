"""The commands the site shows are commands `quantum` runs, and the pages a
visitor lands on first show only tested code.

- Every `quantum …` line in a ```bash block of a published page (every
  language) is parsed by the real command-line parser: a command, option or
  choice that does not exist fails here. Synopsis lines (`quantum <command>`,
  `[options]`) are skipped.
- The homes, the Sponsor page, the blog posts and the Roadmap, in every
  language, hold no code of their own: an import of a tested Cookbook file, or
  a ```bash block checked above.
- The theme's Example* components draw code given to them by a page; only
  unpublished pages (srcExclude) use them.
"""

import contextlib
import io
import re
import shlex
from pathlib import Path

import pytest

from quantum.cli.runner import build_parser
from tests.docs.test_no_deprecated_content import UNPUBLISHED

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
FENCE = '`' * 3
LANGS = ('', 'pt/', 'es/', 'zh/')
FIRST_PAGES = [f'{lang}{page}' for lang in LANGS
               for page in ('index.md', 'sponsor/index.md', 'roadmap/index.md')]


def published():
    for path in sorted(DOCS.rglob('*.md')):
        rel = path.relative_to(DOCS).as_posix()
        if 'node_modules' in path.parts or '.vitepress' in path.parts or rel in UNPUBLISHED:
            continue
        yield rel, path.read_text(encoding='utf-8')


def commands():
    for rel, text in published():
        for block in re.finditer('^' + FENCE + r'(?:bash|sh|shell|console)[^\n]*\n(.*?)^' + FENCE, text, re.S | re.M):
            for line in block.group(1).splitlines():
                line = re.sub(r'^\$\s*', '', line.strip())
                if not line.startswith('quantum ') or re.search(r'<[^>]+>|\[[a-z ]+\]', line):
                    continue
                yield rel, line.split('#')[0].split('&&')[0].strip()


COMMANDS = sorted(set(commands()))


def test_the_site_shows_commands():
    assert len(COMMANDS) > 50


@pytest.mark.parametrize('page,command', COMMANDS)
def test_a_command_on_the_site_is_one_quantum_runs(page, command):
    parser, _ = build_parser()
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            parser.parse_args(shlex.split(command)[1:])
    except SystemExit as exit_:
        assert not exit_.code, f'docs/{page}: `{command}` — {err.getvalue().strip().splitlines()[-1]}'


def test_the_first_pages_show_only_tested_code():
    posts = [p.relative_to(DOCS).as_posix() for p in DOCS.rglob('blog/posts/*.md') if 'node_modules' not in p.parts]
    for page in FIRST_PAGES + posts:
        path = DOCS / page
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        fences = re.findall('^' + FENCE + r'(\w*)', text, re.M)[::2]          # opening fences
        assert set(fences) <= {'bash'}, f'docs/{page}: a code block that nothing runs ({fences})'
        for target in re.findall(r'^<<< @/\.\./(\S+?)(?:\{|$)', text, re.M):
            assert target.startswith('examples/cookbook/') and (REPO / target).is_file(), \
                f'docs/{page}: imports {target}, which is not a tested Cookbook file'


def test_the_example_components_are_only_on_unpublished_pages():
    components = [p.stem for p in (DOCS / '.vitepress' / 'theme' / 'components').glob('Example*.vue')]
    for rel, text in published():
        used = [c for c in components if re.search(rf'<{c}\b', text)]
        assert not used, f'docs/{rel} uses {used}, which draw code no test runs'
