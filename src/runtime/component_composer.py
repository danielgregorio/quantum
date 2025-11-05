"""
Quantum Component Composer

Phase 2: Component Composition
Orchestrates component rendering with props and slots.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import (
    ComponentNode, ComponentCallNode, SlotNode, QuantumNode,
    HTMLNode, TextNode, ImportNode
)
from runtime.component_resolver import ComponentResolver, ComponentNotFoundError
from runtime.component import ComponentRuntime
from runtime.execution_context import ExecutionContext
from runtime.renderer import HTMLRenderer


class ComponentComposer:
    """
    Composes components with props and slots.

    Phase 2: Component Composition

    Responsibilities:
    - Load child components
    - Pass props from parent to child
    - Inject slot content
    - Render composed output
    """

    def __init__(self, resolver: ComponentResolver):
        self.resolver = resolver

    def compose(
        self,
        component_call: ComponentCallNode,
        parent_context: ExecutionContext
    ) -> str:
        """
        Compose and render a component call.

        Args:
            component_call: The <ComponentName /> call
            parent_context: Parent component's execution context

        Returns:
            Rendered HTML string
        """

        # 1. Resolve component
        try:
            metadata = self.resolver.resolve(component_call.component_name)
        except ComponentNotFoundError as e:
            # Return error placeholder
            return f'<!-- Component Error: {e} -->'

        child_component = metadata.ast

        # 2. Prepare props (merge call props + defaults)
        props = self._prepare_props(child_component, component_call.props, parent_context)

        # 3. Execute child component with props
        runtime = ComponentRuntime()
        runtime.execute_component(child_component, props)

        # 4. Replace slots with content from parent
        processed_ast = self._process_slots(
            child_component,
            component_call.children,
            parent_context
        )

        # 5. Render child component
        renderer = HTMLRenderer(runtime.execution_context)
        html = renderer.render(processed_ast)

        return html

    def _prepare_props(
        self,
        child_component: ComponentNode,
        call_props: Dict[str, str],
        parent_context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Prepare props for child component.

        1. Get component parameter definitions
        2. Merge with call props
        3. Apply databinding from parent context
        4. Validate required props
        """

        props = {}

        # Process each parameter definition
        for param_def in child_component.params:
            param_name = param_def.name

            # Get value from call props or use default
            if param_name in call_props:
                value = call_props[param_name]

                # Apply databinding from parent context
                value = self._apply_databinding_from_context(value, parent_context)

                props[param_name] = value

            elif param_def.default is not None:
                props[param_name] = param_def.default

            elif param_def.required:
                # Required prop missing!
                raise ComponentCompositionError(
                    f"Required prop '{param_name}' missing for component '{child_component.name}'"
                )

        return props

    def _apply_databinding_from_context(self, value: str, context: ExecutionContext) -> Any:
        """
        Apply databinding from parent context.

        Examples:
          "{user.name}" → "John Doe"
          "{product.price}" → 29.99
          "Hello {name}!" → "Hello World!"
        """

        if not isinstance(value, str):
            return value

        # Check if entire value is a binding expression
        if value.startswith('{') and value.endswith('}'):
            expression = value[1:-1].strip()
            try:
                return context.get_variable(expression)
            except:
                return value

        # Mixed content - apply string interpolation
        import re
        pattern = r'\{([^}]+)\}'

        def replace_binding(match):
            expr = match.group(1).strip()
            try:
                result = context.get_variable(expr)
                return str(result) if result is not None else ''
            except:
                return match.group(0)

        return re.sub(pattern, replace_binding, value)

    def _process_slots(
        self,
        child_component: ComponentNode,
        slot_content: List[QuantumNode],
        parent_context: ExecutionContext
    ) -> ComponentNode:
        """
        Replace <q:slot> nodes with content from parent.

        Args:
            child_component: Child component AST
            slot_content: Children from parent's component call
            parent_context: Parent's execution context

        Returns:
            Modified component AST with slots filled
        """

        # Build slot content map: {slot_name: [nodes]}
        slot_content_map = {
            'default': slot_content
        }

        # TODO: Support named slots
        # For now, all content goes to default slot

        # Traverse child component and replace SlotNodes
        processed_statements = self._replace_slots_in_nodes(
            child_component.statements,
            slot_content_map,
            parent_context
        )

        # Create modified component
        modified_component = ComponentNode(
            name=child_component.name,
            component_type=child_component.component_type
        )
        modified_component.statements = processed_statements
        modified_component.params = child_component.params
        modified_component.returns = child_component.returns
        modified_component.functions = child_component.functions

        return modified_component

    def _replace_slots_in_nodes(
        self,
        nodes: List[QuantumNode],
        slot_content_map: Dict[str, List[QuantumNode]],
        parent_context: ExecutionContext
    ) -> List[QuantumNode]:
        """
        Recursively replace SlotNodes in node tree.
        """

        result = []

        for node in nodes:
            if isinstance(node, SlotNode):
                # Replace with slot content
                slot_name = node.name
                content = slot_content_map.get(slot_name, node.default_content)
                result.extend(content)

            elif isinstance(node, HTMLNode):
                # Process children recursively
                processed_children = self._replace_slots_in_nodes(
                    node.children,
                    slot_content_map,
                    parent_context
                )
                node.children = processed_children
                result.append(node)

            else:
                # Keep node as-is
                result.append(node)

        return result


class ComponentCompositionError(Exception):
    """Error during component composition"""
    pass
