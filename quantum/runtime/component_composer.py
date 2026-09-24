"""
Quantum Component Composer — <Component prop="…">slot content</Component>.

COMP-1..4 (SPEC.md). What this used to get wrong, found by building the admin
layout on it:

  - the component was searched in ./components relative to the process's
    working directory — paths.components from quantum.config.yaml and the
    `from=` of q:import were ignored;
  - a component that was not found, or failed, became an HTML comment and the
    page answered 200 with the section missing;
  - the child ran as ComponentRuntime() with no configuration, so a q:query
    or q:invoke service= inside a child component had no datasources/services;
  - slot content was grafted into the child's AST and evaluated in the
    CHILD's scope: a q:loop over the page's rows inside a layout saw nothing.
    Worse, the graft mutated the child AST held in the resolver cache, so the
    first request's slot content replaced the q:slot for every later request;
  - props used get_variable only (no expressions) and fell back to the
    placeholder text on failure.
"""

import re
from typing import Any, Dict, List

from quantum.core.ast_nodes import ComponentCallNode, ComponentNode, HTMLNode, QuantumNode, SlotNode
from quantum.core.expressions import ExpressionError
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.component_resolver import ComponentNotFoundError, ComponentResolver


class ComponentCompositionError(Exception):
    """A component call could not be composed; the message names the component."""


class RenderedHTML(QuantumNode):
    """Markup the parent already rendered (slot content), inserted as-is."""

    def __init__(self, html: str):
        self.html = html

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "rendered_html", "length": len(self.html)}

    def validate(self) -> List[str]:
        return []


class ComponentComposer:
    def __init__(self, resolver: ComponentResolver):
        self.resolver = resolver

    def compose(self, call: ComponentCallNode, parent) -> str:
        """Render `call` as a child of the HTMLRenderer `parent`."""
        from quantum.runtime.renderer import HTMLRenderer

        name, origin = parent.imports.get(call.component_name, (call.component_name, None))
        try:
            child = self.resolver.resolve(name, origin).ast
        except ComponentNotFoundError as exc:
            raise ComponentCompositionError(f"<{call.component_name}>: {exc}") from exc

        props = self._props(child, call, parent)
        # COMP-4: the same configuration and the same session, application and
        # request scopes as the page — a layout showing {session.userName}
        # used to see an empty session.
        props.update(_session_scope=parent.context.session_vars,
                     _application_scope=parent.context.application_vars,
                     _request_scope=parent.context.request_vars)
        runtime = ComponentRuntime(config=parent.config)
        runtime.execute_component(child, props)

        # COMP-3: slot content belongs to the page — rendered here, with the
        # page's variables, before the child sees it.
        slot = RenderedHTML(parent.render_all(call.children)) if call.children else None
        filled = ComponentNode(name=child.name, component_type=child.component_type)
        filled.statements = self._with_slot(child.statements, slot)
        filled.params, filled.returns, filled.functions = child.params, child.returns, child.functions

        renderer = HTMLRenderer(runtime.execution_context, components_dir=parent.components_dir,
                                function_resolver=runtime._resolve_expression_function, config=parent.config)
        return renderer.render(filled)

    def _props(self, child: ComponentNode, call: ComponentCallNode, parent) -> Dict[str, Any]:
        props = {}
        for definition in child.params:
            if definition.name in call.props:
                props[definition.name] = self._evaluate(call.props[definition.name], definition.name, call, parent)
            elif definition.default is not None:
                props[definition.name] = definition.default
            elif definition.required:
                raise ComponentCompositionError(
                    f"<{call.component_name}> requires the prop {definition.name!r}")
        return props

    @staticmethod
    def _evaluate(value, prop, call, parent):
        """COMP-2: a prop is an attribute of a tag — an expression that fails is an error."""
        if not isinstance(value, str) or "{" not in value:
            return value
        variables = parent.context.get_all_variables()
        try:
            whole = re.fullmatch(r"\s*\{([^{}]*)\}\s*", value)
            if whole:
                return parent._expressions.evaluate(whole.group(1), variables)
            return re.sub(r"\{([^{}]*)\}",
                          lambda m: str(parent._expressions.evaluate(m.group(1), variables)), value)
        except ExpressionError as exc:
            raise ComponentCompositionError(
                f"<{call.component_name} {prop}=\"{value}\">: {exc}") from exc

    def _with_slot(self, nodes: List[QuantumNode], slot) -> List[QuantumNode]:
        """Copy of `nodes` with each q:slot replaced — the cached child AST is never touched."""
        result = []
        for node in nodes:
            if isinstance(node, SlotNode):
                # Only the default slot receives the call's children; named
                # slots keep their default content (named slots are not
                # implemented, as before).
                if slot is not None and (node.name or "default") == "default":
                    result.append(slot)
                else:
                    result.extend(node.default_content or [])
            elif isinstance(node, HTMLNode) and self._has_slot(node.children):
                copy = HTMLNode(tag=node.tag, attributes=dict(node.attributes),
                                 children=self._with_slot(node.children, slot), self_closing=node.self_closing)
                result.append(copy)
            else:
                result.append(node)
        return result

    def _has_slot(self, nodes) -> bool:
        return any(isinstance(n, SlotNode) or (isinstance(n, HTMLNode) and self._has_slot(n.children))
                   for n in nodes)
