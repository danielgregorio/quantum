"""
Base Code Generator
===================

Abstract base class for all code generators (Python, JavaScript, etc.)
Uses visitor pattern to traverse AST and generate code.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ast_nodes import (
    QuantumNode, ComponentNode, ApplicationNode, SetNode, LoopNode,
    IfNode, FunctionNode, HTMLNode, TextNode, QueryNode, ActionNode,
    ImportNode, SlotNode, ComponentCallNode, PythonNode, PyImportNode,
    RedirectNode, FlashNode, DocTypeNode, CommentNode, QueryParamNode
)


@dataclass
class Scope:
    """Represents a variable scope."""
    variables: Dict[str, str] = field(default_factory=dict)  # name -> type hint
    parent: Optional['Scope'] = None

    def declare(self, name: str, type_hint: str = 'Any'):
        """Declare a variable in this scope."""
        self.variables[name] = type_hint

    def lookup(self, name: str) -> Optional[str]:
        """Look up a variable, checking parent scopes."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def is_declared(self, name: str) -> bool:
        """Check if variable is declared in any scope."""
        return self.lookup(name) is not None


@dataclass
class GeneratorContext:
    """Context for code generation."""
    component_name: str = ''
    function_name: str = ''
    in_loop: bool = False
    in_conditional: bool = False
    in_html: bool = False
    imports: Set[str] = field(default_factory=set)
    functions: List[str] = field(default_factory=list)
    html_var: str = '_html'


