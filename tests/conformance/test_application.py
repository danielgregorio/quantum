"""Conformance: SPEC.md section 9a (q:application)."""

import os
import pathlib
import subprocess
import sys

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError

REPO = pathlib.Path(__file__).resolve().parents[2]


class TestRemovedTypes:
    @pytest.mark.parametrize('attribute,cited', [
        ('type="html"', 'type="html"'), ('type="api"', 'type="api"'),
        ('type="microservices"', 'type="microservices"'), ('', 'with no type='),
    ])
    def test_parse_refuses_and_points_to_components(self, attribute, cited):
        # APP-1 (were G17: html did not start; G18: api did not run the route)
        with pytest.raises(QuantumParseError) as error:
            QuantumParser().parse(f'<q:application id="app" {attribute} xmlns:q="https://quantum.lang/ns">'
                                  '<q:route path="/" method="GET"><h1>hi</h1></q:route></q:application>')
        message = str(error.value)
        assert cited in message and 'components/' in message and 'quantum start' in message

    def test_quantum_run_exits_with_an_error_and_the_message(self, tmp_path):
        # APP-1
        app = tmp_path / 'app.q'
        app.write_text('<q:application id="app" type="html" xmlns:q="https://quantum.lang/ns">'
                       '<q:route path="/" method="GET"><h1>hi</h1></q:route></q:application>',
                       encoding='utf-8')
        result = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'run', str(app)],
                                capture_output=True, text=True, cwd=tmp_path, timeout=60,
                                env=dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8'))
        assert result.returncode == 1
        assert 'quantum start' in result.stdout + result.stderr
        assert 'Traceback' not in result.stdout + result.stderr

    @pytest.mark.parametrize('type_', ['game', 'terminal', 'ui'])
    def test_the_types_that_remain(self, type_):
        # APP-1
        assert QuantumParser().parse(
            f'<q:application id="a" type="{type_}" xmlns:q="https://quantum.lang/ns"></q:application>'
        ).app_type == type_


class TestRemovedTestingEngine:
    """APP-2: the qtest: engine was removed in 0.22 (decision D-T1)."""

    @staticmethod
    def _refused(source):
        with pytest.raises(QuantumParseError) as error:
            QuantumParser(use_cache=False).parse(source)
        message = str(error.value)
        assert 'removed in Quantum 0.22' in message and '`quantum test`' in message
        return error.value

    def test_type_testing_is_refused(self):
        # APP-2
        error = self._refused('<q:application id="t" type="testing" xmlns:q="https://quantum.lang/ns">'
                              '</q:application>')
        # quantum test exists (TEST-1): the message sends there, not to "a later release"
        assert 'later release' not in str(error)

    def test_a_qtest_tag_is_refused_at_its_line(self):
        # APP-2: anywhere in a file, not only under type="testing".
        error = self._refused('<q:component name="A">\n'
                              '  <p>hi</p>\n'
                              '  <qtest:suite name="s" />\n'
                              '</q:component>')
        assert '<qtest:suite>' in str(error) and error.line == 3

    def test_a_declared_qtest_namespace_is_refused_too(self):
        # APP-2: an author who declared xmlns:qtest gets the same message.
        self._refused('<q:application id="t" type="terminal" xmlns:q="https://quantum.lang/ns" '
                      'xmlns:qtest="https://quantum.lang/testing">'
                      '<qtest:fixture name="f" /></q:application>')

    def test_quantum_run_exits_with_an_error_and_the_message(self, tmp_path):
        # APP-2
        app = tmp_path / 'tests.q'
        app.write_text('<q:application id="t" type="testing" xmlns:q="https://quantum.lang/ns">'
                       '<qtest:suite name="s" /></q:application>', encoding='utf-8')
        result = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'run', str(app)],
                                capture_output=True, text=True, cwd=tmp_path, timeout=60,
                                env=dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8'))
        output = result.stdout + result.stderr
        assert result.returncode == 1
        assert 'removed in Quantum 0.22' in output and 'Traceback' not in output
