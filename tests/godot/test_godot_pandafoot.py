"""PandaFoot (projects/pandafoot/pandafoot.q, PLAN_PANDAFOOT.md) played through the play protocol.

A manager starts a game in a world of a number, looks at the screens a key away, plays a live round at 16x
and comes back to the dashboard with the table, the purse and the players changed; the same number makes
the same world; a saved game continues where it was; in Portuguese, the screens say it in Portuguese.
"""

import base64
import json
import math
import re
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'
MINE, MINE_NAME = 36, 'Camelo FC'    # the club new_game() draws in world 7: its path is the same every time


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


def new_game(game):
    """From the title: a new game, the world as it is (7), one manager, a club drawn for him, started. The draw is the
    world's and the ticks', so this path always draws the same club: MINE."""
    game.act(ticks=3)
    game.act(tap=['select'], ticks=3)                       # Novo jogo
    for _ in range(3):                                      # past the world, the slot and the name, to the draw
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
    assert [(t['name'], t['club'], t['patience']) for t in first['managers']] == [('Manager 1', MINE, 50)]
    assert clubs[MINE]['manager'] == 1
    assert clubs[MINE]['div'] == 4                                      # a manager starts in the 4th division
    geniuses = [(c['div'], p['strength']) for c in clubs for p in c['players'] if p['genius']]
    hidden = [s for div, s in geniuses if div >= 3]
    assert 3 <= len(geniuses) <= 5 and len(hidden) == 1 and 40 <= hidden[0] <= 42
    assert all(div == 1 for div, s in geniuses if div < 3)
    for c in clubs:                                                 # a club's first keeper is as good as its eleven
        best = sorted(c['players'], key=lambda p: -p['strength'])[:11]
        assert [p['pos'] for p in best].count('GK') == 1, c['name']
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
        assert texts(seen)[0].startswith('PANDAFOOT  ' + MINE_NAME)
        squad = game.act(tap=['squad'], ticks=3)
        table = tables(squad)[0]
        assert table['table'][:4] == ['#', 'Name', 'Pos', 'Str'] and len(table['rows']) == 22
        lineup = game.act(tap=['lineup'], ticks=3)
        rows = [i['button'] for i in menus(lineup)[0]['items']]
        assert len(rows) == 22 and sum('ELEVEN' in r for r in rows) == 11
        assert sum('ELEVEN GK' in r for r in rows) == 1
        standings = game.act(tap=['tactics'], ticks=3)
        assert texts(standings)[0].startswith(f'TACTICS - {MINE_NAME} x ')
        for key, title in (('cancel', 'PANDAFOOT'), ('standings', 'PANDA LEAGUE'), ('cancel', 'PANDAFOOT'),
                           ('finances', 'FINANCES')):
            seen = game.act(tap=[key], ticks=3)
            assert texts(seen)[0].startswith(title), (key, texts(seen)[0])


def test_a_live_round_changes_the_table_the_purses_and_the_players(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        before = new_game(game)['state']['game']
        live = game.act(tap=['select'], ticks=3)
        assert live['scene'] == 'round' and len(shown(live)[0]['items']) == 5      # the round's five matches
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
        assert [(t['name'], t['club']) for t in seen['state']['game']['managers']] == [('Técnico 1', MINE)]
        squad = game.act(tap=['squad'], ticks=3)
        assert tables(squad)[0]['table'][:4] == ['#', 'Nome', 'Pos', 'For']
        assert {row[2].split('/')[0] for row in tables(squad)[0]['rows']} <= {'GOL', 'DEF', 'MEI', 'ATA'}


def test_the_version_is_in_view_and_whats_new_opens_its_changelog(pandafoot, godot):
    """The version on the title and in the dashboard's corner, and "What's new" on the title opening the
    changelog's page in the player's language (asked for on the second evening). The newest version of each
    changelog is the game's."""
    source = (PROJECTS / 'pandafoot' / 'pandafoot.q').read_text(encoding='utf-8')
    version = re.search(r'<q:function name="game_version"><q:return value="\{.([0-9.]+).\}" />', source).group(1)
    for log in ('CHANGELOG.md', 'CHANGELOG.pt.md', 'CHANGELOG.es.md'):
        text = (PROJECTS / 'pandafoot' / log).read_text(encoding='utf-8')
        assert re.search(r'^## (\S+)', text, re.M).group(1) == version, log
    for lang, page in (('en', ''), ('pt', 'pt/'), ('es', 'es/')):
        with PlaySession(pandafoot, binary=godot, lang=lang) as game:
            title = game.act(ticks=3)
            assert f'PandaFoot v{version} beta' in texts(title)
            buttons = [i['button'] for i in menus(title)[0]['items'] if i['shown']]
            k = next(i for i, b in enumerate(buttons) if b.endswith(f'(v{version})'))
            for _ in range(k):
                game.act(tap=['down'], ticks=2)
            opened = game.act(tap=['select'], ticks=3)
            assert [e['url'] for e in opened['events'] if e['kind'] == 'open-url'] == [
                f'https://quantumframework.net/games/pandafoot/changelog/{page}']
            assert opened['scene'] == 'title'
            if lang == 'en':
                for _ in range(k):
                    game.act(tap=['up'], ticks=2)
                assert f'v{version} beta' in texts(new_game(game))


def fields(obs):
    """The report panel's menu, as {label: item}: its buttons by what they start with, its text box."""
    out = {}
    for item in menus(obs)[0]['items']:
        label = item.get('button', item.get('field', ''))
        out[label.split(':')[0]] = item
    return out


def type_report(game, text):
    """In the open panel: down to the text box, typed in, Enter; then down to Send."""
    game.act(tap=['down'], ticks=2)
    game.act(tap=['select'], ticks=2)
    game.act(text=text + '\n', ticks=3)
    game.act(tap=['down'], ticks=2)                                  # Attach my game
    return game.act(tap=['down'], ticks=2)                           # Send


def test_the_report_panel_opens_over_any_screen(pandafoot, godot):
    """The beta's reports (PLAN_PANDAFOOT.md): "Report a bug or suggest" on the title, F9 or the [!] on any screen,
    opens the panel over the screen, which stands still under it; it knows the screen and the option the cursor was
    on. With no server set up yet, a report waits in the outbox, with where the game is and the game itself."""
    with PlaySession(pandafoot, binary=godot) as game:
        title = game.act(ticks=3)
        assert PlaySession.screen(title, 'touch')['controls'][0]['action'] == 'report'      # the [!]
        buttons = [i['button'] for i in menus(title)[0]['items'] if i['shown']]
        for _ in range(buttons.index('Report a bug or suggest')):
            game.act(tap=['down'], ticks=2)
        panel = game.act(tap=['select'], ticks=3)
        assert panel['scene'] == 'report' and panel['under'] == 'title'
        assert texts(panel)[1].rstrip() == 'Where: title - Report a bug or suggest'       # fit to the box
        assert list(fields(panel)) == ['Kind', 'What happened, or your idea', 'Attach my game', 'Send', 'Back']
        assert fields(panel)['Kind']['button'] == 'Kind: Bug'
        game.act(tap=['select'], ticks=2)                                # a suggestion
        for _ in range(3):
            game.act(tap=['down'], ticks=2)
        empty = game.act(tap=['select'], ticks=3)                       # Send, with nothing written
        assert 'Write a few words first.' in texts(empty) and empty['state']['game']['outbox'] == []
        for _ in range(3):
            game.act(tap=['up'], ticks=2)
        type_report(game, 'A cup for the 4th division only')
        kept = game.act(tap=['select'], ticks=3)
        assert "Kept: it goes when the beta's server is ready." in texts(kept)
        assert 'Waiting to be sent: 1' in texts(kept)
        (entry,) = kept['state']['game']['outbox']
        report = entry['report']
        assert {k: report[k] for k in ('game', 'version', 'kind', 'text', 'screen', 'option')} == {
            'game': 'pandafoot', 'version': '2.2', 'kind': 'suggestion', 'text': 'A cup for the 4th division only',
            'screen': 'title', 'option': 'Report a bug or suggest'}
        assert report['context'].endswith('screen title; no game in progress')
        assert json.loads(report['save'])['scene'] == 'title'
        back = game.act(tap=['cancel'], ticks=3)                         # back where it was, the cursor too
        every = [i['button'] for i in menus(title)[0]['items']]           # its focus counts the hidden ones too
        assert back['scene'] == 'title' and back['state']['menus'] == [every.index('Report a bug or suggest')]
        for _ in range(buttons.index('Report a bug or suggest')):
            game.act(tap=['up'], ticks=2)
        seen = new_game(game)
        panel = game.act(tap=['report'], ticks=3)                       # F9 on the dashboard
        assert panel['scene'] == 'report' and panel['under'] == 'dashboard'
        assert 'Waiting to be sent: 1' in texts(panel)
        before = panel['state']['game']
        game.act(tap=['down'], ticks=2)
        game.act(tap=['down'], ticks=2)
        game.act(tap=['select'], ticks=2)                                # Attach my game: no
        assert fields(game.observe())['Attach my game']['button'] == 'Attach my game: no'
        for _ in range(2):
            game.act(tap=['up'], ticks=2)
        type_report(game, 'The table froze')
        second = game.act(tap=['select'], ticks=3)
        report = second['state']['game']['outbox'][1]['report']
        assert report['kind'] == 'bug' and report['screen'] == 'dashboard' and report['save'] == ''
        assert ('screen dashboard; world 7, season 2026, round 0/18, next league; Manager 1 at ' + MINE_NAME + ' '
                '(division 4,') in report['context']
        assert report['player'] == 'Manager 1'
        assert second['state']['game']['clubs'] == before['clubs']      # nothing of the game ran meanwhile
        back = game.act(tap=['report'], ticks=3)                         # F9 again closes it
        assert back['scene'] == 'dashboard' and texts(back)[0] == texts(seen)[0]
        live = game.act(tap=['select'], ticks=3)                         # and over a live round, which stops
        assert live['scene'] == 'round'
        over = game.act(tap=['report'], ticks=3)
        assert over['scene'] == 'report' and over['under'] == 'round'
        game.act(ticks=120)
        after = game.act(tap=['report'], ticks=3)
        assert after['scene'] == 'round' and after['state']['minute'] <= live['state']['minute'] + 1
        going = game.act(ticks=120)
        assert going['state']['minute'] > after['state']['minute'] + 1      # as 120 ticks of a round do


# --- the beta's reports, end to end: the game, the receiver (projects/beta-reports), a forge of the test ---

class Answers:
    """A server of the test that answers each report with the next of `answers` (a status and a JSON)."""

    def __init__(self, answers):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self.answers, self.received = list(answers), []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                outer.received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                status, body = outer.answers.pop(0) if len(outer.answers) > 1 else outer.answers[0]
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.http.server_port}/api/reports'
        threading.Thread(target=self.http.serve_forever, daemon=True).start()


