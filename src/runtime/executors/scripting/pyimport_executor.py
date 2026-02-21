"""
PyImport Executor - Execute q:pyimport statements

Handles Python module imports.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import PyImportNode


class PyImportExecutor(BaseExecutor):
    """
    Executor for q:pyimport statements.

    Supports:
    - Module import with alias
    - Specific name imports (from X import Y)
    - Star imports (from X import *)
    """

    @property
    def handles(self) -> List[Type]:
        return [PyImportNode]

    def execute(self, node: PyImportNode, exec_context) -> Any:
        """
        Execute Python import.

        Args:
            node: PyImportNode with import configuration
            exec_context: Execution context

        Returns:
            Imported module or names
        """
        try:
            import importlib

            # Import the module
            module = importlib.import_module(node.module)

            # Handle different import styles
            if node.alias:
                # import X as Y
                exec_context.set_variable(node.alias, module, scope="component")
                return module

            elif node.names:
                # from X import Y, Z
                imported = {}
                for name in node.names:
                    name = name.strip()
                    if name == '*':
                        # Import all public names
                        for attr_name in dir(module):
                            if not attr_name.startswith('_'):
                                attr = getattr(module, attr_name)
                                exec_context.set_variable(attr_name, attr, scope="component")
                                imported[attr_name] = attr
                    else:
                        attr = getattr(module, name)
                        exec_context.set_variable(name, attr, scope="component")
                        imported[name] = attr
                return imported

            else:
                # import X
                # Use last part of module name
                module_name = node.module.split('.')[-1]
                exec_context.set_variable(module_name, module, scope="component")
                return module

        except ImportError as e:
            raise ExecutorError(f"Import error: Cannot import '{node.module}': {e}")
        except AttributeError as e:
            raise ExecutorError(f"Import error: Module '{node.module}' has no attribute: {e}")
        except Exception as e:
            raise ExecutorError(f"PyImport execution error: {e}")
