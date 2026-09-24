"""Conformance: the page from the URL (DB-9) and <ui:pager> (M14, UI-11)."""

import re
import sqlite3

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'


def page(body, query_attrs='paginate="true" page_size="10"'):
    return (f'<q:component name="l" {NS}>'
            f'<q:query name="items" datasource="db" {query_attrs}>SELECT n FROM t ORDER BY id</q:query>'
            f'<p>[{{items_result.pagination.currentPage}}/{{items_result.pagination.totalPages}}]</p>'
            f'<ui:window title="L">{body}</ui:window></q:component>')


@pytest.fixture
def open_page(serve_pages, tmp_path):
    db = tmp_path / 'a.db'
    c = sqlite3.connect(db)
    c.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, n TEXT)')
    c.executemany('INSERT INTO t (n) VALUES (?)', [(f'item{i:02d}',) for i in range(1, 96)])
    c.commit()
    c.close()
    ds = f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n'
    return lambda **p: serve_pages(datasources_yaml=ds, **p)


def state(html):
    return re.search(r'\[(\d+)/(\d+)\]', html).groups()


def nav(html):
    return html.split('<nav', 1)[1].split('</nav>', 1)[0] if '<nav' in html else ''


class TestPageFromTheUrl:
    @pytest.mark.parametrize('url,expected', [('/l', '1'), ('/l?page=3', '3'), ('/l?page=abc', '1'),
                                              ('/l?page=-2', '1')])
    def test_the_page_comes_from_the_page_parameter(self, open_page, url, expected):
        # DB-9 (before: page= was read as an integer at parse time; the URL never changed the page)
        assert state(open_page(l=page('')).get(url).get_data(as_text=True)) == (expected, '10')

    def test_page_as_an_expression(self, open_page):
        # DB-9
        c = open_page(l=page('', 'paginate="true" page_size="10" page="{query.p}"'))
        assert state(c.get('/l?p=4&page=9').get_data(as_text=True)) == ('4', '10')

    def test_an_invalid_literal_page_is_a_parse_error(self):
        # DB-9
        from quantum.core.parser import QuantumParser
        with pytest.raises(Exception, match=r'page="two"'):
            QuantumParser().parse(page('', 'paginate="true" page_size="10" page="two"'))


class TestPager:
    def test_previous_numbers_with_a_gap_and_next(self, open_page):
        # UI-11
        html = nav(open_page(l=page('<ui:pager for="items"/>')).get('/l?page=5').get_data(as_text=True))
        labels = [re.sub(r'\s+', '', r) for r in re.findall(r'>([^<]+)</(?:a|span)>', html)]
        assert labels == ['‹', '1', '…', '3', '4', '5', '6', '7', '…', '10', '›']
        assert re.search(r'<span class="q-page-current" aria-current="page">\s*5', html)

    def test_links_keep_the_other_parameters(self, open_page):
        # UI-11
        html = nav(open_page(l=page('<ui:pager for="items"/>')).get('/l?page=2&order=name').get_data(as_text=True))
        assert 'href="/l?order=name&amp;page=1"' in html and 'href="/l?order=name&amp;page=3"' in html

    def test_at_the_ends_previous_and_next_are_not_links(self, open_page):
        # UI-11
        c = open_page(l=page('<ui:pager for="items" window="1"/>'))
        first = nav(c.get('/l').get_data(as_text=True))
        assert re.search(r'<span class="q-page-disabled">\s*‹', first)
        last = nav(c.get('/l?page=10').get_data(as_text=True))
        assert re.search(r'<span class="q-page-disabled">\s*›', last)

    def test_a_single_page_draws_nothing(self, open_page):
        # UI-11
        c = open_page(l=page('<ui:pager for="items"/>', 'paginate="true" page_size="500"'))
        assert '<nav' not in c.get('/l').get_data(as_text=True)

    def test_a_query_that_is_not_paginated_is_an_error(self, open_page, caplog):
        # UI-11
        import logging
        c = open_page(l=page('<ui:pager for="items"/>', ''))
        with caplog.at_level(logging.ERROR, logger='quantum.server'):
            assert c.get('/l').status_code == 500
        assert any('there is no paginated q:query named "items"' in r.getMessage() for r in caplog.records)

    def test_without_for_it_is_a_parse_error(self):
        # UI-11
        from quantum.core.parser import QuantumParser
        with pytest.raises(Exception, match=r'<ui:pager> needs for='):
            QuantumParser().parse(page('<ui:pager/>'))

    def test_the_console_gets_the_same_items(self, open_page):
        # UI-11, UI-3
        tree = open_page(l=page('<ui:pager for="items"/>')).get(
            '/l?page=2', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()
        window = next(n for n in tree['view'] if n['type'] == 'window')
        row = window['children'][0]
        assert [(n['type'], n['props'].get('text'), n['props'].get('to')) for n in row['children']][:4] == [
            ('link', '‹', '/l?page=1'), ('link', '1', '/l?page=1'), ('text', '[2]', None), ('link', '3', '/l?page=3')]


def test_the_pager_style_reaches_the_page(open_page):
    # UI-11 (a first cut drew the pager without its CSS)
    c = open_page(l=page('<ui:pager for="items"/>'))
    html = c.get('/l').get_data(as_text=True)
    sheets = re.findall(r'href="(/static/[^"]+\.css)"', html)
    css = ''
    for f in sheets:
        with c.get(f) as sheet:   # a static file: close it
            css += sheet.get_data(as_text=True)
    assert '.q-pager' in css or '.q-pager {' in html
