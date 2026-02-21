"""
PyClass Executor - Execute q:class statements

Handles inline Python class definitions.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import PyClassNode


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

            # Build class body
            class_body = {}
            exec(node.code, namespace, class_body)

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
