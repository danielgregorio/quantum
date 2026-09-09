"""
PyClass Executor - Execute q:class statements

Handles inline Python class definitions.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.runtime.executors.scripting.python_executor import (
    normalise_python_source,
)
from quantum.core.ast_nodes import PyClassNode


class PyClassExecutor(BaseExecutor):
    """
    Executor for q:class statements.

    Supports:
    - Inline class definition
    - Base class inheritance
    - Decorator application
    """

    @property
    def handles(self) -> List[Type]:
        return [PyClassNode]

    def execute(self, node: PyClassNode, exec_context) -> Any:
        """
        Execute Python class definition.

        Args:
            node: PyClassNode with class configuration
            exec_context: Execution context

        Returns:
            Defined class
        """
        try:
            self.require_python_scripting('q:pyclass')

            context = exec_context.get_all_variables()

            # Build namespace with existing variables
            namespace = dict(context)

            # Resolve base classes
            bases = []
            for base_name in node.bases:
                if base_name in namespace:
                    bases.append(namespace[base_name])
                else:
                    # Try to import/eval the base class
                    try:
                        base = eval(base_name, namespace)
                        bases.append(base)
                    except:
                        raise ExecutorError(f"Base class '{base_name}' not found")

            if not bases:
                bases = [object]

            # Build class body. The source is dedented for the same reason
            # q:python's is: markup-indented code raised "unexpected indent"
            # on line 2, which is every class body written inside XML.
            class_body = {}
            exec(normalise_python_source(node.code), namespace, class_body)

            # Create the class
            cls = type(node.name, tuple(bases), class_body)

            # Apply decorators (in reverse order)
            for decorator_name in reversed(node.decorators):
                if decorator_name in namespace:
                    decorator = namespace[decorator_name]
                else:
                    try:
                        decorator = eval(decorator_name, namespace)
                    except:
                        raise ExecutorError(f"Decorator '{decorator_name}' not found")
                cls = decorator(cls)

            # Store class in context
            exec_context.set_variable(node.name, cls, scope="component")

            return cls

        except Exception as e:
            raise ExecutorError(f"PyClass execution error: {e}")
