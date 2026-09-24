"""Conformance: the error points to the line (M2, SPEC DEV-2)."""

import re

import pytest

from quantum.core.parser import QuantumParser

NS = 'xmlns:q="https://quantum.lang/ns"'


class TestParse:
    @pytest.mark.parametrize('source,line', [
        (f'<q:component name="c" {NS}>\n<p>hi</p>\n<q:sett name="x" value="1"/>\n</q:component>', 3),
        (f'<q:component name="c" {NS}>\n\n<div>\n  <q:set name="x" value="1"/>\n</div>\n</q:component>', 4),
        (f'<q:component name="c" {NS}>\n<q:set name="d" value="1"/>\n'
         '<q:if condition="d"><q:redirect url="/"/></q:if>\n'
         '<q:action name="a" method="POST"><q:redirect url="/"/></q:action></q:component>', 3),
    ])
    def test_a_parse_error_says_the_line(self, source, line):
        # DEV-2
        with pytest.raises(Exception) as error:
            QuantumParser().parse(source)
        assert error.value.line == line
        assert f'at line {line}: ' in str(error.value)

    def test_the_error_cites_the_rule(self):
        # DEV-2
        with pytest.raises(Exception, match=r'never runs \(PARSE-2\)'):
            QuantumParser().parse(f'<q:component name="c" {NS}><div><q:set name="x" value="1"/></div></q:component>')


class TestRunning:
    def test_the_innermost_statement_gives_the_line(self):
        # DEV-2: the q:set inside the q:if, not the q:if
        from quantum.core.xml_lines import error_location
        from quantum.runtime.component import ComponentRuntime
        source = (f'<q:component name="c" {NS}>\n<q:set name="a" value="1"/>\n<q:if condition="a">\n'
                  '  <q:set name="b" value="{a + nothing}" type="number"/>\n</q:if>\n</q:component>')
        with pytest.raises(Exception) as error:
            ComponentRuntime(config={}).execute_component(QuantumParser().parse(source), {})
        assert error_location(error.value)[1] == 4


PAGE = '''<q:component name="Bill">
  <q:set name="price" value="10" type="number" />
  <q:if condition="price">
    <q:set name="total" value="{price * query.qty}" type="number" />
  </q:if>
  <p>Total: {total}</p>
</q:component>
'''

BROKEN = '''<q:component name="B">
  <div>
    <q:set name="x" value="1" />
  </div>
</q:component>
'''


@pytest.fixture
def build(tmp_path):
    from quantum.runtime.web_server import QuantumWebServer

    def create(debug, folder=None, **components):
        folder = folder or tmp_path
        comp = folder / 'components'
        comp.mkdir(parents=True, exist_ok=True)
        for name, source in components.items():
            (comp / f'{name}.q').write_text(source, encoding='utf-8')
        config = folder / 'quantum.config.yaml'
        config.write_text(f"server:\n  debug: {'true' if debug else 'false'}\n"
                          f"paths:\n  components: {comp.as_posix()}\n"
                          "logging:\n  level: CRITICAL\n  console: false\n  file: false\n", encoding='utf-8')
        server = QuantumWebServer(str(config))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return create


def marked_line(page):
    m = re.search(r'<tr class="marked"><td class="ln">(\d+)</td>', page)
    return int(m.group(1)) if m else None


class TestErrorPage:
    def test_in_debug_it_shows_the_snippet_with_the_line_marked(self, build):
        # DEV-2
        c = build(True, bill=PAGE, broken=BROKEN)
        page = c.get('/bill?qty=abc').get_data(as_text=True)
        assert marked_line(page) == 4 and 'bill.q, line 4' in page
        broken = c.get('/broken').get_data(as_text=True)
        assert marked_line(broken) == 3
        assert 'SPEC.md#:~:text=PARSE-2' in broken                 # the rule, with a link

    def test_without_debug_it_does_not_show_the_source(self, build):
        # DEV-2
        c = build(False, bill=PAGE)
        page = c.get('/bill?qty=abc').get_data(as_text=True)
        assert marked_line(page) is None and 'price * query.qty' not in page

    def test_the_error_page_escapes_what_came_from_the_request(self, build):
        # DEV-2 (before: title, message and details went into the HTML unescaped)
        c = build(True, bill=PAGE)
        page = c.get('/bill?qty=<script>alert(1)</script>').get_data(as_text=True)
        assert '<script>alert(1)' not in page

    def test_an_error_in_an_imported_component_points_to_its_file(self, build):
        # DEV-2
        child = f'<q:component name="Child" {NS}>\n  <p>ok</p>\n  <q:set name="x" value="{{1 + nothing}}" type="number"/>\n</q:component>\n'
        parent = (f'<q:component name="parent" {NS}>\n  <q:import component="Child"/>\n'
                  '  <Child />\n</q:component>\n')
        c = build(True, parent=parent, Child=child)
        page = c.get('/parent').get_data(as_text=True)
        assert 'Child.q, line 3' in page and marked_line(page) == 3


class TestReloadKeepsTheSession:
    PAGE = (f'<q:component name="s" {NS}>'
            '<q:action name="enter" method="POST"><q:set name="session.who" value="Ana"/>'
            '<q:redirect url="/s"/></q:action><p>[{session.who}]</p></q:component>')

    def test_in_debug_the_key_survives_a_new_process(self, build, tmp_path):
        # DEV-2: the reloader is another process; the session stays valid
        first = build(True, s=self.PAGE)
        first.post('/s', data={'action': 'enter'})
        cookie = first.get_cookie('session')
        second = build(True, s=self.PAGE)                            # "after the reload"
        second.set_cookie('session', cookie.value)
        assert '[Ana]' in second.get('/s').get_data(as_text=True)
        assert (tmp_path / '.quantum' / 'dev-secret-key').exists()

    def test_without_debug_nothing_is_written(self, build, tmp_path):
        # DEV-2
        build(False, s=self.PAGE)
        assert not (tmp_path / '.quantum' / 'dev-secret-key').exists()
