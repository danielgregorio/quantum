"""
Two documented attributes the textual target silently dropped.

1. `<ui:toast show="hasError">` — the binding became a COMMENT in the
   generated code (`self.q_toast_1()  # show="hasError"`) and the toast fired
   unconditionally. An error toast showed on every launch of the app, error or
   not. It is not a missing attribute: it is the opposite of what it asks.

2. `<ui:step icon="OK">` — it never reached anywhere, neither the indicator
   nor the panel. The html adapter uses `step.icon if step.icon else str(i+1)`.

The first needed a single point where state is written: the widgets wrote
straight to `self._q_state`, so nothing could REACT to a change, and that is
why `show=` could only become a comment.

These tests look at the GENERATED code. Checking that it runs would need
headless Textual; what holds the defect here is the difference between "always
calls" and "calls under a condition", which shows in the generation.
"""

import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.ui_builder import UIBuilder


def generate(body):
    source = ('<q:application id="T" type="ui"><ui:window title="t">'
              + body + '</ui:window></q:application>')
    path = pathlib.Path(tempfile.mkdtemp()) / 't.q'
    path.write_text(source, encoding='utf-8')
    app = QuantumParser().parse_file(str(path))
    return UIBuilder().build(app, target='textual')


class TestTheToastHonoursShow:
    def test_with_show_the_call_is_conditional(self):
        code = generate('<ui:toast message="it failed" show="hasError" variant="danger" />')
        assert '_q_truthy(self._q_state.get("hasError"))' in code

    def test_with_show_it_does_not_fire_unconditionally(self):
        code = generate('<ui:toast message="it failed" show="hasError" />')
        lines = [l.strip() for l in code.splitlines()]
        # The call exists, but never loose at the column of _q_show_toasts's
        # body: it lives inside the if.
        loose = [l for l in lines if l == 'self.q_toast_1()']
        indented = [l for l in code.splitlines()
                    if l.strip() == 'self.q_toast_1()' and l.startswith('            ')]
        assert indented, "the call should be inside the if"
        assert len(loose) == len(indented), (
            "there is an unconditional call left over")

    def test_without_show_it_still_fires(self):
        code = generate('<ui:toast message="hello" variant="info" />')
        assert 'self.q_toast_1()' in code
        assert '_q_truthy' not in code.split('def q_toast_1')[0].split(
            'def _q_show_toasts')[-1]

    def test_the_binding_is_no_longer_just_a_comment(self):
        code = generate('<ui:toast message="x" show="hasError" />')
        assert '# show="hasError"' not in code

    def test_it_fires_when_the_variable_changes_later(self):
        # "hidden until it becomes true" must not become "never".
        code = generate('<ui:toast message="x" show="hasError" />')
        assert 'def _q_toast_on_state' in code
        assert 'if name == "hasError"' in code

    def test_it_fires_only_once(self):
        code = generate('<ui:toast message="x" show="hasError" />')
        assert '_q_toasts_shown' in code, "without memory, it would repeat on every change"


class TestStateHasASinglePointOfWriting:
    """Without it, nothing can react to a change of state."""

    def test_the_helper_exists(self):
        code = generate('<ui:carousel><ui:slide>a</ui:slide></ui:carousel>')
        assert 'def _q_set_state' in code

    def test_the_widgets_write_through_it(self):
        code = generate('<ui:carousel bind="current"><ui:slide>a</ui:slide></ui:carousel>')
        assert 'self._q_set_state(info["bind"]' in code
        assert 'self._q_state[info["bind"]] =' not in code

    @pytest.mark.parametrize("value,expected", [
        ("", False), ("false", False), ("FALSE", False), ("0", False),
        ("no", False), ("off", False), ("  ", False),
        ("true", True), ("yes", True), ("any text", True),
        (None, False), (False, False), (True, True),
        (0, False), (1, True), ([], False), (["a"], True),
    ])
    def test_the_notion_of_true(self, value, expected):
        """The same notion the html target uses in a binding.

        It runs the module's own runtime block instead of slicing the
        generated code: slicing strings breaks as soon as the signature changes
        — which happened in the first version of this test — and what matters
        here is the semantics, not the format of the generation.
        """
        from quantum.runtime import ui_textual_adapter as mod

        ns = {}
        exec(mod._STATE_ACCESSOR, ns)
        assert ns["_q_truthy"](None, value) is expected


class TestTheStepIcon:
    def test_the_icon_shows_in_the_indicator(self):
        code = generate('<ui:stepper><ui:step title="Account" icon="OK"/></ui:stepper>')
        assert 'OK' in code

    def test_without_an_icon_it_uses_the_number(self):
        code = generate('<ui:stepper><ui:step title="Account"/></ui:stepper>')
        assert '"1. Account"' in code

    def test_the_icon_replaces_the_number(self):
        # The same contract as html: `step.icon if step.icon else str(i + 1)`.
        code = generate('<ui:stepper><ui:step title="Account" icon="OK"/></ui:stepper>')
        assert '"OK. Account"' in code
        assert '"1. Account"' not in code
