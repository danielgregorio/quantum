"""
q:invoke function= silently produced nothing.

The tenth instance of this project's recurring pattern. InvocationService
called `context.get_function(name)` and `context.execute_function(name, args)`
on whatever it was handed — and it was handed ComponentRuntime, which had
NEITHER method. The service dutifully returned "Context does not support
function invocation" and the executor stored that as the result, so the
variable came back as None with no error anywhere.

A second bug underneath it: the executor read `param.default` for each
argument, but the invoke parser stores the value= attribute on `param.value`.
So even once the bridge existed, every argument would have arrived as ''.
"""

import contextlib
import io

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


def _run(src):
    with contextlib.redirect_stdout(io.StringIO()):
        ast = QuantumParser().parse(src)
        rt = ComponentRuntime()
        rt.execute_component(ast)
    return rt


COMPONENT = '''<q:component name="I">
  <q:function name="dobro">
    <q:param name="n" type="number" />
    <q:return value="{{n * 2}}" />
  </q:function>
  <q:function name="soma">
    <q:param name="a" type="number" />
    <q:param name="b" type="number" />
    <q:return value="{{a + b}}" />
  </q:function>
  {invoke}
</q:component>'''


class TestInvokeFunction:
    def test_the_result_reaches_the_variable(self):
        rt = _run(COMPONENT.format(
            invoke='<q:invoke name="r" function="dobro">'
                   '<q:param name="n" value="21" /></q:invoke>'
        ))
        assert rt.execution_context.get_variable("r") == 42

    def test_arguments_come_from_value_not_default(self):
        """The executor read param.default; the parser writes param.value."""
        rt = _run(COMPONENT.format(
            invoke='<q:invoke name="r" function="soma">'
                   '<q:param name="a" value="17" />'
                   '<q:param name="b" value="25" /></q:invoke>'
        ))
        assert rt.execution_context.get_variable("r") == 42

    def test_the_result_metadata_reports_success(self):
        rt = _run(COMPONENT.format(
            invoke='<q:invoke name="r" function="dobro">'
                   '<q:param name="n" value="4" /></q:invoke>'
        ))
        meta = rt.execution_context.get_variable("r_result")
        assert meta["success"] is True
        assert meta["data"] == 8
        assert meta["invocationType"] == "function"

    def test_arguments_can_be_databound(self):
        rt = _run(COMPONENT.format(
            invoke='<q:set name="x" value="6" type="number" />'
                   '<q:invoke name="r" function="dobro">'
                   '<q:param name="n" value="{x}" /></q:invoke>'
        ))
        assert rt.execution_context.get_variable("r") == 12


class TestTheBridgeItself:
    """ComponentRuntime now provides what InvocationService always called."""

    def test_get_function_finds_a_declared_function(self):
        rt = _run(COMPONENT.format(invoke=""))
        assert rt.get_function("dobro") is not None

    def test_get_function_returns_none_for_a_missing_one(self):
        rt = _run(COMPONENT.format(invoke=""))
        assert rt.get_function("naoexiste") is None

    def test_execute_function_reports_failure_instead_of_raising(self):
        rt = _run(COMPONENT.format(invoke=""))
        out = rt.execute_function("naoexiste", {})
        assert out["success"] is False
        assert "not found" in out["error"]["message"]
