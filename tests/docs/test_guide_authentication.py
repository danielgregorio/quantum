"""docs/guide/authentication.md: the login it shows works as the page says.

The page's blocks are served as an app over a users table: the protected
dashboard, the guard, the login page, account creation and logout. Every row
of the page's visitor table is checked, and the claims under the login (one
message for a wrong password and an unknown e-mail, the hash stored instead of
the password).
"""

import re
import sqlite3
from pathlib import Path

import pytest

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'authentication.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3
NS = 'xmlns:q="https://quantum.lang/ns"'


def block_after(marker):
    start = TEXT.index(marker)
    return re.search(F + r'xml\n(.*?)' + F, TEXT[start:], re.S).group(1)


def page_of(action_block, name):
    return f'<q:component name="{name}" {NS}>{action_block}</q:component>'


@pytest.fixture
def client(serve_pages, tmp_path):
    from quantum.core.expression_stdlib import hash_password
    db = tmp_path / 'users.db'
    c = sqlite3.connect(db)
    c.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, '
              'role TEXT, password_hash TEXT)')
    c.execute('INSERT INTO users (email, name, role, password_hash) VALUES (?, ?, ?, ?), (?, ?, ?, ?)',
              ('ana@example.com', 'Ana', 'admin', hash_password('correct horse'),
               'bruno@example.com', 'Bruno', 'user', hash_password('battery staple')))
    c.commit()
    c.close()
    return serve_pages(
        datasources_yaml=f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n',
        dashboard=block_after('## Protecting a page'),
        welcome=block_after('### Guards'),
        login=block_after('Save as `components/login.q`'),
        signup=page_of(block_after('## Creating an account'), 'signup'),
        logout=page_of(block_after('## Logging out'), 'logout'))


def sign_in(client, email, password):
    return client.post('/login', data={'email': email, 'password': password})


def flash_after(client, response):
    return client.get(response.headers['Location']).get_data(as_text=True)


def test_a_visitor_who_is_not_logged_in_is_sent_to_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302 and response.headers['Location'].endswith('/login')


def test_the_admin_gets_the_page(client):
    response = sign_in(client, 'ana@example.com', 'correct horse')
    assert response.headers['Location'].endswith('/dashboard')
    assert 'Hello, Ana' in client.get('/dashboard').get_data(as_text=True)


def test_a_user_without_the_role_gets_403(client):
    sign_in(client, 'bruno@example.com', 'battery staple')
    assert client.get('/dashboard').status_code == 403


def test_an_expired_session_is_sent_to_login_with_expired(client):
    sign_in(client, 'ana@example.com', 'correct horse')
    with client.session_transaction() as session:
        scope = dict(session['quantum_session'])
        scope['sessionExpiry'] = '2000-01-01T00:00:00'      # eight hours have passed
        session['quantum_session'] = scope
    response = client.get('/dashboard')
    assert response.status_code == 302 and response.headers['Location'].endswith('/login?expired=true')


def test_a_wrong_password_and_an_unknown_email_get_the_same_message(client):
    wrong = flash_after(client, sign_in(client, 'ana@example.com', 'wrong password'))
    unknown = flash_after(client, sign_in(client, 'nobody@example.com', 'whatever'))
    assert 'Invalid e-mail or password' in wrong and 'Invalid e-mail or password' in unknown
    assert client.get('/dashboard').status_code == 302


def test_the_guard_sends_a_logged_in_user_to_the_dashboard(client):
    assert 'Please sign in.' in client.get('/welcome').get_data(as_text=True)
    sign_in(client, 'ana@example.com', 'correct horse')
    response = client.get('/welcome')
    assert response.status_code == 302 and response.headers['Location'].endswith('/dashboard')


def test_an_account_stores_the_hash_and_can_sign_in(client, tmp_path):
    client.post('/signup', data={'email': 'carla@example.com', 'name': 'Carla', 'password': 'long enough pw'})
    stored = sqlite3.connect(tmp_path / 'users.db').execute(
        "SELECT password_hash FROM users WHERE email = 'carla@example.com'").fetchone()[0]
    assert stored != 'long enough pw' and stored.startswith('$2')           # bcrypt
    assert sign_in(client, 'carla@example.com', 'long enough pw').headers['Location'].endswith('/dashboard')


def test_logging_out_ends_the_session(client):
    sign_in(client, 'ana@example.com', 'correct horse')
    client.post('/logout')
    assert client.get('/dashboard').status_code == 302
