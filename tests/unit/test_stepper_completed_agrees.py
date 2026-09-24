"""
The targets disagreed about what `completed` means on a ui:stepper.

The right rule (the html adapter's): the explicit attribute wins; without it,
a step is completed if it is behind the current one. `linear` has nothing to
do with it.

Each target had its own version:

- desktop: `list(range(current)) if linear else []`. On a NON-linear stepper it
  emitted an empty list, and since the bridge runs after the static markup it
  ERASED on boot the marks the html had drawn right. And
  `_as_bool(completed, False)` collapsed "not set" and "set to false", so a
  step with `completed="false"` before the current one got the mark back.
- textual: `set_class(position < index, "q-step-done")` in on_mount,
  overwriting what compose had drawn — `completed` had no effect at all.

Now there is a single function, `completed_step_indices`, and these tests exist
so they do not diverge again: each case is checked on each target (the old
desktop target left in 0.16, UI-8) against the same expectation.
"""

import pathlib
import re
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.ui_builder import UIBuilder
from quantum.runtime.ui_html_adapter import completed_step_indices


def build(body, target):
    source = ('<q:application id="T" type="ui"><ui:window title="t">'
              + body + '</ui:window></q:application>')
    path = pathlib.Path(tempfile.mkdtemp()) / 't.q'
    path.write_text(source, encoding='utf-8')
    app = QuantumParser().parse_file(str(path))
    return UIBuilder().build(app, target=target)


def marked_in_html(body):
    html = build(body, 'html')
    classes = re.findall(r'class="(q-step-item[^"]*)"', html)
    return [i for i, c in enumerate(classes) if 'completed' in c]


def marked_in_textual(body):
    tui = build(body, 'textual')
    classes = re.findall(r'classes="(q-step-indicator[^"]*)"', tui)
    return [i for i, c in enumerate(classes) if 'q-step-done' in c]


CASES = {
    'implicit progress':
        ('<ui:stepper current="2"><ui:step title="A"/><ui:step title="B"/>'
         '<ui:step title="C"/><ui:step title="D"/></ui:stepper>', [0, 1]),
    'non-linear has the same progress':
        ('<ui:stepper current="2" linear="false"><ui:step title="A"/>'
         '<ui:step title="B"/><ui:step title="C"/><ui:step title="D"/>'
         '</ui:stepper>', [0, 1]),
    'an explicit completed=false wins over the position':
        ('<ui:stepper current="2"><ui:step title="A" completed="false"/>'
         '<ui:step title="B"/><ui:step title="C"/></ui:stepper>', [1]),
    'completed=true wins over the position':
        ('<ui:stepper current="0"><ui:step title="A"/>'
         '<ui:step title="B" completed="true"/></ui:stepper>', [1]),
    'the first step, nothing completed':
        ('<ui:stepper current="0"><ui:step title="A"/><ui:step title="B"/>'
         '</ui:stepper>', []),
}


@pytest.mark.parametrize("name", list(CASES))
class TestTheTargetsAgree:
    def test_html(self, name):
        body, expected = CASES[name]
        assert marked_in_html(body) == expected

    def test_textual(self, name):
        body, expected = CASES[name]
        assert marked_in_textual(body) == expected


class TestTheRuleAlone:
    """The shared function, through no adapter at all."""

    class Step:
        def __init__(self, completed=None):
            self.completed = completed

    def test_without_the_attribute_it_uses_the_position(self):
        steps = [self.Step(), self.Step(), self.Step()]
        assert completed_step_indices(steps, 2) == [0, 1]

    def test_an_explicit_true_wins(self):
        steps = [self.Step(), self.Step('true')]
        assert completed_step_indices(steps, 0) == [1]

    def test_an_explicit_false_wins(self):
        steps = [self.Step('false'), self.Step(), self.Step()]
        assert completed_step_indices(steps, 2) == [1]

    def test_it_accepts_a_real_boolean(self):
        steps = [self.Step(True), self.Step(False)]
        assert completed_step_indices(steps, 2) == [0]

    @pytest.mark.parametrize("written", ['true', '1', 'yes', 'on', 'TRUE', ' true '])
    def test_the_written_forms_of_true(self, written):
        assert completed_step_indices([self.Step(written)], 0) == [0]

    @pytest.mark.parametrize("written", ['false', '0', 'no', 'off', 'maybe', ''])
    def test_anything_else_is_false(self, written):
        # An ALLOW list, like UIHtmlAdapter._as_bool. A deny list would treat
        # "maybe" as completed.
        assert completed_step_indices([self.Step(written)], 1) == []

    def test_without_steps(self):
        assert completed_step_indices([], 0) == []
