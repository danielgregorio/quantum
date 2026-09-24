"""Conformance: forms that already know the action's rules (M1, SPEC UI-9)."""

import re

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

PAGE = (f'<q:component name="p" {NS}>'
        '<q:action name="save" method="POST">'
        '<q:param name="name" required="true" minlength="3" maxlength="40"/>'
        '<q:param name="age" type="integer" min="18" max="99"/>'
        '<q:param name="email" type="email"/>'
        '<q:param name="code" pattern="^[A-Z]{3}$"/>'
        '<q:param name="nickname" pattern="^[a-z]"/>'
        '<q:param name="password" required="true"/>'
        '<q:param name="plan" enum="free,pro" default="free"/>'
        '<q:param name="agree" default="off"/>'
        '<q:redirect url="/p" flash="ok {name}"/></q:action>'
        '<ui:window title="T"><ui:form on-submit="save">'
        '<ui:input bind="name"/><ui:input bind="age"/><ui:input bind="email"/>'
        '<ui:input bind="code"/><ui:input bind="nickname"/>'
        '<ui:input bind="password" type="password"/><ui:select bind="plan"/>'
        '<ui:checkbox bind="agree" label="I agree" checked="true"/>'
        '<ui:button>Save</ui:button></ui:form></ui:window></q:component>')


def field(html, name):
    m = re.search(rf'<(?:input|select)[^>]*name="{name}"[^>]*>', html)
    return m.group(0) if m else ''


def errors(html):
    return re.findall(r'<span class="q-field-error"[^>]*>\s*([^<]*?)\s*</span>', html)


class TestAttributes:
    def test_the_q_param_rules_become_attributes(self, serve_pages):
        # UI-9
        html = serve_pages(p=PAGE).get('/p').get_data(as_text=True)
        assert 'required' in field(html, 'name') and 'minlength="3"' in field(html, 'name') \
            and 'maxlength="40"' in field(html, 'name')
        assert 'type="number"' in field(html, 'age') and 'min="18"' in field(html, 'age') \
            and 'max="99"' in field(html, 'age')
        assert 'type="email"' in field(html, 'email')
        assert 'pattern="[A-Z]{3}"' in field(html, 'code')         # ^…$ becomes the HTML pattern
        assert 'pattern' not in field(html, 'nickname')            # without $: only the server checks
        assert '<option value="free">' in html and '<option value="pro">' in html  # enum becomes options

    def test_an_attribute_written_on_the_field_wins(self, serve_pages):
        # UI-9
        html = serve_pages(p=PAGE.replace('<ui:input bind="name"/>', '<ui:input bind="name" minlength="1"/>')
                           ).get('/p').get_data(as_text=True)
        assert 'minlength="1"' in field(html, 'name')

    def test_rules_off_turns_it_off(self, serve_pages):
        # UI-9
        html = serve_pages(p=PAGE.replace('<ui:form on-submit="save">', '<ui:form on-submit="save" rules="off">')
                           ).get('/p').get_data(as_text=True)
        assert 'minlength' not in field(html, 'name') and 'required' not in field(html, 'name')

    def test_rules_with_an_unknown_value_is_an_error(self):
        # UI-9
        from quantum.core.parser import QuantumParser
        with pytest.raises(Exception, match=r'rules="yes"'):
            QuantumParser().parse(PAGE.replace('on-submit="save">', 'on-submit="save" rules="yes">'))


class TestComingBackWithErrors:
    def send(self, c, **fields):
        data = {'action': 'save', 'name': 'Al', 'age': '12', 'password': 's3cr3t', 'code': 'AB"<',
                'nickname': 'Zeca'}
        data.update(fields)
        return c.post('/p', data=data, headers={'Referer': 'http://localhost/p'})

    def test_each_field_shows_its_error_and_the_value_sent(self, serve_pages):
        # UI-9: every field is checked, not only the first
        c = serve_pages(p=PAGE)
        assert self.send(c).status_code == 302
        html = c.get('/p').get_data(as_text=True)
        assert errors(html) == ['Must be at least 3 characters', 'Must be at least 18 (got 12)',
                                "Does not match &#x27;^[A-Z]{3}$&#x27;", "Does not match &#x27;^[a-z]&#x27;"]
        assert 'value="Al"' in field(html, 'name') and 'q-invalid' in field(html, 'name')
        assert 'value="AB&quot;&lt;"' in field(html, 'code')              # escaped
        assert 'value=' not in field(html, 'password')                     # a password never comes back

    def test_a_box_comes_back_as_it_was_sent(self, serve_pages):
        # UI-9: unchecked when sent (the browser does not send it) comes back unchecked
        c = serve_pages(p=PAGE)
        self.send(c)
        assert 'checked' not in re.search(r'<input type="checkbox" name="agree"[^>]*>', c.get('/p').get_data(as_text=True)).group(0)
        self.send(c, agree='on')
        assert 'checked' in re.search(r'<input type="checkbox" name="agree"[^>]*>', c.get('/p').get_data(as_text=True)).group(0)

    def test_the_error_shows_once(self, serve_pages):
        # UI-9
        c = serve_pages(p=PAGE)
        self.send(c)
        c.get('/p')
        html = c.get('/p').get_data(as_text=True)
        assert errors(html) == [] and 'value="Al"' not in field(html, 'name')

    def test_the_console_gets_values_and_errors(self, serve_pages):
        # UI-9, UI-3
        c = serve_pages(p=PAGE)
        self.send(c)
        tree = c.get('/p', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()
        fields = {}

        def walk(nodes):
            for node in nodes:
                if node.get('props', {}).get('bind'):
                    fields[node['props']['bind']] = node['props']
                walk(node.get('children', []))
        walk(tree['view'])
        assert fields['name']['value'] == 'Al' and fields['name']['error'] == 'Must be at least 3 characters'
        assert fields['name']['minlength'] == 3 and fields['name']['required'] is True
        assert 'value' not in fields['password'] or not fields['password'].get('value')


def test_the_browser_checks_before_sending(tmp_path, monkeypatch):
    # UI-9: in a real browser, the generated minlength stops the submit
    playwright = pytest.importorskip('playwright.sync_api', reason='Playwright is not installed')
    import logging
    import threading
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    (tmp_path / 'components').mkdir()
    (tmp_path / 'components' / 'p.q').write_text(PAGE, encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text('paths: {components: ./components}\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    logging.disable(logging.WARNING)
    server = make_server('127.0.0.1', 0, QuantumWebServer('quantum.config.yaml').app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Playwright's Chromium is not available: {exc}")
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/p')
            page.fill('input[name=name]', 'Al')
            page.fill('input[name=password]', 'x')
            page.get_by_role('button', name='Save').click()
            assert page.evaluate('document.querySelector("input[name=name]").validity.tooShort') is True
            assert page.url.endswith('/p') and 'ok Al' not in page.content()
            browser.close()
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
