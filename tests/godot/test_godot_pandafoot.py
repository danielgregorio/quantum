"""PandaFoot (projects/pandafoot/pandafoot.q, PLAN_PANDAFOOT.md) played through the play protocol.

A manager starts a game in a world of a number, looks at the screens a key away, plays a live round at 16x
and comes back to the dashboard with the table, the purse and the players changed; the same number makes
the same world; a saved game continues where it was; in Portuguese, the screens say it in Portuguese.
"""

import json
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
    """From the title: a new game, the world as it is (7), one manager of the 4th division's `club`-th club, started."""
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
    assert [len(c['players']) for c in clubs] == [22] * 40
    assert [sum(c['div'] == d for c in clubs) for d in (1, 2, 3, 4)] == [10] * 4
    assert [(t['name'], t['club'], t['patience']) for t in first['managers']] == [('Manager 1', 34, 50)]
    assert clubs[34]['manager'] == 1
    assert clubs[34]['div'] == 4                                      # a manager starts in the 4th division
    geniuses = [(c['div'], p['strength']) for c in clubs for p in c['players'] if p['genius']]
    hidden = [s for div, s in geniuses if div >= 3]
    assert 3 <= len(geniuses) <= 5 and len(hidden) == 1 and 40 <= hidden[0] <= 42
    assert all(div == 1 for div, s in geniuses if div < 3)
    names = [p['name'] for c in clubs for p in c['players']]        # no two players of the world share a name
    assert len(set(names)) == len(names) == 880
    strength = {d: sum(p['strength'] for c in clubs if c['div'] == d for p in c['players']) / 220 for d in (1, 2, 3, 4)}
    assert strength[1] > strength[2] > strength[3] > strength[4]
    rounds = first['fixtures']
    assert len(rounds) == 18 and all(len(r) == 20 for r in rounds)
    pairs = sorted(tuple(g) for r in rounds for g in r)
    assert len(pairs) == 360 == len(set(pairs))                 # each club at home and away to each other once
    assert all(clubs[h]['div'] == clubs[a]['div'] for h, a in pairs)  # of its own division
    for r in rounds:
        assert sorted(c for g in r for c in g) == list(range(40))


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
        # to the last minute first: a round's ticks carry many events, an answer at most 500 of them
        game.until('minute >= 89', max_ticks=2000)
        after = game.until("scene == 'results'", max_ticks=600)
        assert after['stopped'] == 'condition'
        state = after['state']['game']
        assert state['matchday'] == 1 and len(state['last']) == 20
        clubs = state['clubs']
        assert sum(c['played'] for c in clubs) == 40 and sum(c['gf'] for c in clubs) == sum(c['ga'] for c in clubs)
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
        assert [(t['name'], t['club']) for t in seen['state']['game']['managers']] == [('Técnico 1', 34)]
        squad = game.act(tap=['squad'], ticks=3)
        assert tables(squad)[0]['table'][:4] == ['#', 'Nome', 'Pos', 'For']
        assert {row[2].split('/')[0] for row in tables(squad)[0]['rows']} <= {'GOL', 'DEF', 'MEI', 'ATA'}


# --- what the first people to play it found (PLAN_PANDAFOOT.md, the fixes of 2026-10-23) ---

def play_round(game):
    """From the dashboard: a round at 16x, to its results."""
    live = game.act(tap=['select'], ticks=3)
    assert live['scene'] == 'round', live['scene']
    for _ in range(3):
        game.act(tap=['faster'], ticks=2)
    game.until('minute >= 89', max_ticks=2000)
    return game.until("scene == 'results'", max_ticks=600)


