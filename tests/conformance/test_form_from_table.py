"""Conformance: a form from the table (M17, SPEC UI-10)."""

import re
import sqlite3

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

SCHEMA = """
CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
INSERT INTO authors (name) VALUES ('Bia'), ('Ana');
CREATE TABLE posts (
  id INTEGER PRIMARY KEY,
  title VARCHAR(80) NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
  featured BOOLEAN NOT NULL DEFAULT 0,
  score INTEGER,
  author_id INTEGER NOT NULL REFERENCES authors(id)
);
INSERT INTO posts (title, status, featured, score, author_id) VALUES ('First', 'published', 1, 7, 1);
"""

INSERT = ('<q:query name="i" datasource="db">INSERT INTO posts (title, status, featured, score, author_id) '
          'VALUES (:title, :status, :featured, :score, :author_id)'
          '<q:param name="title" value="{title}"/><q:param name="status" value="{status}"/>'
          '<q:param name="featured" value="{featured}" type="boolean"/>'
          '<q:param name="score" value="{score}" type="integer" null="true"/>'
          '<q:param name="author_id" value="{author_id}" type="integer"/></q:query>')


def page(action_attrs='table="posts" datasource="db"', form='<ui:form on-submit="create" submit="Create post"/>',
         extra='', before=''):
    return (f'<q:component name="p" {NS}>{before}'
            f'<q:action name="create" method="POST" {action_attrs}>{extra}{INSERT}'
            '<q:redirect url="/p" flash="ok"/></q:action>'
            f'<ui:window title="T">{form}</ui:window></q:component>')


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                # sqlite relative to the working directory (DB-7)
    c = sqlite3.connect(tmp_path / 'app.db')
    c.executescript(SCHEMA)
    c.close()
    return tmp_path / 'app.db'


@pytest.fixture
def open_page(serve_pages, db):
    ds = f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n'

    def f(**pages):
        return serve_pages(datasources_yaml=ds, **pages)
    return f


def form(html):
    return html.split('<form', 1)[1].split('</form>', 1)[0]


def field(html, name):
    m = re.search(rf'<(?:input|select)[^>]*name="{name}"[^>]*>', html)
    return m.group(0) if m else ''


class TestParamsFromTheTable:
    def test_a_form_without_fields_draws_one_per_column(self, open_page):
        # UI-10
        html = form(open_page(p=page()).get('/p').get_data(as_text=True))
        assert [re.sub(r'\s+', ' ', r).strip() for r in re.findall(r'q-formitem-label">([^<]*)<', html)] == \
            ['Title', 'Status', 'Score', 'Author']
        assert 'required' in field(html, 'title') and 'maxlength="80"' in field(html, 'title')
        assert '<option value="draft">' in html and '<option value="published">' in html
        assert 'type="checkbox" name="featured"' in html
        assert 'type="number"' in field(html, 'score') and 'required' not in field(html, 'score')
        assert re.search(r'<option value="2">\s*Ana\s*</option>', html)      # foreign key: a label, by name
        assert 'Create post' in html and 'name="id"' not in html               # the primary key is left out

    def test_a_form_with_fields_of_its_own_generates_none(self, open_page):
        # UI-10
        html = form(open_page(p=page(form='<ui:form on-submit="create"><ui:input bind="title"/>'
                                          '<ui:button>Go</ui:button></ui:form>')).get('/p').get_data(as_text=True))
        assert 'name="status"' not in html and 'required' in field(html, 'title')   # rules, yes (UI-9)

    def test_a_written_q_param_wins_and_columns_chooses_and_orders(self, open_page):
        # UI-10
        html = form(open_page(p=page(action_attrs='table="posts" datasource="db" columns="author_id,title"',
                                     extra='<q:param name="title" required="true" minlength="5"/>')
                              ).get('/p').get_data(as_text=True))
        assert re.findall(r'q-formitem-label">([^<]*)<', html) == ['Author', 'Title']
        assert 'minlength="5"' in field(html, 'title') and 'maxlength' not in field(html, 'title')

    def test_an_edit_opens_with_the_row_values(self, open_page):
        # UI-10
        before = ('<q:query name="post" datasource="db">SELECT * FROM posts WHERE id = 1</q:query>')
        html = form(open_page(p=page(form='<ui:form on-submit="create" values="{post}"/>', before=before)
                              ).get('/p').get_data(as_text=True))
        assert 'value="First"' in field(html, 'title') and 'value="7"' in field(html, 'score')
        assert '<option value="published" selected>' in html
        assert re.search(r'<option value="1" selected>\s*Bia', html)
        assert re.search(r'name="featured" checked', html)


