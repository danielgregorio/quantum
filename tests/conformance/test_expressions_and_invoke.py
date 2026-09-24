"""Conformance: SPEC.md sections 6 (Expressions) and 7 (Invocation)."""

import http.server
import json
import logging
import re
import threading
import urllib.parse

import pytest

from quantum.core import expression_diagnostics
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.renderer import HTMLRenderer


@pytest.fixture(autouse=True)
def clean_diagnostics():
    expression_diagnostics.reset()
    yield
    expression_diagnostics.reset()


class TestExpressions:
    def test_an_unknown_name_in_an_attribute_is_an_error_that_names_it(self, run_body):
        # EXPR-1 (was G12: returned 'x{nothing}y' silently)
        with pytest.raises(Exception, match="nothing"):
            run_body('<q:return value="x{nothing}y"/>')

    def test_an_unknown_name_suggests_the_similar_one(self, run_body):
        # EXPR-1
        with pytest.raises(Exception, match="did you mean 'total'"):
            run_body('<q:set name="total" value="3" type="number"/>'
                     '<q:set name="r" value="{totl + 1}"/>')

    def test_an_evaluation_error_is_an_error(self, run_body):
        # EXPR-2 (was G14: {10 / z} came back with raw braces)
        with pytest.raises(Exception, match="division by zero"):
            run_body('<q:set name="z" value="0" type="number"/>'
                     '<q:return value="{10 / z}"/>')

    def test_a_missing_scope_reference_is_empty(self, run_body):
        # EXPR-3
        assert run_body('<q:return value="[{session.name}]"/>') == '[]'

    def test_arithmetic_on_a_missing_scope_value_is_an_error_with_a_hint(self, run_body):
        # EXPR-3 (was G15: '' and then "could not convert string to float")
        with pytest.raises(Exception) as error:
            run_body('<q:set name="session.visits" value="{session.visits + 1}" type="number"/>')
        message = str(error.value)
        assert 'session.visits + 1' in message and 'is not set' in message
        assert 'operation="increment"' in message
        assert 'float' not in message

    def test_a_session_counter_with_increment(self, run_body):
        # EXPR-3: the way the message points to works on the first visit
        assert run_body('<q:set name="session.visits" operation="increment"/>'
                        '<q:return value="{session.visits}"/>') == 1

    def test_html_content_stays_literal_and_is_logged_once(self, caplog):
        # EXPR-4
        renderer = HTMLRenderer(ExecutionContext())
        with caplog.at_level(logging.WARNING, logger='quantum.databinding'):
            for _ in range(50):
                assert renderer._apply_databinding('A={nothing}') == 'A={nothing}'
        assert len(caplog.records) == 1 and 'nothing' in caplog.text

    def test_a_served_page_with_code_in_its_content(self, serve_pages):
        # EXPR-4: code braces in the content do not break the page
        client = serve_pages(p='<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                               '<p>function f() { return 1; }</p></q:component>')
        r = client.get('/p')
        assert r.status_code == 200 and 'function f() { return 1; }' in r.get_data(as_text=True)

    @pytest.mark.parametrize('value', ['[{"a": 1}, {"b": 2}]', r'\d{10,11}'])
    def test_json_and_a_quantifier_are_not_expressions(self, run_body, value):
        # EXPR-4
        assert run_body(f"<q:return value='{value}'/>") == value

    @pytest.mark.parametrize('condition', ['flash', 'session.user.is_admin', 'user.admin', 'items[3]'])
    def test_a_condition_with_a_missing_name_is_false(self, run_body, condition):
        # EXPR-5: <q:if condition="flash"> before flash exists
        assert run_body('<q:set name="user" type="object" value=\'{"name": "a"}\'/>'
                        '<q:set name="items" type="array" value="[1]"/>'
                        f'<q:if condition="{condition}"><q:return value="yes"/></q:if>'
                        '<q:return value="no"/>') == 'no'

    @pytest.mark.parametrize('condition,expected', [
        ('not session.authenticated', 'yes'), ('!session.authenticated', 'yes'),
        ("session.role == 'admin'", 'no'), ('session.role', 'no'),
        ('not query.page', 'yes'),
    ])
    def test_a_missing_scope_key_is_none_in_a_condition(self, run_body, condition, expected):
        # EXPR-8 (before: `not session.authenticated` was FALSE without a session, and the guard never fired)
        assert run_body(f'<q:if condition="{condition}"><q:return value="yes"/></q:if>'
                        '<q:return value="no"/>') == expected

    @pytest.mark.parametrize('condition,expected', [
        ('age >= 18 && ok', 'yes'), ('age < 18 || ok', 'yes'),
        ('!ok || age > 30', 'no'), ("name != 'x' && !(age == 3)", 'yes'),
        # inside a string nothing is translated: translated, it would be ' and ' in 'x&&y', false
        ("'&&' in 'x&&y'", 'yes')])
    def test_javascript_style_operators(self, run_body, condition, expected):
        # EXPR-6 (before: && and || did not parse and the condition was always false)
        assert run_body('<q:set name="age" value="20" type="number"/>'
                        '<q:set name="ok" value="true" type="boolean"/>'
                        '<q:set name="name" value="ana"/>'
                        f'<q:if condition="{condition}"><q:return value="yes"/></q:if>'
                        '<q:return value="no"/>') == expected

    @pytest.mark.parametrize('expression,expected', [
        ("{ok and items[5]}", 'False'), ("{name or items[5]}", 'ana'),
        ("{ok && nothing.field}", 'False'), ("{len(items) > 0 and items[0]}", 'False')])
    def test_and_and_or_stop_at_the_deciding_value(self, run_body, expression, expected):
        # EXPR-6 (before: both sides were evaluated — `a and a.b` failed without `a`)
        assert str(run_body('<q:set name="ok" value="false" type="boolean"/>'
                            '<q:set name="name" value="ana"/>'
                            '<q:set name="items" type="array" value="[]"/>'
                            f'<q:return value="{expression}"/>')) == expected

    @pytest.mark.parametrize('condition', ['age === 18', 'older(age)'])
    def test_a_condition_with_another_error_is_an_error(self, run_body, condition):
        # EXPR-5: only absence becomes false; syntax or a missing function is an error
        with pytest.raises(Exception, match='could not be evaluated'):
            run_body('<q:set name="age" value="20" type="number"/>'
                     f'<q:if condition="{condition}"><q:return value="yes"/></q:if>')


class TestArithmetic:
    @pytest.mark.parametrize('expression', ["{'-' * 40}", "{name * 2}", "{name - 1}", "{'%s' % name}"])
    def test_an_arithmetic_operator_on_text_is_an_error(self, run_body, expression):
        # EXPR-7 (before: '-' * 40 repeated, '%s' % x formatted)
        with pytest.raises(Exception, match='needs two numbers'):
            run_body(f'<q:set name="name" value="ana"/><q:return value="{expression}"/>')

    @pytest.mark.parametrize('expression,expected', [
        ("{'ab' + 'cd'}", 'abcd'), ('{n + 1}', 42), ('{t * 2}', 84), ('{7 // 2}', 3)])
    def test_what_still_works(self, run_body, expression, expected):
        # EXPR-7
        assert run_body('<q:set name="n" value="41" type="number"/><q:set name="t" value="42"/>'
                        f'<q:return value="{expression}"/>') == expected

    def test_a_value_of_digits_only_is_a_number(self, run_body):
        # EXPR-7 (before: {1} came back as the text '{1}', and n * '{1}' repeated)
        assert run_body('<q:function name="fact"><q:param name="n" type="number"/>'
                        '<q:if condition="n <= 1"><q:return value="{1}"/></q:if>'
                        '<q:return value="{n * fact(n - 1)}"/></q:function>'
                        '<q:return value="{fact(5)}"/>') == 120

    def test_a_quantifier_inside_text_stays(self, run_body):
        # EXPR-7 / EXPR-4
        assert run_body('<q:return value="[0-9]{3}"/>') == '[0-9]{3}'


class TestSlices:
    @pytest.mark.parametrize('expression,expected', [
        ('{xs[1:]}', [2, 3]), ('{xs[:-1]}', [1, 2]), ('{xs[-1]}', 3), ("{'quantum'[0:3]}", 'qua')])
    def test_a_slice_without_a_step(self, run_body, expression, expected):
        # EXPR-13
        assert run_body(f'<q:set name="xs" value="{{[1, 2, 3]}}" type="array"/>'
                        f'<q:return value="{expression}"/>') == expected

    @pytest.mark.parametrize('expression', ['{xs[::-1]}', '{xs[0:3:2]}'])
    def test_a_slice_with_a_step_is_an_error(self, run_body, expression):
        # EXPR-13 (before: [1, 2, 3][::-1] silently returned [1, 2, 3])
        with pytest.raises(Exception, match='slice with a step'):
            run_body(f'<q:set name="xs" value="{{[1, 2, 3]}}" type="array"/>'
                     f'<q:return value="{expression}"/>')


class TestMissingKeys:
    def test_a_missing_key_by_index_is_the_same_error_as_by_attribute(self):
        # EXPR-16 (was G19: d['missing'] was null while d.missing was an error)
        from quantum.core.expressions import ExpressionEvaluator, ExpressionError
        ev = ExpressionEvaluator()
        for expression in ("d['missing']", 'd.missing'):
            with pytest.raises(ExpressionError, match="'missing' not found"):
                ev.evaluate(expression, {'d': {}})

    def test_the_error_suggests_the_similar_key(self, run_body):
        # EXPR-16
        with pytest.raises(Exception, match="did you mean 'name'"):
            run_body('<q:set name="u" value=\'{"name": "Ana"}\' type="json"/>'
                     '<q:return value="{u[\'naem\']}"/>')

    @pytest.mark.parametrize('expression,expected', [
        ("get(d, 'k')", 1), ("get(d, 'x')", None), ("get(d, 'x', 'none')", 'none'),
        ("get(xs, 1)", 20), ("get(xs, 5, 0)", 0), ("get(xs, -1)", 30), ("get(nothing, 'k', 7)", 7),
        ("d['k']", 1), ("'x' in d", False)])
    def test_an_optional_key_is_read_with_get(self, expression, expected):
        # EXPR-16
        from quantum.core.expressions import ExpressionEvaluator
        context = {'d': {'k': 1}, 'xs': [10, 20, 30], 'nothing': None}
        assert ExpressionEvaluator().evaluate(expression, context) == expected


class TestMembershipAndChance:
    @pytest.mark.parametrize('expression,context,expected', [
        ("'5' in xs", {'xs': [5]}, True), ("5 in xs", {'xs': ['5']}, True),
        ("'2.0' in xs", {'xs': [2]}, True), ("'x' in xs", {'xs': [1, 2]}, False),
        ("'k' in d", {'d': {'k': 1}}, True), ("'a' in t", {'t': 'cat'}, True),
        ("3 not in xs", {'xs': [1, 2]}, True), ("'1' not in xs", {'xs': [1]}, False)])
    def test_in_compares_like_equals(self, expression, context, expected):
        # EXPR-14 (before: '5' in [5] was false while '5' == 5 was true)
        from quantum.core.expressions import ExpressionEvaluator
        assert ExpressionEvaluator().evaluate(expression, context) is expected

    def test_in_needs_a_container(self):
        # EXPR-14
        from quantum.core.expressions import ExpressionEvaluator, ExpressionError
        with pytest.raises(ExpressionError):
            ExpressionEvaluator().evaluate('1 in n', {'n': 5})

    def test_the_chance_functions(self):
        # EXPR-15
        from quantum.core.expressions import ExpressionEvaluator
        ev = ExpressionEvaluator()
        assert all(1 <= ev.evaluate('random(1, 6)', {}) <= 6 for _ in range(200))
        assert {ev.evaluate('random(1, 2)', {}) for _ in range(200)} == {1, 2}
        assert all(0 <= ev.evaluate('random()', {}) < 1 for _ in range(200))
        assert ev.evaluate('chance(1)', {}) is True and ev.evaluate('chance(0)', {}) is False
        assert ev.evaluate('pick(xs)', {'xs': ['only']}) == 'only'

    @pytest.mark.parametrize('expression', ['random(6, 1)', 'chance(2)', 'pick(xs)', 'random(1)'])
    def test_what_the_chance_functions_refuse(self, expression):
        # EXPR-15
        from quantum.core.expressions import ExpressionEvaluator
        with pytest.raises(Exception):
            ExpressionEvaluator().evaluate(expression, {'xs': []})


class _Api(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == '/fail':
            self.send_response(503)
            self.end_headers()
            return
        if url.path == '/html':
            body = b'<html><body>Maintenance</body></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = json.dumps({'name': 'Ana', 'query': dict(urllib.parse.parse_qsl(url.query))}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = json.dumps({'method': self.command}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_PUT = do_DELETE = do_POST

    def log_message(self, *args):
        pass


@pytest.fixture
def api():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Api)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_address[1]}'
    server.shutdown()
    server.server_close()


