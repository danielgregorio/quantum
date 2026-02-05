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

        # Phase F: Scope support (session/application/request)
        # Session vars are shared globally (user-specific, persistent)
        if parent is None:
            self.session_vars: Dict[str, Any] = {}
            self.application_vars: Dict[str, Any] = {}  # Global state
            self.request_vars: Dict[str, Any] = {}  # Request-scoped
        else:
            self.session_vars = parent.session_vars
            self.application_vars = parent.application_vars
            self.request_vars = parent.request_vars

    def set_variable(self, name: str, value: Any, scope: str = "local"):
        """
        Set a variable in the specified scope

        Phase F: Supports session.variable, application.variable, request.variable syntax

        Args:
            name: Variable name (can include scope prefix like "session.userId")
            value: Variable value
            scope: 'local', 'function', 'component', 'session', 'application', or 'request'
        """
        # Phase F: Parse scope prefix from variable name
        if '.' in name:
            prefix, var_name = name.split('.', 1)
            if prefix in ['session', 'application', 'request', 'cookie']:
                if prefix == 'session':
                    self.session_vars[var_name] = value
                elif prefix == 'application':
                    self.application_vars[var_name] = value
                elif prefix == 'request':
                    self.request_vars[var_name] = value
                elif prefix == 'cookie':
                    # Store in session with cookie prefix for now
                    self.session_vars[f'__cookie_{var_name}'] = value
                return

        # Normal scope handling
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
        elif scope == "application":
            self.application_vars[name] = value
        elif scope == "request":
            self.request_vars[name] = value
        else:
            raise ValueError(f"Invalid scope: {scope}")

    def update_variable(self, name: str, value: Any):
        """
        Update a variable in whatever scope it already exists, or create in local scope if new

        Args:
            name: Variable name (can include scope prefix like "session.userId", "application.messages")
            value: New value
        """
        # Handle scope prefix (session.X, application.X, request.X)
        if '.' in name:
            prefix, var_name = name.split('.', 1)
            if prefix in ['session', 'application', 'request', 'cookie']:
                if prefix == 'session':
                    self.session_vars[var_name] = value
                elif prefix == 'application':
                    self.application_vars[var_name] = value
                elif prefix == 'request':
                    self.request_vars[var_name] = value
                elif prefix == 'cookie':
                    self.session_vars[f'__cookie_{var_name}'] = value
                return

        # Check local scope first
        if name in self.local_vars:
            self.local_vars[name] = value
            return

        # Check function scope
        if name in self.function_vars:
            self.function_vars[name] = value
            return

        # Check component scope (including parent contexts)
        ctx = self
        while ctx:
            if name in ctx.component_vars:
                ctx.component_vars[name] = value
                return
            ctx = ctx.parent

        # Check session scope
        if name in self.session_vars:
            self.session_vars[name] = value
            return

        # Variable doesn't exist - create in local scope
        self.local_vars[name] = value

    def get_variable(self, name: str) -> Any:
        """
        Get a variable value, searching through scopes in order:
        local -> function -> component -> session -> application -> request -> parent

        Phase F: Supports session.variable, application.variable, request.variable syntax

        Args:
            name: Variable name (can include scope prefix like "session.userId")

        Returns:
            Variable value

        Raises:
            VariableNotFoundError: If variable not found in any scope
        """
        # Phase F: Parse scope prefix from variable name
        if '.' in name:
            prefix, var_name = name.split('.', 1)
            if prefix in ['session', 'application', 'request', 'cookie']:
                if prefix == 'session':
                    return self.session_vars.get(var_name, '')
                elif prefix == 'application':
                    return self.application_vars.get(var_name, '')
                elif prefix == 'request':
                    return self.request_vars.get(var_name, '')
                elif prefix == 'cookie':
                    return self.session_vars.get(f'__cookie_{var_name}', '')

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

        # Search application scope
        if name in self.application_vars:
            return self.application_vars[name]

        # Search request scope
        if name in self.request_vars:
            return self.request_vars[name]

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

        Phase F: Also includes scoped variables with dot notation (session.variable, application.variable, request.variable)
        """
        all_vars = {}

        # Start with parent vars (if any)
        if self.parent:
            all_vars.update(self.parent.get_all_variables())

        # Phase F: Add session vars (both direct and with scope prefix)
        all_vars.update(self.session_vars)
        for key, value in self.session_vars.items():
            all_vars[f'session.{key}'] = value

        # Phase F: Add application vars (both direct and with scope prefix)
        all_vars.update(self.application_vars)
        for key, value in self.application_vars.items():
            all_vars[f'application.{key}'] = value

        # Phase F: Add request vars (both direct and with scope prefix)
        all_vars.update(self.request_vars)
        for key, value in self.request_vars.items():
            all_vars[f'request.{key}'] = value

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
