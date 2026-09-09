"""
Python Executor - Execute q:python statements

Handles embedded Python code execution.
"""

import logging
import textwrap
from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import PythonNode

logger = logging.getLogger(__name__)


def normalise_python_source(raw: str) -> str:
    """Make XML-indented Python compile.

    The code inside <q:python> is indented to match the surrounding markup,
    which is what anyone writing XML does:

        <q:python>
          total = 0
          for i in range(5):
              total += i
        </q:python>

    This was passed through `.strip()`, which removes the leading whitespace
    of the string — so the FIRST line lost its indentation and every other
    line kept it. Python then said "unexpected indent (<string>, line 2)".
    Every multi-line q:python block in the documentation fails that way.

    Strategy: try the candidate forms in order and take the first that
    compiles. The current behaviour is tried first, so nothing that worked
    before changes; dedent covers the ordinary case; and dedenting the tail
    separately covers code that starts on the tag's own line.
    """
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ""

    candidates = [text.strip(), textwrap.dedent(text).strip("\n")]

    lines = text.split("\n")
    if lines and lines[0].strip() and len(lines) > 1:
        tail = textwrap.dedent("\n".join(lines[1:]))
        candidates.append((lines[0].strip() + "\n" + tail).strip("\n"))

    for candidate in candidates:
        try:
            compile(candidate, "<q:python>", "exec")
            return candidate
        except SyntaxError:
            continue

    # None compile: the code is genuinely broken. Hand back the dedented
    # form, so the error the user sees points at their code rather than at
    # indentation this function should have handled.
    return candidates[1]


class PythonExecutor(BaseExecutor):
    """
    Executor for q:python statements.

    Supports:
    - Inline Python code execution
    - Component, isolated, and module scopes
    - Async execution
    - Timeout limits
    - Bridge object for context access
    """

    @property
    def handles(self) -> List[Type]:
        return [PythonNode]

    def execute(self, node: PythonNode, exec_context) -> Any:
        """
        Execute Python code block.

        Args:
            node: PythonNode with Python code
            exec_context: Execution context

        Returns:
            Execution result (if result attribute set)
        """
        try:
            self.require_python_scripting('q:python')

            context = exec_context.get_all_variables()

            # Build bridge object for q.variable access
            bridge = QuantumBridge(exec_context, context)

            # Build execution namespace
            namespace = {
                'q': bridge,
                '__quantum_context__': context
            }

            # Add component scope variables if not isolated
            if node.scope == 'component':
                namespace.update(context)

            # Execute code (dedented — see normalise_python_source)
            code = normalise_python_source(node.code)

            if node.async_mode:
                result = self._execute_async(code, namespace, node.timeout)
            else:
                result = self._execute_sync(code, namespace, node.timeout)

            # Store result if requested
            if node.result:
                exec_context.set_variable(node.result, result, scope="component")

            # Export bridge changes to context
            for key, value in bridge._exports.items():
                exec_context.set_variable(key, value, scope="component")

            return result

        except Exception as e:
            raise ExecutorError(f"Python execution error: {e}")

    def _execute_sync(self, code: str, namespace: Dict, timeout: str = None) -> Any:
        """Execute Python code synchronously."""
        # Handle return statements
        if 'return ' in code:
            # Wrap in function
            wrapped = f"def __quantum_exec__():\n"
            for line in code.split('\n'):
                wrapped += f"    {line}\n"
            wrapped += "__quantum_result__ = __quantum_exec__()"
            exec(wrapped, namespace)
            return namespace.get('__quantum_result__')
        else:
            exec(code, namespace)
            return None

    def _execute_async(self, code: str, namespace: Dict, timeout: str = None) -> Any:
        """Execute Python code asynchronously."""
        import asyncio

        async def run_async():
            # Wrap in async function
            wrapped = f"async def __quantum_async__():\n"
            for line in code.split('\n'):
                wrapped += f"    {line}\n"
            exec(wrapped, namespace)
            return await namespace['__quantum_async__']()

        # Parse timeout
        timeout_seconds = None
        if timeout:
            timeout_seconds = self._parse_timeout(timeout)

        return asyncio.run(asyncio.wait_for(run_async(), timeout=timeout_seconds))

    def _parse_timeout(self, timeout: str) -> float:
        """Parse timeout string to seconds."""
        if timeout.endswith('s'):
            return float(timeout[:-1])
        elif timeout.endswith('m'):
            return float(timeout[:-1]) * 60
        elif timeout.endswith('h'):
            return float(timeout[:-1]) * 3600
        return float(timeout)


class QuantumBridge:
    """Bridge object for accessing Quantum context from Python."""

    def __init__(self, exec_context, context: Dict[str, Any]):
        self._exec_context = exec_context
        self._context = context
        self._exports = {}
        self._missing_reported = set()

    def __getattr__(self, name: str) -> Any:
        """Get variable from context.

        A name that is not in the context returns None, as before — scripts
        do test optional variables. But it now says so once: `q.info(...)`
        in the shipped example resolved to None and then raised
        "'NoneType' object is not callable" four frames away, with nothing
        naming `info`. (q.info exists now; the diagnosis should still work
        for the next typo.)
        """
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if name not in self._context:
            if name not in self._missing_reported:
                self._missing_reported.add(name)
                logger.warning(
                    "q:python read q.%s, which is not defined in the "
                    "component — it is None. Calling it raises "
                    "\"'NoneType' object is not callable\".", name
                )
        return self._context.get(name)

    # -- logging from a script --------------------------------------------
    #
    # The documented example calls q.info(...). There was no such method, so
    # it resolved to None through __getattr__ above and the whole block died
    # on the call. These are what that example always meant.

    def log(self, *parts: Any) -> None:
        """Log at info level."""
        logger.info("q:python: %s", " ".join(str(p) for p in parts))

    def info(self, *parts: Any) -> None:
        self.log(*parts)

    def debug(self, *parts: Any) -> None:
        logger.debug("q:python: %s", " ".join(str(p) for p in parts))

    def warn(self, *parts: Any) -> None:
        logger.warning("q:python: %s", " ".join(str(p) for p in parts))

    warning = warn

    def error(self, *parts: Any) -> None:
        logger.error("q:python: %s", " ".join(str(p) for p in parts))

    def __setattr__(self, name: str, value: Any):
        """Set variable in context."""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._exports[name] = value

    def export(self, name: str, value: Any):
        """Explicitly export a variable."""
        self._exports[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        """Get variable with default."""
        return self._context.get(name, default)

    def set(self, name: str, value: Any):
        """Set variable."""
        self._exports[name] = value

    def has(self, name: str) -> bool:
        """Check if variable exists."""
        return name in self._context
