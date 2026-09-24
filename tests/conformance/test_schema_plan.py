"""Conformance: declarative schema — `quantum migrate plan` (M6, SPEC DB-10)."""

import sqlite3

import pytest

from quantum.cli.schema_plan import make_plan, run_plan

V001 = """
CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')), old_notes TEXT);
CREATE TABLE drafts (id INTEGER PRIMARY KEY, body TEXT);
CREATE INDEX posts_title ON posts (title);
INSERT INTO posts (title, status, old_notes) VALUES ('First', 'published', 'x'), ('Second', 'draft', NULL);
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'migrations').mkdir()
    (tmp_path / 'migrations' / 'V001_start.sql').write_text(V001, encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text(
        'paths:\n  migrations: ./migrations\n'
        'datasources:\n  db:\n    driver: sqlite\n    database: ./app.db\n', encoding='utf-8')
    return tmp_path


def schema(project, sql):
    (project / 'schema.sql').write_text(sql, encoding='utf-8')


SAME = """
CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')), old_notes TEXT);
CREATE TABLE drafts (id INTEGER PRIMARY KEY, body TEXT);
CREATE INDEX posts_title ON posts (title);
"""


def steps(project):
    return [(s.kind, s.target, s.loses_data) for s in make_plan(project / 'schema.sql', project / 'migrations').steps]


def apply_all(project):
    """The real `quantum migrate up`, on a real SQLite file."""
    from quantum.cli.migrations import MigrationRunner
    return MigrationRunner(project).up()


def test_nothing_to_do_when_migrations_already_match(project, capsys):
    # DB-10
    schema(project, SAME)
    assert steps(project) == []
    assert run_plan(project, None, None, False, False) == 0
    assert 'Nothing to do' in capsys.readouterr().out


def test_a_nullable_column_is_added_in_place(project):
    # DB-10
    schema(project, SAME.replace('old_notes TEXT);', 'old_notes TEXT, summary TEXT);'))
    plan = make_plan(project / 'schema.sql', project / 'migrations')
    assert [(s.kind, s.target) for s in plan.steps] == [('add-column', 'posts.summary')]
    assert plan.up_sql == 'ALTER TABLE "posts" ADD COLUMN "summary" TEXT;'


def test_a_changed_check_rebuilds_and_keeps_the_rows(project):
    # DB-10
    schema(project, SAME.replace("('draft', 'published')", "('draft', 'published', 'archived')"))
    assert steps(project) == [('rebuild', 'posts', False), ('add-index', 'posts_title', False)]
    assert run_plan(project, None, 'archive_status', True, False) == 0
    assert [r['status'] for r in apply_all(project)] == ['applied', 'applied']
    conn = sqlite3.connect(project / 'app.db')
    try:
        assert conn.execute('SELECT title, status FROM posts ORDER BY id').fetchall() == \
            [('First', 'published'), ('Second', 'draft')]
        conn.execute("INSERT INTO posts (title, status) VALUES ('Third', 'archived')")      # the new CHECK
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'posts_title'").fetchone()
    finally:
        conn.close()
    assert steps(project) == []                                    # the migration reproduced schema.sql


def test_dropping_a_column_or_a_table_is_refused_without_the_flag(project, capsys):
    # DB-10
    schema(project, SAME.replace(', old_notes TEXT', '').replace('CREATE TABLE drafts (id INTEGER PRIMARY KEY, body TEXT);', ''))
    assert steps(project) == [('rebuild', 'posts', True), ('drop-table', 'drafts', True),
                              ('add-index', 'posts_title', False)]
    assert run_plan(project, None, 'cleanup', True, False) == 1
    assert 'loses data' in capsys.readouterr().out
    assert not list((project / 'migrations').glob('V002*'))
    assert run_plan(project, None, 'cleanup', True, True) == 0
    assert (project / 'migrations' / 'V002_cleanup.sql').exists()


def test_not_null_without_default_warns(project):
    # DB-10
    schema(project, SAME.replace('old_notes TEXT);', 'old_notes TEXT, slug TEXT NOT NULL);'))
    plan = make_plan(project / 'schema.sql', project / 'migrations')
    assert plan.steps[0].kind == 'rebuild' and 'NOT NULL' in plan.steps[0].warning


def test_the_rollback_undoes_the_plan(project):
    # DB-10
    schema(project, SAME + 'CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT);')
    assert run_plan(project, None, 'tags', True, False) == 0
    down = (project / 'migrations' / 'V002_tags.down.sql').read_text(encoding='utf-8')
    assert 'DROP TABLE "tags";' in down


def test_indexes_follow_the_schema(project):
    # DB-10
    schema(project, SAME.replace('CREATE INDEX posts_title ON posts (title);',
                                 'CREATE INDEX posts_status ON posts (status);'))
    assert steps(project) == [('drop-index', 'posts_title', False), ('add-index', 'posts_status', False)]


def test_writing_asks_first(project, capsys):
    # DB-10
    schema(project, SAME + 'CREATE TABLE tags (id INTEGER PRIMARY KEY);')
    assert run_plan(project, None, 'tags', False, False, ask=lambda _: 'n') == 1
    assert run_plan(project, None, 'tags', False, False, interactive=False) == 1
    assert 'Confirm with --yes' in capsys.readouterr().out
    assert not list((project / 'migrations').glob('V002*'))
    assert run_plan(project, None, 'tags', False, False, ask=lambda _: 'y') == 0


@pytest.mark.parametrize('content,message', [(None, 'schema.sql does not exist'),
                                             ('CREATE TABLE (oops;', 'schema.sql: near')])
def test_errors_say_what_is_wrong(project, capsys, content, message):
    # DB-10
    if content is not None:
        schema(project, content)
    assert run_plan(project, None, None, False, False) == 1
    assert message in capsys.readouterr().out