def pandafoot_to(godot, folder: Path, url: str) -> Path:
    """PandaFoot with its reports going to `url`."""
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    source = (PROJECTS / 'pandafoot' / 'pandafoot.q').read_text(encoding='utf-8')
    server = '<q:function name="report_server"><q:return value="{\'\'}" /></q:function>'
    assert server in source
    folder.mkdir(parents=True, exist_ok=True)
    copy = folder / 'pandafoot.q'
    copy.write_text(source.replace(server, server.replace("\'\'", repr(url))), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(copy)), str(folder / 'godot'),
                            source_dir=str(PROJECTS / 'pandafoot')))
    assert check_project(out, binary=godot) == []
    return out


def send_one(game, text):
    """From the title: the panel, a bug written, sent."""
    game.act(ticks=3)
    game.act(tap=['report'], ticks=3)
    type_report(game, text)
    return game.act(tap=['select'], ticks=3)


def test_a_report_not_taken_now_waits_and_goes_later(godot, tmp_path):
    """The server down (503): the report stays in the outbox, kept between runs, and goes the next time the title
    is seen; one refused for what it is (422) is dropped."""
    answers = Answers([(503, {'error': 'down', 'message': 'Service Unavailable'}), (201, {'number': 4})])
    game_dir = pandafoot_to(godot, tmp_path, answers.url)
    persist = tmp_path / 'persist'
    with PlaySession(game_dir, binary=godot, persist_dir=persist) as game:
        send_one(game, 'The table froze')
        down = game.until({'path': 'state.game.report_status', 'op': '!=', 'value': 'Sending...'}, max_ticks=6000)
        assert down['state']['game']['report_status'] == ('Not sent now (503: Service Unavailable): it is kept and '
                                                          'goes later.')
        assert len(down['state']['game']['outbox']) == 1
        game.act(tap=['cancel'], ticks=3)
        game.act(tap=['down'], ticks=2)                                  # a scene changed: the outbox kept
        game.act(tap=['up'], ticks=2)
    with PlaySession(game_dir, binary=godot, persist_dir=persist) as game:     # another run
        later = game.until({'path': 'state.game.outbox', 'op': '==', 'value': []}, max_ticks=6000)
        assert later['scene'] == 'title' and later['stopped'] == 'condition'
        assert [r['text'] for r in answers.received] == ['The table froze', 'The table froze']
    answers.answers = [(422, {'error': 'invalid', 'message': "Parameter 'text' is too long"})]
    with PlaySession(game_dir, binary=godot, persist_dir=persist) as game:
        send_one(game, 'Another one')
        refused = game.until({'path': 'state.game.outbox', 'op': '==', 'value': []}, max_ticks=6000)
        assert refused['state']['game']['report_status'] == ("The report was not accepted: 422: Parameter 'text' is "
                                                             "too long")


