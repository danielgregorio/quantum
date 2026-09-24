"""
A real login in .q: find the user, check the password, open the session.

Authentication went into the Core (decision D4), and two defects prevented an
honest login written in the language:

1. There was no way to check a password against a hash without q:python.
   Every login example wrote session.authenticated=true for whoever sent the
   form. Now `hashPassword()` and `verifyPassword()` are part of the
   expressions' standard library (rule AUTH-3 of SPEC.md).

2. Every q:query inside a q:action failed. The ActionHandler created its own
   ComponentRuntime WITHOUT the server's config, so the datasources of
   quantum.config.yaml did not exist for it: "Datasource 'db' is not declared
   locally". A form that writes to the database did not work — and no test ran
   a q:query inside an action against the server.

Found while writing docs/guide/authentication.md and running the example.
"""

import re
import sqlite3

import pytest

from quantum.core.expression_stdlib import hash_password, verify_password
from quantum.runtime.web_server import QuantumWebServer

LOGIN = '''<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <q:action name="signin" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" required="true" />
    <q:query name="user" datasource="db">
      SELECT id, name, role, password_hash FROM users WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:if condition="user.length == 1 and verifyPassword(password, user[0].password_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userName" value="{user[0].name}" />
      <q:set name="session.userRole" value="{user[0].role}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/panel" />
    </q:if>
    <q:flash type="error" message="Invalid e-mail or password" />
    <q:redirect url="/login" />
  </q:action>
  <html><body><q:if condition="flash"><p>{flash}</p></q:if></body></html>
</q:component>'''

PANEL = ('<q:component name="panel" require_auth="true" require_role="admin" '
         'xmlns:q="https://quantum.lang/ns"><html><body><p>Hello, {session.userName}</p>'
         '</body></html></q:component>')


@pytest.fixture
def app(tmp_path):
    db = tmp_path / 'app.db'
    con = sqlite3.connect(db)
    con.execute('create table users (id integer primary key, email text unique, '
                'name text, role text, password_hash text)')
    con.execute('insert into users (email, name, role, password_hash) values (?,?,?,?)',
                ('ana@example.com', 'Ana', 'admin', hash_password('ana-s-password')))
    con.commit()
    con.close()

    components = tmp_path / 'components'
    components.mkdir()
    (components / 'login.q').write_text(LOGIN, encoding='utf-8')
    (components / 'panel.q').write_text(PANEL, encoding='utf-8')
    config = tmp_path / 'config.yaml'
    config.write_text(
        f"server:\n  debug: false\npaths:\n  components: {components.as_posix()}\n"
        "  static: ./static\n  logs: ./logs\n"
        "logging:\n  level: ERROR\n  console: false\n  file: false\n"
        f"datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n",
        encoding='utf-8')
    server = QuantumWebServer(str(config))
    server.app.config['TESTING'] = True
    return server.app


def text(response):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', response.get_data(as_text=True)))


class TestLogin:
    def test_the_right_password_opens_the_panel(self, app):
        client = app.test_client()
        r = client.post('/login', data={'email': 'ana@example.com', 'password': 'ana-s-password'})
        assert r.headers['Location'].endswith('/panel'), text(client.get('/login'))
        panel = client.get('/panel')
        assert panel.status_code == 200
        assert 'Hello, Ana' in text(panel)

    def test_a_wrong_password_does_not_open(self, app):
        client = app.test_client()
        r = client.post('/login', data={'email': 'ana@example.com', 'password': 'guess'})
        assert r.headers['Location'].endswith('/login')
        assert client.get('/panel').status_code == 302
        assert 'Invalid e-mail or password' in text(client.get('/login'))

    def test_a_missing_user_does_not_open(self, app):
        client = app.test_client()
        client.post('/login', data={'email': 'nobody@example.com', 'password': 'ana-s-password'})
        assert client.get('/panel').status_code == 302


class TestQueryInsideAnAction:
    def test_the_action_sees_the_config_datasource(self, app):
        # Defect 2's symptom: the message about an undeclared datasource.
        client = app.test_client()
        client.post('/login', data={'email': 'ana@example.com', 'password': 'guess'})
        assert 'is not declared locally' not in text(client.get('/login'))


class TestPasswordFunctions:
    def test_hash_and_verification(self):
        h = hash_password('secret')
        assert h != 'secret'
        assert verify_password('secret', h)
        assert not verify_password('other', h)

    @pytest.mark.parametrize('password,hash_', [
        ('', '$2b$12$abc'), ('secret', ''), ('secret', None),
        ('secret', 'this-is-not-a-hash'), (None, None),
    ])
    def test_bad_data_is_false_never_an_error(self, password, hash_):
        assert verify_password(password, hash_) is False

    def test_hashing_an_empty_password_is_refused(self):
        with pytest.raises(ValueError):
            hash_password('')
