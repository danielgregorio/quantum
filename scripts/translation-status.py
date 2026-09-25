"""Which translated pages are behind their English source.

    python scripts/translation-status.py               # the report (exit 0)
    python scripts/translation-status.py --stamp PAGE  # after updating a translation
    python scripts/translation-status.py --stamp-all   # every translated page

A translated page (docs/pt/, docs/es/, docs/zh/) records the English page it
came from and the hash of that page's text:

    source: guide/installation.md
    source_hash: 3f2a9c1b7d4e

When the English changes, the hash no longer matches: the page shows "this
translation may be out of date" (docs/.vitepress/translations.js computes the
same hash at build time), and this report lists it. CI prints the report; a
stale page is not a failure. Stamp a page once its translation is updated.
The source defaults to the same path without the language folder.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs'
LANGUAGES = ('pt', 'es', 'zh')
FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)


def source_hash(text):
    """sha256 of the text with CRLF as LF, first 12 hex digits (as translations.js)."""
    return hashlib.sha256(text.replace('\r\n', '\n').encode('utf-8')).hexdigest()[:12]


def translated_pages():
    for lang in LANGUAGES:
        for path in sorted((DOCS / lang).rglob('*.md')):
            yield lang, path


def read(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def field(text, name):
    m = FRONTMATTER.match(text)
    if not m:
        return None
    f = re.search(rf'^{name}:\s*(.+?)\s*$', m.group(1), re.M)
    return f.group(1).strip('\'"') if f else None


def default_source(lang, path):
    return path.relative_to(DOCS / lang).as_posix()


def status(lang, path):
    """(page, source, state) with state ok, stale, no-source or missing-source."""
    text = read(path)
    page = path.relative_to(DOCS).as_posix()
    source = field(text, 'source')
    if not source:
        return page, None, 'no-source'
    english = DOCS / source
    if not english.is_file():
        return page, source, 'missing-source'
    return page, source, 'ok' if field(text, 'source_hash') == source_hash(read(english)) else 'stale'


def stamp(path, lang):
    text = read(path)
    source = field(text, 'source') or default_source(lang, path)
    english = DOCS / source
    if not english.is_file():
        sys.exit(f'{path.relative_to(DOCS)}: its English source {source} does not exist')
    values = {'source': source, 'source_hash': source_hash(read(english))}
    m = FRONTMATTER.match(text)
    if m:
        body = m.group(1)
        for name, value in values.items():
            if re.search(rf'^{name}:', body, re.M):
                body = re.sub(rf'^{name}:.*$', f'{name}: {value}', body, flags=re.M)
            else:
                body += f'\n{name}: {value}'
        text = f'---\n{body}\n---\n' + text[m.end():]
    else:
        text = '---\n' + ''.join(f'{k}: {v}\n' for k, v in values.items()) + '---\n\n' + text
    path.write_text(text, encoding='utf-8', newline='\n')
    print(f'stamped {path.relative_to(DOCS).as_posix()} <- {source} ({values["source_hash"]})')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--stamp', nargs='+', metavar='PAGE', help='docs/<lang>/... pages to stamp')
    parser.add_argument('--stamp-all', action='store_true')
    args = parser.parse_args()

    if args.stamp_all or args.stamp:
        wanted = {str(Path(p).resolve()) for p in (args.stamp or [])}
        for lang, path in translated_pages():
            if args.stamp_all or str(path.resolve()) in wanted:
                stamp(path, lang)
        return 0

    rows = [status(lang, path) for lang, path in translated_pages()]
    stale = [r for r in rows if r[2] != 'ok']
    print(f'{len(rows)} translated pages, {len(rows) - len(stale)} up to date')
    for page, source, state in stale:
        print(f'  {state:15} docs/{page}' + (f'  (from {source})' if source else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