def test_a_report_reaches_the_receiver_and_the_forge(godot, tmp_path, monkeypatch):
    """The whole way: the game posts to projects/beta-reports served over HTTP, which keeps it in SQLite, puts the
    save on the forge's branch and opens an issue; the game says the number it got."""
    import logging
    import shutil
    import sqlite3
    import threading
    from werkzeug.serving import make_server
    from tests.apps.test_beta_reports import PROJECT, FakeForge
    from quantum.cli.migrations import MigrationRunner
    from quantum.runtime.web_server import QuantumWebServer
    receiver = tmp_path / 'beta-reports'
    shutil.copytree(PROJECT, receiver, ignore=shutil.ignore_patterns('data', '.quantum', '__pycache__'))
    monkeypatch.chdir(receiver)
    monkeypatch.setenv('GITHUB_TOKEN', 'test-token')
    MigrationRunner(receiver).up()
    with FakeForge() as forge:
        with sqlite3.connect(receiver / 'data' / 'reports.db') as db:
            db.execute("UPDATE settings SET forge = ?, repo = 'acme/beta'", (forge.url,))
        logging.disable(logging.WARNING)
        http = make_server('127.0.0.1', 0, QuantumWebServer(str(receiver / 'quantum.config.yaml')).app, threaded=True)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            game_dir = pandafoot_to(godot, tmp_path / 'game', f'http://127.0.0.1:{http.server_port}/api/reports')
            with PlaySession(game_dir, binary=godot) as game:
                new_game(game)
                game.act(tap=['report'], ticks=3)
                type_report(game, 'The keeper scored from his own area')
                game.act(tap=['select'], ticks=3)
                sent = game.until({'path': 'state.game.outbox', 'op': '==', 'value': []}, max_ticks=6000)
                assert sent['state']['game']['report_status'] == 'Sent: report no. 1. Thank you!'
                assert 'Sent: report no. 1. Thank you!' in texts(sent)
        finally:
            http.shutdown()
            logging.disable(logging.NOTSET)
        with sqlite3.connect(receiver / 'data' / 'reports.db') as db:
            db.row_factory = sqlite3.Row
            (row,) = [dict(r) for r in db.execute('SELECT * FROM reports')]
        assert (row['game'], row['version'], row['kind'], row['screen']) == ('pandafoot', '2.2', 'bug', 'dashboard')
        assert row['text'] == 'The keeper scored from his own area' and row['issue'] == 41
        assert json.loads(row['save'])['game']['world'] == 7
        (put, _, _, body), (issue_method, issue_path, _, issue) = forge.received
        assert put == 'PUT' and json.loads(base64.b64decode(body['content']))['scene'] == 'dashboard'
        assert issue['title'] == '[pandafoot 2.2] bug: The keeper scored from his own area'
        assert issue['labels'] == ['beta-report', 'pandafoot', 'bug']
        assert MINE_NAME in issue['body']


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
    three substitutions at most; who is hurt or banned misses the next match; the crowd fits the ground. The Panda
    Cup goes on between the rounds: drawn on screen when a manager plays it, at once when none does."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        reds = knocks = subs = 0
        draws = []
        rnd = 0
        while True:
            after = play_round(game)
            rnd += 1
            state = after['state']['game']
            for m in state['last']:
                assert 0 < m['crowd'] <= state['clubs'][m['home']]['capacity']
                for short in (state['clubs'][m['home']]['short'], state['clubs'][m['away']]['short']):
                    events = [e for e in reversed(m['events']) if e.get('club') == short]   # in the order they came
                    gone, booked, came = set(), {}, 0
                    for e in events:
                        if e['kind'] in ('tactic', 'pens'):
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
            cup_due = state['cup_round'] < 6 and state['matchday'] >= [3, 6, 9, 12, 15, 18][min(5, int(state['cup_round']))]
            mine = state['managers'][0]['club']
            if state['matchday'] < 18 and not cup_due:                # the next match's elevens are ready
                for c in state['clubs']:
                    assert len([p for p in c['players'] if p['xi']]) == 11
                    assert not [p['name'] for p in c['players'] if p['xi'] and (p['injured'] or p['suspended'])]
            if state['matchday'] >= 18 and not (cup_due and state['cup_round'] == 5 and mine in state['cup_alive']):
                break                                                  # the last results (a final to play aside)
            seen = game.act(tap=['select'], ticks=3)
            while seen['scene'] in ('job', 'draw'):
                if seen['scene'] == 'draw':                            # the draw: all at once, then the dashboard
                    seen = game.act(tap=['select'], ticks=3)
                    draws.append((seen['state']['game']['cup_round'], seen['state']['game']['cup_ties']))
                seen = game.act(tap=['select'], ticks=3)              # sacked: the career goes on, at the first club
            assert seen['scene'] == 'dashboard', seen['scene']
        assert draws and draws[0][0] == 0                            # the preliminary round: the 4th's ten and six
        first = draws[0][1]
        clubs = state['clubs']
        assert len(first) == 8 and {c for t in first for c in t} >= {i for i, c in enumerate(clubs) if c['div'] == 4}
        assert all(clubs[h]['div'] >= clubs[a]['div'] for h, a in first)       # the lower division at home
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
        cup = seen['state']['game']
        assert cup['cup_round'] == 6 and cup['cup_winner'] >= 0                  # the final was played
        assert again['honours'][0]['cup'] == clubs[int(cup['cup_winner'])]['name']
        assert again['cup_round'] == 0 and len(again['cup_alive']) == 40
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
        rested = min(100, 98 + mine['training'])                  # a week: who played tires (-12, +10 and a point a
        for p in mine['players']:                                 # level of the training center), who did not rests
            assert p['form'] == (rested if p['name'] in eleven or p['played'] else 100), p
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
        off = [i['button'] for i in [m for m in menus(choosing) if m['shown']][0]['items'] if i['shown']]
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
        mine = [m for m in after['state']['game']['last'] if clubs[m['home']]['div'] == clubs[MINE]['div']]
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
        assert texts(mine)[0].startswith('SQUAD - ' + MINE_NAME)
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
    data['game']['cup_round'] = 6                                 # the cup out of the way (the season test plays it)
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
        state['clubs'][MINE]['balance'] = -10_000_000
        state['clubs'][MINE]['expect'] = 1                          # a board that wanted the title: no round pleases it
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
        assert mine['club'] != MINE and state['clubs'][mine['club']]['manager'] == 1 and state['clubs'][MINE]['manager'] == 0
        assert mine['patience'] == 50 and mine['career']['sacked'] == 1
        assert mine['career']['clubs'] == [MINE_NAME, state['clubs'][mine['club']]['name']]
        assert texts(taken)[0].startswith('PANDAFOOT  ' + state['clubs'][mine['club']]['name'])
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_a_sacked_manager_can_end_the_career(pandafoot, godot, tmp_path):
    def at_the_end(state):
        state['managers'][0]['patience'] = 1
        state['clubs'][MINE]['balance'] = -10_000_000
        state['clubs'][MINE]['expect'] = 1                          # a board that wanted the title: no round pleases it
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
        state['clubs'][MINE]['points'] = 99
    saved_then(pandafoot, godot, tmp_path, last_round_on_top)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        end = game.act(tap=['select'], ticks=3)
        assert end['scene'] == 'season-end'
        assert any(t.startswith(MINE_NAME + ': 1º of the 4th division, promoted!') for t in texts(end))
        offer = game.act(tap=['select'], ticks=3)                  # New season
        assert offer['scene'] == 'job' and texts(offer)[0] == '✉ AN OFFER'
        state = offer['state']['game']
        offered = state['jobs'][0]['clubs']
        assert len(offered) == 2 and all(state['clubs'][i]['div'] == 2 and state['clubs'][i]['manager'] == 0
                                         for i in offered)
        assert state['clubs'][MINE]['div'] == 3 and state['managers'][0]['career']['ups'] == 1
        stays = [b['button'] for b in menus(offer)[1]['items'] if b['shown']]
        assert stays == ['Stay at ' + MINE_NAME]
        for _ in range(2):                                         # past the two offers, to staying
            game.act(tap=['down'], ticks=2)
        back = game.act(tap=['select'], ticks=3)
        assert back['scene'] == 'dashboard' and back['state']['game']['managers'][0]['club'] == MINE
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


# --- transfers (PLAN_PANDAFOOT.md Phase 2): Elifoot 2's auction of wages ---

def to_dashboard(game):
    """From the results to the dashboard, past a cup's draw (all of it at once) or a job (the first club)."""
    seen = game.act(tap=['select'], ticks=3)
    while seen['scene'] in ('draw', 'job'):
        if seen['scene'] == 'draw':
            game.act(tap=['select'], ticks=3)
        seen = game.act(tap=['select'], ticks=3)
    assert seen['scene'] == 'dashboard', seen['scene']
    return seen


def to_the_list(game):
    """From the results: the dashboard, then the transfer list (F6)."""
    to_dashboard(game)
    return game.act(tap=['market'], ticks=3)


def test_the_list_fills_and_the_computers_clubs_trade(pandafoot, godot):
    """After a round the list has free agents and players of the computer's clubs; three rounds on, the first
    auctions are decided: a player changes clubs, the fee changes purses, the papers say so."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        before = game.observe()['state']['game']
        after = play_round(game)
        market = after['state']['game']['market']
        assert sum(e['seller'] < 0 for e in market) >= 6 and all(e['left'] == 3 for e in market)
        listing = to_the_list(game)
        rows = [i['button'] for i in menus(listing)[0]['items'] if i['shown']]
        assert len(rows) == len(market) and any('free' in r for r in rows)
        game.act(tap=['cancel'], ticks=3)
        for _ in range(5):
            after = play_round(game)
            to_dashboard(game)
        state = after['state']['game']
        news = [n['text'] for n in state['news']]
        assert 'Signed:' in news or 'Surprise! He took the long shot:' in news
        squads = {p['name'] for c in state['clubs'] for p in c['players']}
        assert len(squads) == sum(len(c['players']) for c in state['clubs'])        # no one in two clubs
        assert sum(len(c['players']) for c in state['clubs']) > sum(len(c['players']) for c in before['clubs'])
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_a_manager_signs_a_free_agent(pandafoot, godot, tmp_path):
    """Three times the wage he asks: a free agent of the 4th's level would come (80% or more), and three rounds on he
    is the manager's. The club is on top of the table (a club at the bottom weighs against him: -10)."""
    def on_top(state):
        state['clubs'][MINE]['points'] = 99
        for agent in state['free_agents']:
            agent['strength'] = 20
    saved_then(pandafoot, godot, tmp_path, on_top)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        listing = to_the_list(game)
        market = listing['state']['game']['market']
        at = next(k for k, e in enumerate(market) if e['seller'] < 0)
        for _ in range(at):
            game.act(tap=['down'], ticks=2)
        bid = game.act(tap=['select'], ticks=3)
        assert bid['scene'] == 'bid' and texts(bid)[1] == 'A free agent'
        for _ in range(36):                                        # 120% to 300% of what he asks
            bid = game.act(tap=['right'], ticks=2)
        line = [t for t in texts(bid) if t.startswith('He would come:')][0]
        assert int(line.split()[3].rstrip('%')) >= 80, line
        game.act(tap=['down'], ticks=2)
        back = game.act(tap=['select'], ticks=3)                  # Make the bid
        assert back['scene'] == 'market'
        entry = back['state']['game']['market'][at]
        who = entry['who']
        assert [(b['club'], b['wage']) for b in entry['bids'] if b['club'] == MINE] == [(MINE, round(entry['wage'] * 3))]
        game.act(tap=['cancel'], ticks=3)
        for _ in range(5):                                         # three rounds of the league (a cup date between)
            after = play_round(game)
            to_dashboard(game)
            if who not in [e['who'] for e in after['state']['game']['market']]:
                break
        mine = after['state']['game']['clubs'][MINE]
        assert who in [p['name'] for p in mine['players']] and len(mine['players']) == 23
        assert who not in [p['name'] for p in after['state']['game']['free_agents']]


