"""Conformance: SPEC.md section 10 (UI, the ui: namespace)."""

import contextlib
import io
import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'
APP = (f'<q:application id="Panel" type="ui" {NS}><ui:window title="T">'
       '<ui:text>Hi</ui:text></ui:window></q:application>')


def render(source):
    from quantum.runtime.component import ComponentRuntime
    from quantum.runtime.renderer import HTMLRenderer
    ast = QuantumParser().parse(source)
    runtime = ComponentRuntime(config={})
    with contextlib.redirect_stdout(io.StringIO()):
        runtime.execute_component(ast, {})
    return HTMLRenderer(runtime.execution_context).render(ast)


class TestHonesty:
    def test_building_from_a_component_explains(self):
        # UI-0 (before: AttributeError 'ComponentNode' object has no attribute 'app_id')
        from quantum.runtime.ui_builder import UIBuildError, UIBuilder
        comp = QuantumParser().parse(f'<q:component name="p" {NS}><ui:window title="T"/></q:component>')
        with pytest.raises(UIBuildError, match=r'needs <q:application type="ui">; this file is a <q:component>'):
            UIBuilder().build(comp, target='html')

    def test_each_target_writes_its_own_file(self, tmp_path, monkeypatch):
        # UI-0 (before: console and desktop wrote the same Panel.py)
        from quantum.runtime.ui_builder import UIBuilder
        monkeypatch.chdir(tmp_path)
        app = QuantumParser().parse(APP)
        names = {target: Path(UIBuilder().build_to_file(app, target=target)).name
                 for target in ('html', 'textual', 'mobile')}
        assert names == {'html': 'Panel.html', 'textual': 'Panel_console.py', 'mobile': 'Panel.js'}


PAGE = (f'<q:component name="p" {NS}>'
        '<q:set name="items" type="array" value=\'[{"id": 1, "name": "&lt;b&gt;one&lt;/b&gt;"}, {"id": 2, "name": "two"}]\'/>'
        '<q:action name="remove" method="POST"><q:param name="id" type="integer"/>'
        '<q:set name="session.removed" value="{id}"/><q:redirect url="/p"/></q:action>'
        '<q:action name="create" method="POST"><q:param name="title" required="true"/>'
        '<q:set name="session.created" value="{title}"/><q:redirect url="/p"/></q:action>'
        '<ui:window title="Tasks"><ui:vbox gap="md">'
        '<ui:text>Removed: {session.removed} Created: {session.created}</ui:text>'
        '<q:loop type="array" items="{items}" var="t"><ui:hbox gap="sm"><ui:text>{t.name}</ui:text>'
        '<ui:button on-click="remove" with="id={t.id}">Remove</ui:button></ui:hbox></q:loop>'
        '<ui:form on-submit="create"><ui:input bind="title" required="true"/><ui:button>Create</ui:button></ui:form>'
        '<p class="free">HTML <b>alongside</b></p>'
        '</ui:vbox></ui:window></q:component>')


class TestOnThePage:
    def test_drawn_with_the_page_runtime(self, serve_pages):
        # UI-1 (before 0.15: raw <window><vbox>, or an error)
        c = serve_pages(p=PAGE)
        html = c.get('/p').get_data(as_text=True)
        assert 'class="q-window"' in html and 'flex-direction: column' in html
        assert '<p class="free"> HTML <b>alongside</b> </p>' in re.sub(r'\s+', ' ', html)
        # the server moves inline CSS to a file; the ui:* elements' CSS comes once
        css = ''
        for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html):
            with c.get(href) as sheet:   # a static file: close it
                css += sheet.get_data(as_text=True)
        assert css.count('.q-btn {') == 1

    def test_values_are_resolved_and_escaped(self, serve_pages):
        # UI-1: the adapter's builder does not escape; data values are escaped before it
        html = serve_pages(p=PAGE).get('/p').get_data(as_text=True)
        assert '&lt;b&gt;one&lt;/b&gt;' in html and '<b>one</b>' not in html

    def test_an_event_is_an_action(self, serve_pages):
        # UI-1: on-click posts to the q:action, with the with= fields
        c = serve_pages(p=PAGE)
        html = c.get('/p').get_data(as_text=True)
        assert '<input type="hidden" name="action" value="remove" />' in html
        assert '<input type="hidden" name="id" value="2" />' in html
        assert c.post('/p', data={'action': 'remove', 'id': '2'}).status_code == 302
        assert 'Removed: 2' in c.get('/p').get_data(as_text=True)
        assert c.post('/p', data={'action': 'create', 'title': 'new'}).status_code == 302
        assert 'Created: new' in c.get('/p').get_data(as_text=True)

    def test_an_event_without_an_action_is_an_error(self):
        # UI-1
        with pytest.raises(ValueError, match=r'on-click="vanish" names no q:action of this page \(UI-1; actions: x\)'):
            render(f'<q:component name="p" {NS}><q:action name="x" method="POST"><q:redirect url="/"/></q:action>'
                   '<ui:window title="T"><ui:button on-click="vanish">B</ui:button></ui:window></q:component>')

    def test_an_unknown_ui_tag_suggests(self):
        # UI-1
        with pytest.raises(Exception, match=r'Unknown UI tag: <ui:buton>; did you mean <ui:button>\?'):
            QuantumParser().parse(f'<q:component name="p" {NS}><ui:buton>x</ui:buton></q:component>')

    def test_a_statement_inside_ui_is_an_error(self):
        # UI-1 / PARSE-2: inside ui:* a statement would never run, as inside HTML
        from quantum.core.parser import QuantumParseError
        with pytest.raises(QuantumParseError, match=r'<q:set name="x"> inside <ui:vbox>'):
            QuantumParser().parse(f'<q:component name="p" {NS}><ui:vbox><q:set name="x" value="1"/>'
                                  '<ui:text>{x}</ui:text></ui:vbox></q:component>')


