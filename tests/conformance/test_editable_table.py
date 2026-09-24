"""Conformance: a table that sorts and edits itself (M16, SPEC UI-13)."""

import asyncio
import logging
import re
import sqlite3
import threading

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

SCHEMA = """
CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
  done BOOLEAN NOT NULL DEFAULT 0);
INSERT INTO tasks (title, priority) VALUES ('Beta', 'high'), ('Alpha', 'low'), ('Gamma', 'medium');
"""


def page(table='sort="true" edit="tasks" datasource="db"', query='sortable="true"',
         select='id, title, priority, done', before=''):
    return (f'<q:component name="t" {NS}>{before}'
            f'<q:query name="tasks" datasource="db" {query}>SELECT {select} FROM tasks</q:query>'
            '<ui:window title="T"><q:if condition="flash"><ui:alert>{flash}</ui:alert></q:if>'
            f'<ui:table source="{{tasks}}" {table}>'
            '<ui:column key="title" label="Title"/><ui:column key="priority" label="Priority"/>'
            '<ui:column key="done" label="Done"/><ui:column key="id" label="#" edit="false"/>'
            '</ui:table></ui:window></q:component>')


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 't.db'
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.close()
    return path


@pytest.fixture
def open_page(serve_pages, db, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    ds = f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n'
    return lambda **p: serve_pages(datasources_yaml=ds, **p)


def rows(db, sql):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def edit(c, column, key, value=None, table='tasks'):
    data = {'action': '__edit', '__table': table, '__key': str(key), '__column': column}
    if value is not None:
        data['value'] = value
    return c.post('/t', data=data, headers={'Referer': 'http://localhost/t'})


class TestSorting:
    def test_a_header_sorts_in_sql_and_toggles(self, open_page):
        # UI-13
        c = open_page(t=page())
        html = c.get('/t?sort=title&dir=asc&x=1&page=2').get_data(as_text=True)
        assert re.findall(r'value="(Alpha|Beta|Gamma)"', html) == ['Alpha', 'Beta', 'Gamma']
        assert 'href="/t?x=1&amp;sort=title&amp;dir=desc"' in html and 'Title ▲' in html
        html = c.get('/t?sort=title&dir=desc').get_data(as_text=True)
        assert re.findall(r'value="(Alpha|Beta|Gamma)"', html) == ['Gamma', 'Beta', 'Alpha']

    def test_a_column_from_the_url_that_does_not_exist_is_ignored(self, open_page):
        # UI-13: it comes from the URL — not an error, and never SQL
        html = open_page(t=page()).get('/t?sort=title;DROP TABLE tasks&dir=asc').get_data(as_text=True)
        assert re.findall(r'value="(Alpha|Beta|Gamma)"', html) == ['Beta', 'Alpha', 'Gamma']

    def test_it_sorts_before_paginating(self, open_page):
        # UI-13 + DB-9: the order applies to every page, not only the current one
        c = open_page(t=page(query='sortable="true" paginate="true" page_size="2"', table='sort="true"'))
        html = c.get('/t?sort=title&dir=asc&page=2').get_data(as_text=True)
        assert re.findall(r'>\s*(Alpha|Beta|Gamma)\s*<', html) == ['Gamma']

    def test_a_sortable_table_needs_a_sortable_query(self, open_page, caplog):
        # UI-13
        c = open_page(t=page(query='', table='sort="true"'))
        with caplog.at_level(logging.ERROR, logger='quantum.server'):
            assert c.get('/t').status_code == 500
        assert any('needs sortable="true"' in r.getMessage() for r in caplog.records)


class TestEditing:
    def test_a_cell_is_a_form_with_the_column_rules(self, open_page):
        # UI-13
        html = open_page(t=page()).get('/t').get_data(as_text=True)
        cell = re.search(r'<form method="post" class="q-cell">(?:(?!</form>).)*name="__key" value="2"'
                         r'(?:(?!</form>).)*name="__column" value="title".*?</form>', html, re.S).group(0)
        assert 'name="action" value="__edit"' in cell and 'value="Alpha"' in cell and 'required' in cell
        assert 'id="cell-title-2"' in cell
        assert '<option value="low" selected>' in html                    # CHECK … IN becomes a selection
        assert 'name="__column" value="id"' not in html                    # the key is not editable

    def test_editing_saves_and_shows_in_dev(self, open_page, db):
        # UI-13
        c = open_page(t=page())
        assert edit(c, 'title', 2, 'Alpha 2').status_code == 302
        assert rows(db, 'SELECT title FROM tasks WHERE id = 2') == [('Alpha 2',)]
        assert 'Saved: title' in c.get('/t').get_data(as_text=True)
        edit(c, 'done', 3, 'on')
        assert rows(db, 'SELECT done FROM tasks WHERE id = 3') == [(1,)]
        edit(c, 'done', 3)                                                  # unchecked: not sent
        assert rows(db, 'SELECT done FROM tasks WHERE id = 3') == [(0,)]

    def test_an_invalid_value_comes_back_in_the_cell(self, open_page, db):
        # UI-13
        c = open_page(t=page())
        edit(c, 'priority', 1, 'urgent')
        html = c.get('/t').get_data(as_text=True)
        assert re.findall(r'q-field-error"[^>]*>\s*([^<]*?)\s*</span>', html) == ['Must be one of: low, medium, high']
        assert rows(db, 'SELECT priority FROM tasks WHERE id = 1') == [('high',)]
        edit(c, 'title', 1, '')
        assert 'Required' in c.get('/t').get_data(as_text=True)

    @pytest.mark.parametrize('column,table', [('id', 'tasks'), ('sql', 'sqlite_master'), ('nothing', 'tasks')])
    def test_only_what_the_page_declares_is_editable(self, open_page, db, column, table):
        # UI-13: a forged form finds nothing
        c = open_page(t=page())
        assert edit(c, column, 1, 'x', table=table).status_code == 400
        assert rows(db, 'SELECT id, title FROM tasks WHERE id = 1') == [(1, 'Beta')]

    def test_the_page_guard_applies_to_editing(self, open_page, db):
        # UI-13 + AUTH-6
        c = open_page(t=page(before='<q:if condition="not session.owner"><q:redirect url="/signin"/></q:if>'))
        r = edit(c, 'title', 2, 'Break-in')
        assert r.status_code == 302 and r.headers['Location'].endswith('/signin')
        assert rows(db, 'SELECT title FROM tasks WHERE id = 2') == [('Alpha',)]

    def test_rows_without_the_key_are_an_error(self, open_page, caplog):
        # UI-13
        c = open_page(t=page(select='title, priority, done').replace('<ui:column key="id" label="#" edit="false"/>', ''))
        with caplog.at_level(logging.ERROR, logger='quantum.server'):
            assert c.get('/t').status_code == 500
        assert any('the rows need the key column "id"' in r.getMessage() for r in caplog.records)

    def test_edit_without_datasource_is_a_parse_error(self):
        # UI-13
        from quantum.core.parser import QuantumParser
        with pytest.raises(Exception, match=r'edit="tasks"> needs datasource='):
            QuantumParser().parse(page(table='edit="tasks"'))


def test_the_dev_panel_shows_the_edit(tmp_path, db, monkeypatch):
    # UI-13 + DEV-1: what it generates shows in /_dev
    from quantum.runtime.web_server import QuantumWebServer
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'components').mkdir()
    (tmp_path / 'components' / 't.q').write_text(page(), encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text(
        'server: {debug: true}\npaths: {components: ./components}\n'
        f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n', encoding='utf-8')
    c = QuantumWebServer('quantum.config.yaml').app.test_client()
    edit(c, 'title', 2, 'New')
    panel = c.get('/_dev').get_data(as_text=True)
    assert '__edit tasks.title' in panel and 'UPDATE &quot;tasks&quot; SET &quot;title&quot;' in panel


def test_the_console_sorts_and_edits(tmp_path, db, monkeypatch):
    # UI-13 + UI-3
    from textual.widgets import Button, Input
    from werkzeug.serving import make_server
    from quantum.runtime.ui_console import ConsoleUI
    from quantum.runtime.web_server import QuantumWebServer
    from tests.console_pilot import enter, page_loaded, press
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'components').mkdir()
    (tmp_path / 'components' / 't.q').write_text(page(), encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text(
        'paths: {components: ./components}\n'
        f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n', encoding='utf-8')
    logging.disable(logging.WARNING)
    srv = make_server('127.0.0.1', 0, QuantumWebServer('quantum.config.yaml').app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    async def main():
        app = ConsoleUI(f'http://127.0.0.1:{srv.server_port}/', '/t')
        async with app.run_test(size=(140, 40)) as pilot:
            await page_loaded(app, pilot)
            await press(app, pilot, [b for b in app.query(Button) if str(b.label).startswith('Title')][0])
            order = [w.value for w in app.query(Input) if w.id and w.id.startswith('cell-title')]
            field = [w for w in app.query(Input) if w.id == 'cell-title-2'][0]
            field.value = 'From the console'
            field.focus()
            await enter(app, pilot)
            return order, app.path

    try:
        order, path = asyncio.run(main())
    finally:
        srv.shutdown()
        logging.disable(logging.NOTSET)
    assert order == ['Alpha', 'Beta', 'Gamma'] and 'sort=title' in path
    assert rows(db, 'SELECT title FROM tasks WHERE id = 2') == [('From the console',)]