def test_a_strong_free_agent_wants_a_club_of_his_level(pandafoot, godot, tmp_path):
    """A free agent of 40 is of the 1st division's level: to the 4th he would hardly come, even at three times his
    wage (50, +40 the wage, +10 the top of the table, -25 a division down: 25%, 30 with the squad in good spirits),
    and the division is why."""
    def strong(state):
        state['clubs'][MINE]['points'] = 99
        for agent in state['free_agents']:
            agent['strength'] = 40
    saved_then(pandafoot, godot, tmp_path, strong)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        listing = to_the_list(game)
        at = next(k for k, e in enumerate(listing['state']['game']['market']) if e['seller'] < 0)
        for _ in range(at):
            game.act(tap=['down'], ticks=2)
        bid = game.act(tap=['select'], ticks=3)
        for _ in range(36):                                        # 120% to 300% of what he asks
            bid = game.act(tap=['right'], ticks=2)
        line = [t for t in texts(bid) if t.startswith('He would come:')][0]
        assert int(line.split()[3].rstrip('%')) <= 30 and line.endswith('(Lower division)'), line


def test_a_manager_puts_a_player_on_the_list(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        game.act(tap=['market'], ticks=3)
        selling = game.act(tap=['sell'], ticks=3)
        assert menus(selling)[0]['items'][0]['slider'] == 'Asking price %' and menus(selling)[0]['items'][0]['value'] == 100
        first = selling['state']['game']['clubs'][MINE]['players'][0]
        game.act(tap=['down'], ticks=2)                            # from the price to the squad
        listed = game.act(tap=['select'], ticks=3)
        entry = [e for e in listed['state']['game']['market'] if e['who'] == first['name']]
        worth = 300_000 * 2 ** ((first['strength'] - 26) / 4) * (1 + 0.15 * (len(first['traits']) + 2 * first['genius']))
        assert entry and entry[0]['seller'] == MINE and entry[0]['fee'] == round(worth / 1000) * 1000
        assert any('ON THE LIST' in i['button'] for i in menus(listed)[1]['items'])
        off = game.act(tap=['select'], ticks=3)                    # and off it again
        assert not [e for e in off['state']['game']['market'] if e['who'] == first['name']]


def test_a_loan_comes_back_with_the_new_season(pandafoot, godot, tmp_path):
    """A rich manager borrows a player of a computer's club for the rest of the season; with the new season he is
    back at his club."""
    def two_rounds_left_and_rich(state):
        state['matchday'] = 16
        state['clubs'][MINE]['balance'] = 50_000_000
        state['clubs'][MINE]['points'] = 99                         # first: a pleased board
    saved_then(pandafoot, godot, tmp_path, two_rounds_left_and_rich)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)                                           # the list fills
        listing = to_the_list(game)
        state = listing['state']['game']
        at = next(k for k, e in enumerate(state['market'])
                  if e['seller'] >= 0 and state['clubs'][e['seller']]['manager'] == 0)
        entry = state['market'][at]
        for _ in range(at):
            game.act(tap=['down'], ticks=2)
        bid = game.act(tap=['select'], ticks=3)
        buttons = [i['button'] for i in menus(bid)[0]['items'] if 'button' in i and i['shown']]
        assert buttons[1].startswith('Borrow him for the season'), buttons      # after the wage and the bid
        game.act(tap=['down'], ticks=2)
        game.act(tap=['down'], ticks=2)
        lent = game.act(tap=['select'], ticks=3)['state']['game']
        mine = lent['clubs'][MINE]
        him = [p for p in mine['players'] if p['name'] == entry['who']]
        assert him and him[0]['loan'] == entry['seller'] and len(mine['players']) == 23
        assert mine['balance'] == pytest.approx(state['clubs'][MINE]['balance'] - 0.1 * entry['fee'])
        assert entry['who'] not in [p['name'] for p in lent['clubs'][entry['seller']]['players']]
        game.act(tap=['cancel'], ticks=3)
        play_round(game)
        assert game.act(tap=['select'], ticks=3)['scene'] == 'season-end'
        seen = game.act(tap=['select'], ticks=3)                   # New season (and perhaps an offer: stay)
        if seen['scene'] == 'job':
            game.act(tap=['down'], ticks=2)
            game.act(tap=['down'], ticks=2)
            seen = game.act(tap=['select'], ticks=3)
        state = seen['state']['game']
        assert entry['who'] not in [p['name'] for p in state['clubs'][MINE]['players']]
        back = [p for p in state['clubs'][entry['seller']]['players'] if p['name'] == entry['who']]
        assert back and back[0]['loan'] == -1
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


# --- the club's seasons (PLAN_PANDAFOOT.md Phase 2): growth, the ground, the crisis, the history ---

def test_the_season_makes_the_players(pandafoot, godot, tmp_path):
    """A forward who scored twelve goals becomes a Star; a player of more than 30 who hardly played loses a point (one
    of 30 or less does not, nor one who grew in training); the goals go into those of all time; the history (F8) has
    the season's champions and the manager's title."""
    def a_season_of_goals(state):
        state['matchday'] = 17
        state['clubs'][MINE]['points'] = 99
        squad = state['clubs'][MINE]['players']
        scorer = next(p for p in squad if p['xi'] == 'FW')
        scorer.update(apps=15, morale=90, goals=14)
        idle, weak, trained = [p for p in squad if p['xi'] == '' and not p['bench']][:3]
        idle.update(apps=0, strength=34)
        weak.update(apps=0, strength=20)
        trained.update(apps=0, strength=34, grown=1)
        state['test'] = {'scorer': scorer['name'], 'strength': scorer['strength'], 'idle': idle['name'],
                         'idle_strength': idle['strength'], 'weak': weak['name'], 'trained': trained['name']}
    saved_then(pandafoot, godot, tmp_path, a_season_of_goals)
    marks = json.loads((tmp_path / 'quantum-save-1.json').read_text())['game']['test']
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        game.act(tap=['select'], ticks=3)                          # the season's end
        seen = game.act(tap=['select'], ticks=3)                   # New season (and an offer: stay)
        if seen['scene'] == 'job':
            game.act(tap=['down'], ticks=2)
            game.act(tap=['down'], ticks=2)
            seen = game.act(tap=['select'], ticks=3)
        squad = {p['name']: p for p in seen['state']['game']['clubs'][MINE]['players']}
        scorer, idle = squad[marks['scorer']], squad[marks['idle']]
        assert scorer['strength'] == marks['strength'] and 'Star' in scorer['traits']    # the months grow, not the end
        assert scorer['total'] >= 14 and scorer['goals'] == 0 and scorer['apps'] == 0
        assert idle['strength'] == marks['idle_strength'] - 1 and squad[marks['weak']]['strength'] == 20
        assert squad[marks['trained']]['strength'] == 34
        assert 'A star is born:' in [n['text'] for n in seen['state']['game']['news']]
        history = game.act(tap=['history'], ticks=3)
        assert history['scene'] == 'history'
        rows = tables(history)
        assert rows[0]['rows'][0][:5] == ['2026', *seen['state']['game']['honours'][0]['champions']]
        assert rows[0]['rows'][0][4] == MINE_NAME
        ranking = menus(history)[0]['items'][0]['button']           # name, seasons, points, a match, titles, cups...
        assert ranking.startswith('Manager 1') and ranking[13:18].strip() == '1' and ranking[30:34].strip() == '1'
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_the_ground_wears_and_is_rebuilt(pandafoot, godot, tmp_path):
    """A home match wears the ground; maintenance mends it at $3 a seat; works due at the month's end open the new
    stand, the ground as new."""
    def works_due(state):
        state['matchday'] = 3                                      # this round ends the month
        club = state['clubs'][MINE]
        club.update(health=80, works=4, adding=2000, balance=5_000_000)
        state['test'] = {'capacity': club['capacity']}
    saved_then(pandafoot, godot, tmp_path, works_due)
    capacity = json.loads((tmp_path / 'quantum-save-1.json').read_text())['game']['test']['capacity']
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        after = play_round(game)
        club = after['state']['game']['clubs'][MINE]
        assert club['works'] == 0 and club['adding'] == 0 and club['capacity'] == capacity + 2000
        assert club['health'] == 100
        game.act(tap=['select'], ticks=3)
        finances = game.act(tap=['finances'], ticks=3)
        assert any(t.startswith('Health:') and t.endswith('100%') for t in texts(finances))
        buttons = [i['button'] for i in menus(finances)[0]['items'] if i['shown']]
        assert not any(b.startswith('Maintenance') for b in buttons)              # nothing to mend
    with PlaySession(pandafoot, binary=godot) as game:
        before = new_game(game)['state']['game']['clubs'][MINE]
        after = play_round(game)['state']['game']
        mine = [m for m in after['last'] if MINE in (m['home'], m['away'])][0]
        club = after['clubs'][MINE]
        if mine['home'] == MINE:
            assert club['health'] < before['health']
            assert club['gate'] == round(mine['crowd'] * club['ticket'] * (1.0 if before['health'] >= 90 else 0.97))
        else:
            assert club['health'] == before['health']


