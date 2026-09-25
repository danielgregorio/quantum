"""The translated pages: each has its English source, is reachable, and says when it is behind.

A page in docs/pt/, docs/es/ or docs/zh/ names the English page it was
translated from and the hash of that text (scripts/translation-status.py).
When the English changes, the build marks the translation stale and the page
shows a notice (docs/.vitepress/translations.js, TranslationNotice.vue). A
stale page is reported, not failed. Code blocks equal to the English are
checked elsewhere (the site's code guard).
"""

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
spec = importlib.util.spec_from_file_location('translation_status', REPO / 'scripts' / 'translation-status.py')
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)

PAGES = list(status.translated_pages())
NODE = shutil.which('node')


def translated_routes():
    """TRANSLATED in docs/.vitepress/locales.js: the pages each language's nav links to."""
    text = (DOCS / '.vitepress' / 'locales.js').read_text(encoding='utf-8')
    block = re.search(r'const TRANSLATED = \{(.*?)\n\}', text, re.S).group(1)
    return {lang: re.findall(r"'([^']+)'", entries)
            for lang, entries in re.findall(r'^\s*(\w+):\s*\[(.*?)\]', block, re.M | re.S)}


def route(lang, path):
    rel = path.relative_to(DOCS / lang).as_posix()
    return '/' + re.sub(r'(^|/)index\.md$', r'\1', rel).removesuffix('.md')


def test_every_translated_page_names_its_english_source():
    assert PAGES
    for lang, path in PAGES:
        page, source, state = status.status(lang, path)
        assert state != 'no-source', f'docs/{page}: no source: in its frontmatter (--stamp it)'
        assert state != 'missing-source', f'docs/{page}: its source {source} does not exist'
        assert re.fullmatch(r'[0-9a-f]{12}', status.field(status.read(path), 'source_hash') or ''), page


def test_a_translated_page_imports_the_same_files_as_its_english_page():
    # The code and the results a page shows are imported (<<< @/...), never
    # retyped: a translation imports the same files, in the same order.
    for lang, path in PAGES:
        page, source, state = status.status(lang, path)
        if state in ('no-source', 'missing-source'):
            continue
        english = status.read(DOCS / source)
        wanted = [line for line in english.splitlines() if line.startswith('<<< ')]
        got = [line for line in status.read(path).splitlines() if line.startswith('<<< ')]
        assert got == wanted, f'docs/{page}: its imports differ from docs/{source}'


def test_every_translated_page_is_in_its_language_nav_and_every_entry_has_its_page():
    listed = translated_routes()
    for lang, path in PAGES:
        r = route(lang, path)
        if r == '/' or r.startswith('/blog/'):
            continue                     # the language's home, and posts listed by the blog
        if r.startswith('/cookbook/') and r != '/cookbook/' and '/cookbook/' in listed.get(lang, []):
            # a recipe is reached from the language's Cookbook index, which the generator writes
            index = (DOCS / lang / 'cookbook' / 'index.md').read_text(encoding='utf-8')
            assert f'(./{r[len("/cookbook/"):]}.md)' in index, f'docs/{lang}{r}: not linked from docs/{lang}/cookbook/index.md'
            continue
        assert r in listed.get(lang, []), f'docs/{lang}{r}: not in TRANSLATED.{lang} (locales.js)'
    for lang, routes in listed.items():
        for r in routes:
            file = DOCS / lang / (r.strip('/') + ('/index.md' if r.endswith('/') else '.md'))
            assert file.is_file(), f'TRANSLATED.{lang} lists {r}, and docs/{lang}{r} does not exist'


@pytest.mark.skipif(not NODE, reason='node is needed to run the site config')
def test_python_and_the_site_compute_the_same_hash(tmp_path):
    sample = tmp_path / 'sample.md'
    sample.write_bytes('# Title\r\n\r\nSome text, 中文.\r\n'.encode('utf-8'))
    js = subprocess.run([NODE, str(DOCS / '.vitepress' / 'translations.js'), str(sample)],
                        capture_output=True, text=True, check=True).stdout.strip()
    assert js == status.source_hash(sample.read_text(encoding='utf-8'))


@pytest.mark.skipif(not NODE, reason='node is needed to run the site config')
def test_the_build_marks_a_translation_whose_english_changed():
    module = (DOCS / '.vitepress' / 'translations.js').as_uri()
    english = status.source_hash(status.read(DOCS / 'guide' / 'installation.md'))
    script = f"""
      const {{ markStaleTranslation }} = await import({json.dumps(module)});
      const docs = {json.dumps(str(DOCS))};
      const fresh = {{ frontmatter: {{ source: 'guide/installation.md', source_hash: '{english}' }} }};
      const old = {{ frontmatter: {{ source: 'guide/installation.md', source_hash: '000000000000' }} }};
      markStaleTranslation(fresh, docs); markStaleTranslation(old, docs);
      console.log(JSON.stringify([fresh.frontmatter.translationStale ?? false,
                                  old.frontmatter.translationStale ?? false, old.frontmatter.englishLink]));
    """
    out = subprocess.run([NODE, '--input-type=module', '-e', script],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert json.loads(out) == [False, True, '/guide/installation']


def test_the_report_lists_a_stale_page_without_failing(tmp_path, monkeypatch, capsys):
    docs = tmp_path / 'docs'
    (docs / 'guide').mkdir(parents=True)
    (docs / 'guide' / 'a.md').write_text('# A\n', encoding='utf-8')
    (docs / 'zh' / 'guide').mkdir(parents=True)
    (docs / 'zh' / 'guide' / 'a.md').write_text(
        '---\nsource: guide/a.md\nsource_hash: 000000000000\n---\n\n# A\n', encoding='utf-8')
    monkeypatch.setattr(status, 'DOCS', docs)
    monkeypatch.setattr('sys.argv', ['translation-status.py'])
    assert status.main() == 0
    out = capsys.readouterr().out
    assert '1 translated pages, 0 up to date' in out and 'stale' in out and 'docs/zh/guide/a.md' in out