class TestServer:
    def test_it_validates_by_the_schema_and_saves(self, open_page, db):
        # UI-10
        c = open_page(p=page())
        r = c.post('/p', data={'action': 'create', 'title': '', 'status': 'archived', 'author_id': '9'},
                   headers={'Referer': 'http://localhost/p'})
        assert r.status_code == 302
        errors = re.findall(r'q-field-error"[^>]*>\s*([^<]*?)\s*</span>', c.get('/p').get_data(as_text=True))
        assert errors == ['Required', 'Must be one of: draft, published',
                          'Must name an existing row of authors (no id = 9)']
        assert c.post('/p', data={'action': 'create', 'title': 'New', 'status': 'draft', 'author_id': '2',
                                  'featured': 'on', 'score': ''}).status_code == 302
        connection = sqlite3.connect(db)
        assert connection.execute("SELECT title, featured, author_id FROM posts WHERE title = 'New'").fetchone() == ('New', 1, 2)
        connection.close()

    def test_a_new_column_shows_without_a_restart(self, open_page, db):
        # UI-10: the schema is read again when the database file changes
        c = open_page(p=page())
        assert 'name="summary"' not in c.get('/p').get_data(as_text=True)
        connection = sqlite3.connect(db)
        connection.execute('ALTER TABLE posts ADD COLUMN summary TEXT')
        connection.commit()
        connection.close()
        import os
        import time
        os.utime(db, (time.time() + 5, time.time() + 5))
        assert 'name="summary"' in c.get('/p').get_data(as_text=True)

    def test_a_table_that_does_not_exist_is_an_error_that_lists_the_tables(self, open_page, caplog):
        # UI-10: and the log records it (before, a rendering 500 left no trace)
        import logging
        c = open_page(p=page(action_attrs='table="postz" datasource="db"'))
        with caplog.at_level(logging.ERROR, logger='quantum.server'):
            assert c.get('/p').status_code == 500
        assert any("table 'postz' does not exist in datasource 'db' (tables: authors, posts)" in r.getMessage()
                   for r in caplog.records)

    def test_table_without_datasource_is_a_parse_error(self):
        # UI-10
        from quantum.core.parser import QuantumParser
        with pytest.raises(Exception, match=r'table="posts"> needs datasource='):
            QuantumParser().parse(page(action_attrs='table="posts"'))

    def test_the_console_gets_the_generated_fields(self, open_page):
        # UI-10, UI-3
        tree = open_page(p=page()).get('/p', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()
        binds = []

        def walk(nodes):
            for node in nodes:
                if node.get('props', {}).get('bind'):
                    binds.append(node['props']['bind'])
                walk(node.get('children', []))
        walk(tree['view'])
        assert binds == ['title', 'status', 'featured', 'score', 'author_id']


def test_quantum_check_checks_the_action_table(tmp_path):
    # UI-10, DEV-3
    c = sqlite3.connect(tmp_path / 'app.db')
    c.executescript(SCHEMA)
    c.close()
    (tmp_path / 'components').mkdir()
    (tmp_path / 'components' / 'p.q').write_text(
        page(action_attrs='table="postz" datasource="db"').replace(INSERT, ''), encoding='utf-8')
    (tmp_path / 'components' / 'q.q').write_text(
        page(action_attrs='table="posts" datasource="db" columns="title,titel"').replace(INSERT, ''), encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text(
        'paths:\n  components: ./components\ndatasources:\n  db:\n    driver: sqlite\n    database: ./app.db\n',
        encoding='utf-8')
    from quantum.cli.check import ProjectChecker
    problems = [str(p) for p in ProjectChecker(tmp_path, tmp_path / 'quantum.config.yaml').run()]
    assert any('p.q' in p and 'table="postz">: no such table' in p for p in problems)
    assert any('q.q' in p and 'has no column "titel"' in p for p in problems)