def test_the_crisis_bites(pandafoot, godot, tmp_path):
    """Three million in the red at the month's end: six points off, once, and the best player on the list."""
    def deep_in_debt(state):
        state['matchday'] = 3
        state['clubs'][MINE]['balance'] = -3_000_000
    saved_then(pandafoot, godot, tmp_path, deep_in_debt)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        seen = continued(game)
        assert any('GRAVE' in t for t in texts(seen))
        after = play_round(game)
        state = after['state']['game']
        club = state['clubs'][MINE]
        assert club['fined'] == 2026 and club['points'] in (-6, -5, -3)          # the round's 0, 1 or 3, less 6
        best = max(club['players'], key=lambda p: p['strength'])
        assert best['name'] in [e['who'] for e in state['market'] if e['seller'] == MINE]
        assert 'Six points off for the debts:' in [n['text'] for n in state['news']]


def test_a_bankrupt_club_sacks_its_manager(pandafoot, godot, tmp_path):
    def broke(state):
        state['matchday'] = 3
        state['clubs'][MINE]['balance'] = -9_000_000
    saved_then(pandafoot, godot, tmp_path, broke)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        after = play_round(game)
        state = after['state']['game']
        assert state['clubs'][MINE]['bankrupt'] and state['clubs'][MINE]['balance'] >= -1_000_000
        assert state['jobs'] and state['jobs'][0]['kind'] == 'sacked'
        assert game.act(tap=['select'], ticks=3)['scene'] == 'job'


# --- what the beta's first players asked for (PLAN_PANDAFOOT.md, the feedback of 2026-10-24) ---

def test_the_club_is_drawn(pandafoot, godot):
    """No club is chosen: each manager is given one, drawn among the small clubs of the 4th no one has."""
    with PlaySession(pandafoot, binary=godot) as game:
        game.act(ticks=3)
        screen = game.act(tap=['select'], ticks=3)
        labels = [i.get('button', i.get('slider', i.get('field'))) for m in menus(screen) for i in m['items']]
        assert "Draw the manager's club" in labels and 'Camelo FC' not in labels       # no list of clubs to pick from
        for _ in range(3):
            game.act(tap=['down'], ticks=2)
        game.act(tap=['select'], ticks=3)
        two = game.act(tap=['select'], ticks=5)                                        # a second manager, drawn too
        managers = two['state']['game']['managers']
        assert [t['name'] for t in managers] == ['Manager 1', 'Manager 2']
        assert len({t['club'] for t in managers}) == 2 and all(30 <= t['club'] <= 39 for t in managers)


def test_the_round_is_in_view_and_tab_shows_another_division(pandafoot, godot):
    """The live round says which round it is, and TAB goes through the four divisions, not match by match."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        live = game.act(tap=['select'], ticks=3)
        panel = [t for t in texts(live) if 'LIVE ROUND' in t]
        assert panel == ['═══ LIVE ROUND 1/18 ═══']
        seen = []
        for _ in range(4):
            seen.append(next(t for t in texts(live) if t.endswith('division')))
            live = game.act(tap=['other'], ticks=2)
        assert sorted(seen) == ['1st division', '2nd division', '3rd division', '4th division']
        assert any('[TAB] Another division' in t for t in texts(live))


def test_the_squad_shows_the_goals_of_a_career(pandafoot, godot, tmp_path):
    def scored(state):
        p = state['clubs'][MINE]['players'][10]
        p['total'], p['goals'] = 31, 4
    saved_then(pandafoot, godot, tmp_path, scored)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        squad = game.act(tap=['squad'], ticks=3)
        table = tables(squad)[0]
        at = table['table'].index('Car')
        row = table['rows'][10]
        assert row[table['table'].index('Gls')].strip() == '4' and row[at].strip() == '35'


def test_a_thousand_seats_a_third_at_once(pandafoot, godot, tmp_path):
    """A thousand more seats cost a 4th-division club $80 each, a third at once and the rest in seven months; without
    the money for the third, the screen says so."""
    def poor(state):
        state['clubs'][MINE]['balance'] = 20_000
        state['clubs'][MINE]['health'] = 90
    saved_then(pandafoot, godot, tmp_path, poor)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        finances = game.act(tap=['finances'], ticks=3)
        buttons = [i['button'] for i in menus(finances)[0]['items'] if i['shown']]
        k = next(i for i, b in enumerate(buttons) if b.startswith('+1.000 seats'))
        assert buttons[k] == '+1.000 seats ($80.000)'
        for _ in range(k // 2):                                  # two columns: down a row
            game.act(tap=['down'], ticks=2)
        for _ in range(k % 2):
            game.act(tap=['right'], ticks=2)
        refused = game.act(tap=['select'], ticks=3)
        assert 'Not enough money: a third at once is $26.667' in texts(refused)
        assert refused['state']['game']['clubs'][MINE]['works'] == 0
    def rich(state):
        state['clubs'][MINE]['balance'] = 200_000
        state['clubs'][MINE]['health'] = 90
    saved_then(pandafoot, godot, tmp_path, rich)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        game.act(tap=['finances'], ticks=3)
        for _ in range(k // 2):
            game.act(tap=['down'], ticks=2)
        for _ in range(k % 2):
            game.act(tap=['right'], ticks=2)
        done = game.act(tap=['select'], ticks=3)['state']['game']
        club = done['clubs'][MINE]
        assert (club['works'], club['adding']) == (12, 1000)
        assert club['balance'] == pytest.approx(200_000 - 80_000 / 3)
        assert [(d['to'], d['left'], round(d['each'])) for d in club['debts']] == [(-1, 7, round(80_000 * 2 / 3 / 7))]
        assert done['news'][0]['text'] == 'Works begin:'


def test_the_penalty_taker_is_chosen_in_tactics(pandafoot, godot):
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        tactics = game.act(tap=['tactics'], ticks=3)
        buttons = [i['button'] for i in menus(tactics)[0]['items']]
        k = next(i for i, b in enumerate(buttons) if b.startswith('Penalty taker:'))
        assert buttons[k].startswith('Penalty taker: the best (')
        best = buttons[k][len('Penalty taker: the best ('):-1]
        for _ in range(k):
            game.act(tap=['down'], ticks=2)
        first = game.act(tap=['select'], ticks=3)                       # the best, by name: the manager's choice
        assert menus(first)[0]['items'][k]['button'] == f'Penalty taker: {best}'
        second = game.act(tap=['select'], ticks=3)                      # the next one
        chosen = second['state']['game']['clubs'][MINE]['taker']
        assert chosen not in ('', best) and menus(second)[0]['items'][k]['button'] == f'Penalty taker: {chosen}'
        eleven = [p['name'] for p in second['state']['game']['clubs'][MINE]['players'] if p['xi'] and p['xi'] != 'GK']
        assert chosen in eleven


def test_tired_men_in_the_eleven_are_a_warning(pandafoot, godot, tmp_path):
    def worn(state):
        for p in state['clubs'][MINE]['players']:
            if p['xi'] and p['xi'] != 'GK':
                p['form'] = 50
    saved_then(pandafoot, godot, tmp_path, worn)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        seen = continued(game)
        assert '⚠ 10 tired in the eleven: rest them (F1)' in [t.rstrip() for t in texts(seen)]


def test_a_bid_for_a_computer_clubs_player_opens_an_auction(pandafoot, godot):
    """From another club's squad, B: its players, and a bid for one puts him on the transfer list (a third above his
    worth), the manager's bid to be made, the other clubs free to bid for three rounds."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        table = game.act(tap=['standings'], ticks=3)
        rows = menus(table)[0]['items']
        k = next(i for i, r in enumerate(rows) if MINE_NAME not in r['button'])
        for _ in range(k):
            game.act(tap=['down'], ticks=2)
        squad = game.act(tap=['select'], ticks=3)
        club = next(i for i, c in enumerate(squad['state']['game']['clubs']) if texts(squad)[0].startswith('SQUAD - ' + c['name']))
        assert any('[B] Bid for a player' in t for t in texts(squad))
        scout = game.act(tap=['scout'], ticks=3)
        assert scout['scene'] == 'scout' and texts(scout)[0].startswith('BID FOR A PLAYER OF')
        bid = game.act(tap=['select'], ticks=3)
        assert bid['scene'] == 'bid'
        state = bid['state']['game']
        entry = state['market'][-1]
        him = state['clubs'][club]['players'][0]
        assert (entry['who'], entry['seller'], entry['left']) == (him['name'], club, 3)
        assert state['news'][0]['text'] == 'Up for auction:' and state['viewing'] == -1


