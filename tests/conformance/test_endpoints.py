"""A component's API, q:endpoint (SPEC.md §3d, API-1 to API-6), and what it brought: EXPR-17 (a dictionary
written in an attribute), EXPR-18 (base64), INV-3 (a credential from the environment) and CFG-4 (behind a
proxy)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from quantum.core.parser import QuantumParseError, QuantumParser

NOTES = '''<q:component name="notes">
  <q:endpoint method="GET">
    <q:respond json="{ {'notes': [], 'asked': get(body, 'who', 'nobody')} }" />
  </q:endpoint>
  <q:endpoint method="POST" origins="https://game.example" limit="3/minute" maxsize="1kb">
    <q:param name="text" type="string" required="true" maxlength="20" />
    <q:param name="stars" type="integer" min="1" max="5" default="3" />
    <q:if condition="{text == 'quiet'}"><q:respond status="202" /></q:if>
    <q:if condition="{text == 'nothing'}"><q:set name="x" value="1" /><q:else>
      <q:respond status="201" json="{ {'saved': text, 'stars': stars, 'sent': body} }" />
    </q:else></q:if>
  </q:endpoint>
  <q:endpoint method="DELETE">
    <q:param name="id" type="integer" required="true" />
    <q:respond json="{ {'deleted': id} }" />
  </q:endpoint>
</q:component>'''


def answer(response):
    return response.status_code, (json.loads(response.get_data(as_text=True))
                                  if response.get_data() else None)


class TestTheApi:
    """API-1, API-2: each method its endpoint, its q:params from the JSON body, the answer JSON."""

    def test_a_post_answers_what_q_respond_says(self, serve_pages):
        client = serve_pages(notes=NOTES)
        status, data = answer(client.post('/notes', json={'text': 'hello', 'stars': 5}))
        assert status == 201 and data == {'saved': 'hello', 'stars': 5, 'sent': {'text': 'hello', 'stars': 5}}
        assert client.post('/notes', json={'text': 'hi'}).get_json()['stars'] == 3      # the default (ACT-2)

    def test_a_refusal_names_each_field(self, serve_pages):
        status, data = answer(serve_pages(notes=NOTES).post('/notes', json={'stars': 9}))
        assert status == 422 and data['error'] == 'invalid'
        assert data['fields'] == {'text': 'Required', 'stars': 'Must be at most 5 (got 9)'}

    def test_get_and_delete_read_the_query_string(self, serve_pages):
        client = serve_pages(notes=NOTES)
        assert answer(client.get('/notes?who=ana')) == (200, {'notes': [], 'asked': 'ana'})
        assert answer(client.delete('/notes?id=7')) == (200, {'deleted': 7})
        assert answer(client.delete('/notes?id=x'))[0] == 422

    def test_without_q_respond_204_and_with_no_json_no_body(self, serve_pages):
        client = serve_pages(notes=NOTES)
        response = client.post('/notes', json={'text': 'nothing'})
        assert response.status_code == 204 and response.get_data() == b''
        response = client.post('/notes', json={'text': 'quiet'})
        assert response.status_code == 202 and response.get_data() == b''

    def test_a_body_that_is_not_json_or_of_another_type(self, serve_pages):
        client = serve_pages(notes=NOTES)
        assert answer(client.post('/notes', data='{nope', content_type='application/json'))[0] == 400
        assert answer(client.post('/notes', data='[1, 2]', content_type='application/json'))[0] == 400
        assert answer(client.post('/notes', data='text', content_type='text/plain'))[0] == 415

    def test_a_method_without_an_endpoint_is_405_with_allow(self, serve_pages):
        response = serve_pages(notes=NOTES).put('/notes', json={})
        assert response.status_code == 405 and response.get_json()['allowed'] == ['DELETE', 'GET', 'POST']
        assert 'POST' in response.headers['Allow'] and 'HEAD' in response.headers['Allow']

    def test_head_answers_as_get(self, serve_pages):
        assert serve_pages(notes=NOTES).head('/notes').status_code == 200

    @pytest.mark.parametrize('source, says', [
        ('<q:component name="a"><q:endpoint method="POST"/><q:endpoint method="POST"/></q:component>',
         'one endpoint a method'),
        ('<q:component name="a"><q:endpoint method="POST"/><q:action name="x"/></q:component>',
         'has q:endpoint and q:action'),
        ('<q:component name="a"><q:if condition="{true}"><q:endpoint method="POST"/></q:if></q:component>',
         'is inside another tag'),
        ('<q:component name="a"><q:endpoint method="FETCH"/></q:component>', 'the method is one of'),
        ('<q:component name="a"><q:respond json="{1}"/></q:component>', 'is outside a q:endpoint'),
        ('<q:component name="a"><q:endpoint method="GET"><q:loop type="range" var="i" from="1" to="2">'
         '<q:respond json="{i}"/></q:loop></q:endpoint></q:component>', 'inside a tag that is not q:if'),
        ('<q:component name="a"><q:endpoint method="POST"><q:redirect url="/"/></q:endpoint></q:component>',
         'it neither redirects nor sets a flash'),
        ('<q:component name="a"><q:endpoint method="POST"><q:respond status="99"/></q:endpoint></q:component>',
         'an HTTP status'),
    ])
    def test_what_an_api_cannot_be_is_a_parse_error(self, source, says):
        with pytest.raises(QuantumParseError, match=says):
            QuantumParser(use_cache=False).parse(source)


class TestWhoMayCall:
    """API-3: the component's and the endpoint's roles and guards, the refusals in JSON."""

    SOURCE = '''<q:component name="cards">
      <q:endpoint method="POST" require_role="member"><q:respond json="{ {'ok': true} }" /></q:endpoint>
      <q:endpoint method="GET"><q:respond json="{ {'open': true} }" /></q:endpoint>
    </q:component>'''

    def test_401_and_403_in_json(self, serve_pages):
        client = serve_pages(cards=self.SOURCE)
        assert answer(client.get('/cards')) == (200, {'open': True})
        status, data = answer(client.post('/cards', json={}))
        assert status == 401 and data['error'] == 'unauthenticated'
        from quantum.runtime.auth_service import AuthService
        for role, expected in (('viewer', 403), ('member', 200)):
            with client.session_transaction() as s:
                s['quantum_session'] = AuthService.login({}, 1, 'ana', role)
            assert answer(client.post('/cards', json={}))[0] == expected

    def test_a_guard_that_redirects_is_403(self, serve_pages):
        source = '''<q:component name="private">
          <q:if condition="{not session.username}"><q:redirect url="/login" /></q:if>
          <q:endpoint method="GET"><q:respond json="{ {'secret': 1} }" /></q:endpoint>
        </q:component>'''
        status, data = answer(serve_pages(private=source).get('/private'))
        assert status == 403 and data['error'] == 'forbidden'


class TestOtherSites:
    """API-4: origins=, the preflight, and the answer a browser may read."""

    def test_another_site_is_refused_before_anything_runs(self, serve_pages):
        status, data = answer(serve_pages(notes=NOTES).post(
            '/notes', json={'text': 'x'}, headers={'Origin': 'https://evil.example'}))
        assert status == 403 and data['error'] == 'origin'

    def test_an_allowed_site_reads_the_answer(self, serve_pages):
        response = serve_pages(notes=NOTES).post('/notes', json={'text': 'from the game'},
                                                 headers={'Origin': 'https://game.example'})
        assert response.status_code == 201
        assert response.headers['Access-Control-Allow-Origin'] == 'https://game.example'
        assert 'Origin' in response.headers['Vary']
        assert 'Access-Control-Allow-Credentials' not in response.headers

    def test_the_preflight(self, serve_pages):
        client = serve_pages(notes=NOTES)
        asked = client.open('/notes', method='OPTIONS', headers={
            'Origin': 'https://game.example', 'Access-Control-Request-Method': 'POST'})
        assert asked.status_code == 204
        assert asked.headers['Access-Control-Allow-Origin'] == 'https://game.example'
        assert asked.headers['Access-Control-Allow-Methods'] == 'POST'       # GET and DELETE name no origins
        assert asked.headers['Access-Control-Allow-Headers'] == 'Content-Type'
        refused = client.open('/notes', method='OPTIONS', headers={
            'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'POST'})
        assert refused.status_code == 204 and 'Access-Control-Allow-Origin' not in refused.headers

    def test_without_an_origin_or_from_its_own_pages_it_goes_on(self, serve_pages):
        client = serve_pages(notes=NOTES)
        assert client.get('/notes').status_code == 200                                  # no Origin
        assert client.get('/notes', headers={'Origin': 'http://localhost'}).status_code == 200   # its own

    def test_any_site_with_a_star(self, serve_pages):
        source = '<q:component name="open"><q:endpoint method="GET" origins="*"><q:respond json="{1}" />' \
                 '</q:endpoint></q:component>'
        response = serve_pages(open=source).get('/open', headers={'Origin': 'https://any.example'})
        assert response.status_code == 200 and response.headers['Access-Control-Allow-Origin'] == 'https://any.example'

    @pytest.mark.parametrize('origins', ['example.com', 'https://example.com/path', 'ftp://x'])
    def test_an_origin_is_a_scheme_and_a_host(self, origins):
        with pytest.raises(QuantumParseError, match='a scheme and a host'):
            QuantumParser(use_cache=False).parse(
                f'<q:component name="a"><q:endpoint method="GET" origins="{origins}"/></q:component>')


class TestLimits:
    """API-5: limit= and maxsize=; CFG-4: behind a proxy, the caller's address."""

    def test_one_more_call_is_429_with_retry_after(self, serve_pages):
        client = serve_pages(notes=NOTES)
        for _ in range(3):
            assert client.post('/notes', json={'text': 'x'}).status_code == 201
        response = client.post('/notes', json={'text': 'x'})
        assert response.status_code == 429 and response.get_json()['error'] == 'rate_limited'
        assert 1 <= int(response.headers['Retry-After']) <= 60
        # another address is another count
        assert client.post('/notes', json={'text': 'x'}, environ_base={'REMOTE_ADDR': '10.0.0.9'}).status_code == 201

    def test_a_larger_body_is_413_before_it_is_read(self, serve_pages):
        status, data = answer(serve_pages(notes=NOTES).post('/notes', json={'text': 'x' * 2000}))
        assert status == 413 and data == {'error': 'too_large',
                                          'message': 'The body is larger than 1024 bytes.', 'max_bytes': 1024}

    @pytest.mark.parametrize('limit', ['ten', '10', '0/minute', '5/week'])
    def test_a_limit_is_so_many_per_unit(self, limit):
        with pytest.raises(QuantumParseError, match='so many calls per'):
            QuantumParser(use_cache=False).parse(
                f'<q:component name="a"><q:endpoint method="GET" limit="{limit}"/></q:component>')

    def test_behind_a_proxy_each_caller_is_counted(self, tmp_path):
        """CFG-4: with server.proxies the address is X-Forwarded-For's; without it the header is ignored."""
        from quantum.runtime.web_server import QuantumWebServer
        source = '<q:component name="hit"><q:endpoint method="POST" limit="1/hour"><q:respond json="{1}" />' \
                 '</q:endpoint></q:component>'

        def client(proxies):
            folder = tmp_path / f'p{proxies}' / 'components'
            folder.mkdir(parents=True)
            (folder / 'hit.q').write_text(source, encoding='utf-8')
            config = folder.parent / 'quantum.config.yaml'
            config.write_text(f'server:\n  debug: false\n  proxies: {proxies}\npaths:\n  components: '
                              f'{folder.as_posix()}\nlogging:\n  level: ERROR\n  console: false\n  file: false\n',
                              encoding='utf-8')
            server = QuantumWebServer(str(config))
            server.app.config['TESTING'] = True
            return server.app.test_client()

        behind = client(1)
        for player in ('1.1.1.1', '2.2.2.2'):          # two players through one proxy: one call each
            assert behind.post('/hit', json={}, headers={'X-Forwarded-For': player}).status_code == 200
        assert behind.post('/hit', json={}, headers={'X-Forwarded-For': '1.1.1.1'}).status_code == 429
        direct = client(0)                              # no proxy: a header a caller wrote counts for nothing
        assert direct.post('/hit', json={}, headers={'X-Forwarded-For': '1.1.1.1'}).status_code == 200
        assert direct.post('/hit', json={}, headers={'X-Forwarded-For': '2.2.2.2'}).status_code == 429