class CodeGenerator(ABC):
    """
    Abstract base class for code generators.

    Implements visitor pattern for AST traversal and provides
    common utilities for code emission and scope management.
    """

    def __init__(self):
        self.indent_level: int = 0
        self.indent_str: str = "    "
        self.output_lines: List[str] = []
        self.scope: Scope = Scope()
        self.context: GeneratorContext = GeneratorContext()
        self._visitor_cache: Dict[str, callable] = {}

    # =========================================================================
    # Abstract methods - must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for this generator."""
        pass

    @abstractmethod
    def generate_header(self) -> str:
        """Generate file header (imports, comments, etc.)"""
        pass

    @abstractmethod
    def generate_footer(self) -> str:
        """Generate file footer."""
        pass

    @abstractmethod
    def transpile_expression(self, expr: str) -> str:
        """Transpile a Quantum expression to target language."""
        pass

    # =========================================================================
    # Core generation methods
    # =========================================================================

    def generate(self, node: QuantumNode) -> str:
        """
        Generate code for an AST node and return the complete output.

        Args:
            node: The root AST node to generate code for

        Returns:
            Complete generated source code as a string
        """
        self.output_lines = []
        self.indent_level = 0
        self.scope = Scope()
        self.context = GeneratorContext()

        # Generate header
        header = self.generate_header()
        if header:
            self.output_lines.append(header)

        # Visit the AST
        self.visit(node)

        # Generate footer
        footer = self.generate_footer()
        if footer:
            self.output_lines.append(footer)

        return '\n'.join(self.output_lines)

    def visit(self, node: QuantumNode) -> Optional[str]:
        """
        Visit an AST node using the visitor pattern.

        Dispatches to visit_NodeType method based on node class.

        Args:
            node: The AST node to visit

        Returns:
            Optional string result from the visitor
        """
        if node is None:
            return None

        node_type = type(node).__name__

        # Check cache first
        if node_type not in self._visitor_cache:
            method_name = f'visit_{node_type}'
            visitor = getattr(self, method_name, None)
            self._visitor_cache[node_type] = visitor

        visitor = self._visitor_cache[node_type]

        if visitor:
            return visitor(node)
        else:
            return self.generic_visit(node)

    def generic_visit(self, node: QuantumNode) -> Optional[str]:
        """
        Fallback visitor for unhandled node types.

        Override in subclass to provide custom fallback behavior.
        """
        node_type = type(node).__name__
        self.emit_comment(f"TODO: Unhandled node type: {node_type}")

        # Try to visit children if they exist
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self.visit(child)

        return None

    def visit_children(self, node: QuantumNode) -> List[Optional[str]]:
        """Visit all children of a node."""
        results = []
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                result = self.visit(child)
                results.append(result)
        return results

    # =========================================================================
    # Code emission utilities
    # =========================================================================

    def emit(self, code: str):
        """
        Emit a line of code with proper indentation.

        Args:
            code: The code to emit (without leading indentation)
        """
        if code:
            indent = self.indent_str * self.indent_level
            self.output_lines.append(f"{indent}{code}")
        else:
            self.output_lines.append('')

    def emit_raw(self, code: str):
        """Emit code without any indentation."""
        self.output_lines.append(code)

    def emit_blank(self):
        """Emit a blank line."""
        self.output_lines.append('')

    def emit_comment(self, comment: str):
        """Emit a comment (format depends on target language)."""
        # Default to Python-style comments
        self.emit(f"# {comment}")

    def emit_block(self, lines: List[str]):
        """Emit multiple lines with current indentation."""
        for line in lines:
            self.emit(line)

    # =========================================================================
    # Indentation management
    # =========================================================================

    def indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indentation level."""
        self.indent_level = max(0, self.indent_level - 1)

    class indented:
        """Context manager for indented blocks."""

        def __init__(self, generator: 'CodeGenerator'):
            self.generator = generator

        def __enter__(self):
            self.generator.indent()
            return self

        def __exit__(self, *args):
            self.generator.dedent()

    # =========================================================================
    # Scope management
    # =========================================================================

    def push_scope(self):
        """Enter a new variable scope."""
        self.scope = Scope(parent=self.scope)

    def pop_scope(self):
        """Exit current scope and return to parent."""
        if self.scope.parent:
            self.scope = self.scope.parent

    def declare_var(self, name: str, type_hint: str = 'Any'):
        """Declare a variable in current scope."""
        self.scope.declare(name, type_hint)

    def is_declared(self, name: str) -> bool:
        """Check if variable is declared in any visible scope."""
        return self.scope.is_declared(name)

    class scoped:
        """Context manager for scoped blocks."""

        def __init__(self, generator: 'CodeGenerator'):
            self.generator = generator

        def __enter__(self):
            self.generator.push_scope()
            return self

        def __exit__(self, *args):
            self.generator.pop_scope()

    # =========================================================================
    # Expression utilities
    # =========================================================================

    def extract_expression(self, value: str) -> str:
        """
        Extract expression from Quantum {expr} format.

        Args:
            value: Value that may contain {expression}

        Returns:
            The expression without braces, or original if no braces
        """
        if not value:
            return ''

        value = str(value).strip()

        if value.startswith('{') and value.endswith('}'):
            return value[1:-1].strip()

        return value

    def is_expression(self, value: str) -> bool:
        """Check if value is a Quantum expression {expr}."""
        if not value:
            return False
        value = str(value).strip()
        return value.startswith('{') and value.endswith('}')

    def is_literal(self, value: str) -> bool:
        """Check if value is a literal (number, string, boolean)."""
        if not value:
            return False

        value = str(value).strip()

        # Check for numeric
        try:
            float(value)
            return True
        except ValueError:
            pass

        # Check for boolean
        if value.lower() in ('true', 'false'):
            return True

        # Check for quoted string
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return True

        return False

    # =========================================================================
    # Helper methods
    # =========================================================================

    def sanitize_identifier(self, name: str) -> str:
        """
        Sanitize a name to be a valid identifier.

        Args:
            name: The name to sanitize

        Returns:
            A valid identifier string
        """
        import re
        # Replace invalid characters with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure doesn't start with number
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized or '_unnamed'

    def generate_temp_var(self, prefix: str = '_temp') -> str:
        """Generate a unique temporary variable name."""
        if not hasattr(self, '_temp_counter'):
            self._temp_counter = 0
        self._temp_counter += 1
        return f"{prefix}_{self._temp_counter}"
