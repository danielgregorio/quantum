"""
Unit Tests for HTML Renderer

Tests databinding and HTML rendering.
"""

import pytest
from runtime.renderer import HTMLRenderer
from runtime.execution_context import ExecutionContext
from core.ast_nodes import HTMLNode, TextNode, ComponentNode


class TestDatabinding:
    """Test databinding functionality"""

    @pytest.mark.unit
    @pytest.mark.phase1
    def test_simple_variable_binding(self, execution_context):
        """Test simple {variable} databinding"""
        execution_context.set_variable('name', 'John', scope='component')

        renderer = HTMLRenderer(execution_context)
        text_node = TextNode('Hello {name}!')

        result = renderer.render(text_node)
        assert result == 'Hello John!'

    @pytest.mark.unit
    @pytest.mark.phase1
    def test_nested_property_binding(self, execution_context):
        """Test {object.property} databinding"""
        user = {'name': 'Alice', 'email': 'alice@example.com'}
        execution_context.set_variable('user', user, scope='component')

        renderer = HTMLRenderer(execution_context)
        text_node = TextNode('User: {user.name}')

        result = renderer.render(text_node)
        assert 'Alice' in result

    @pytest.mark.unit
    @pytest.mark.phase1
    def test_html_node_rendering(self, execution_context):
        """Test HTML node rendering"""
        renderer = HTMLRenderer(execution_context)

        html_node = HTMLNode(
            tag='div',
            attributes={'class': 'container'},
            children=[TextNode('Hello')]
        )

        result = renderer.render(html_node)
        assert '<div class="container">Hello</div>' in result


class TestComponentRendering:
    """Test component rendering"""

    @pytest.mark.unit
    @pytest.mark.phase2
    def test_component_with_children(self, execution_context):
        """Test rendering component with child nodes"""
        renderer = HTMLRenderer(execution_context)

        component = ComponentNode('TestComp', 'pure')
        component.statements = [
            HTMLNode('h1', {}, [TextNode('Title')]),
            HTMLNode('p', {}, [TextNode('Content')])
        ]

        result = renderer.render(component)
        assert '<h1>Title</h1>' in result
        assert '<p>Content</p>' in result