class TestInvocation:
    def test_a_url_without_a_declared_timeout_runs(self, run_body, api):
        # INV-1 (never worked: a missing timeout became None / 1000)
        assert run_body(f'<q:invoke name="u" url="{api}/u"/>'
                        '<q:return value="{u.name}"/>') == 'Ana'

    def test_a_param_becomes_the_query_string(self, run_body, api):
        # INV-1
        assert run_body(f'<q:invoke name="u" url="{api}/u"><q:param name="q" value="x y"/></q:invoke>'
                        '<q:return value="{u.query.q}"/>') == 'x y'

    @pytest.mark.parametrize('method', ['POST', 'PUT', 'DELETE'])
    def test_the_declared_method(self, run_body, api, method):
        # INV-1: GET when not declared (the tests above)
        assert run_body(f'<q:invoke name="u" url="{api}/u" method="{method}"/>'
                        '<q:return value="{u.method}"/>') == method

    def test_an_http_failure_is_an_error(self, run_body, api):
        # INV-2
        with pytest.raises(Exception, match='q:invoke .u. failed: HTTP 503.*onerror="continue"'):
            run_body(f'<q:invoke name="u" url="{api}/fail"/><q:return value="never"/>')

    def test_an_http_failure_with_continue_is_in_name_result(self, run_body, api):
        # INV-2
        r = run_body(f'<q:invoke name="u" url="{api}/fail" onerror="continue"/>'
                     '<q:return value="{u_result}"/>')
        assert r['success'] is False and '503' in r['error']['message']

    def test_an_invalid_onerror_is_a_parse_error(self, run_body, api):
        # INV-2
        with pytest.raises(Exception, match='onerror must be'):
            run_body(f'<q:invoke name="u" url="{api}/u" onerror="ignore"/>')

    def test_json_that_is_not_json_is_a_failure(self, run_body, api):
        # INV-2: it used to succeed with {"error": ..., "text": ...} as the value
        with pytest.raises(Exception, match=r'q:invoke .u. failed: responseFormat="json", but the response is '
                                            r'not JSON \(Content-Type: text/html\)'):
            run_body(f'<q:invoke name="u" url="{api}/html" responseFormat="json"/><q:return value="never"/>')

    def test_json_that_is_not_json_with_continue(self, run_body, api):
        # INV-2
        r = run_body(f'<q:invoke name="u" url="{api}/html" responseFormat="json" onerror="continue"/>'
                     '<q:return value="{u_result}"/>')
        assert r['success'] is False and 'not JSON' in r['error']['message'] and 'Maintenance' in r['error']['message']

    def test_auto_still_takes_the_text(self, run_body, api):
        # INV-1: without responseFormat, a response that is not JSON is its text
        assert 'Maintenance' in run_body(f'<q:invoke name="u" url="{api}/html"/><q:return value="{{u}}"/>')


