"""
Quantum Execution Context - Manages variable scopes and state
"""

from typing import Any, Dict, Optional, List


class VariableNotFoundError(Exception):
    """Raised when a variable is not found in any scope"""
    pass


class ExecutionContext:
    """
    Manages execution context with nested scopes for variables
    Supports: local, function, component, and session scopes
    """

    def __init__(self, parent: Optional['ExecutionContext'] = None):
        self.parent = parent
        self.local_vars: Dict[str, Any] = {}
        self.function_vars: Dict[str, Any] = {}
        self.component_vars: Dict[str, Any] = {}
        # Session vars are shared globally (for future use)
        if parent is None:
            self.session_vars: Dict[str, Any] = {}
        else:
            self.session_vars = parent.session_vars

    def set_variable(self, name: str, value: Any, scope: str = "local"):
        """
        Set a variable in the specified scope

        Args:
            name: Variable name
            value: Variable value
            scope: 'local', 'function', 'component', or 'session'
        """
        if scope == "local":
            self.local_vars[name] = value
        elif scope == "function":
            self.function_vars[name] = value
        elif scope == "component":
            # Set in root component context
            ctx = self._get_root_context()
            ctx.component_vars[name] = value
        elif scope == "session":
            # Set in session (shared globally)
            self.session_vars[name] = value
        else:
            raise ValueError(f"Invalid scope: {scope}")

    def get_variable(self, name: str) -> Any:
        """
        Get a variable value, searching through scopes in order:
        local -> function -> component -> session -> parent

        Args:
            name: Variable name

        Returns:
            Variable value

        Raises:
            VariableNotFoundError: If variable not found in any scope
        """
        # Search local scope first
        if name in self.local_vars:
            return self.local_vars[name]

        # Search function scope
        if name in self.function_vars:
            return self.function_vars[name]

        # Search component scope (go to root)
        root_ctx = self._get_root_context()
        if name in root_ctx.component_vars:
            return root_ctx.component_vars[name]

        # Search session scope
        if name in self.session_vars:
            return self.session_vars[name]

        # Search parent context
        if self.parent:
            try:
                return self.parent.get_variable(name)
            except VariableNotFoundError:
                pass

        raise VariableNotFoundError(f"Variable '{name}' not found in any scope")

    def has_variable(self, name: str) -> bool:
        """Check if variable exists in any scope"""
        try:
            self.get_variable(name)
            return True
        except VariableNotFoundError:
            return False

    def delete_variable(self, name: str, scope: str = "local") -> bool:
        """
        Delete a variable from the specified scope

        Args:
            name: Variable name
            scope: 'local', 'function', 'component', or 'session'

        Returns:
            True if deleted, False if not found
        """
        if scope == "local":
            if name in self.local_vars:
                del self.local_vars[name]
                return True
        elif scope == "function":
            if name in self.function_vars:
                del self.function_vars[name]
                return True
        elif scope == "component":
            root_ctx = self._get_root_context()
            if name in root_ctx.component_vars:
                del root_ctx.component_vars[name]
                return True
        elif scope == "session":
            if name in self.session_vars:
                del self.session_vars[name]
                return True

        return False

    def create_child_context(self) -> 'ExecutionContext':
        """Create a child context (for nested scopes like loops/functions)"""
        return ExecutionContext(parent=self)

    def get_all_variables(self) -> Dict[str, Any]:
        """
        Get all variables from all scopes as a flat dictionary
        (for backward compatibility with existing code)
        """
        all_vars = {}

        # Start with parent vars (if any)
        if self.parent:
            all_vars.update(self.parent.get_all_variables())

        # Add session vars
        all_vars.update(self.session_vars)

        # Add component vars
        root_ctx = self._get_root_context()
        all_vars.update(root_ctx.component_vars)

        # Add function vars
        all_vars.update(self.function_vars)

        # Add local vars (highest priority)
        all_vars.update(self.local_vars)

        return all_vars

    def _get_root_context(self) -> 'ExecutionContext':
        """Get the root (component-level) context"""
        ctx = self
        while ctx.parent is not None:
            ctx = ctx.parent
        return ctx

    def __repr__(self) -> str:
        return (f"ExecutionContext(local={len(self.local_vars)}, "
                f"function={len(self.function_vars)}, "
                f"component={len(self.component_vars)}, "
                f"session={len(self.session_vars)})")
