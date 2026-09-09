"""
Security policy tests for in-process Python scripting.

q:python / q:pyclass / q:pyimport run arbitrary Python in the server process
with no sandbox — full access to os, filesystem and network. The 2026-09
audit flagged this as the blocker for any feature that would let an LLM
generate or choose template content (see FULL_AUDIT_2026-09.md, Cluster B,
and AUDIT_FIX_PLAN.md Fase 4).

An allowlist was rejected: the real examples import json, csv, collections,
statistics and functools, so any allowlist permissive enough to keep them
working would not be a meaningful boundary. The control that matters is
whether the code reaching exec() was written by the application author, so
the policy is a switch, not a fake sandbox.
"""

import pytest

from quantum.runtime.component import ComponentRuntime
from quantum.runtime.executors.base import ExecutorError
from quantum.core.ast_nodes import PythonNode, PyImportNode


def _runtime(enabled: bool) -> ComponentRuntime:
    return ComponentRuntime(config={'security': {'python_scripting': enabled}})


class TestPolicyDefault:
    def test_this_repository_enables_it_in_its_own_config(self):
        # Este teste se chamava `test_enabled_by_default` e afirmava que o
        # DEFAULT era ligado. Depois da inversao ele continuaria passando —
        # nao pelo default, mas porque o quantum.config.yaml deste
        # repositorio liga explicitamente (os exemplos usam q:python). Um
        # teste que passa pelo motivo errado e pior que um que falha.
        # O default de verdade esta em TestTheDefaultIsOff.
        runtime = ComponentRuntime()
        assert runtime.services.python_scripting_enabled is True, (
            "o quantum.config.yaml deste repo deveria ligar o scripting")

    def test_explicit_true_is_enabled(self):
        assert _runtime(True).services.python_scripting_enabled is True

    def test_explicit_false_is_disabled(self):
        assert _runtime(False).services.python_scripting_enabled is False


class TestPolicyEnforcement:
    def test_python_runs_when_enabled(self):
        runtime = _runtime(True)
        # q.<name> is the documented export bridge back into Quantum scope
        node = PythonNode(code="q.result = 1 + 1")

        runtime.executor_registry.execute(node, runtime.execution_context)

        assert runtime.execution_context.get_variable("result") == 2

    def test_python_refused_when_disabled(self):
        runtime = _runtime(False)
        node = PythonNode(code="import os; os.getcwd()")

        with pytest.raises(ExecutorError, match="security.python_scripting"):
            runtime.executor_registry.execute(node, runtime.execution_context)

    def test_pyimport_refused_when_disabled(self):
        runtime = _runtime(False)
        node = PyImportNode(module="os")

        with pytest.raises(ExecutorError, match="security.python_scripting"):
            runtime.executor_registry.execute(node, runtime.execution_context)

    def test_refusal_message_explains_why(self):
        runtime = _runtime(False)
        node = PythonNode(code="pass")

        with pytest.raises(ExecutorError) as exc:
            runtime.executor_registry.execute(node, runtime.execution_context)

        message = str(exc.value)
        assert "no sandbox" in message
        assert "q:python" in message


class TestTheSwitchCannotBeWalkedAround:
    """security.python_scripting was bypassable through q:action.

    ActionHandler._execute_python runs a q:python block with its own exec(),
    mirroring PythonExecutor — but it never checked the flag the executors
    check. So an operator who set python_scripting: false to stop in-process
    Python execution was still executing it, as long as the block sat inside a
    q:action. A security switch that does not switch everything off is worse
    than no switch, because the operator believes they are covered.

    Found by an independent verification pass over this session's claims, not
    by the tests written alongside the switch.
    """

    @staticmethod
    def _run(enabled):
        from quantum.core.ast_nodes import PythonNode
        from quantum.runtime.action_handler import ActionHandler
        from quantum.runtime.component import ComponentRuntime, ComponentExecutionError
        from quantum.runtime.execution_context import ExecutionContext

        runtime = ComponentRuntime(config={'security': {'python_scripting': enabled}})
        handler = ActionHandler(runtime)
        node = PythonNode(code="executed = True")
        try:
            handler._execute_python(node, ExecutionContext())
            return 'ran'
        except ComponentExecutionError as exc:
            return str(exc)

    def test_disabled_blocks_python_inside_an_action(self):
        result = self._run(False)
        assert 'disabled' in result
        assert 'python_scripting' in result

    def test_enabled_still_allows_it(self):
        assert self._run(True) == 'ran'


class TestTheDefaultIsOff:
    """O default era LIGADO — a ultima falha-aberta de configuracao.

    Executar um `.q` que voce nao escreveu significava executar o Python
    dele, sem sandbox, no seu processo. Um default precisa ser seguro para
    quem nao leu a documentacao; quem usa q:python leu, porque teve de
    escrever a tag.
    """

    def test_no_configuration_means_off(self):
        from quantum.runtime.service_container import ServiceContainer
        assert ServiceContainer(config={}).python_scripting_enabled is False

    def test_a_config_without_the_security_block_means_off(self):
        from quantum.runtime.service_container import ServiceContainer
        services = ServiceContainer(config={'datasources': {}})
        assert services.python_scripting_enabled is False

    def test_an_empty_security_block_means_off(self):
        from quantum.runtime.service_container import ServiceContainer
        services = ServiceContainer(config={'security': {}})
        assert services.python_scripting_enabled is False

    def test_true_turns_it_on(self):
        from quantum.runtime.service_container import ServiceContainer
        services = ServiceContainer(config={'security': {'python_scripting': True}})
        assert services.python_scripting_enabled is True

    def test_false_stays_off(self):
        from quantum.runtime.service_container import ServiceContainer
        services = ServiceContainer(config={'security': {'python_scripting': False}})
        assert services.python_scripting_enabled is False

    def test_the_environment_variable_turns_it_on(self, monkeypatch):
        from quantum.runtime.service_container import ServiceContainer
        monkeypatch.setenv('QUANTUM_PYTHON_SCRIPTING', '1')
        assert ServiceContainer(config={}).python_scripting_enabled is True

    def test_the_config_wins_over_the_environment(self, monkeypatch):
        # Um arquivo versionado que diz `false` nao pode ser anulado por uma
        # variavel de ambiente esquecida no shell.
        from quantum.runtime.service_container import ServiceContainer
        monkeypatch.setenv('QUANTUM_PYTHON_SCRIPTING', '1')
        services = ServiceContainer(config={'security': {'python_scripting': False}})
        assert services.python_scripting_enabled is False

    def test_the_refusal_says_how_to_enable_it(self):
        from quantum.core.ast_nodes import PythonNode
        runtime = _runtime(False)
        with pytest.raises(ExecutorError) as exc:
            runtime.executor_registry.execute(PythonNode(code="pass"),
                                              runtime.execution_context)
        message = str(exc.value)
        assert "python_scripting: true" in message
        assert "QUANTUM_PYTHON_SCRIPTING" in message
