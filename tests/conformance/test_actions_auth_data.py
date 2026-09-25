"""Conformance: SPEC.md sections 3 (Actions), 4 (Authentication) and 5 (Data)."""

import re
import sqlite3

import pytest

from quantum.core.expression_stdlib import hash_password, verify_password


def text_of(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


def text(response):
    return text_of(response.get_data(as_text=True))


TWO_ACTIONS = ('<q:component name="actions" xmlns:q="https://quantum.lang/ns">'
               '<q:action name="create" method="POST"><q:redirect url="/created"/></q:action>'
               '<q:action name="delete" method="POST"><q:redirect url="/deleted"/></q:action>'
               '<p>x</p></q:component>')

FORM = ('<q:component name="form" xmlns:q="https://quantum.lang/ns">'
        '<q:action name="save" method="POST">'
        '<q:param name="name" required="true" minlength="2"/>'
        '<q:param name="age" type="integer" min="18"/>'
        '<q:set name="session.seen" value="{name}|{age}"/>'
        '<q:redirect url="/form" flash="Saved {name}"/></q:action>'
        '<html><body><q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>'
        '<p>SEEN={session.seen}</p></body></html></q:component>')


class TestActions:
    def test_the_action_field_chooses(self, serve_pages):
        # ACT-1
        client = serve_pages(actions=TWO_ACTIONS)
        assert client.post('/actions', data={'action': 'delete'}).headers['Location'].endswith('/deleted')
        assert client.post('/actions', data={'action': 'create'}).headers['Location'].endswith('/created')

    def test_params_are_converted_and_validated(self, serve_pages):
        # ACT-2
        client = serve_pages(form=FORM)
        client.post('/form', data={'name': 'Ana', 'age': '30'})
        assert 'SEEN=Ana|30' in text(client.get('/form'))

    def test_a_failed_validation_does_not_run_and_comes_back_with_the_reason(self, serve_pages):
        # ACT-2
        client = serve_pages(form=FORM)
        r = client.post('/form', data={'name': 'A', 'age': '30'},
                        headers={'Referer': 'http://localhost/form'})
        assert r.status_code == 302
        html = client.get('/form').get_data(as_text=True)   # once: the flash is gone afterwards (ACT-3)
        assert 'at least 2 characters' in html
        assert 'class="error"' in html
        assert 'SEEN=A|' not in text_of(html)

    def test_the_flash_shows_once(self, serve_pages):
        # ACT-3
        client = serve_pages(form=FORM)
        client.post('/form', data={'name': 'Bia', 'age': '20'})
        assert 'Saved Bia' in text(client.get('/form'))
        assert 'Saved Bia' not in text(client.get('/form'))

    def test_flash_and_redirect_take_expressions(self, serve_pages):
        # ACT-3 (before: only a plain name; {r.msg} was a 500 "not found in any scope")
        client = serve_pages(ex=('<q:component name="ex" xmlns:q="https://quantum.lang/ns">'
                                 '<q:action name="a" method="POST">'
                                 '<q:set name="r" type="object" value=\'{"msg": "ok", "n": 3}\'/>'
                                 '<q:set name="items" type="array" value="[1, 2]"/>'
                                 '<q:flash type="error" message="{r.msg}: {len(items)} items"/>'
                                 '<q:redirect url="/ex?n={r.n + 1}"/></q:action>'
                                 '<p>[{flash}]</p></q:component>'))
        r = client.post('/ex', data={})
        assert r.status_code == 302 and r.headers['Location'].endswith('/ex?n=4')
        assert '[ok: 2 items]' in text(client.get('/ex'))

    def test_the_flash_exists_empty_without_a_message(self, serve_pages):
        # ACT-3: always defined, '' without a message
        client = serve_pages(v=('<q:component name="v" xmlns:q="https://quantum.lang/ns">'
                                '<p>[{flash}|{flashType}]</p><q:if condition="flash"><p>HAS</p></q:if></q:component>'))
        body = text(client.get('/v'))
        assert '[|]' in body and 'HAS' not in body

    def test_an_unknown_action_is_400_and_runs_no_other(self, serve_pages):
        # ACT-5 (was G6: it fell silently into the first action)
        client = serve_pages(actions=TWO_ACTIONS)
        r = client.post('/actions', data={'action': 'delet'})
        assert r.status_code == 400
        body = r.get_data(as_text=True)
        assert 'delet' in body and 'create' in body and 'delete' in body

    def test_a_missing_action_field_with_several_actions_is_400(self, serve_pages):
        # ACT-5
        assert serve_pages(actions=TWO_ACTIONS).post('/actions', data={}).status_code == 400

    def test_a_single_action_does_not_need_the_field(self, serve_pages):
        # ACT-5
        client = serve_pages(form=FORM)
        assert client.post('/form', data={'name': 'Caio', 'age': '40'}).status_code == 302

    def test_form_inside_the_action(self, serve_pages):
        # ACT-6 (was G7: {form.field} was empty inside the action)
        client = serve_pages(echo=('<q:component name="echo" xmlns:q="https://quantum.lang/ns">'
                                   '<q:action name="save" method="POST">'
                                   '<q:set name="session.seen" value="{form.name}"/>'
                                   '<q:redirect url="/echo"/></q:action>'
                                   '<p>SEEN={session.seen}</p></q:component>'))
        client.post('/echo', data={'name': 'ana'})
        assert 'SEEN=ana' in text(client.get('/echo'))

    def test_form_is_the_text_sent_and_the_param_is_the_typed_value(self, serve_pages):
        # ACT-6: form.age is '5' (text, so + joins); the q:param age is the integer 5
        client = serve_pages(f=('<q:component name="f" xmlns:q="https://quantum.lang/ns">'
                                '<q:action name="a" method="POST"><q:param name="age" type="integer"/>'
                                '<q:set name="session.t" value="{form.age + \'!\'}|{age + 1}"/>'
                                '<q:redirect url="/f"/></q:action><p>[{session.t}]</p></q:component>'))
        client.post('/f', data={'age': '5'})
        assert '[5!|6]' in text(client.get('/f'))

    def test_a_query_in_an_action_uses_the_configured_datasource(self, serve_pages, tmp_path):
        # ACT-4
        db = tmp_path / 'app.db'
        sqlite3.connect(db).execute('create table t (v text)').connection.commit()
        client = serve_pages(
            datasources_yaml=f"datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n",
            write=('<q:component name="write" xmlns:q="https://quantum.lang/ns">'
                   '<q:action name="w" method="POST"><q:param name="v" required="true"/>'
                   '<q:query name="ins" datasource="db">INSERT INTO t (v) VALUES (:v)'
                   '<q:param name="v" value="{v}" type="string"/></q:query>'
                   '<q:redirect url="/write"/></q:action><p>ok</p></q:component>'))
        assert client.post('/write', data={'v': 'written'}).status_code == 302
        assert sqlite3.connect(db).execute('select v from t').fetchall() == [('written',)]


PAGE = ('<q:component name="{name}" require_auth="true" {extra} '
        'xmlns:q="https://quantum.lang/ns"><p>INSIDE</p></q:component>')

SIGN_IN = ('<q:component name="signin" xmlns:q="https://quantum.lang/ns">'
           '<q:action name="e" method="POST"><q:param name="role" required="true"/>'
           '<q:param name="hours" type="integer" required="true"/>'
           '<q:set name="session.authenticated" value="true" type="boolean"/>'
           '<q:set name="session.userRole" value="{role}"/>'
           '<q:set name="session.sessionExpiry" value="{dateAdd(\'h\', hours)}"/>'
           '<q:redirect url="/signin"/></q:action><p>x</p></q:component>')


class TestAuthentication:
    def pages(self, serve_pages):
        return serve_pages(
            signin=SIGN_IN,
            open=PAGE.format(name='open', extra=''),
            admin=PAGE.format(name='admin', extra='require_role="admin"'),
            team=PAGE.format(name='team', extra='require_role="admin,editor"'))

    def test_without_a_session_it_redirects(self, serve_pages):
        # AUTH-1
        r = self.pages(serve_pages).get('/open')
        assert r.status_code == 302 and r.headers['Location'].endswith('/login')

    def test_a_valid_session_gets_in(self, serve_pages):
        # AUTH-1
        client = self.pages(serve_pages)
        client.post('/signin', data={'role': 'user', 'hours': '1'})
        assert 'INSIDE' in text(client.get('/open'))

    def test_an_expired_session_redirects_with_expired(self, serve_pages):
        # AUTH-1
        client = self.pages(serve_pages)
        client.post('/signin', data={'role': 'user', 'hours': '-1'})
        r = client.get('/open')
        assert r.status_code == 302 and 'expired=true' in r.headers['Location']

    def test_a_session_without_expiry_counts_as_expired(self, serve_pages):
        # AUTH-1
        client = serve_pages(
            signin=('<q:component name="signin" xmlns:q="https://quantum.lang/ns">'
                    '<q:action name="e" method="POST">'
                    '<q:set name="session.authenticated" value="true" type="boolean"/>'
                    '<q:redirect url="/signin"/></q:action><p>x</p></q:component>'),
            open=PAGE.format(name='open', extra=''))
        client.post('/signin', data={})
        r = client.get('/open')
        assert r.status_code == 302 and 'expired=true' in r.headers['Location']

    def test_a_wrong_role_is_403_and_a_list_is_accepted(self, serve_pages):
        # AUTH-2
        client = self.pages(serve_pages)
        client.post('/signin', data={'role': 'editor', 'hours': '1'})
        assert client.get('/admin').status_code == 403
        assert 'INSIDE' in text(client.get('/team'))

    def test_the_session_cookie_is_httponly_and_samesite_lax(self, serve_pages):
        # AUTH-5: without SameSite, another site could post a form (q:action) with the session
        client = self.pages(serve_pages)
        r = client.post('/signin', data={'role': 'user', 'hours': '1'})
        cookie = r.headers.get('Set-Cookie', '')
        assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie

    def test_login_url_is_configurable(self, serve_pages):
        # AUTH-4
        c = serve_pages(datasources_yaml="security:\n  login_url: /admin/login\n",
                        open=PAGE.format(name='open', extra=''))
        r = c.get('/open')
        assert r.status_code == 302 and r.headers['Location'].endswith('/admin/login')

    def test_login_url_per_component(self, serve_pages):
        # AUTH-4: a component can point to another login without changing the config
        c = serve_pages(admin=('<q:component name="admin" require_auth="true" login_url="/admin/login" '
                               'xmlns:q="https://quantum.lang/ns"><p>x</p></q:component>'),
                        open=PAGE.format(name='open', extra=''))
        assert c.get('/admin').headers['Location'].endswith('/admin/login')
        assert c.get('/open').headers['Location'].endswith('/login')

    def test_an_external_login_url_on_a_component_is_a_parse_error(self):
        # AUTH-4
        from quantum.core.parser import QuantumParser, QuantumParseError
        with pytest.raises(QuantumParseError, match='login_url'):
            QuantumParser().parse('<q:component name="x" require_auth="true" login_url="https://evil.example" '
                                  'xmlns:q="https://quantum.lang/ns"/>')

    @pytest.mark.parametrize('url', ['https://evil.example/login', '//evil.example/login', 'login'])
    def test_login_url_only_takes_a_local_path(self, serve_pages, url):
        # AUTH-4: a full URL would make every protected page an open redirect
        from quantum.runtime.web_server import ConfigError
        with pytest.raises(ConfigError, match='login_url'):
            serve_pages(datasources_yaml=f"security:\n  login_url: '{url}'\n",
                        open=PAGE.format(name='open', extra=''))

    @pytest.mark.parametrize('password,hash_', [('', 'x'), ('s', None), ('s', 'garbage')])
    def test_password_checking_fails_closed(self, password, hash_):
        # AUTH-3
        assert verify_password(password, hash_) is False

    def test_each_hash_has_its_own_salt(self):
        # AUTH-3
        a, b = hash_password('same'), hash_password('same')
        assert a != b and verify_password('same', a) and verify_password('same', b)


NS = 'xmlns:q="https://quantum.lang/ns"'
WRITE = ('<q:action name="write" method="POST"><q:query name="i" datasource="db">'
         "INSERT INTO t (v) VALUES ('ran')</q:query><q:redirect url=\"/done\"/></q:action>")
GUARD = '<q:if condition="not session.authenticated"><q:redirect url="/signin"/></q:if>'
LOG_IN = ('<q:component name="login" ' + NS + '><q:set name="session.authenticated" value="true" '
          'type="boolean"/><q:redirect url="/"/></q:component>')


@pytest.fixture
def with_db(serve_pages, tmp_path):
    db = tmp_path / 'g.db'
    sqlite3.connect(db).execute('create table t (v text)').connection.commit()

    def build(**components):
        client = serve_pages(datasources_yaml=f"datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n",
                             **components)
        return client, lambda: sqlite3.connect(db).execute('select count(*) from t').fetchone()[0]
    return build


class TestRedirectOnThePage:
    def test_a_redirect_on_the_page_ends_it_and_answers(self, serve_pages):
        # ACT-7 (before: silently ignored; the page rendered)
        c = serve_pages(old=(f'<q:component name="old" {NS}><q:redirect url="/new" flash="Moved {{1 + 1}}"/>'
                             '<p>NO</p></q:component>'),
                        new=(f'<q:component name="new" {NS}><p>[{{flash}}]</p></q:component>'))
        r = c.get('/old')
        assert r.status_code == 302 and r.headers['Location'].endswith('/new')
        assert '[Moved 2]' in text(c.get('/new'))

    def test_logout_clears_the_session_and_redirects(self, serve_pages):
        # ACT-7: what the page wrote to the session before the redirect stays
        c = serve_pages(login=LOG_IN,
                        logout=(f'<q:component name="logout" {NS}><q:set name="session.authenticated" value="false" '
                                'type="boolean"/><q:redirect url="/see"/></q:component>'),
                        see=(f'<q:component name="see" {NS}><p>[{{session.authenticated}}]</p></q:component>'))
        c.get('/login')
        assert '[True]' in text(c.get('/see'))
        assert c.get('/logout').status_code == 302
        assert '[False]' in text(c.get('/see'))

    def test_a_redirect_inside_a_loop_in_an_action(self, serve_pages):
        # ACT-7: through the q:loop the redirect arrives another way, and still ends the action
        c = serve_pages(p=(f'<q:component name="p" {NS}><q:action name="a" method="POST">'
                           '<q:loop type="range" var="i" from="1" to="3"><q:if condition="i == 2">'
                           '<q:redirect url="/two"/></q:if></q:loop><q:redirect url="/end"/></q:action>'
                           '<p>x</p></q:component>'))
        assert c.post('/p', data={}).headers['Location'].endswith('/two')


class TestGuards:
    def test_a_guard_protects_the_page_and_the_action(self, with_db):
        # AUTH-6 (before: GET 200, and the POST wrote without a session)
        c, rows = with_db(p=f'<q:component name="p" {NS}>{GUARD}{WRITE}<p>INSIDE</p></q:component>',
                          login=LOG_IN)
        assert c.get('/p').headers['Location'].endswith('/signin')
        assert c.post('/p', data={}).headers['Location'].endswith('/signin')
        assert rows() == 0
        c.get('/login')
        assert 'INSIDE' in text(c.get('/p'))
        assert c.post('/p', data={}).headers['Location'].endswith('/done')
        assert rows() == 1

    def test_a_guard_for_whoever_is_logged_in_does_not_block_the_action(self, with_db):
        # AUTH-6: the login page redirects whoever is logged in, and login still works
        c, rows = with_db(p=(f'<q:component name="p" {NS}><q:if condition="session.authenticated">'
                             f'<q:redirect url="/panel"/></q:if>{WRITE}<p>form</p></q:component>'))
        assert c.post('/p', data={}).headers['Location'].endswith('/done')
        assert rows() == 1

    def test_a_guard_that_reads_a_page_variable_is_an_error(self):
        # AUTH-6: in the action the variable would not exist, the condition would be false and the action would pass
        from quantum.core.parser import QuantumParser, QuantumParseError
        with pytest.raises(QuantumParseError, match=r'\{logged\} does not exist'):
            QuantumParser().parse(f'<q:component name="p" {NS}><q:set name="logged" value="{{session.ok}}"/>'
                                  '<q:if condition="not logged"><q:redirect url="/signin"/></q:if>'
                                  f'{WRITE}</q:component>')
        # without an action, the same guard applies to the GET only, where the variable exists
        QuantumParser().parse(f'<q:component name="p" {NS}><q:set name="logged" value="{{session.ok}}"/>'
                              '<q:if condition="not logged"><q:redirect url="/signin"/></q:if></q:component>')

    def test_a_guard_that_cannot_decide_fails_closed(self, with_db):
        # AUTH-6: session.user does not exist; as false, the guard would let the action through
        c, rows = with_db(p=(f'<q:component name="p" {NS}><q:if condition="not session.user.is_admin">'
                             f'<q:redirect url="/signin"/></q:if>{WRITE}<p>INSIDE</p></q:component>'))
        assert c.get('/p').status_code == 500
        assert c.post('/p', data={}).status_code == 500
        assert rows() == 0

    def test_an_if_in_a_loop_in_an_action_sees_the_loop_variable(self, serve_pages):
        # ACT-8 (before: the q:if read the runtime's context and did not see `i`)
        c = serve_pages(p=(f'<q:component name="p" {NS}><q:action name="a" method="POST">'
                           '<q:loop type="range" var="i" from="1" to="3"><q:if condition="i == 2">'
                           '<q:set name="session.saw" value="{i}"/></q:if></q:loop>'
                           '<q:redirect url="/p"/></q:action><p>[{session.saw}]</p></q:component>'))
        c.post('/p', data={})
        assert '[2]' in text(c.get('/p'))

    def test_an_action_does_not_see_a_page_variable_and_the_error_says_why(self, serve_pages):
        # ACT-9: the action does not run the page's statements
        import logging
        c = serve_pages(p=(f'<q:component name="p" {NS}><q:set name="post" type="object" value=\'{{"id": 7}}\'/>'
                           '<q:action name="a" method="POST"><q:set name="session.x" value="{post.id}"/>'
                           '<q:redirect url="/p"/></q:action><p>[{flash}]</p></q:component>'))
        logging.disable(logging.CRITICAL)
        try:
            assert c.post('/p', data={}).status_code == 500
        finally:
            logging.disable(logging.NOTSET)
        assert 'A q:action does not run the page' in text(c.get('/p'))

    @pytest.mark.parametrize('filename,mimetype,passes', [
        ('photo.png', 'image/png', True),
        ('photo.exe', 'image/png', False),     # the declared type comes from the browser; the name decides too
        ('note.pdf', 'application/pdf', True),
        ('note.txt', 'text/plain', False),
    ])
    def test_accept_restricts_the_upload(self, serve_pages, filename, mimetype, passes):
        # ACT-11 (before: accept= was accepted and never applied — any file passed)
        import io
        c = serve_pages(up=(f'<q:component name="up" {NS}><q:action name="a" method="POST">'
                            '<q:param name="doc" type="file" required="true" accept="image/*,.pdf"/>'
                            '<q:set name="session.ok" value="{doc.filename}"/><q:redirect url="/up"/></q:action>'
                            '<p>[{session.ok}|{flash}]</p></q:component>'))
        r = c.post('/up', data={'doc': (io.BytesIO(b'content'), filename, mimetype)},
                   content_type='multipart/form-data', headers={'Referer': 'http://localhost/up'})
        assert r.status_code == 302
        page = text(c.get('/up'))
        if passes:
            assert f'[{filename}|]' in page
        else:
            assert "accepts image/*,.pdf" in page and '[|' in page


class TestData:
    @pytest.fixture(autouse=True)
    def files(self, tmp_path, monkeypatch):
        (tmp_path / 'c.csv').write_text('id,name,extra\n1,Ana,x\n2,Bia,y\n', encoding='utf-8')
        (tmp_path / 'l.xml').write_text(
            '<ls><l id="1"><t>A</t><e s="X"/></l><l id="2"><t>B</t><e s="Y"/></l></ls>',
            encoding='utf-8')
        (tmp_path / 'p.json').write_text('[{"n": "a", "v": 3}, {"n": "b", "v": 1}, {"n": "c", "v": 2}]',
                                         encoding='utf-8')
        monkeypatch.chdir(tmp_path)

    def test_csv_declared_columns_typed_and_the_rest_text(self, run_body):
        # DATA-1
        r = run_body('<q:data name="c" source="c.csv" type="csv">'
                     '<q:column name="id" type="integer"/></q:data><q:return value="{c}"/>')
        assert r == [{'id': 1, 'name': 'Ana', 'extra': 'x'}, {'id': 2, 'name': 'Bia', 'extra': 'y'}]

    def test_xml_paths_and_types(self, run_body):
        # DATA-2
        r = run_body('<q:data name="l" source="l.xml" type="xml" xpath=".//l">'
                     '<q:field name="id" xpath="@id" type="integer"/>'
                     '<q:field name="t" xpath="t/text()"/><q:field name="s" xpath="e/@s"/>'
                     '<q:field name="t2" xpath="t"/></q:data><q:return value="{l}"/>')
        assert r == [{'id': 1, 't': 'A', 's': 'X', 't2': 'A'}, {'id': 2, 't': 'B', 's': 'Y', 't2': 'B'}]

    def test_a_missing_file_is_an_error_that_names_the_source(self, run_body):
        # DATA-4 (was G16: it returned None silently)
        with pytest.raises(Exception, match="q:data 'x' could not read 'missing.csv'.*onerror"):
            run_body('<q:data name="x" source="missing.csv" type="csv"/><q:return value="never"/>')

    def test_with_continue_the_failure_is_in_the_result(self, run_body):
        # DATA-4
        r = run_body('<q:data name="x" source="missing.csv" type="csv" onerror="continue"/>'
                     '<q:return value="{x_result}"/>')
        assert r['success'] is False and 'missing.csv' in r['error']['message']

    def test_transformations_in_order(self, run_body):
        # DATA-3
        r = run_body('<q:data name="p" source="p.json" type="json"><q:transform>'
                     '<q:compute field="d" expression="{v} * 10" type="integer"/>'
                     '<q:filter condition="v > 1"/><q:sort by="v" order="asc"/>'
                     '<q:limit value="1"/></q:transform></q:data><q:return value="{p}"/>')
        assert r == [{'n': 'c', 'v': 2, 'd': 20}]


# ------------------------------------------------------------------ ACT-2 (the rules of FN-1), ACT-3 (q:flash)

@pytest.mark.parametrize('param,value', [('<q:param name="n" enum="a,b"/>', 'c'),
                                         ('<q:param name="n" type="email"/>', 'x'),
                                         ('<q:param name="n" type="integer" range="1..10"/>', '50')])
def test_enum_email_and_range_on_an_action_param(serve_pages, param, value):
    # ACT-2, FN-1: range= let any value through on an action (it worked on functions)
    # ACT-2
    c = serve_pages(f=(f'<q:component name="f" {NS}><q:action name="a" method="POST">{param}'
                       '<q:set name="session.n" value="{n}"/><q:redirect url="/f"/></q:action>'
                       '<p>[{session.n}|{flashType}]</p></q:component>'))
    c.post('/f', data={'n': value}, headers={'Referer': 'http://localhost/f'})
    assert '[|error]' in text(c.get('/f'))


@pytest.mark.parametrize('value,shown', [('2026-09-20', '[2026-09-20|success]'),
                                         ('2026-02-30', '[|error]'),
                                         ('20/09/2026', '[|error]'),
                                         ('tomorrow', '[|error]')])
def test_a_date_param_is_checked_on_the_server(serve_pages, value, shown):
    # ACT-2: type="date" drew <input type="date"> and the server took any text
    c = serve_pages(f=(f'<q:component name="f" {NS}><q:action name="a" method="POST">'
                       '<q:param name="d" type="date"/>'
                       '<q:set name="session.d" value="{d}"/><q:redirect url="/f" flash="ok"/></q:action>'
                       '<p>[{session.d}|{flashType}]</p></q:component>'))
    c.post('/f', data={'d': value}, headers={'Referer': 'http://localhost/f'})
    assert shown in text(c.get('/f'))


def test_a_default_has_the_param_type(serve_pages):
    # ACT-2: the default was used as text, so an unchecked box with
    # default="false" read as true ("false" is a non-empty string)
    c = serve_pages(f=(f'<q:component name="f" {NS}><q:action name="a" method="POST">'
                       '<q:param name="box" type="boolean" default="false"/>'
                       '<q:param name="n" type="integer" default="2"/>'
                       '<q:set name="session.r" value="{\'yes\' if box else \'no\'} {n + 1}"/>'
                       '<q:redirect url="/f"/></q:action>'
                       '<p>[{session.r}]</p></q:component>'))
    c.post('/f', data={})
    assert '[no 3]' in text(c.get('/f'))


def test_q_flash_sets_a_flash_of_another_kind(serve_pages):
    # ACT-3
    c = serve_pages(f=(f'<q:component name="f" {NS}>'
                       '<q:action name="a" method="POST"><q:flash type="warning" message="Careful {1 + 1}"/>'
                       '<q:redirect url="/f"/></q:action>'
                       '<q:action name="b" method="POST"><q:flash>Plain</q:flash><q:redirect url="/f"/></q:action>'
                       '<q:action name="c" method="POST"><q:flash type="warning">first</q:flash>'
                       '<q:redirect url="/f" flash="second"/></q:action>'
                       '<p>[{flash}|{flashType}]</p></q:component>'))
    shown = {}
    for action in 'abc':
        c.post('/f', data={'action': action})
        shown[action] = re.findall(r'\[[^\]]*\]', text(c.get('/f')))
    assert shown == {'a': ['[Careful 2|warning]'], 'b': ['[Plain|info]'], 'c': ['[second|success]']}


# ------------------------------------------------------------------ DATA-1: reading the file

@pytest.mark.parametrize('content,attributes,expected', [
    ('n;v\n"a;b";1\n', 'delimiter=";"', [{'n': 'a;b', 'v': '1'}]),
    ("n,v\n'a,b',1\n", 'quote="\'"', [{'n': 'a,b', 'v': '1'}]),
    ('a,1\nb,2\n', 'header="false"', [{'0': 'a', '1': '1'}, {'0': 'b', '1': '2'}]),
])
def test_csv_options(run_body, tmp_path, monkeypatch, content, attributes, expected):
    # DATA-1
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'f.csv').write_text(content, encoding='utf-8')
    assert run_body(f'<q:data name="d" source="f.csv" {attributes}/><q:return value="{{d}}"/>') == expected


