"""
q:python and q:class could not run indented code — which is all of it.

The source inside the tag is indented to match the surrounding markup. It was
passed through `.strip()`, which removes the leading whitespace of the STRING,
so the first line lost its indentation and every other line kept it. Python
answered "unexpected indent (<string>, line 2)".

That is not an edge case: `examples/python-data-processing.q`, the shipped
demonstration of the feature, died on its first q:class. Reproduced by running
it, which is also how the two bugs behind it turned up — q.info() did not
exist, so it resolved to None and the block died on "'NoneType' object is not
callable" with nothing naming `info`.
"""

import logging

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.executors.scripting.python_executor import (
    QuantumBridge, normalise_python_source,
)


class TestNormaliseSource:
    def test_uniformly_indented_code_is_dedented(self):
        raw = "\n    total = 0\n    for i in range(3):\n        total += i\n"
        assert normalise_python_source(raw).startswith("total = 0")
        compile(normalise_python_source(raw), "<t>", "exec")

    def test_code_that_starts_on_the_tag_line_also_compiles(self):
        raw = "total = 0\n    total += 1\n"
        compile(normalise_python_source(raw), "<t>", "exec")

    def test_already_flush_code_is_untouched(self):
        raw = "a = 1\nb = 2\n"
        assert normalise_python_source(raw) == "a = 1\nb = 2"

    def test_nested_blocks_keep_their_relative_indentation(self):
        raw = (
            "\n    if True:\n"
            "        x = 1\n"
            "    else:\n"
            "        x = 2\n"
        )
        namespace = {}
        exec(normalise_python_source(raw), namespace)
        assert namespace["x"] == 1

    def test_windows_line_endings(self):
        raw = "\r\n    a = 1\r\n    b = 2\r\n"
        namespace = {}
        exec(normalise_python_source(raw), namespace)
        assert (namespace["a"], namespace["b"]) == (1, 2)

    def test_empty_source_is_empty(self):
        assert normalise_python_source("") == ""
        assert normalise_python_source("   \n  \n") == ""

    def test_genuinely_broken_code_still_raises_on_execution(self):
        # The helper must not paper over a real syntax error.
        with pytest.raises(SyntaxError):
            compile(normalise_python_source("\n    def (:\n"), "<t>", "exec")


def run(source, **params):
    # python_scripting agora vem DESLIGADO por padrao. Estes testes rodam
    # porque o quantum.config.yaml deste repositorio o liga explicitamente, e
    # ComponentRuntime() sem config le esse arquivo. Se um dia ele parar de
    # ligar, estes testes falham com a mensagem de recusa — que e o
    # comportamento certo, nao um teste quebrado.
    node = QuantumParser().parse(source)
    runtime = ComponentRuntime()
    runtime.execute_component(node, params)
    return runtime.execution_context.get_all_variables()


class TestIndentedPythonRuns:
    def test_a_multi_line_block_executes(self):
        variables = run('''<q:component name="C">
  <q:python>
    total = 0
    for i in range(5):
        total += i
    q.soma = total
  </q:python>
</q:component>''')
        assert variables["soma"] == 10

    def test_an_indented_class_body_executes(self):
        variables = run('''<q:component name="C">
  <q:class name="Contador">
      def __init__(self):
          self.n = 0

      def somar(self, k):
          self.n += k
          return self.n
  </q:class>
  <q:python>
    c = Contador()
    c.somar(3)
    q.total = c.somar(4)
  </q:python>
</q:component>''')
        assert variables["total"] == 7


class TestTheBridgeLogs:
    def test_info_logs_instead_of_raising(self, caplog):
        bridge = QuantumBridge(None, {})
        with caplog.at_level(logging.INFO):
            bridge.info("processando", 10, "registros")
        assert "processando 10 registros" in caplog.text

    def test_the_other_levels_exist(self):
        bridge = QuantumBridge(None, {})
        for method in ("log", "debug", "warn", "warning", "error"):
            assert callable(getattr(bridge, method)), method

    def test_reading_a_variable_still_works(self):
        bridge = QuantumBridge(None, {"nome": "quantum"})
        assert bridge.nome == "quantum"

    def test_an_unknown_name_is_still_none_but_says_so(self, caplog):
        bridge = QuantumBridge(None, {})
        with caplog.at_level(logging.WARNING):
            assert bridge.nao_existe is None
        assert "nao_existe" in caplog.text

    def test_it_complains_once_per_name(self, caplog):
        bridge = QuantumBridge(None, {})
        with caplog.at_level(logging.WARNING):
            for _ in range(5):
                bridge.nao_existe
        assert caplog.text.count("nao_existe") == 1

    def test_assignment_still_exports(self):
        bridge = QuantumBridge(None, {})
        bridge.resultado = 42
        assert bridge._exports == {"resultado": 42}