def test_a_season_keeps_the_rules_of_football(pandafoot, godot):
    """A second yellow is a red, and who is sent off, carried off or taken off does nothing more in the match;
    three substitutions at most; who is hurt or banned misses the next match; the crowd fits the ground."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        reds = knocks = subs = 0
        for rnd in range(18):
            after = play_round(game)
            state = after['state']['game']
            for m in state['last']:
                assert 0 < m['crowd'] <= state['clubs'][m['home']]['capacity']
                for short in (state['clubs'][m['home']]['short'], state['clubs'][m['away']]['short']):
                    events = [e for e in reversed(m['events']) if e.get('club') == short]   # in the order they came
                    gone, booked, came = set(), {}, 0
                    for e in events:
                        if e['kind'] == 'tactic':
                            continue
                        assert e['who'] not in gone, (rnd, e)       # off the pitch: no goal, no card, no knock
                        if e['kind'] == 'card':
                            assert booked.get(e['who'], 0) == 0, (rnd, e)   # a second yellow is a red, not a card
                            booked[e['who']] = 1
                        if e['kind'] in ('red', 'knock'):
                            gone.add(e['who'])
                            reds += e['kind'] == 'red'
                            knocks += e['kind'] == 'knock'
                        if e['kind'] == 'sub':
                            assert e['who'] not in gone                    # who comes on had not played
                            gone.add(e['out'])
                            came += 1
                    assert came <= 3
                    subs += came
            if state['matchday'] < 18:                                # the next match's elevens are ready
                for c in state['clubs']:
                    assert len([p for p in c['players'] if p['xi']]) == 11
                    assert not [p['name'] for p in c['players'] if p['xi'] and (p['injured'] or p['suspended'])]
                seen = game.act(tap=['select'], ticks=3)
        # after the last results, a look at the table and back: the season's end. It was the dashboard, round 19 of
        # 18, the last match again, and again (its first players could not get past it)
        assert game.act(tap=['standings'], ticks=3)['scene'] == 'standings'
        seen = game.act(tap=['cancel'], ticks=3)
        assert seen['scene'] == 'season-end'
        clubs = seen['state']['game']['clubs']

        def table(d):
            return sorted((i for i, c in enumerate(clubs) if c['div'] == d),
                          key=lambda i: (-clubs[i]['points'], -(clubs[i]['gf'] - clubs[i]['ga']), -clubs[i]['gf'], i))
        tables_then = {d: table(d) for d in (1, 2, 3, 4)}
        again = game.act(tap=['select'], ticks=3)['state']['game']                    # New season
        assert again['matchday'] == 0 and again['season'] == 2027
        divs = [c['div'] for c in again['clubs']]
        for d in (1, 2, 3):                                                      # two up and two down
            assert [divs[i] for i in tables_then[d][8:]] == [d + 1, d + 1]
            assert [divs[i] for i in tables_then[d + 1][:2]] == [d, d]
        assert [divs.count(d) for d in (1, 2, 3, 4)] == [10] * 4
        assert again['honours'][0]['season'] == 2026
        assert again['honours'][0]['champions'][3] == clubs[tables_then[4][0]]['name']
        assert all(sorted(c for g in r for c in g) == list(range(40)) for r in again['fixtures'])
        assert knocks > 0 and subs > 0
        assert reds > 0


def test_resting_rests_and_the_managers_eleven_stays(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        seen = new_game(game)
        mine = seen['state']['game']['clubs'][4]
        before_formation = mine['formation']
        eleven = {p['name'] for p in mine['players'] if p['xi']}
        assert len(eleven) == 11 and all(p['form'] == 100 for p in mine['players'])
        after = play_round(game)
        mine = after['state']['game']['clubs'][4]
        for p in mine['players']:                                 # a week: who played tires, who did not rests
            assert p['form'] == (94 if p['name'] in eleven or p['played'] else 100), p
        still = {p['name'] for p in mine['players'] if p['xi']}
        assert len(still) == 11
        # the manager's eleven, but for its gaps: who cannot play, and the places the formation of the next match
        # (Auto: by the next opponent) no longer has
        shape = {'4-4-2': [4, 4, 2], '4-3-3': [4, 3, 3], '5-3-2': [5, 3, 2], '4-5-1': [4, 5, 1], '3-4-3': [3, 4, 3],
                 '5-4-1': [5, 4, 1]}
        was, now = shape[before_formation], shape[mine['formation']]
        moved = sum(max(0, a - b) for a, b in zip(was, now))
        out = {p['name'] for p in mine['players'] if p['injured'] or p['suspended']}
        assert len(eleven - out - still) <= moved
        computer = after['state']['game']['clubs'][0]
        assert len([p for p in computer['players'] if p['xi']]) == 11


def test_a_dearer_ticket_keeps_people_away(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        finances = game.act(tap=['finances'], ticks=3)
        def crowd(seen):
            """'Crowd at this price:  9.350-12.650': about how many, never exactly (the day changes it)"""
            low, high = [t for t in texts(seen) if t.startswith('Crowd at this price:')][0].split()[-1].split('-')
            return int(low.replace('.', '')), int(high.replace('.', ''))
        low_15, high_15 = crowd(finances)
        assert low_15 < high_15
        for _ in range(35):                                       # Ticket +$1, to $50
            seen = game.act(tap=['select'], ticks=2)
        assert any(t.startswith('Ticket:') and t.endswith('$50') for t in texts(seen))
        assert crowd(seen)[1] < low_15 / 3


def test_a_new_game_starts_from_nothing(pandafoot, godot):
    """A game played before leaves no manager behind, and the league starts in its first season again."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        play_round(game)
        game.act(tap=['select'], ticks=3)
        game.act(tap=['cancel'], ticks=3)                         # saves and goes to the title
        again = game.act(tap=['select'], ticks=3)                 # New game
        state = again['state']['game']
        assert again['scene'] == 'new-game' and state['managers'] == [] and state['season'] == 2026
        assert state['matchday'] == 0


