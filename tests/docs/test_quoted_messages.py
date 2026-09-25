"""A message the site quotes is a message Quantum can print.

The guide's **Error:** lines are run (test_guide_examples_run.py). A message
quoted in a ```text block is not. Here every such block — one
introduced as a message, error or refusal, and not a `quantum test` report,
which test_guide_testing.py checks — is cut into its literal parts (what is
between quoted names, values, paths and numbers), and each part must be in
the code under quantum/.

A message built from several strings is cut at its punctuation first, so a
part is matched as the code writes it. This catches words Quantum does not
print — an old wording, an invented one. A quote cut short (the q:application
page left out the parser's last sentence) still passes: every word it keeps is
real.
"""

import re
from pathlib import Path

import pytest

from tests.docs.test_no_deprecated_content import UNPUBLISHED

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
FENCE = '`' * 3
# The paragraph before the block says it shows what Quantum prints.
INTRO = re.compile(r'message|stops with|parse error|says|refused|fails with|error', re.I)
TRANSLATIONS = ('pt/', 'es/', 'zh/')           # their blocks are the English ones (test_translations)


def code_text():
    text = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in (REPO / 'quantum').rglob('*.py'))
    return re.sub(r'\s+', ' ', text)


SOURCE = code_text()


def parts(line):
    """The literal parts of a message line, long enough to mean something."""
    line = re.sub(r"'[^']*'|\"[^\"]*\"|\{[^}]*\}|<[^>]*>|`[^`]*`|\S*[/\\]\S*|\b\d+(\.\d+)?\b|…", '\x00', line)
    for chunk in re.split(r'[\x00.:;()]', line):
        chunk = re.sub(r'\s+', ' ', chunk).strip(' ,-')
        if len(chunk) >= 12 and not re.fullmatch(r'[\w:-]+(, [\w:-]+)+', chunk):   # not a list of names
            yield chunk


def quoted_messages():
    for path in sorted(DOCS.rglob('*.md')):
        rel = path.relative_to(DOCS).as_posix()
        if ('node_modules' in path.parts or '.vitepress' in path.parts or rel in UNPUBLISHED
                or rel.startswith(TRANSLATIONS + ('changelog/', 'blog/'))):
            continue
        text = path.read_text(encoding='utf-8')
        for m in re.finditer('^' + FENCE + r'text[^\n]*\n(.*?)^' + FENCE, text, re.S | re.M):
            before = text[:m.start()].rstrip().rsplit('\n\n', 1)[-1]
            body = m.group(1)
            if INTRO.search(before) and not re.search(r'\b(PASS|FAIL)\b|passed,', body):
                yield rel, text[:m.start()].count('\n') + 1, body


MESSAGES = list(quoted_messages())


def test_the_site_quotes_some_messages():
    assert len(MESSAGES) >= 3


@pytest.mark.parametrize('page,line,body', MESSAGES, ids=[f'{p}:{n}' for p, n, _ in MESSAGES])
def test_a_quoted_message_is_in_the_code(page, line, body):
    missing = [part for text_line in body.splitlines() for part in parts(text_line) if part not in SOURCE]
    assert not missing, f'docs/{page}:{line} quotes words Quantum does not print: {missing}'