class TestFunctionsAndHabits:
    @pytest.mark.parametrize('expr,expected', [
        ('round(2.5)', 3), ('round(-2.5)', -3), ('round(0.125, 2)', 0.13), ('round(2.567, 2)', 2.57),
        ('ceil(2.1)', 3), ('ceil(-2.1)', -2), ('floor(2.9)', 2), ('max(1, ceil(7 / 200))', 1),
        ("len(split('a b c', ' '))", 3), ("slugify('Olá, Mundo! Ação')", 'ola-mundo-acao'),
    ])
    def test_rounding_and_split(self, run_body, expr, expected):
        # EXPR-9 (before: round(2.5) was 2, round(0.125, 2) was 0.12; ceil/floor did not exist)
        assert run_body(f'<q:return value="{{{expr}}}"/>') == expected

    @pytest.mark.parametrize('expr,hint', [
        ('Math.ceil(n / 2)', 'write ceil(x) instead of Math.ceil'),
        ('Date.now()', 'write now() instead of Date.now'),
        ("t.split(' ')", "write split(text, ' ') instead of x.split"),
        ('parseInt(t)', 'write int(x)'),
    ])
    def test_a_javascript_habit_says_the_equivalent(self, run_body, expr, hint):
        # EXPR-10
        with pytest.raises(Exception, match=re.escape(hint)):
            run_body(f'<q:set name="n" value="3" type="number"/><q:set name="t" value="a b"/>'
                     f'<q:return value="{{{expr}}}"/>')

    def test_a_scope_key_does_not_become_a_bare_name(self, serve_pages):
        # EXPR-11 (before: session.role was also `role`, and request.path was `path`)
        c = serve_pages(p=('<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                           '<q:set name="session.role" value="admin"/>'
                           '<p>[{session.role}|{request.path}]</p>'
                           '<q:if condition="role"><p>BARE</p></q:if></q:component>'))
        html = c.get('/p').get_data(as_text=True)
        assert '[admin|/p]' in html and 'BARE' not in html

    SCOPES = ('<q:component name="s" xmlns:q="https://quantum.lang/ns">'
              '<q:action name="keep" method="POST">'
              '<q:set name="session.n" value="1" type="number"/>'
              '<q:set name="application.m" value="2" type="number"/>'
              '<q:set name="cookie.c" value="3" type="number"/>'
              """<q:set name="session.user" value='{"name": "Ana"}' type="object"/>"""
              '<q:redirect url="/s?q=hi"/></q:action>'
              "<p>[text={session.n + 1},{application.m + 1},{cookie.c + 1},{query.q + '!'},"
              "{request.path + '#'},{session.user.name}]</p>"
              '<a href="/x/{session.n + 1}/{application.m * 10}/{cookie.c - 1}">attr</a>'
              "<q:if condition=\"session.n > 0 and application.m > 1 and cookie.c > 2 and query.q == 'hi'\">"
              '<p>[if=yes]</p></q:if>'
              "<ui:link to=\"/ui/{session.n + 1}/{query.q + 'x'}\">ui</ui:link></q:component>")

    def test_a_scope_inside_an_expression_is_read_everywhere(self, serve_pages):
        # EXPR-11: {session.n + 1} rendered '' in HTML — the page read it as the
        # session key "n + 1" — while q:set evaluated it. Every scope, every place.
        c = serve_pages(s=self.SCOPES)
        c.post('/s', data={'action': 'keep'})
        html = c.get('/s?q=hi').get_data(as_text=True)
        assert '[text=2,3,4,hi!,/s#,Ana]' in html
        assert 'href="/x/2/20/2"' in html
        assert '[if=yes]' in html
        assert 'href="/ui/2/hix"' in html

    def test_form_inside_an_expression(self, serve_pages):
        # EXPR-11: form. on a page without an action
        c = serve_pages(f='<q:component name="f" xmlns:q="https://quantum.lang/ns">'
                          "<p>[form={form.t + '?'}]</p></q:component>")
        assert '[form=hi?]' in c.post('/f', data={'t': 'hi'}).get_data(as_text=True)