class TestResponsive:
    def test_attributes_become_classes(self):
        # UI-2
        html = render(f'<q:component name="p" {NS}><ui:hbox stack-below="md">'
                      '<ui:vbox width="200" hide-below="sm"><ui:text>a</ui:text></ui:vbox>'
                      '<ui:vbox grow="true" hide-above="lg"><ui:text>b</ui:text></ui:vbox>'
                      '<ui:grid columns="1 sm:2 lg:3"><ui:text>c</ui:text></ui:grid></ui:hbox></q:component>')
        for css_class in ('q-stack-md', 'q-hide-sm', 'q-grow', 'q-hide-above-lg', 'q-cols-1', 'q-sm-cols-2', 'q-lg-cols-3'):
            assert css_class in html, css_class
        assert '@media (max-width: 767.98px)' in html and '.q-stack-md {' in html

    def test_a_breakpoint_that_does_not_exist_is_an_error(self):
        # UI-2
        with pytest.raises(Exception, match=r'stack-below="xl": use sm \(640 px\), md \(768 px\) or lg \(1024 px\)'):
            QuantumParser().parse(f'<q:component name="p" {NS}><ui:hbox stack-below="xl"/></q:component>')

    def test_badly_written_columns_are_an_error(self):
        # UI-2
        with pytest.raises(ValueError, match=r'columns="1 xl:2"'):
            render(f'<q:component name="p" {NS}><ui:grid columns="1 xl:2"><ui:text>c</ui:text></ui:grid></q:component>')


class TestViewTree:
    def test_the_page_as_a_tree_for_the_console(self, serve_pages):
        # UI-3: the same runtime answers the view tree instead of HTML
        import json
        c = serve_pages(p=PAGE)
        r = c.get('/p', headers={'Accept': 'application/vnd.quantum.view+json'})
        assert r.mimetype == 'application/vnd.quantum.view+json'
        view = json.loads(r.get_data(as_text=True))
        window = view['view'][0]
        assert window['type'] == 'window' and window['props']['title'] == 'Tasks'
        box = window['children'][0]
        buttons = [f for row in box['children'] if row['type'] == 'hbox'
                   for f in row['children'] if f['type'] == 'button']
        assert [b['event'] for b in buttons] == [{'action': 'remove', 'fields': {'id': '1'}},
                                                 {'action': 'remove', 'fields': {'id': '2'}}]
        texts = [f['props']['text'] for row in box['children'] if row['type'] == 'hbox'
                 for f in row['children'] if f['type'] == 'text']
        assert texts == ['<b>one</b>', 'two']        # raw data: the console draws text, not HTML
        form = [f for f in box['children'] if f['type'] == 'form'][0]
        assert form['event']['action'] == 'create'
        assert form['children'][0] == {'type': 'input', 'props': {'bind': 'title', 'input_type': 'text', 'required': True}, 'children': []}