class TestFailures:
    """API-6: a failure is JSON, its message only with server.debug."""

    def test_a_failure_is_500_in_json(self, serve_pages):
        source = '<q:component name="bad"><q:endpoint method="GET"><q:set name="x" value="{nothing.here}" />' \
                 '</q:endpoint></q:component>'
        status, data = answer(serve_pages(bad=source).get('/bad'))
        assert status == 500 and data['error'] == 'server' and 'nothing' not in data['message']


class TestADictionaryInAnAttribute:
    """EXPR-17: an attribute that is one expression may hold braces of its own."""

    def test_the_dictionary_not_the_text(self):
        from quantum.runtime.component import ComponentRuntime
        runtime = ComponentRuntime()
        assert runtime._apply_databinding("{ {'a': x, 'b': [x, 1]} }", {'x': 5}) == {'a': 5, 'b': [5, 1]}
        assert runtime._apply_databinding('{ {"s": "}"} }', {}) == {'s': '}'}
        assert runtime._apply_databinding('{a} {b}', {'a': 1, 'b': 2}) == '1 2'          # still two
        assert runtime._apply_databinding('{a}{b}', {'a': 1, 'b': 2}) == '12'


class TestBase64:
    """EXPR-18: base64(v), of the text's UTF-8."""

    def test_a_text_and_its_accents(self):
        from quantum.runtime.component import ComponentRuntime
        runtime = ComponentRuntime()
        assert runtime._apply_databinding('{base64(x)}', {'x': 'Onça 2º'}) == 'T27Dp2EgMsK6'
        assert runtime._apply_databinding("{base64('')}", {}) == ''