def test_a_manager_doing_well_is_offered_a_club_at_mid_season(pandafoot, godot, tmp_path):
    """Halfway through the season, top of the 4th: an offer from two clubs of the 3rd, at once."""
    def halfway(state):
        state['matchday'] = 8
        state['clubs'][MINE]['points'] = 99
    saved_then(pandafoot, godot, tmp_path, halfway)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        job = game.act(tap=['select'], ticks=3)
        assert job['scene'] == 'job' and texts(job)[0] == '✉ AN OFFER'
        offer = job['state']['game']['jobs'][0]
        assert offer['kind'] == 'offer' and len(offer['clubs']) == 2
        assert all(job['state']['game']['clubs'][ci]['div'] == 3 for ci in offer['clubs'])


def test_a_regular_back_from_injury_is_back_in_the_eleven(pandafoot, godot, tmp_path):
    """The manager's eleven is who he picked: one who stood in for an injured regular steps back as soon as the
    regular can play again, with no one putting him back by hand (the bad run of the beta: a team that lost its
    best men to a knock or a ban kept their stand-ins for good)."""
    hurt = {}
    def knocked(state):
        club = state['clubs'][MINE]
        p = max((q for q in club['players'] if q['xi'] not in ('', 'GK')), key=lambda q: q['strength'])
        p['injured'] = 1
        hurt.update(name=p['name'], place=p['xi'])
    saved_then(pandafoot, godot, tmp_path, knocked)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        live = game.act(tap=['select'], ticks=3)
        regular = next(p for p in live['state']['game']['clubs'][MINE]['players'] if p['name'] == hurt['name'])
        assert regular['xi'] == '' and regular['pick'] == hurt['place']          # out of this match, still picked
        after = play_round(game)
        back = next(p for p in after['state']['game']['clubs'][MINE]['players'] if p['name'] == hurt['name'])
        assert back['injured'] == 0 and back['xi'] == hurt['place']               # back in his place for the next
        assert len([p for p in after['state']['game']['clubs'][MINE]['players'] if p['xi']]) == 11


# --- the beta's fourth feedback (PLAN_PANDAFOOT.md, 2026-10-25): PandaFoot 2.2 ---

def shown(obs):
    """The menus on the screen now (a menu hidden by its if= is in the view, not shown)."""
    return [m for m in menus(obs) if m['shown']]


def worth(p, prized=False):
    """What a player is worth: $300.000 at strength 26, twice as much every four (a third more with a prize)."""
    return 300_000 * 2 ** ((p['strength'] - 26) / 4) * (1 + 0.15 * (len(p['traits']) + 2 * p['genius'])) * \
        (1.3 if prized else 1)


def table_place(clubs, i):
    """Where a club is in its division's table, as the game orders it."""
    div = [k for k, c in enumerate(clubs) if c['div'] == clubs[i]['div']]
    order = sorted(div, key=lambda k: (-clubs[k]['points'], -(clubs[k]['gf'] - clubs[k]['ga']), -clubs[k]['gf'], k))
    return order.index(i) + 1


def test_a_player_sells_and_the_list_has_every_level(pandafoot, godot):
    """Nobody bought a player of the manager's but his best (a worth above a small club's purse, and a bid only from
    clubs of the player's own level) and the list had players of 10 to 20 after a while: now the worth halves every
    four of strength, the asking price is the manager's (half his worth here), any club he would be one of the sixteen
    best of may bid, and the computer's clubs list regulars too."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        game.act(tap=['market'], ticks=3)
        game.act(tap=['sell'], ticks=3)
        for _ in range(5):                                         # the asking price, 100% to 50%
            game.act(tap=['left'], ticks=2)
        seen = game.observe()
        state = seen['state']['game']
        assert state['asking'] == 50
        squad = state['clubs'][MINE]['players']
        k = min((i for i, p in enumerate(squad) if p['xi'] and p['xi'] != 'GK'), key=lambda i: squad[i]['strength'])
        weak = squad[k]                                             # the weakest of the eleven
        game.act(tap=['down'], ticks=2)                            # from the price to the squad
        for _ in range(k):
            game.act(tap=['down'], ticks=2)
        listed = game.act(tap=['select'], ticks=3)['state']['game']
        entry = next(e for e in listed['market'] if e['who'] == weak['name'])
        assert entry['seller'] == MINE and entry['fee'] == round(worth(weak) * 0.5 / 1000) * 1000
        game.act(tap=['cancel'], ticks=3)
        game.act(tap=['cancel'], ticks=3)
        bids = 0
        strong = 0
        for _ in range(4):
            after = play_round(game)['state']['game']
            strong = max([strong] + [e['str'] for e in after['market'] if e['seller'] >= 0 and e['seller'] != MINE])
            on = [e for e in after['market'] if e['who'] == weak['name']]
            bids = max(bids, len(on[0]['bids']) if on else 0)
            gone = weak['name'] not in [p['name'] for p in after['clubs'][MINE]['players']]
            to_dashboard(game)
            if gone:
                break
        assert gone or bids > 0, 'no club bid for a regular at half his worth'
        assert strong >= 30                                        # the list is not only reserves of 10 to 20
        assert len(after['free_agents']) >= 30
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_every_match_is_rated(pandafoot, godot):
    """Each player who played is rated, 3 to 10, and the man of the match is the best of them; [R] on the results
    shows the manager's match's ratings side by side; the squad has the matches played and the mean."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        after = play_round(game)
        state = after['state']['game']
        for m in state['last']:
            assert len([x for x in m['ratings'] if x['home'] and not x['on']]) == 11
            assert all(3 <= x['r'] <= 10 for x in m['ratings'])
            best = max(m['ratings'], key=lambda x: x['r'])
            assert m['motm'].startswith(best['who'] + ' (')
        mine = next(m for m in state['last'] if MINE in (m['home'], m['away']))
        assert [t for t in texts(after) if t.startswith('Man of the match: ')][0].startswith(
            'Man of the match: ' + mine['motm'])
        rated = game.act(tap=['ratings'], ticks=3)
        assert texts(rated)[0].startswith('═══ RATINGS ═══')
        rows = tables(rated)[0]['rows']
        assert len(rows) == max(sum(x['home'] for x in mine['ratings']), sum(not x['home'] for x in mine['ratings']))
        assert not any(t.startswith('═══ YOUR MATCH') for t in texts(rated))     # in its place
        to_dashboard(game)
        squad = tables(game.act(tap=['squad'], ticks=3))[0]
        gm, avg = squad['table'].index('Gm'), squad['table'].index('Avg')
        ratings = {x['who']: x['r'] for x in mine['ratings']}
        for p, row in zip(state['clubs'][MINE]['players'], squad['rows']):
            if p['name'] in ratings:
                assert row[gm].strip() == '1' and row[avg].strip() == f"{ratings[p['name']]:.1f}"
            else:
                assert row[avg].strip() == '-'