def test_a_substitution_in_a_pause(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        game.act(tap=['select'], ticks=3)
        game.act(ticks=120)
        paused = game.act(tap=['pause'], ticks=2)
        assert texts(paused)[-1].startswith('[F1] Substitution (0/3)')
        choosing = game.act(tap=['lineup'], ticks=2)
        off = [i['button'] for i in menus(choosing)[0]['items'] if i['shown']]
        assert len(off) == 11 and 'Who comes off?' in texts(choosing)
        coming = game.act(tap=['select'], ticks=2)                # the first of the eleven comes off
        assert any(t.startswith('Who comes on for ') for t in texts(coming))
        done = game.act(tap=['select'], ticks=2)                  # the first of the bench comes on
        events = [t for tb in tables(done) for row in tb['rows'] for t in row if '⇄' in t]
        assert len(events) == 1 and ' for ' in events[0]
        assert texts(done)[-1].startswith('[F1] Substitution (1/3)')


def test_the_results_say_who_scored_and_who_came(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        after = play_round(game)
        shown = texts(after)
        assert any(t.startswith('═══ YOUR MATCH ═══') for t in shown)
        assert any(t.startswith('Crowd: ') for t in shown) and any(t.startswith('Man of the match: ') for t in shown)
        goals = sum(m['hg'] + m['ag'] for m in after['state']['game']['last'])
        clubs = after['state']['game']['clubs']
        mine = [m for m in after['state']['game']['last'] if clubs[m['home']]['div'] == clubs[34]['div']]
        assert len(mine) == len(tables(after)[0]['rows']) == 5                   # the manager's division's five
        for m, row in zip(mine, tables(after)[0]['rows']):
            sides = [[f"{e['who']} {int(e['minute'])}′" for e in reversed(m['events'])
                      if e['kind'] == 'goal' and e['club'] == clubs[c]['short']] for c in (m['home'], m['away'])]
            full = ', '.join(sides[0]) + ' / ' + ', '.join(sides[1]) if sides[0] or sides[1] else ''
            assert len(sides[0]) == m['hg'] and len(sides[1]) == m['ag']
            shown = full.strip()                                  # as a table cell reads, without its padding
            assert shown.startswith(row[3]) and (row[3] == shown or len(full) > 42), (row, full)   # cut at 42
        assert goals > 0
        standings = game.act(tap=['standings'], ticks=3)
        assert '═ TOP SCORERS ═' in texts(standings)
        top = tables(standings)[0]['rows']
        assert top and int(top[0][0]) >= int(top[-1][0])
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_a_match_in_numbers(pandafoot, godot):
    """The shots (on target), the ball and who is pressing, as the match goes; the shots in the results."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        game.act(tap=['select'], ticks=3)
        live = game.act(ticks=400)
        line = texts(live)[2]
        assert line.startswith('Shots ') and ' Ball ' in line and 'Pressing: ' in line, line
        for _ in range(3):
            game.act(tap=['faster'], ticks=2)
        game.until('minute >= 89', max_ticks=2000)
        after = game.until("scene == 'results'", max_ticks=600)
        for m in after['state']['game']['last']:
            for side, goals in ((m['h'], m['hg']), (m['a'], m['ag'])):
                assert side['shots'] >= side['on'] >= goals
        mine = [t for t in texts(after) if t.startswith('Man of the match: ')][0]
        assert ' Shots ' in mine


def test_any_clubs_squad_from_the_table(pandafoot, godot):
    """F7, a club's row, Enter: its squad (the hidden genius not marked); Esc: the table again."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        table = game.act(tap=['standings'], ticks=3)
        rows = [i['button'] for i in menus(table)[0]['items'] if i['shown']]
        assert len(rows) == 10 and sum('►' in r for r in rows) == 1           # the manager's club marked
        game.act(tap=['down'], ticks=2)
        game.act(tap=['down'], ticks=2)
        squad = game.act(tap=['select'], ticks=3)
        assert squad['scene'] == 'squad'
        club = squad['state']['game']['clubs'][int(squad['state']['game']['viewing'])]
        assert texts(squad)[0].startswith('SQUAD - ' + club['name']) and club['name'] in rows[2]
        assert len(tables(squad)[0]['rows']) == 22
        if club['div'] >= 3:
            assert not [r for r in tables(squad)[0]['rows'] if '◆' in r[4]]
        back = game.act(tap=['cancel'], ticks=3)
        assert back['scene'] == 'standings' and back['state']['game']['viewing'] == -1
        mine = game.act(tap=['squad'], ticks=3)
        assert texts(mine)[0].startswith('SQUAD - Lontra AC')
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


# --- the career (PLAN_PANDAFOOT.md Phase 2): a save made to the point, and the game continued from it ---

def saved_then(pandafoot, godot, folder, change):
    """A new game saved in `folder`, its state changed by `change(state)`, saved again for a session to continue."""
    with PlaySession(pandafoot, binary=godot, persist_dir=folder):
        pass
    with PlaySession(pandafoot, binary=godot, persist_dir=folder) as game:
        new_game(game)
    save = folder / 'quantum-save-1.json'
    data = json.loads(save.read_text())
    change(data['game'])
    save.write_text(json.dumps(data))


def continued(game):
    game.act(ticks=3)
    game.act(tap=['down'], ticks=2)                            # Continue 1
    return game.act(tap=['select'], ticks=3)


def test_the_board_sacks_and_other_clubs_offer(pandafoot, godot, tmp_path):
    """A board at the end of its patience, the purse deep in the red: after the round, sacked; the job: two clubs of
    the 4th that no one manages, and the career goes on at one of them."""
    def at_the_end(state):
        state['managers'][0]['patience'] = 1
        state['clubs'][34]['balance'] = -10_000_000
    saved_then(pandafoot, godot, tmp_path, at_the_end)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        seen = continued(game)
        assert seen['scene'] == 'dashboard'
        assert any('The board is losing its patience' in t for t in texts(seen))
        after = play_round(game)
        assert any(t.startswith('✖ SACKED: Manager 1') for t in texts(after))
        job = game.act(tap=['select'], ticks=3)
        assert job['scene'] == 'job' and texts(job)[0] == '✖ SACKED'
        offers = [i['button'] for i in menus(job)[0]['items'] if i['shown']]
        state = job['state']['game']
        assert len(offers) == 2 and all('(4th division' in o for o in offers)
        assert [b['button'] for b in menus(job)[1]['items'] if b['shown']] == ['End the career']
        taken = game.act(tap=['select'], ticks=3)
        state = taken['state']['game']
        assert taken['scene'] == 'dashboard'
        mine = state['managers'][0]
        assert mine['club'] != 34 and state['clubs'][mine['club']]['manager'] == 1 and state['clubs'][34]['manager'] == 0
        assert mine['patience'] == 50 and mine['career']['sacked'] == 1
        assert mine['career']['clubs'] == ['Lontra AC', state['clubs'][mine['club']]['name']]
        assert texts(taken)[0].startswith('PANDAFOOT  ' + state['clubs'][mine['club']]['name'])
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_a_sacked_manager_can_end_the_career(pandafoot, godot, tmp_path):
    def at_the_end(state):
        state['managers'][0]['patience'] = 1
        state['clubs'][34]['balance'] = -10_000_000
    saved_then(pandafoot, godot, tmp_path, at_the_end)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        game.act(tap=['select'], ticks=3)                         # the job
        for _ in range(2):                                        # down past the two offers to End the career
            game.act(tap=['down'], ticks=2)
        over = game.act(tap=['select'], ticks=3)
        assert over['scene'] == 'career-over', over['scene']
        state = over['state']['game']
        assert state['managers'] == [] and state['retired'][0]['name'] == 'Manager 1'
        assert any(t.startswith('═══ THE END OF THE CAREER') for t in texts(over))
        assert game.act(tap=['select'], ticks=3)['scene'] == 'title'


def test_a_promoted_manager_is_offered_a_bigger_club(pandafoot, godot, tmp_path):
    """The last round, top of the 4th by far: promoted, and two clubs of the 2nd offer; staying keeps the club."""
    def last_round_on_top(state):
        state['matchday'] = 17
        state['clubs'][34]['points'] = 99
    saved_then(pandafoot, godot, tmp_path, last_round_on_top)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        end = game.act(tap=['select'], ticks=3)
        assert end['scene'] == 'season-end'
        assert any(t.startswith('Lontra AC: 1º of the 4th division, promoted!') for t in texts(end))
        offer = game.act(tap=['select'], ticks=3)                  # New season
        assert offer['scene'] == 'job' and texts(offer)[0] == '✉ AN OFFER'
        state = offer['state']['game']
        offered = state['jobs'][0]['clubs']
        assert len(offered) == 2 and all(state['clubs'][i]['div'] == 2 and state['clubs'][i]['manager'] == 0
                                         for i in offered)
        assert state['clubs'][34]['div'] == 3 and state['managers'][0]['career']['ups'] == 1
        stays = [b['button'] for b in menus(offer)[1]['items'] if b['shown']]
        assert stays == ['Stay at Lontra AC']
        for _ in range(2):                                         # past the two offers, to staying
            game.act(tap=['down'], ticks=2)
        back = game.act(tap=['select'], ticks=3)
        assert back['scene'] == 'dashboard' and back['state']['game']['managers'][0]['club'] == 34
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]