def ui_page(body, extra=''):
    return (f'<q:component name="p" {NS}>'
            '<q:set name="rows" type="array" value=\'[{"id": 1, "name": "&lt;i&gt;Ana&lt;/i&gt;"}, {"id": 2, "name": "Bia"}]\'/>'
            '<q:action name="remove" method="POST"><q:param name="id" type="integer"/><q:redirect url="/p"/></q:action>'
            f'{extra}<ui:window title="T">{body}</ui:window></q:component>')


class TestData:
    def test_a_table_draws_one_row_per_record(self):
        # UI-5 (before: an empty tbody and all the data in an HTML comment)
        html = render(ui_page(
            '<ui:table source="{rows}"><ui:column key="name" label="Name"/>'
            '<ui:column label="Actions"><ui:button on-click="remove" with="id={row.id}">Remove {row.name}</ui:button></ui:column>'
            '</ui:table>'))
        assert html.count('<tr>') == 3                         # header + 2 rows
        assert '&lt;i&gt;Ana&lt;/i&gt;' in html and '<i>Ana' not in html
        assert 'name="id" value="2"' in html and 'Remove Bia' in html
        assert 'Data source' not in html

    def test_a_table_without_columns_shows_every_field(self):
        # UI-5 (before: every row was drawn empty)
        html = render(ui_page('<ui:table source="{rows}"/>'))
        assert re.findall(r'<th>\s*([^<]*?)\s*</th>', html) == ['Id', 'Name']
        assert re.search(r'<td>\s*Bia\s*</td>', html)

    def test_a_list_repeats_its_content_with_the_variable(self):
        # UI-5 (before: {l.name} came out raw)
        html = render(ui_page(
            '<ui:list source="{rows}" as="l"><ui:item><ui:text>Person {l.id}</ui:text></ui:item></ui:list>'))
        assert 'Person 1' in html and 'Person 2' in html and '{l.' not in html

    def test_a_source_that_is_not_a_list_is_an_error(self):
        # UI-5
        with pytest.raises(ValueError, match=r'<ui:table source="\{nothing\}"> needs a list .* and got str'):
            render(ui_page('<ui:table source="{nothing}"><ui:column key="x"/></ui:table>',
                           '<q:set name="nothing" value="text"/>'))

    def test_a_column_the_row_does_not_have_is_an_error(self):
        # UI-5
        with pytest.raises(ValueError, match=r'key="nme"\]?.*no field "nme" \(fields: id, name\)'):
            render(ui_page('<ui:table source="{rows}"><ui:column key="nme"/></ui:table>'))

    def test_the_view_tree_carries_the_rows(self, serve_pages):
        # UI-5
        c = serve_pages(p=ui_page('<ui:table source="{rows}" as="r"><ui:column key="name" label="Name"/>'
                                  '<ui:column><ui:button on-click="remove" with="id={r.id}">X</ui:button></ui:column>'
                                  '</ui:table>'))
        table = c.get('/p', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()['view'][0]['children'][0]
        assert table['columns'][0]['label'] == 'Name'
        assert table['rows'][1][0] == [{'type': 'text', 'props': {'text': 'Bia'}}]
        assert table['rows'][1][1][0]['event'] == {'action': 'remove', 'fields': {'id': '2'}}


class TestFields:
    def test_initial_field_values(self):
        # UI-6 (before: there was no way to open an edit form filled in)
        html = render(ui_page(
            '<ui:form on-submit="remove"><ui:input bind="name" value="{rows[1].name}"/>'
            '<ui:checkbox bind="a" checked="true"/><ui:switch bind="b" checked="false"/>'
            '<ui:radio bind="r" options="x,y" value="y"/><ui:select bind="s" options="p,q" value="q"/>'
            '</ui:form>'))
        assert 'value="Bia" name="name"' in html
        assert re.search(r'<input type="checkbox" name="a" checked', html)
        assert not re.search(r'name="b" checked', html)
        assert re.search(r'value="y" name="r" checked', html)
        assert '<option value="q" selected>' in html


class TestCoreSet:
    def test_direct_container_text_shows(self):
        # UI-1 (before: <ui:card-header>Top</ui:card-header> came out empty)
        html = render(ui_page('<ui:card><ui:card-header>Top {rows[0].id}</ui:card-header></ui:card>'
                              '<ui:vbox>before <b>middle</b> after</ui:vbox>'))
        assert 'Top 1' in html and 'before' in html and 'after' in html

    def test_card_title_and_an_open_section(self):
        # UI-7 (before: title vanished next to card-header; section was a closed <details>)
        html = render(ui_page('<ui:card title="Card"><ui:card-header>H</ui:card-header></ui:card>'
                              '<ui:section title="Section"><ui:text>inside</ui:text></ui:section>'))
        assert 'Card' in html and '<details' not in html and 'Section' in html

    def test_the_console_says_what_it_does_not_draw(self):
        # UI-7: outside the Core set, the console says so instead of drawing something else
        import asyncio
        from quantum.runtime.ui_console import ConsoleUI
        from textual.widgets import Static

        class Fixed(ConsoleUI):
            def _fetch(self, method, path, data=None):
                return {'title': 'T', 'view': [{'type': 'chart', 'props': {}, 'children': []},
                                               {'type': 'text', 'props': {'text': 'ok'}, 'children': []}]}

        async def main():
            app = Fixed('http://127.0.0.1:1/')
            async with app.run_test() as pilot:
                await pilot.pause()
                return [str(w.render()) for w in app.query(Static)]

        texts = asyncio.run(main())
        assert '[ui:chart is not drawn in the console]' in texts and 'ok' in texts

    def test_the_core_set_is_drawn_by_the_console(self):
        # UI-7: every tag of the Core set has its own drawing in the console
        import inspect
        from quantum.core.features.ui_engine.src.ast_nodes import CORE_TAGS
        from quantum.runtime.ui_console import ConsoleUI
        source = inspect.getsource(ConsoleUI._widget_without_width)
        # column/option: read by the table/select; pager: the tree already sends links (UI-11)
        types = {t.replace('-', '') for t in CORE_TAGS} - {'column', 'option', 'pager', 'history'}
        missing = [t for t in sorted(types) if f"'{t}'" not in source]
        assert missing == []


class TestStandaloneBuild:
    LOGIC = (f'<q:application id="A" type="ui" {NS}><q:set name="n" value="1"/>'
             '<ui:window title="T"><ui:text>{n}</ui:text></ui:window></q:application>')

    def test_the_desktop_target_is_gone_and_points_to_quantum_desktop(self):
        # UI-8
        from quantum.runtime.ui_builder import UIBuildError, UIBuilder
        with pytest.raises(UIBuildError, match=r'--target desktop was removed .* run `quantum desktop`'):
            UIBuilder().build(QuantumParser().parse(APP), target='desktop')

    @pytest.mark.parametrize('target', ['html', 'textual'])
    def test_logic_in_a_standalone_build_is_an_error(self, target):
        # UI-8 (before: the q:set was ignored and {n} came out raw)
        from quantum.runtime.ui_builder import UIBuildError, UIBuilder
        with pytest.raises(UIBuildError, match=rf'a {target} UI build draws layout only, and <q:set name="n"> would not run'):
            UIBuilder().build(QuantumParser().parse(self.LOGIC), target=target)

    def test_mobile_is_laboratory(self, caplog):
        # UI-8
        import logging
        from quantum.core import tiers
        from quantum.runtime.ui_builder import UIBuilder
        tiers.reset_warnings()
        with caplog.at_level(logging.WARNING, logger='quantum.tiers'):
            UIBuilder().build(QuantumParser().parse(self.LOGIC), target='mobile')
        assert any('--target mobile is LABORATORY' in r.getMessage() for r in caplog.records)


class TestBoundAttributesAreNotValidatedAsLiterals:
    """UI-1: `{expressions}` in ui:* are resolved by the page.

    `quantum run` validated `<ui:alert variant="{flashType == 'error' and
    'danger' or 'success'}">` as if the braces were the value, and refused
    examples/form-rules.q with "Invalid alert variant"; the page itself drew it
    right.
    """

    @pytest.mark.parametrize("tag", ['<ui:alert variant="{kind}">x</ui:alert>',
                                     '<ui:toast message="x" variant="{kind}" position="{where}"/>',
                                     '<ui:skeleton variant="{kind}"/>'])
    def test_a_bound_value_passes_validation(self, tag):
        from quantum.core.parser import QuantumParser
        ast = QuantumParser().parse('<q:component name="C" xmlns:q="https://quantum.lang/ns" '
                                    f'xmlns:ui="https://quantum.lang/ui">{tag}</q:component>')
        assert ast.validate() == []

    def test_a_wrong_literal_is_still_refused(self):
        from quantum.core.parser import QuantumParser
        ast = QuantumParser().parse('<q:component name="C" xmlns:q="https://quantum.lang/ns" '
                                    'xmlns:ui="https://quantum.lang/ui"><ui:alert variant="red">x</ui:alert></q:component>')
        assert any('Invalid alert variant' in e for e in ast.validate())