def test_json_is_a_type(run_body, tmp_path, monkeypatch):
    # DATA-1
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'f.json').write_text('[{"a": 1}]', encoding='utf-8')
    assert run_body('<q:data name="d" source="f.json" type="json"/><q:return value="{d}"/>') == [{'a': 1}]


@pytest.mark.parametrize('body', [
    '<q:flash type="error" message="x"/><p>x</p>',
    '<q:if condition="1"><q:flash message="x"/></q:if><p>x</p>',
    '<q:function name="f"><q:flash message="x"/><q:return value="1"/></q:function><p>x</p>',
])
def test_q_flash_outside_an_action_is_a_parse_error(body):
    # ACT-3 (before: skipped without a word — the flash never appeared)
    from quantum.core.parser import QuantumParser, QuantumParseError
    with pytest.raises(QuantumParseError, match=r'<q:flash> .* is outside a q:action'):
        QuantumParser(use_cache=False).parse(f'<q:component name="p" {NS}>{body}</q:component>')


def test_encoding_reads_the_file(run_body, tmp_path, monkeypatch):
    # DATA-1 (before: every file was read as UTF-8 and a Latin-1 file failed)
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'f.csv').write_bytes('name,city\nJoão,São Paulo\n'.encode('latin-1'))
    assert run_body('<q:data name="d" source="f.csv" encoding="latin-1"/><q:return value="{d}"/>') == \
        [{'name': 'João', 'city': 'São Paulo'}]


def test_skip_rows_skips_the_lines_before_the_header(run_body, tmp_path, monkeypatch):
    # DATA-1 (before: the first line became the header and data rows were dropped)
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'f.csv').write_text('Sales report\nexported 2026-09-24\nname,total\nAna,3\nBia,5\n',
                                    encoding='utf-8')
    assert run_body('<q:data name="d" source="f.csv" skip_rows="2"/><q:return value="{d}"/>') == \
        [{'name': 'Ana', 'total': '3'}, {'name': 'Bia', 'total': '5'}]
