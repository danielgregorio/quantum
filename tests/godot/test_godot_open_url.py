"""qg:open-url in Godot: a button that opens a web address (PandaFoot's changelog, a game's page).

Played through the play protocol, it opens nothing and says what it would have opened: an "open-url" event with
the address, written or put together by an expression. An address that is not http:// or https:// is refused
when the game is compiled, and ignored when an expression gives one. url_encode() puts a text (a club's name, with
its accents and an &) into an address.
"""

from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.godot import compile_game
from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

LINKS = '''<q:application id="links" type="game">
  <q:set name="page" value="news" type="string" />
  <qg:scene name="title" width="320" height="180">
    <qg:menu>
      <qg:button label="What's new"><qg:open-url href="https://example.com/game/changelog/" /></qg:button>
      <qg:button label="Its page"><qg:open-url href="{'https://example.com/game/' + page + '/'}" /></qg:button>
      <qg:button label="Not a page"><qg:open-url href="{'file:///' + page}" /></qg:button>
      <qg:button label="A form"><qg:open-url href="{'https://example.com/form?club=' + url_encode('Onça Pintada & 2º') + '&kind=Sugestão'}" /></qg:button>
    </qg:menu>
  </qg:scene>
</q:application>
'''


def build(tmp_path: Path, source: str) -> Path:
    src = tmp_path / 'game.q'
    src.write_text(source, encoding='utf-8')
    return Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(tmp_path / 'godot'),
                             source_dir=str(tmp_path)))


@pytest.fixture(scope='module')
def links(godot, tmp_path_factory) -> Path:
    out = build(tmp_path_factory.mktemp('links'), LINKS)
    assert check_project(out, binary=godot) == []
    return out


def test_a_button_opens_an_address(links, godot):
    with PlaySession(links, binary=godot) as game:
        game.act(ticks=3)
        first = game.act(tap=['select'], ticks=3)
        assert [e['url'] for e in first['events'] if e['kind'] == 'open-url'] == ['https://example.com/game/changelog/']
        game.act(tap=['down'], ticks=2)
        second = game.act(tap=['select'], ticks=3)
        assert [e['url'] for e in second['events'] if e['kind'] == 'open-url'] == ['https://example.com/game/news/']
        game.act(tap=['down'], ticks=2)
        third = game.act(tap=['select'], ticks=3)
        assert [e for e in third['events'] if e['kind'] == 'open-url'] == []        # file:// opens nothing
        assert third['scene'] == 'title'                                             # and the game goes on
        game.act(tap=['down'], ticks=2)
        fourth = game.act(tap=['select'], ticks=3)                                   # url_encode(): a text in it
        assert [e['url'] for e in fourth['events'] if e['kind'] == 'open-url'] == [
            'https://example.com/form?club=On%C3%A7a%20Pintada%20%26%202%C2%BA&kind=Sugestão']


@pytest.mark.parametrize('href', ['file:///etc/passwd', 'javascript:alert(1)', 'example.com', ''])
def test_an_address_that_is_not_a_web_page_is_refused(tmp_path, href):
    source = LINKS.replace('https://example.com/game/changelog/', href)
    with pytest.raises(GameCompileError, match='an http:// or https:// address'):
        build(tmp_path, source)