class _Hook(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        _Hook.seen.append(self.headers.get('Authorization'))
        self.rfile.read(int(self.headers.get('Content-Length') or 0))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *args):
        pass


class TestACredentialFromTheEnvironment:
    """INV-3: ${NAME} in authToken is the environment's NAME, read when the call is made."""

    def test_the_token_is_sent_and_a_missing_one_is_an_error(self, serve_pages, monkeypatch):
        hook = HTTPServer(('127.0.0.1', 0), _Hook)
        threading.Thread(target=hook.serve_forever, daemon=True).start()
        try:
            source = f'''<q:component name="tell">
              <q:endpoint method="POST">
                <q:invoke name="told" url="http://127.0.0.1:{hook.server_port}/hook" method="POST"
                          authType="bearer" authToken="${{QUANTUM_TEST_TOKEN}}"><q:body>{{}}</q:body></q:invoke>
                <q:respond json="{{ {{'told': told.ok}} }}" />
              </q:endpoint>
            </q:component>'''
            client = serve_pages(tell=source)
            monkeypatch.setenv('QUANTUM_TEST_TOKEN', 's3cret')
            assert answer(client.post('/tell', json={})) == (200, {'told': True})
            assert _Hook.seen[-1] == 'Bearer s3cret'
            monkeypatch.delenv('QUANTUM_TEST_TOKEN')
            status, data = answer(client.post('/tell', json={}))
            assert status == 500 and len(_Hook.seen) == 1          # no call made with an empty token
            # with onerror="continue" the call failed, says why, and the endpoint goes on (INV-2)
            later = source.replace('authToken="${QUANTUM_TEST_TOKEN}"',
                                   'authToken="${QUANTUM_TEST_TOKEN}" onerror="continue"').replace(
                "json=\"{ {'told': told.ok} }\"", "json=\"{ {'told': told_result.success, "
                                                   "'why': told_result.error.message} }\"")
            assert 'onerror="continue"' in later and 'told_result' in later
            status, data = answer(serve_pages(later=later.replace('name="tell"', 'name="later"')).post(
                '/later', json={}))
            assert status == 200 and data == {'told': False, 'why': 'the environment variable QUANTUM_TEST_TOKEN '
                                                                    'is not set (INV-3)'}
            assert len(_Hook.seen) == 1
        finally:
            hook.shutdown()
