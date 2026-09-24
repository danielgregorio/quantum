"""Conformance: SPEC.md section 3c (how a page runs)."""

import logging
import re

import pytest

from quantum.core.docs_links import HOW_A_PAGE_RUNS
from quantum.core.parser import QuantumParser

NS = 'xmlns:q="https://quantum.lang/ns"'


def marks(response):
    return re.findall(r'\[[^\]]*\]', response.get_data(as_text=True))


PAGE = (f'<q:component name="p" {NS}>'
        '<q:action name="noredirect" method="POST"><q:set name="session.v" value="done"/></q:action>'
        '<q:action name="withredirect" method="POST"><q:set name="session.v" value="redir"/>'
        '<q:redirect url="/p"/></q:action>'
        '<q:set name="twice" value="{double(21)}" type="number"/>'
        '<q:function name="double"><q:param name="n" type="number"/><q:return value="{n * 2}"/></q:function>'
        '<q:set name="application.visits" value="{application.visits}" default="0" type="number"/>'
        '<q:set name="application.visits" value="{application.visits + 1}"/>'
        '<q:set name="local" value="{session.v}" default="none"/>'
        '<p>[twice={twice}][v={session.v}][visits={application.visits}][local={local}]</p>'
        '</q:component>')


class TestOrder:
    def test_a_function_works_before_where_it_is_written(self, serve_pages):
        # EXEC-1
        assert '[twice=42]' in marks(serve_pages(p=PAGE).get('/p'))

    def test_a_statement_in_markup_points_to_the_guide_page(self):
        # EXEC-1, PARSE-2
        with pytest.raises(Exception, match=re.escape(HOW_A_PAGE_RUNS)):
            QuantumParser().parse(f'<q:component name="c" {NS}><div><q:set name="x" value="1"/></div></q:component>')

    def test_a_guard_that_reads_the_page_points_to_the_guide(self):
        # EXEC-2, AUTH-6
        with pytest.raises(Exception, match=re.escape(HOW_A_PAGE_RUNS)):
            QuantumParser().parse(
                f'<q:component name="c" {NS}><q:set name="owner" value="1"/>'
                '<q:if condition="owner"><q:redirect url="/"/></q:if>'
                '<q:action name="a" method="POST"><q:redirect url="/"/></q:action></q:component>')


class TestPost:
    def test_with_a_redirect_the_browser_asks_for_the_page(self, serve_pages):
        # EXEC-2
        c = serve_pages(p=PAGE)
        r = c.post('/p', data={'action': 'withredirect'})
        assert r.status_code == 302 and r.headers['Location'].endswith('/p')
        assert '[v=redir]' in marks(c.get('/p'))

    def test_without_a_redirect_the_page_runs_after_the_action(self, serve_pages):
        # EXEC-2: 200, and the page's statements run after the action
        c = serve_pages(p=PAGE)
        r = c.post('/p', data={'action': 'noredirect'})
        assert r.status_code == 200
        assert '[v=done]' in marks(r) and '[local=done]' in marks(r)

    def test_an_action_that_reads_the_page_points_to_the_guide(self, serve_pages, caplog):
        # EXEC-2, ACT-9
        c = serve_pages(p=(f'<q:component name="p" {NS}><q:set name="post" value="7"/>'
                           '<q:action name="a" method="POST"><q:set name="session.x" value="{post}"/>'
                           '<q:redirect url="/p"/></q:action><p>x</p></q:component>'))
        with caplog.at_level(logging.ERROR, logger='quantum'):
            assert c.post('/p', data={'action': 'a'}).status_code == 500
        assert any(HOW_A_PAGE_RUNS in r.getMessage() for r in caplog.records)


class TestLifetime:
    def test_a_page_variable_lives_one_request(self, serve_pages):
        # EXEC-3: `local` is computed again on each request, inheriting nothing from the last
        c = serve_pages(p=PAGE)
        assert '[local=none]' in marks(c.get('/p'))
        c.post('/p', data={'action': 'withredirect'})
        assert '[local=redir]' in marks(c.get('/p'))

    def test_session_is_the_visitor_s_application_everyone_s(self, serve_pages):
        # EXEC-3
        one = serve_pages(p=PAGE)
        other = one.application.test_client()
        one.post('/p', data={'action': 'withredirect'})
        assert '[v=redir]' in marks(one.get('/p'))
        others_page = marks(other.get('/p'))
        assert '[v=]' in others_page                           # the session is each visitor's
        # application: both visits by GET (the POST with a redirect only runs the action)
        visits = int(re.search(r'visits=(\d+)', ''.join(others_page)).group(1))
        assert visits == 2

    def test_an_action_writes_and_reads_the_application_scope(self, serve_pages):
        # EXEC-3: the action's application scope is the server's. It used to be an
        # empty one of its own: what an action wrote was lost, and it read nothing.
        c = serve_pages(board=(
            f'<q:component name="board" {NS}>'
            '<q:action name="post" method="POST"><q:param name="text" required="true"/>'
            '<q:set name="application.notes" type="array" value="{application.notes}" default="[]"/>'
            '<q:set name="application.notes" operation="append" value="{text}"/>'
            '<q:set name="session.seen" value="{len(application.notes)}"/>'
            '<q:redirect url="/board"/></q:action>'
            '<q:set name="application.notes" type="array" value="{application.notes}" default="[]"/>'
            '<p>[notes={len(application.notes)}] [seen={session.seen}]</p></q:component>'))
        c.post('/board', data={'action': 'post', 'text': 'one'})
        c.post('/board', data={'action': 'post', 'text': 'two'})
        assert '[seen=2]' in marks(c.get('/board'))                  # the action read what it wrote before
        other = c.application.test_client()
        assert '[notes=2]' in marks(other.get('/board'))             # another visitor sees both

    def test_a_date_in_the_session_comes_back_the_same_date(self, serve_pages):
        # SET-5: {dateAdd(...)} keeps its type, and the session keeps a date without
        # a timezone as the same local date — Flask read it back as UTC, shifted by
        # the server's offset (a login valid for 1 hour was expired in UTC-3).
        c = serve_pages(d=(
            f'<q:component name="d" {NS}>'
            '<q:action name="keep" method="POST">'
            "<q:set name=\"session.until\" value=\"{dateAdd('h', 1)}\"/><q:redirect url=\"/d\"/></q:action>"
            '<p>[later={session.until > now()}] [soon={session.until &lt; dateAdd(\'h\', 2)}]</p></q:component>'))
        c.post('/d', data={'action': 'keep'})
        assert marks(c.get('/d')) == ['[later=True]', '[soon=True]']
