"""The game server, Phase 4 of PLAN_GAME_SERVER.md: a world of a site's accounts (accounts="site").

A ticket is the site's word that an account signed in: its account, the name its hero shows and when it ends, signed
with the secret the site and the world share (QUANTUM_WORLD_SECRET). The world lets in a good ticket once, and no
name, no forged ticket, no ticket of another secret, no old one. An account that signs in again takes its hero over
where it stands, still in its party; one whose connection dropped comes back to its hero where it was.
"""

import time
from pathlib import Path

import pytest

from quantum.runtime.gameserver import GameServerError
from quantum.runtime.gameserver.server import WorldServer, load
from quantum.runtime.gameserver.session import WorldSession, WorldSessionError, serve_world
from quantum.runtime.gameserver.tickets import TicketError, issue, secret_from_env, verify

DEN = Path(__file__).resolve().parent / 'worlds' / 'den' / 'den.server.q'
SECRET = b'the den and its site share this'


def site_den(tmp_path):
    """The den, of a site's accounts, whose heroes are kept while their players are away."""
    source = DEN.read_text()
    for old, new in [('<q:gameserver name="den"', '<q:gameserver name="den" accounts="site"'),
                     ('per-player="true"', 'per-player="true" persist="true"')]:
        assert old in source
        source = source.replace(old, new)
    (tmp_path / 'den.tmx').write_text((DEN.parent / 'den.tmx').read_text())
    path = tmp_path / 'den.server.q'
    path.write_text(source)
    return path


def ticket(account='ana@site', name='Ana', **options):
    return issue(account, name, SECRET, **options)


def test_a_ticket_says_its_account_and_name_and_nothing_else_passes():
    good = ticket()
    assert verify(good, SECRET)[:2] == ('ana@site', 'Ana')
    body, signature = good.split('.')
    other = issue('ana@site', 'Ana', b'not the site secret at all')
    with pytest.raises(TicketError, match="not the site's"):
        verify(other, SECRET)
    forged = ticket('bo@site').split('.')[0] + '.' + signature        # bo's body, ana's signature
    with pytest.raises(TicketError, match="not the site's"):
        verify(forged, SECRET)
    with pytest.raises(TicketError, match='expired'):
        verify(ticket(seconds=60, now=time.time() - 120), SECRET)
    for junk in ('', 'abc', 'a.b.c', 42, None, body + '.!!!!'):
        with pytest.raises(TicketError):
            verify(junk, SECRET)
    with pytest.raises(TicketError, match='an account is'):
        issue('ana site', 'Ana', SECRET)
    assert verify(ticket(name='\x07' + 'A' * 40), SECRET).name == 'A' * 24
    assert verify(ticket(name=''), SECRET).name == 'ana@site'


def test_the_secret_is_the_environments_and_a_short_one_is_none(monkeypatch):
    monkeypatch.setenv('QUANTUM_WORLD_SECRET', 'short')
    assert secret_from_env() is None
    monkeypatch.setenv('QUANTUM_WORLD_SECRET', 'x' * 16)
    assert secret_from_env() == b'x' * 16


def test_a_site_world_does_not_start_without_its_secret(tmp_path, monkeypatch):
    monkeypatch.delenv('QUANTUM_WORLD_SECRET', raising=False)
    with pytest.raises(GameServerError, match='QUANTUM_WORLD_SECRET'):
        WorldServer(load(str(site_den(tmp_path))), data_dir=tmp_path / 'data')


def test_only_a_good_ticket_comes_in_and_only_once(tmp_path):
    with serve_world(site_den(tmp_path), secret=SECRET) as server:
        with pytest.raises(WorldSessionError, match='sign in: a hello has a ticket'):
            WorldSession(server.url, 'ana')
        with pytest.raises(WorldSessionError, match="not the site's"):
            WorldSession(server.url, ticket=issue('ana@site', 'Ana', b'a secret of another site'))
        with pytest.raises(WorldSessionError, match='expired'):
            WorldSession(server.url, ticket=ticket(now=time.time() - 120))
        good = ticket()
        with WorldSession(server.url, ticket=good) as ana:
            assert ana.me_id == 'hero:ana@site'
            seen = ana.observe()
            assert seen['me']['name'] == 'Ana'
            assert {'channel': 'system', 'from': 'world', 'text': 'Welcome to the den, Ana.'} in [
                e['value'] for e in seen['events'] if e['name'] == 'chat']
            with pytest.raises(WorldSessionError, match='used already'):
                WorldSession(server.url, ticket=good)


def test_signing_in_again_takes_the_hero_over_where_it_stands(tmp_path):
    with serve_world(site_den(tmp_path), secret=SECRET) as server:
        with WorldSession(server.url, ticket=ticket()) as ana, \
                WorldSession(server.url, ticket=ticket('bo@site', 'Bo')) as bo:
            ana.act(send=[('party-invite', {'who': 'Bo'})], ticks=1)              # by the name it shows
            bo.act(send=[('party-accept', {'who': 'Ana'})], ticks=1)
            ana.act(send=[('step', {'dir': 'east'})], ticks=3)
            where = ana.observe()['me']['at']
            party = ana.observe()['me']['party']
            assert party
            with WorldSession(server.url, ticket=ticket()) as again:
                assert again.me_id == 'hero:ana@site'
                seen = again.observe()
                assert seen['me']['at'] == where and seen['me']['party'] == party
                with pytest.raises(WorldSessionError, match='signed in somewhere else'):
                    for _ in range(5):
                        ana.observe()
                assert server.world.players == {'ana@site': 'hero:ana@site', 'bo@site': 'hero:bo@site'}
                again.act(send=[('chat', {'channel': 'party', 'text': 'still here'})], ticks=1)
                heard = [e['value'] for e in bo.observe()['events'] if e['name'] == 'chat']
                assert {'channel': 'party', 'from': 'Ana', 'text': 'still here'} in heard


def test_a_dropped_connection_comes_back_to_its_hero_where_it_was(tmp_path):
    with serve_world(site_den(tmp_path), secret=SECRET) as server:
        with WorldSession(server.url, ticket=ticket()) as ana:
            ana.act(send=[('buy', {'item': 'cheese'})], ticks=1)
            ana.act(send=[('step', {'dir': 'east'})], ticks=3)
            before = ana.observe()['me']
        with WorldSession(server.url, control=True) as control:             # the world notices it left
            for _ in range(50):
                if 'ana@site' not in control.act(ticks=1) and 'ana@site' not in control.peek()['players']:
                    break
            assert 'ana@site' not in control.peek()['players']
        with WorldSession(server.url, ticket=ticket()) as ana:
            now = ana.observe()['me']
            assert (now['at'], now['gold'], now['bag']) == (before['at'], before['gold'], before['bag'])
        assert server.world.balanced() == {}
