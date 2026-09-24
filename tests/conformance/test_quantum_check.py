"""Conformance: `quantum check` and the schema reader (M8, SPEC DEV-3)."""

import sqlite3
import subprocess
import sys

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

SCHEMA = '''
CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE posts (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
  author_id INTEGER REFERENCES authors(id)
);
'''


def create_db(path):
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.close()                      # sqlite3's `with` does not close; on Windows the file stays locked


@pytest.fixture
def project(tmp_path):
    create_db(tmp_path / 'app.db')
    (tmp_path / 'components').mkdir()
    (tmp_path / 'quantum.config.yaml').write_text(
        'paths:\n  components: ./components\n'
        'datasources:\n  db:\n    driver: sqlite\n    database: ./app.db\n', encoding='utf-8')

    def with_pages(**pages):
        for name, source in pages.items():
            (tmp_path / 'components' / f'{name}.q').write_text(source, encoding='utf-8')
        from quantum.cli.check import ProjectChecker
        checker = ProjectChecker(tmp_path, tmp_path / 'quantum.config.yaml')
        return [str(p) for p in checker.run()], checker
    return with_pages


def page(body):
    return f'<q:component name="p" {NS}>\n{body}\n</q:component>\n'


def test_a_correct_project_passes(project):
    # DEV-3
    problems, checker = project(p=page(
        '<q:query name="posts" datasource="db">SELECT p.id, p.title, a.name AS author FROM posts p\n'
        '  JOIN authors a ON a.id = p.author_id WHERE p.status = :s<q:param name="s" value="published"/></q:query>\n'
        '<q:loop query="posts"><p>{posts.title} by {posts.author}</p></q:loop>\n'
        '<p>{posts_result.recordCount}</p>'))
    assert problems == [] and checker.queries_checked == 1


def test_sql_that_does_not_compile_says_file_line_and_the_database_error(project):
    # DEV-3
    problems, _ = project(p=page('<p>x</p>\n<q:query name="q" datasource="db">SELECT titel FROM posts</q:query>'))
    assert problems == ['components/p.q:3: <q:query name="q">: no such column: titel']


@pytest.mark.parametrize('use', [
    '<q:loop query="q"><p>{q.titel}</p></q:loop>',
    '<q:loop type="array" items="{q}" var="row"><p>{row.titel}</p></q:loop>',
    '<p>{q.titel}</p>',
    '<ui:window title="w"><ui:table source="{q}"><ui:column key="titel"/></ui:table></ui:window>',
    '<ui:window title="w"><ui:list source="{q}" as="it"><ui:item><ui:text>{it.titel}</ui:text></ui:item></ui:list></ui:window>',
])
def test_a_field_the_query_does_not_return(project, use):
    # DEV-3
    problems, _ = project(p=page(f'<q:query name="q" datasource="db">SELECT id, title FROM posts</q:query>\n{use}'))
    assert len(problems) == 1
    assert 'query "q" returns no column "titel" (columns: id, title)' in problems[0]
    assert problems[0].startswith('components/p.q:3')


def test_an_action_query_is_checked(project):
    # DEV-3
    problems, _ = project(p=page(
        '<q:action name="a" method="POST">\n'
        '  <q:query name="ins" datasource="db">INSERT INTO posts (titel) VALUES (:t)<q:param name="t" value="x"/></q:query>\n'
        '  <q:redirect url="/p"/></q:action>'))
    assert problems == ['components/p.q:3: <q:query name="ins">: table posts has no column named titel']


def test_an_undeclared_datasource_and_a_parse_error_too(project):
    # DEV-3
    problems, _ = project(
        a=page('<q:query name="q" datasource="other">SELECT 1</q:query>'),
        b=page('<q:sett name="x" value="1"/>'))
    assert "components/a.q:2: <q:query name=\"q\">: datasource 'other' is not declared" in problems[0]
    assert problems[1].startswith('components/b.q:2: <q:sett> is not a Quantum tag')


def test_nothing_is_written_to_the_database(project, tmp_path):
    # DEV-3: it compiles, it does not run
    project(p=page('<q:query name="d" datasource="db">DELETE FROM authors</q:query>'))
    c = sqlite3.connect(tmp_path / 'app.db')
    c.execute("INSERT INTO authors (name) VALUES ('Ana')")
    c.commit()
    c.close()
    project(p=page('<q:query name="d" datasource="db">DELETE FROM authors</q:query>'))
    c = sqlite3.connect(tmp_path / 'app.db')
    assert c.execute('SELECT count(*) FROM authors').fetchone() == (1,)
    c.close()


def test_a_missing_database_is_a_note_not_a_silent_ok(project, tmp_path):
    # DEV-3
    (tmp_path / 'app.db').unlink()
    problems, checker = project(p=page('<q:query name="q" datasource="db">SELECT 1</q:query>'))
    assert problems == [] and checker.queries_checked == 0
    assert any('quantum migrate up' in n for n in checker.notes)


def test_the_command_exits_with_1_and_lists_the_problems(project, tmp_path):
    # DEV-3
    project(p=page('<q:query name="q" datasource="db">SELECT titel FROM posts</q:query>'))
    import os
    from pathlib import Path
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[2])}
    r = subprocess.run([sys.executable, '-W', 'ignore', '-m', 'quantum.cli.runner', 'check'],
                       cwd=tmp_path, capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 1
    assert 'components/p.q:2: <q:query name="q">: no such column: titel' in r.stdout
    assert '1 problem(s)' in r.stdout


def test_the_schema_reader(tmp_path):
    # DEV-3: what M6 and M17 read — NOT NULL, default, CHECK … IN, foreign key
    from quantum.runtime.db_schema import connect_readonly, read_schema
    create_db(tmp_path / 'app.db')
    connection = connect_readonly({'driver': 'sqlite', 'database': 'app.db'}, tmp_path)
    schema = read_schema(connection)
    connection.close()
    posts = schema['posts'].columns
    assert posts['title'].not_null and not posts['author_id'].not_null
    assert posts['status'].options == ['draft', 'published'] and posts['status'].default == "'draft'"
    assert posts['author_id'].references == ('authors', 'id') and posts['id'].primary_key
