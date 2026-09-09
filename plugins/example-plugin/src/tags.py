"""
Custom Tag Handler for Example Plugin

Demonstrates how to create tag handlers that parse
custom XML tags into AST nodes.
"""

from typing import Any, List, Optional
from xml.etree.ElementTree import Element
from datetime import datetime

from .nodes import HelloNode, CounterNode, TimestampNode

# Import base class
try:
    from plugins.registry import TagHandler
except ImportError:
    # Fallback for standalone testing
    class TagHandler:
        prefix = ""

        def parse(self, element, parser):
            pass

        def execute(self, node, context, runtime):
            pass

        def render(self, node, renderer):
            pass

        def get_supported_tags(self):
            return []


class ExampleTagHandler(TagHandler):
    """
    Tag handler for the 'ex' prefix.

    Handles:
    - <ex:hello> - Greeting component
    - <ex:counter> - Counter component
    - <ex:timestamp> - Timestamp display
    """

    prefix = "ex"

    def parse(self, element: Element, parser: Any) -> Any:
        """
        Parse an ex:* element into its corresponding AST node.

        Args:
            element: XML element to parse
            parser: Quantum parser instance

        Returns:
            Appropriate AST node
        """
        # Get tag name without prefix
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        elif ':' in tag:
            tag = tag.split(':')[1]

        if tag == 'hello':
            return self._parse_hello(element, parser)
        elif tag == 'counter':
            return self._parse_counter(element, parser)
        elif tag == 'timestamp':
            return self._parse_timestamp(element, parser)
        else:
            raise ValueError(f"Unknown ex: tag: {tag}")

    def _parse_hello(self, element: Element, parser: Any) -> HelloNode:
        """Parse <ex:hello> element"""
        return HelloNode(
            name=element.get('name', 'World'),
            greeting=element.get('greeting', 'Hello'),
            style=element.get('style')
        )

    def _parse_counter(self, element: Element, parser: Any) -> CounterNode:
        """Parse <ex:counter> element"""
        initial = 0
        initial_str = element.get('initial', '0')
        try:
            initial = int(initial_str)
        except ValueError:
            pass

        step = 1
        step_str = element.get('step', '1')
        try:
            step = int(step_str)
        except ValueError:
            pass

        min_value = None
        min_str = element.get('min')
        if min_str:
            try:
                min_value = int(min_str)
            except ValueError:
                pass

        max_value = None
        max_str = element.get('max')
        if max_str:
            try:
                max_value = int(max_str)
            except ValueError:
                pass

        return CounterNode(
            name=element.get('name', ''),
            initial=initial,
            step=step,
            min_value=min_value,
            max_value=max_value
        )

    def _parse_timestamp(self, element: Element, parser: Any) -> TimestampNode:
        """Parse <ex:timestamp> element"""
        return TimestampNode(
            format=element.get('format', '%Y-%m-%d %H:%M:%S'),
            timezone=element.get('timezone'),
            variable=element.get('variable')
        )

    def execute(self, node: Any, context: Any, runtime: Any) -> Any:
        """
        Execute an ex:* node.

        Args:
            node: AST node to execute
            context: Execution context
            runtime: Component runtime

        Returns:
            Execution result
        """
        if isinstance(node, HelloNode):
            return self._execute_hello(node, context, runtime)
        elif isinstance(node, CounterNode):
            return self._execute_counter(node, context, runtime)
        elif isinstance(node, TimestampNode):
            return self._execute_timestamp(node, context, runtime)

        return None

    def _execute_hello(self, node: HelloNode, context: Any, runtime: Any) -> str:
        """Execute HelloNode"""
        # Apply databinding to name
        name = node.name
        if hasattr(runtime, '_apply_databinding'):
            name = runtime._apply_databinding(name, context)

        return f"{node.greeting}, {name}!"

    def _execute_counter(self, node: CounterNode, context: Any, runtime: Any) -> int:
        """Execute CounterNode - initialize counter variable"""
        if hasattr(context, 'set_variable'):
            context.set_variable(node.name, node.initial)
        elif isinstance(context, dict):
            context[node.name] = node.initial

        return node.initial

    def _execute_timestamp(self, node: TimestampNode, context: Any, runtime: Any) -> str:
        """Execute TimestampNode"""
        now = datetime.now()

        # TODO: Handle timezone conversion
        if node.timezone:
            pass  # Would need pytz for proper timezone handling

        formatted = now.strftime(node.format)

        # Store in variable if specified
        if node.variable:
            if hasattr(context, 'set_variable'):
                context.set_variable(node.variable, formatted)
            elif isinstance(context, dict):
                context[node.variable] = formatted

        return formatted

    def render(self, node: Any, renderer: Any) -> str:
        """
        Render an ex:* node to HTML.

        Args:
            node: AST node to render
            renderer: Renderer instance

        Returns:
            HTML string
        """
        if isinstance(node, HelloNode):
            return self._render_hello(node, renderer)
        elif isinstance(node, CounterNode):
            return self._render_counter(node, renderer)
        elif isinstance(node, TimestampNode):
            return self._render_timestamp(node, renderer)

        return ""

    def _render_hello(self, node: HelloNode, renderer: Any) -> str:
        """Render HelloNode to HTML"""
        style_attr = f' style="{node.style}"' if node.style else ''
        name = node.name

        # Apply databinding if renderer supports it
        if hasattr(renderer, 'apply_databinding'):
            name = renderer.apply_databinding(name)

        return f'<span class="ex-hello"{style_attr}>{node.greeting}, {name}!</span>'

    def _render_counter(self, node: CounterNode, renderer: Any) -> str:
        """Render CounterNode to HTML"""
        data_attrs = f'data-step="{node.step}"'
        if node.min_value is not None:
            data_attrs += f' data-min="{node.min_value}"'
        if node.max_value is not None:
            data_attrs += f' data-max="{node.max_value}"'

        return f'''<div class="ex-counter" data-name="{node.name}" {data_attrs}>
    <button class="ex-counter-dec">-</button>
    <span class="ex-counter-value">{node.initial}</span>
    <button class="ex-counter-inc">+</button>
</div>'''

    def _render_timestamp(self, node: TimestampNode, renderer: Any) -> str:
        """Render TimestampNode to HTML"""
        now = datetime.now()
        formatted = now.strftime(node.format)

        return f'<time class="ex-timestamp" datetime="{now.isoformat()}">{formatted}</time>'

    def get_supported_tags(self) -> List[str]:
        """Return list of supported tag names"""
        return ['hello', 'counter', 'timestamp']
