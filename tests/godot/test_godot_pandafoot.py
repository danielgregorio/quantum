"""PandaFoot (projects/pandafoot/pandafoot.q, PLAN_PANDAFOOT.md Phase 1) played through the play protocol.

A manager starts a game in a world of a number, looks at the screens a key away, plays a live round at 16x
and comes back to the dashboard with the table, the purse and the players changed; the same number makes
the same world; a saved game continues where it was; in Portuguese, the screens say it in Portuguese.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'


@pytest.fixture(scope='module')
def pandafoot(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out_dir = tmp_path_factory.mktemp('pandafoot')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(PROJECTS / 'pandafoot' / 'pandafoot.q')),
                            str(out_dir / 'godot'), source_dir=str(PROJECTS / 'pandafoot')))
    assert check_project(out, binary=godot) == []
    return out


def menus(obs):
    return [v for v in obs['screen'] if v['kind'] == 'menu']


def huds(obs):
    return [v for v in obs['screen'] if v['kind'] == 'hud']


def texts(obs):
    return [item for h in huds(obs) for item in h['items'] if isinstance(item, str)]


def tables(obs):
    return [item for h in huds(obs) for item in h['items'] if isinstance(item, dict) and 'table' in item]


def new_game(game, club=4):
    """From the title: a new game, the world as it is (7), one manager of `club`, started."""
    game.act(ticks=3)
    game.act(tap=['select'], ticks=3)                       # Novo jogo
    for _ in range(3 + club):                               # past the world, the slot and the name, to the club
        game.act(tap=['down'], ticks=2)
    game.act(tap=['select'], ticks=3)
    seen = game.observe()
    for _ in range(12):                                     # down to the last menu's first button: start
        start = menus(seen)[-1]
        if start.get('keys', True) and start['focus'] == 0:
            break
        seen = game.act(tap=['down'], ticks=2)
    game.act(tap=['select'], ticks=3)
    return game.until("scene == 'dashboard'", max_ticks=200)


def test_a_world_is_made_from_its_number(pandafoot, godot):
    worlds = []
    for _ in range(2):
        with PlaySession(pandafoot, binary=godot) as game:
            seen = new_game(game)
            worlds.append(seen['state']['game'])
    first, again = worlds
    assert first['clubs'] == again['clubs'] and first['fixtures'] == again['fixtures']
    clubs = first['clubs']
    assert [len(c['players']) for c in clubs] == [22] * 10
    assert first['managers'] == [{'name': 'Manager 1', 'club': 4}] and clubs[4]['manager'] == 1
    geniuses = [(c['level'], p['strength']) for c in clubs for p in c['players'] if p['genius']]
    assert len(geniuses) == 3 and sum(1 for level, s in geniuses if level == 3 and 40 <= s <= 42) == 1
    for c in clubs:                                                  # no two players of a club share a name
        assert len({p['name'] for p in c['players']}) == 22
    rounds = first['fixtures']
    assert len(rounds) == 18 and all(len(r) == 5 for r in rounds)
    pairs = sorted(tuple(g) for r in rounds for g in r)
    assert len(pairs) == 90 == len(set(pairs))                  # each club at home and away to each other once
    for r in rounds:
        assert sorted(c for g in r for c in g) == list(range(10))


def test_the_screens_are_a_key_away(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        seen = new_game(game)
        assert texts(seen)[0].startswith('PANDAFOOT  Lontra AC')
        squad = game.act(tap=['squad'], ticks=3)
        table = tables(squad)[0]
        assert table['table'][:4] == ['#', 'Name', 'Pos', 'Str'] and len(table['rows']) == 22
        lineup = game.act(tap=['lineup'], ticks=3)
        rows = [i['button'] for i in menus(lineup)[0]['items']]
        assert len(rows) == 22 and sum('ELEVEN' in r for r in rows) == 11
        assert sum('ELEVEN GK' in r for r in rows) == 1
        standings = game.act(tap=['tactics'], ticks=3)
        assert texts(standings)[0].startswith('TACTICS - Lontra AC x ')
        for key, title in (('cancel', 'PANDAFOOT'), ('standings', 'PANDA LEAGUE'), ('cancel', 'PANDAFOOT'),
                           ('finances', 'FINANCES')):
            seen = game.act(tap=[key], ticks=3)
            assert texts(seen)[0].startswith(title), (key, texts(seen)[0])


def test_a_live_round_changes_the_table_the_purses_and_the_players(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        before = new_game(game)['state']['game']
        live = game.act(tap=['select'], ticks=3)
        assert live['scene'] == 'round' and len(tables(live)[1]['rows']) == 5      # the round's five matches
        for _ in range(3):
            game.act(tap=['faster'], ticks=2)
        assert '16x' in texts(game.observe())[1]
        after = game.until("scene == 'results'", max_ticks=2000)
        assert after['stopped'] == 'condition'
        state = after['state']['game']
        assert state['matchday'] == 1 and len(state['last']) == 5
        clubs = state['clubs']
        assert sum(c['played'] for c in clubs) == 10 and sum(c['gf'] for c in clubs) == sum(c['ga'] for c in clubs)
        assert sum(c['points'] for c in clubs) == sum(2 if m['hg'] == m['ag'] else 3 for m in state['last'])
        goals = sum(m['hg'] + m['ag'] for m in state['last'])
        assert sum(p['goals'] for c in clubs for p in c['players']) == goals
        for m in state['last']:                                   # the home side took the gate, all paid a week
            home = clubs[m['home']]
            wages = sum(p['salary'] for p in home['players']) / 4
            assert home['gate'] > 0
            assert home['balance'] == pytest.approx(before['clubs'][m['home']]['balance'] + home['gate'] - wages)
        assert any(e['kind'] == 'sound' and e['name'] == 'final' for e in after['events'])
        back = game.act(tap=['select'], ticks=3)
        assert back['scene'] == 'dashboard' and 'Round 2/18' in texts(back)[0]


def test_a_saved_game_continues_where_it_was(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        seen = new_game(game)
        clubs = seen['state']['game']['clubs']
        title = game.act(tap=['cancel'], ticks=3)                 # saves and goes to the title
        assert title['scene'] == 'title'
        buttons = [i['button'] for i in menus(title)[0]['items'] if i['shown']]
        assert buttons[:2] == ['New game', 'Continue 1']
        game.act(tap=['down'], ticks=2)
        back = game.act(tap=['select'], ticks=3)
        assert back['scene'] == 'dashboard' and back['state']['game']['clubs'] == clubs


def test_in_portuguese(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot, lang='pt') as game:
        seen = new_game(game)
        assert texts(seen)[0].endswith('Rodada 1/18  2026') and texts(seen)[1].startswith('Saldo:')
        assert seen['state']['game']['managers'] == [{'name': 'Técnico 1', 'club': 4}]
        squad = game.act(tap=['squad'], ticks=3)
        assert tables(squad)[0]['table'][:4] == ['#', 'Nome', 'Pos', 'For']
        assert {row[2].split('/')[0] for row in tables(squad)[0]['rows']} <= {'GOL', 'DEF', 'MEI', 'ATA'}
