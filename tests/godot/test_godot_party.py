"""Three players in a game for up to four: qg:multiplayer min-players= and qg:start-now in Godot.

Three headless Godots on localhost — one hosts, two join — run a game whose
qg:multiplayer says players="4" min-players="2". Nobody is the fourth: the
host starts with the three who are there (a timer of the waiting scene runs
qg:start-now once net_players() is 3), and from then on the game is a game of
three on every machine — three characters, each moved by its own player, the
same state everywhere.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay_peers, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

PARTY = '''<q:application id="party" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:multiplayer players="4" min-players="2" start="field" delay="2" />
  <qg:scene name="wait" width="320" height="240">
    <qg:menu>
      <qg:button label="Host" if="{net_status() == 'offline'}"><qg:host port="7777" /></qg:button>
      <qg:button label="Join" if="{net_status() == 'offline'}"><qg:join address="{'127.0.0.1:7777'}" /></qg:button>
    </qg:menu>
    <qg:timer every="5">
      <q:if condition="{net_players() >= 3}"><qg:start-now /></q:if>
    </qg:timer>
  </qg:scene>
  <qg:scene name="field" width="320" height="240" seed="3">
    <q:set name="here" value="{net_players()}" type="number" />
    <qg:character id="p1" controller="topdown" player="1" sheet="k" frame="0" x="40" y="40" hitbox="12x12" speed="60" />
    <qg:character id="p2" controller="topdown" player="2" sheet="k" frame="0" x="80" y="40" hitbox="12x12" speed="60" />
    <qg:character id="p3" controller="topdown" player="3" sheet="k" frame="0" x="120" y="40" hitbox="12x12" speed="60"
                  if="{net_players() >= 3}" />
    <qg:character id="p4" controller="topdown" player="4" sheet="k" frame="0" x="160" y="40" hitbox="12x12" speed="60"
                  if="{net_players() >= 4}" />
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('party') / 'party.q'
    src.write_text(PARTY, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def presses(*holds):
    """A lobby tape: each (action, tick) pressed for two ticks."""
    return tape_from_holds([(a, t, t + 2) for a, t in holds])


TAPES = [tape_from_holds([('right', 5, 35)]),    # player 1, the host
         tape_from_holds([('down', 5, 35)]),     # player 2
         tape_from_holds([('left', 5, 25)])]     # player 3


def check_three(states):
    assert states[0] == states[1] == states[2]       # one game, on three machines
    field = states[0]['field']
    assert field['here'] == 3.0 and set(field['nodes']) == {'p1', 'p2', 'p3'}   # no fourth seat
    p1, p2, p3 = (field['nodes'][p] for p in ('p1', 'p2', 'p3'))
    assert p1['x'] > 40 and p1['y'] == 40                # each moved by its own player
    assert p2['y'] > 40 and p2['x'] == 80
    assert p3['x'] < 120 and p3['y'] == 40


def test_the_host_starts_with_the_three_who_are_there(project, godot):
    # the waiting scene's own menu: the host hosts at once, the others join later, a second apart
    # (the seats go in the order they arrive)
    lobby = [presses(('select', 5)), presses(('down', 5), ('select', 60)), presses(('down', 5), ('select', 120))]
    check_three(replay_peers(project, 60, TAPES, binary=godot, lobby_tapes=lobby))


def test_from_the_command_line_the_host_says_how_many_play(project, godot):
    check_three(replay_peers(project, 60, TAPES, binary=godot, players=3))