# ------------------------------------------------------------------ INV-1: headers, body, auth, retry, text

class _Echo(http.server.BaseHTTPRequestHandler):
    failures_left = 0

    def _answer(self):
        length = int(self.headers.get('Content-Length') or 0)
        sent = self.rfile.read(length).decode() if length else ''
        if self.path == '/flaky' and _Echo.failures_left:
            _Echo.failures_left -= 1
            self.send_response(503)
            self.end_headers()
            return
        if self.path == '/text':
            out, kind = b'plain words', 'text/plain'
        else:
            out = json.dumps({'auth': self.headers.get('Authorization'), 'key': self.headers.get('X-Key'),
                              'custom': self.headers.get('X-Custom'), 'type': self.headers.get('Content-Type'),
                              'body': sent}).encode()
            kind = 'application/json'
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    do_GET = do_POST = _answer

    def log_message(self, *args):
        pass


@pytest.fixture
def echo():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Echo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_address[1]}'
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize('attributes,children,field,expected', [
    ('authType="bearer" authToken="T1"', '', 'auth', 'Bearer T1'),
    ('authType="apikey" authToken="K" authHeader="X-Key"', '', 'key', 'K'),
    ('authType="basic" authUsername="ana" authPassword="pw"', '', 'auth', 'Basic YW5hOnB3'),
    ('', '<q:header name="X-Custom" value="v{1 + 1}"/>', 'custom', 'v2'),
    ('method="POST"', '<q:body>{"n": 2}</q:body>', 'body', '{"n": 2}'),
    ('method="POST" contentType="text/plain"', '<q:body>n={1 + 1}</q:body>', 'body', 'n=2'),
    ('method="POST"', '', 'type', 'application/json'),
])
def test_headers_body_and_authentication(run_body, echo, attributes, children, field, expected):
    # INV-1
    r = run_body(f'<q:invoke name="r" url="{echo}/a" {attributes}>{children}</q:invoke><q:return value="{{r}}"/>')
    assert r[field] == expected


def test_a_response_that_is_not_json_is_its_text(run_body, echo):
    # INV-1
    assert run_body(f'<q:invoke name="r" url="{echo}/text"/><q:return value="{{r}}"/>') == 'plain words'


def test_retry_is_for_timeouts_and_connections_not_for_an_http_status(run_body, echo):
    # INV-1: a 503 is an answer — it fails at once, with retry declared
    _Echo.failures_left = 1
    with pytest.raises(Exception, match='HTTP 503'):
        run_body(f'<q:invoke name="r" url="{echo}/flaky" retry="2" retryDelay="10"/>')


def test_retry_tries_again_when_it_cannot_connect(run_body):
    # INV-1
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    r = run_body(f'<q:invoke name="r" url="http://127.0.0.1:{port}/" retry="2" retryDelay="10" onerror="continue"/>'
                 '<q:return value="{r_result}"/>')
    assert r['success'] is False and r['metadata']['attempts'] == 3
