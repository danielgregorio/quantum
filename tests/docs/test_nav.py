"""The top nav (docs/.vitepress/locales.js, nav()) has the site's sections, in every language.

Roadmap and Community were added to the nav once and lost in a merge the same
day, with every other check green; this names what the nav must link to.
"""

import re
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[2] / 'docs' / '.vitepress' / 'locales.js'
TEXT = LOCALES.read_text(encoding='utf-8')
SECTIONS = ['home', 'docs', 'showcase', 'blog', 'changelog', 'status', 'roadmap', 'community', 'sponsor']


def nav_body():
    return re.search(r'function nav\(key\) \{(.*?)\n\}', TEXT, re.S).group(1)


def test_the_nav_links_every_section():
    body = nav_body()
    for section in SECTIONS:
        assert f'text: t.{section}' in body, f'the top nav has no {section} entry'


def test_every_language_names_every_section():
    labels = re.search(r'const TEXT = \{(.*?)\n\}', TEXT, re.S).group(1)
    for lang, block in re.findall(r'^  (\w+): \{(.*?)^  \},', labels, re.S | re.M):
        for section in SECTIONS:
            assert re.search(rf'\b{section}: ', block), f'{lang} has no label for {section}'


def test_translated_sections_link_to_the_translation():
    body = nav_body()
    for section in ('showcase', 'roadmap', 'community'):
        assert re.search(rf"t\.{section}, link: link\(key, '/{section}/'\)", body), section