def test_a_month_of_good_ratings_grows_a_player(pandafoot, godot, tmp_path):
    """At the month's end a mean of 7 or more (two matches at least) grows a player a point, 5 or less takes one; the
    squad shows the arrows and the papers say who."""
    def month_end(state):
        state['matchday'] = 3                                       # this round ends the month
        squad = state['clubs'][MINE]['players']
        squad[0].update(msum=32, mn=4)                              # a mean of 8: 7 or more whatever this match
        squad[1].update(msum=12, mn=4)                              # of 3: 5 or less whatever this match
        state['test'] = [squad[0]['strength'], squad[1]['strength']]
    saved_then(pandafoot, godot, tmp_path, month_end)
    was = json.loads((tmp_path / 'quantum-save-1.json').read_text())['game']['test']
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        after = play_round(game)['state']['game']
        good, poor = after['clubs'][MINE]['players'][:2]
        assert (good['strength'], good['trend'], good['mn']) == (was[0] + 1, 1, 0)
        assert (poor['strength'], poor['trend'], poor['mn']) == (was[1] - 1, -1, 0)
        news = {n['text']: n['arg'] for n in after['news']}
        assert good['name'] in news['Better this month (+1):'] and poor['name'] in news['Worse this month (-1):']
        to_dashboard(game)
        rows = tables(game.act(tap=['squad'], ticks=3))[0]['rows']
        assert '▲' in rows[0] and '▼' in rows[1]


def test_the_reserves_train_with_the_eleven(pandafoot, godot, tmp_path):
    """Who hardly played in the month trains with the eleven: at the month's end one weaker than the eleven's mean may
    grow a point (35% at a training center of level 5), never past the eleven; the papers say who."""
    def month_end(state):
        state['matchday'] = 3                                       # this round ends the month
        reserves = []
        for club in state['clubs']:
            club['training'] = 5
            for p in club['players']:
                if not p['xi']:
                    p.update(strength=10, mn=0, injured=0)
                    reserves.append(p['name'])
        squad = state['clubs'][MINE]['players']
        xi = [p['strength'] for p in squad if p['xi']]
        top = next(p for p in squad if not p['xi'] and not p['bench'])
        top['strength'] = math.ceil(sum(xi) / len(xi))             # as good as the eleven: nothing to learn
        state['test'] = {'top': top['name'], 'strength': top['strength'], 'reserves': reserves}
    saved_then(pandafoot, godot, tmp_path, month_end)
    marks = json.loads((tmp_path / 'quantum-save-1.json').read_text())['game']['test']
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        after = play_round(game)['state']['game']
        world = {p['name']: p for c in after['clubs'] for p in c['players']}
        reserves = [world[n] for n in marks['reserves'] if n != marks['top']]
        grown = [p for p in reserves if p['strength'] == 11]
        assert len(grown) >= len(reserves) // 4 and all(p['strength'] in (10, 11) for p in reserves)
        assert all(p['trend'] == 1 for p in grown)
        assert world[marks['top']]['strength'] == marks['strength']
        mine = [p['name'] for p in after['clubs'][MINE]['players'] if p['name'] in {q['name'] for q in grown}]
        if mine:
            news = {n['text']: n['arg'] for n in after['news']}
            assert mine[0] in news['Better in training (+1):']
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_a_small_clubs_star_goes_on_the_list(pandafoot, godot, tmp_path):
    """A club of the 2nd division or below whose best has outgrown it (six above its sixteen best's mean) puts him on
    the list, a fifth to three fifths above his worth: the big clubs can buy him."""
    def outgrown(state):
        for k, club in enumerate(state['clubs']):
            if club['div'] >= 2 and k != MINE:
                club['balance'] = 50_000_000                       # not short of money (it would sell a regular)
                best = max(club['players'], key=lambda p: p['strength'])
                best.update(strength=best['strength'] + 12, genius=False)
    saved_then(pandafoot, godot, tmp_path, outgrown)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        stars = []
        for _ in range(5):
            state = play_round(game)['state']['game']
            for e in state['market']:
                if e['seller'] >= 0 and e['seller'] != MINE and state['clubs'][e['seller']]['div'] >= 2:
                    club = state['clubs'][e['seller']]
                    p = next((q for q in club['players'] if q['name'] == e['who']), None)
                    if p and p['strength'] == max(q['strength'] for q in club['players']):
                        stars.append((e, p))
            to_dashboard(game)
            if stars:
                break
        assert stars, 'no small club put its star on the list'
        e, p = stars[0]
        assert worth(p) * 1.2 - 1000 <= e['fee'] <= worth(p) * 1.6 + 1000
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_the_season_has_its_prizes(pandafoot, godot, tmp_path):
    """Each division's top scorer and best player (the best mean of ten matches) win their club a prize, shine in gold
    the next season and are worth a third more; the season's end shows them, the honours keep them."""
    def last_round(state):
        state['matchday'] = 17
        squad = state['clubs'][MINE]['players']
        scorer = next(p for p in squad if p['xi'] == 'FW')
        scorer['goals'] = 40
        best = next(p for p in squad if p['xi'] == 'MF')
        best.update(rsum=12 * 9.6, rn=12)
        state['test'] = {'scorer': scorer['name'], 'best': best['name']}
    saved_then(pandafoot, godot, tmp_path, last_round)
    marks = json.loads((tmp_path / 'quantum-save-1.json').read_text())['game']['test']
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        end = game.act(tap=['select'], ticks=3)
        assert end['scene'] == 'season-end'
        prizes = tables(end)[1]['rows'][3]                         # the 4th division's line
        assert prizes[0].startswith(f"4th division:  ✪ {marks['scorer']} (CAM, 4")
        assert prizes[1].startswith(f"✦ {marks['best']} (CAM, 9.")
        seen = game.act(tap=['select'], ticks=3)                   # New season (and an offer, perhaps: stay)
        if seen['scene'] == 'job':
            game.act(tap=['down'], ticks=2)
            game.act(tap=['down'], ticks=2)
            seen = game.act(tap=['select'], ticks=3)
        state = seen['state']['game']
        assert state['honours'][0]['awards'][3]['scorer'].startswith(marks['scorer'] + ' (CAM, 4')
        club = state['clubs'][MINE]
        assert club['prizes'] >= 80_000                              # the 4th's top scorer and best player: $40.000 each
        squad = {p['name']: p for p in club['players']}
        assert (squad[marks['scorer']]['award'], squad[marks['scorer']]['award_season']) == ('scorer', 2026)
        assert squad[marks['best']]['award'] == 'best'
        game.act(tap=['market'], ticks=3)
        selling = game.act(tap=['sell'], ticks=3)
        row = next(i['button'] for i in shown(selling)[1]['items'] if marks['scorer'] in i['button'])
        assert money_in(row)[0] == round(worth(squad[marks['scorer']], prized=True))
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def money_in(text):
    """The sums of money in a line: '$1.234.567' as 1234567."""
    return [int(m.replace('.', '')) for m in re.findall(r'\$([0-9.]+)', text)]


