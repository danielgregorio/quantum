"""Conformance: change history per datasource (M22, SPEC DB-11)."""

import json
import re
import sqlite3

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

SCHEMA = """
CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft');
INSERT INTO posts (title) VALUES ('First');
"""

PAGE = (f'<q:component name="p" {NS}>'
        '<q:set name="session.userName" value="ana"/>'
        '<q:action name="create" method="POST"><q:param name="title" required="true"/>'
        '<q:query name="ins" datasource="db">INSERT INTO posts (title) VALUES (:t)'
        '<q:param name="t" value="{title}" type="string"/></q:query><q:redirect url="/p"/></q:action>'
        '<q:action name="rename" method="POST"><q:param name="id" type="integer"/><q:param name="title"/>'
        '<q:query name="upd" datasource="db">UPDATE posts SET title = :t WHERE id = :id'
        '<q:param name="t" value="{title}" type="string"/><q:param name="id" value="{id}" type="integer"/>'
        '</q:query><q:redirect url="/p"/></q:action>'
        '<q:action name="remove" method="POST"><q:param name="id" type="integer"/>'
        '<q:query name="del" datasource="db">DELETE FROM posts WHERE id = :id'
        '<q:param name="id" value="{id}" type="integer"/></q:query><q:redirect url="/p"/></q:action>'
        '<q:action name="fail" method="POST">'
        '<q:transaction datasource="db"><q:query name="u" datasource="db">UPDATE posts SET title = \'X\' WHERE id = 1</q:query>'
        '<q:query name="bad" datasource="db">INSERT INTO nowhere VALUES (1)</q:query></q:transaction>'
        '<q:redirect url="/p"/></q:action>'
        '<q:query name="posts" datasource="db">SELECT id, title FROM posts</q:query>'
        '<ui:window title="P"><ui:history table="posts" key="1" datasource="db"/></ui:window></q:component>')


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'h.db'
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.close()
    return path


@pytest.fixture
def open_app(serve_pages, database, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def build(history=True, **pages):
        ds = (f'datasources:\n  db:\n    driver: sqlite\n    database: {database.as_posix()}\n'
              + ('    history: true\n' if history else ''))
        return serve_pages(datasources_yaml=ds, **pages)
    return build


def history_rows(database):
    conn = sqlite3.connect(database)
    try:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'quantum_history'").fetchone()
        if not exists:
            return []
        return conn.execute('SELECT user, action, table_name, row_key, op, before, after '
                            'FROM quantum_history ORDER BY id').fetchall()
    finally:
        conn.close()


def test_each_write_of_an_action_is_recorded(open_app, database):
    # DB-11
    c = open_app(p=PAGE)
    c.get('/p')                                         # the session gets userName
    c.post('/p', data={'action': 'create', 'title': 'Second'})
    c.post('/p', data={'action': 'rename', 'id': '1', 'title': 'First!'})
    c.post('/p', data={'action': 'remove', 'id': '2'})
    rows = history_rows(database)
    assert [(r[0], r[1], r[2], r[3], r[4]) for r in rows] == [
        ('ana', 'create', 'posts', '2', 'insert'),
        ('ana', 'rename', 'posts', '1', 'update'),
        ('ana', 'remove', 'posts', '2', 'delete')]
    assert json.loads(rows[0][6])['title'] == 'Second' and rows[0][5] is None
    assert json.loads(rows[1][5])['title'] == 'First' and json.loads(rows[1][6])['title'] == 'First!'
    assert json.loads(rows[2][5])['title'] == 'Second' and rows[2][6] is None


def test_off_by_default(open_app, database):
    # DB-11
    c = open_app(history=False, p=PAGE.replace('<ui:window title="P"><ui:history table="posts" key="1" datasource="db"/></ui:window>', ''))
    c.post('/p', data={'action': 'create', 'title': 'Second'})
    assert history_rows(database) == []


def test_a_rolled_back_write_leaves_no_history(open_app, database):
    # DB-11: the history goes with the write
    import logging
    c = open_app(p=PAGE)
    logging.disable(logging.CRITICAL)
    try:
        assert c.post('/p', data={'action': 'fail'}).status_code == 500
    finally:
        logging.disable(logging.NOTSET)
    assert history_rows(database) == []


def test_page_statements_are_not_recorded(open_app, database):
    # DB-11: only actions
    page = PAGE.replace('<q:query name="posts" datasource="db">',
                        '<q:query name="touch" datasource="db">UPDATE posts SET status = \'draft\' WHERE id = 1</q:query>'
                        '<q:query name="posts" datasource="db">')
    open_app(p=page).get('/p')
    assert history_rows(database) == []


def test_ui_history_lists_a_row(open_app):
    # DB-11
    c = open_app(p=PAGE)
    assert 'No changes recorded yet.' in c.get('/p').get_data(as_text=True)
    c.post('/p', data={'action': 'rename', 'id': '1', 'title': 'First!'})
    html = c.get('/p').get_data(as_text=True)
    table = html.split('q-history', 1)[1].split('</table>', 1)[0]
    assert re.search(r'>\s*ana\s*<', table) and re.search(r'>\s*rename\s*<', table)
    assert 'title: First → First!' in table


def test_ui_history_on_a_datasource_without_history_is_an_error(open_app, caplog):
    # DB-11
    import logging
    c = open_app(history=False, p=PAGE)
    with caplog.at_level(logging.ERROR, logger='quantum.server'):
        assert c.get('/p').status_code == 500
    assert any('does not record history' in r.getMessage() for r in caplog.records)


def test_cell_edits_are_recorded(open_app, database):
    # DB-11 + UI-13
    page = (f'<q:component name="t" {NS}><q:query name="posts" datasource="db">SELECT id, title FROM posts</q:query>'
            '<ui:window title="T"><ui:table source="{posts}" edit="posts" datasource="db">'
            '<ui:column key="title"/></ui:table></ui:window></q:component>')
    c = open_app(t=page)
    c.post('/t', data={'action': '__edit', '__table': 'posts', '__key': '1', '__column': 'title', 'value': 'Edited'},
           headers={'Referer': 'http://localhost/t'})
    assert [(r[1], r[4]) for r in history_rows(database)] == [('__edit posts.title', 'update')]


def test_console_shows_the_history(open_app):
    # DB-11 + UI-3
    c = open_app(p=PAGE)
    c.post('/p', data={'action': 'rename', 'id': '1', 'title': 'First!'})
    tree = c.get('/p', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()
    table = tree['view'][0]['children'][0]
    assert [col['label'] for col in table['columns']] == ['When', 'Who', 'Action', 'Change']
    assert table['rows'][0][3][0]['props']['text'] == 'title: First → First!'


@pytest.mark.parametrize('attrs,message', [('table="posts" key="1"', 'needs datasource='),
                                           ('table="posts" key="1" datasource="db" limit="x"', 'a number')])
def test_ui_history_attributes(attrs, message):
    # DB-11
    from quantum.core.parser import QuantumParser
    with pytest.raises(Exception, match=message):
        QuantumParser().parse(f'<q:component name="p" {NS}><ui:history {attrs}/></q:component>')
