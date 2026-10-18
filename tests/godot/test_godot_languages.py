"""Every text a game shows has a phrase in each of its languages.

A qg:phrase is found by its text exactly, and a text without one stays as
written: a phrase that does not match, or a text added later, would leave
the screen half translated with nothing to say so. This reads each game's
.q and lists what it shows as written: a label, a dialogue's lines and who
says them, a qg:text's literal value, and the literal values of the q:sets
a qg:text shows. Texts put together by an expression (Chess's status, Arena's
round) are checked by playing them (test_godot_play.py).
"""

import re
from pathlib import Path

import pytest

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'

# the same in every language: a name
SAME = {'HOPPER', 'KEEP', 'DELVE'}


def _unescape(text: str) -> str:
    return text.replace('&#10;', '\n').replace('&amp;', '&').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')


def shown(source: str) -> set:
    texts = set()
    for attr in ('label', 'local-label', 'text', 'who'):
        for m in re.finditer(rf'<qg:(?!phrase)[\w-]+[^>]*?\s{attr}="([^"{{][^"]*)"', source):
            texts.add(m.group(1))
    texts |= set(re.findall(r"<qg:text value=\"\{'([^']*)'\}\"", source))
    for name in set(re.findall(r'<qg:text bind="(\w+)"', source)):
        texts |= set(re.findall(rf'<q:set name="{name}" value="([^"{{][^"]*)"', source))
    return {_unescape(t) for t in texts} - SAME


def phrases(source: str) -> dict:
    out = {}
    for m in re.finditer(r'<qg:language lang="(\w+)"[^>]*>(.*?)</qg:language>', source, re.S):
        out[m.group(1)] = {_unescape(t) for t in re.findall(r'<qg:phrase text="([^"]*)"', m.group(2))}
    return out


GAMES = sorted(p for p in PROJECTS.glob('*/*.q') if '<qg:language' in p.read_text())


def test_the_games_have_languages():
    assert {p.stem for p in GAMES} >= {'arena', 'chess', 'creeps', 'drift', 'hopper', 'keep', 'pong', 'robot',
                                       'rpg', 'towers'}


@pytest.mark.parametrize('game', GAMES, ids=lambda p: p.stem)
def test_every_text_shown_has_a_phrase_in_each_language(game):
    source = game.read_text()
    texts = shown(source)
    assert texts, 'found no text: the reading above is out of date'
    for lang, known in phrases(source).items():
        assert sorted(texts - known) == [], f'{game.stem}: no lang="{lang}" phrase for these'