def test_the_training_center_and_the_academy(pandafoot, godot, tmp_path):
    """F5: a level of the training center and of the youth academy, a third at once and the rest in seven months; what
    they cost a month is in the club's costs; the academy's youth joins the squad with the new season."""
    def rich_and_last(state):
        state['matchday'] = 17
        state['clubs'][MINE]['balance'] = 5_000_000
    saved_then(pandafoot, godot, tmp_path, rich_and_last)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        for what, cost in (('Training center → 1', 120_000), ('Youth academy → 1', 100_000)):
            finances = game.act(tap=['finances'], ticks=3)
            buttons = [i['button'] for i in menus(finances)[0]['items'] if i['shown']]
            k = next(i for i, b in enumerate(buttons) if b.startswith(what))
            assert money_in(buttons[k]) == [cost]
            for _ in range(k // 2):
                game.act(tap=['down'], ticks=2)
            for _ in range(k % 2):
                game.act(tap=['right'], ticks=2)
            before = game.observe()['state']['game']['clubs'][MINE]['balance']
            built = game.act(tap=['select'], ticks=3)
            club = built['state']['game']['clubs'][MINE]
            assert club['balance'] == pytest.approx(before - cost / 3)
            assert club['debts'][-1]['what'] == ('training' if what.startswith('Training') else 'academy')
            game.act(tap=['cancel'], ticks=3)
        assert (club['training'], club['academy']) == (1, 1)
        costs = [t for t in texts(game.act(tap=['finances'], ticks=3)) if t.startswith('They cost a month:')]
        assert money_in(costs[0]) == [8_000 + 10_000]
        game.act(tap=['cancel'], ticks=3)
        play_round(game)
        game.act(tap=['select'], ticks=3)                          # the season's end
        seen = game.act(tap=['select'], ticks=3)                   # New season
        if seen['scene'] == 'job':
            game.act(tap=['down'], ticks=2)
            game.act(tap=['down'], ticks=2)
            seen = game.act(tap=['select'], ticks=3)
        state = seen['state']['game']
        assert len(state['clubs'][MINE]['players']) == 23
        assert 'From the academy:' in [n['text'] for n in state['news']]
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_every_player_on_one_screen(pandafoot, godot):
    """F4: the players of the world, by strength (the first 120); a position (←→), a division (TAB), another order (O);
    Enter on a computer's club's player puts him up for auction, the manager's bid first."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        seen = game.act(tap=['players'], ticks=3)
        assert texts(seen)[0].startswith('PLAYERS - every position, every division, by strength')
        rows = [i['button'] for i in menus(seen)[0]['items']]
        strengths = [int(r[35:39]) for r in rows]
        assert len(rows) == 120 and strengths == sorted(strengths, reverse=True)
        keepers = [i['button'] for i in menus(game.act(tap=['right'], ticks=3))[0]['items']]
        assert keepers and all(r[26:35].startswith('GK') for r in keepers)
        first = [i['button'] for i in menus(game.act(tap=['other'], ticks=3))[0]['items']]
        assert len(first) == 20 and all(r[22:26].strip() == '1' for r in first)    # ten clubs, two keepers each
        by_goals = game.act(tap=['order'], ticks=3)
        assert texts(by_goals)[0].startswith('PLAYERS - GK, 1st division, by goals')
        bid = game.act(tap=['select'], ticks=3)                    # the first of them: up for auction
        assert bid['scene'] == 'bid'
        state = bid['state']['game']
        entry = state['market'][int(state['bidding'])]
        assert entry['seller'] >= 0 and state['clubs'][entry['seller']]['div'] == 1 and entry['pos'] == 'GK'
        assert 'Up for auction:' in [n['text'] for n in state['news']]


def test_the_teams_of_a_live_match(pandafoot, godot):
    """In the live round a match of the list is put in front with Enter (a click); F3 (or "The teams") shows the two
    elevens with their ratings so far, and the round waits under the panel."""
    with PlaySession(pandafoot, binary=godot) as game:
        new_game(game)
        live = game.act(tap=['select'], ticks=3)
        rows = [i['button'] for i in shown(live)[0]['items']]
        assert len(rows) == 5 and sum('►' in r or '◄' in r for r in rows) == 1   # the division's five, the manager's ►
        mine = next(k for k, r in enumerate(rows) if '►' in r or '◄' in r)
        other = (mine + 1) % 5
        for _ in range(other):
            game.act(tap=['down'], ticks=2)
        front = game.act(tap=['select'], ticks=3)
        home = rows[other][1:5].strip()
        clubs = front['state']['game']['clubs']
        assert texts(front)[0].startswith(next(c['name'] for c in clubs if c['short'] == home))
        live = game.act(ticks=200)
        minute = live['state']['minute']
        panel = game.act(tap=['squad'], ticks=3)
        assert panel['scene'] == 'teams' and panel['under'] == 'round'
        sides = tables(panel)
        assert len(sides) == 2 and all(len(t['rows']) >= 12 for t in sides)   # the heading and the eleven (the bench)
        assert all(re.search(r' \d+\.\d', row[0]) for t in sides for row in t['rows'][1:12])   # a rating each
        game.act(ticks=300)                                        # the round waits
        back = game.act(tap=['cancel'], ticks=3)
        assert back['scene'] == 'round' and back['state']['minute'] <= minute + 1
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_the_board_is_pleased_by_a_win_and_a_draw(pandafoot, godot):
    """The board's patience after a round: a win +4, a draw +1, a defeat -3, and half a point a place above or below
    what it expects, two at most (a manager winning half his matches saw the bar only go down); the dashboard says it
    as a number too."""
    with PlaySession(pandafoot, binary=godot) as game:
        before = new_game(game)['state']['game']['managers'][0]['patience']
        after = play_round(game)['state']['game']
        club = after['clubs'][MINE]
        delta = {'W': 4, 'D': 1, 'L': -3}[club['form'][-1]] + \
            max(-2, min(2, 0.5 * (club['expect'] - table_place(after['clubs'], MINE))))
        patience = after['managers'][0]['patience']
        assert patience == pytest.approx(max(0, min(100, before + delta)))
        seen = to_dashboard(game)
        assert texts(seen)[2].endswith(f' {round(patience)}%')


def test_a_career_club_by_club(pandafoot, godot, tmp_path):
    """Sacked, and taken on by another club: the career keeps each club's time and how it ended; F8's ranking has the
    points, the cups and the sackings; Enter on it, the whole career."""
    def at_the_end(state):
        state['managers'][0]['patience'] = 1
        state['clubs'][MINE]['balance'] = -10_000_000
        state['clubs'][MINE]['expect'] = 1
    saved_then(pandafoot, godot, tmp_path, at_the_end)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        continued(game)
        play_round(game)
        game.act(tap=['select'], ticks=3)                          # the job
        taken = game.act(tap=['select'], ticks=3)['state']['game']
        career = taken['managers'][0]['career']
        new = taken['clubs'][taken['managers'][0]['club']]['name']
        assert [(s['club'], s['how'], s['div']) for s in career['stints']] == [(MINE_NAME, 'sacked', 4), (new, '', 4)]
        history = game.act(tap=['history'], ticks=3)
        row = menus(history)[0]['items'][0]['button']
        assert row.startswith('Manager 1') and row[44:49].strip() == '1'                 # sacked once
        page = game.act(tap=['select'], ticks=3)
        assert page['scene'] == 'career' and texts(page)[0] == 'CAREER - Manager 1'
        lines = [r[0] for r in tables(page)[0]['rows']]
        assert lines[0].startswith(MINE_NAME) and lines[0].endswith('sacked')
        assert lines[1].startswith(new) and lines[1].endswith('still there')
        assert game.act(tap=['cancel'], ticks=3)['scene'] == 'history'


def test_a_game_of_2_1_goes_on(pandafoot, godot, tmp_path):
    """A game saved by 2.1 (no ratings, prizes, facilities or stints) continues in 2.2, brought up to it: the computer's
    clubs given their facilities, forty free agents, a stint for the club the manager is at."""
    def as_saved_by_2_1(state):
        state.pop('save_version')
        for c in state['clubs']:
            for k in ('training', 'academy', 'prizes'):
                c.pop(k)
            for p in c['players']:
                for k in ('rating', 'rsum', 'rn', 'msum', 'mn', 'trend', 'grown', 'award', 'award_season'):
                    p.pop(k)
        state['free_agents'] = [{k: v for k, v in p.items() if k not in ('rating', 'rsum', 'rn', 'msum', 'mn',
                                 'trend', 'grown', 'award', 'award_season')} for p in state['free_agents'][:10]]
        for t in state['managers']:
            t['career'].pop('cups')
            t['career'].pop('stints')
    saved_then(pandafoot, godot, tmp_path, as_saved_by_2_1)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        seen = continued(game)
        assert seen['scene'] == 'dashboard'
        state = seen['state']['game']
        assert state['save_version'] == 22 and len(state['free_agents']) == 40
        assert all('training' in c and all('rsum' in p for p in c['players']) for c in state['clubs'])
        assert state['clubs'][0]['training'] == 2 and state['clubs'][MINE]['training'] == 0
        assert [s['club'] for s in state['managers'][0]['career']['stints']] == [MINE_NAME]
        for key in ('squad', 'players', 'finances', 'history', 'market'):
            assert game.act(tap=[key], ticks=3)['scene'] != 'dashboard'
            game.act(tap=['cancel'], ticks=3)
        after = play_round(game)
        assert all('ratings' in m for m in after['state']['game']['last'])
        assert not [line for line in game.log if 'SCRIPT ERROR' in line]


def test_the_ground_says_what_stops_it_growing(pandafoot, godot, tmp_path):
    """A worn ground cannot grow: the dashboard warns before it is too late, and F5 says what to do."""
    def worn(state):
        state['clubs'][MINE]['health'] = 55
    saved_then(pandafoot, godot, tmp_path, worn)
    with PlaySession(pandafoot, binary=godot, persist_dir=tmp_path) as game:
        seen = continued(game)
        assert any('The ground needs care (F5)' in t for t in texts(seen))
        finances = game.act(tap=['finances'], ticks=3)
        assert '✗ Health over 60 first: Maintenance.' in texts(finances)
