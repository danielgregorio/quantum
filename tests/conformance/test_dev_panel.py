"""Conformance: the /_dev panel (M12, SPEC DEV-1)."""

import sqlite3

import pytest

NS = 'xmlns:q="https://quantum.lang/ns"'

PAGE = (f'<q:component name="p" {NS}>'
        '<q:action name="save" method="POST"><q:param name="name" required="true"/>'
        '<q:set name="session.name" value="{name}"/>'
        '<q:redirect url="/p" flash="Saved: {name}"/></q:action>'
        '<q:set name="title" value="&lt;script&gt;x&lt;/script&gt;"/>'
        '<q:query name="people" datasource="db">SELECT id, name FROM people WHERE id &gt; :minimum'
        '<q:param name="minimum" value="0" type="integer"/></q:query>'
        '<p>{people_result.recordCount}</p></q:component>')


@pytest.fixture
def build(tmp_path):
    from quantum.runtime.web_server import QuantumWebServer
    db = tmp_path / 'db.sqlite'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT)')
        c.executemany('INSERT INTO people (name) VALUES (?)', [('Ana',), ('Bia',)])

    def create(debug, **components):
        folder = tmp_path / 'components'
        folder.mkdir(exist_ok=True)
        for name, source in components.items():
            (folder / f'{name}.q').write_text(source, encoding='utf-8')
        config = tmp_path / 'quantum.config.yaml'
        config.write_text(
            f"server:\n  debug: {'true' if debug else 'false'}\n  host: 127.0.0.1\n"
            f"paths:\n  components: {folder.as_posix()}\n"
            "logging:\n  level: ERROR\n  console: false\n  file: false\n"
            f"datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n",
            encoding='utf-8')
        server = QuantumWebServer(str(config))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return create


def test_it_shows_the_queries_and_variables_of_the_last_request(build):
    # DEV-1
    c = build(True, p=PAGE)
    assert c.get('/p').status_code == 200
    panel = c.get('/_dev').get_data(as_text=True)
    assert 'GET /p' in panel and 'p.q' in panel
    assert 'SELECT id, name FROM people WHERE id &gt; :minimum' in panel
    assert 'minimum=0' in panel and '<td>2</td>' in panel          # parameter and rows
    assert 'title' in panel and '&lt;script&gt;' in panel and '<script>x' not in panel


def test_it_shows_the_action_the_redirect_and_the_flash(build):
    # DEV-1
    c = build(True, p=PAGE)
    r = c.post('/p', data={'action': 'save', 'name': 'Carla'})
    assert r.status_code == 302
    panel = c.get('/_dev').get_data(as_text=True)
    assert 'POST /p' in panel and 'save' in panel
    assert '/p</td>' in panel and 'Saved: Carla' in panel
    assert '<h2>action (' in panel and 'Carla' in panel.split('<h2>action (')[1].split('<h2>')[0]
    assert '<h2>session (1)' in panel


def test_a_failing_query_shows_with_its_error(build):
    # DEV-1
    c = build(True, p=(f'<q:component name="p" {NS}><q:query name="x" datasource="db">'
                       'SELECT * FROM missing</q:query><p>x</p></q:component>'))
    c.get('/p')
    panel = c.get('/_dev').get_data(as_text=True)
    assert 'SELECT * FROM missing' in panel and 'no such table' in panel


def test_each_request_has_its_own_page(build):
    # DEV-1
    c = build(True, p=PAGE)
    c.get('/p')
    c.get('/p?x=1')
    assert 'GET /p?x=1' in c.get('/_dev/2').get_data(as_text=True)
    assert c.get('/_dev').get_data(as_text=True).count('<a href="/_dev/') == 2   # /_dev does not record itself


def test_without_debug_it_does_not_exist_and_nothing_is_recorded(build):
    # DEV-1
    c = build(False, p=PAGE)
    c.get('/p')
    assert c.get('/_dev').status_code == 404
    assert c.application.view_functions.get('dev_panel') is None


def test_it_only_answers_this_machine(build):
    # DEV-1: it shows sessions and parameters; from another address it does not exist
    c = build(True, p=PAGE)
    c.get('/p')
    assert c.get('/_dev', environ_base={'REMOTE_ADDR': '10.0.0.5'}).status_code == 404
    assert c.get('/_dev', environ_base={'REMOTE_ADDR': '127.0.0.1'}).status_code == 200
