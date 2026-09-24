"""An `on-click` written with parentheses reached nothing.

Different targets, forms of the same defect — the RAW text of the handler was
used as if it were a name:

  * **terminal (Textual)** — `py_id("save()")` returned `save()` and the
    generator wrote `def action_save()(self):`. The generated Python file did
    not COMPILE: a single button with parentheses brought down the whole
    application on import. And the comparison with the q:function names never
    matched, so not even the right function was called.

  (The old desktop target, a pywebview bridge that translated q:functions to
  JavaScript, went away in 0.16 — UI-8; the desktop is now the page in a
  window, UI-4.)

And, on the web target, a q:function's body never goes to the browser — but
the `onclick="myFunction()"` did, with no definition along with it: a
`ReferenceError` in the console and silence everywhere else.
"""

import ast as pyast

import pytest

from quantum.core.parser import QuantumParser


def _app(src):
    return QuantumParser(use_cache=False).parse(src)


def _generate_terminal(src):
    from quantum.runtime.terminal_builder import TerminalBuilder
    return TerminalBuilder().build(_app(src))


SRC_TERMINAL = '''<q:application id="t" type="terminal">
  <q:function name="save"><q:set name="x" value="1" /></q:function>
  <qt:screen name="main">
    <qt:button id="b1" label="With parentheses" on-click="save()" />
    <qt:button id="b2" label="Without parentheses" on-click="save" />
  </qt:screen>
</q:application>'''


class TestTerminal:
    def test_the_generated_file_compiles(self):
        code = _generate_terminal(SRC_TERMINAL)
        pyast.parse(code)          # before: SyntaxError

    def test_there_is_no_method_with_parentheses_in_its_name(self):
        code = _generate_terminal(SRC_TERMINAL)
        assert 'def action_save()' not in code, code

    def test_both_forms_call_the_same_action(self):
        code = _generate_terminal(SRC_TERMINAL)
        assert code.count('self.action_save()') >= 2, code
        # And a single method, not two.
        assert code.count('def action_save(self):') == 1

    def test_the_action_calls_the_user_s_q_function(self):
        code = _generate_terminal(SRC_TERMINAL)
        body = code.split('def action_save(self):')[1]
        assert 'self.save()' in body.split('def ')[0], body[:300]

    def test_a_handler_with_garbage_still_generates_valid_code(self):
        code = _generate_terminal('''<q:application id="t" type="terminal">
  <qt:screen name="main">
    <qt:button id="b" label="x" on-click="does not exist!" />
  </qt:screen>
</q:application>''')
        pyast.parse(code)

    @pytest.mark.parametrize("given,expected", [
        ('save()', ('save', '')),
        ('save', ('save', None)),
        ('save(1, 2)', ('save', '1, 2')),
        ('  save( a )  ', ('save', 'a')),
        ('', ('', None)),
    ])
    def test_split_call(self, given, expected):
        from quantum.runtime.terminal_templates import split_call
        assert split_call(given) == expected

    @pytest.mark.parametrize("given", [
        'save()', 'does not exist!', 'a.b(c)', '9start', '', 'with-dash',
    ])
    def test_py_id_always_produces_an_identifier(self, given):
        from quantum.runtime.terminal_templates import py_id
        assert py_id(given).isidentifier(), (given, py_id(given))


class TestFunctionsAtTheTopOfTheApplication:
    """A `<q:function>` that was a direct child of `<q:application>` was dropped.

    The per-engine parsers (qt:, qg:, ui:) only look at children of their OWN
    namespace, and there was nowhere to keep a `q:` child. The terminal
    generator then only found functions declared inside a `<qt:screen>`, and
    the on-click that pointed to the global function fell into the "unknown
    action" branch: `self.notify("Action: save")` — the button ANNOUNCED the
    action instead of running it.
    """

    SRC = '''<q:application id="t" type="terminal">
  <q:set name="counter" type="integer" value="0" />
  <q:function name="save"><q:set name="x" value="1" /></q:function>
  <qt:screen name="main"><qt:button id="b" label="x" on-click="save()" /></qt:screen>
</q:application>'''

    def test_the_function_is_kept_on_the_application_node(self):
        app = _app(self.SRC)
        assert [f.name for f in app.functions] == ['save']

    def test_the_top_level_q_set_too(self):
        app = _app(self.SRC)
        assert [s.name for s in app.state_vars] == ['counter']

    def test_the_button_runs_the_function_instead_of_announcing_it(self):
        code = _generate_terminal(self.SRC)
        assert 'self.notify("Action: save")' not in code, code
        assert 'def save(self):' in code
        body = code.split('def action_save(self):')[1].split('def ')[0]
        assert 'self.save()' in body, body

    def test_the_top_level_variable_becomes_reactive_state(self):
        code = _generate_terminal(self.SRC)
        assert 'counter = reactive(' in code, code


class TestQFunctionOnTheWebTarget:
    def _render(self, source):
        from quantum.runtime.component import ComponentRuntime
        from quantum.runtime.renderer import HTMLRenderer
        ast = _app(source)
        context = ComponentRuntime().execute_component(ast, {})
        return HTMLRenderer(context if isinstance(context, dict) else {}
                            ).render(ast)

    SRC = ('<q:component name="C">'
           '<q:function name="increment"><q:set name="n" value="1" />'
           '</q:function>'
           '<button onclick="increment()">+1</button>'
           '</q:component>')

    def test_the_called_name_exists_on_the_client(self):
        html = self._render(self.SRC)
        assert 'increment' in html.split('<script>')[-1], html

    def test_the_error_says_what_to_use_instead(self):
        html = self._render(self.SRC)
        assert 'q:action' in html

    def test_the_warning_goes_to_the_server_log(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger='quantum.renderer'):
            self._render(self.SRC)
        assert any('increment' in r.getMessage() for r in caplog.records), \
            [r.getMessage() for r in caplog.records]

    def test_the_script_goes_in_the_document_not_after_the_html(self):
        """After `</html>` the browser moves it by itself, but the output stops
        being valid HTML."""
        html = self._render(
            '<q:component name="C">'
            '<q:function name="f"><q:set name="n" value="1" /></q:function>'
            '<html><body><button onclick="f()">x</button></body></html>'
            '</q:component>')
        assert html.rstrip().endswith('</html>'), html
        assert html.index('<script>') < html.index('</body>'), html

    def test_a_handler_that_is_not_a_q_function_does_not_become_a_script(self):
        """Plain JavaScript on the page must not be hijacked."""
        html = self._render(
            '<q:component name="C">'
            '<button onclick="alert(1)">x</button>'
            '</q:component>')
        assert '<script>' not in html, html

    def test_without_any_handler_there_is_no_script(self):
        html = self._render(
            '<q:component name="C">'
            '<q:function name="f"><q:set name="n" value="1" /></q:function>'
            '<p>hi</p></q:component>')
        assert '<script>' not in html, html
