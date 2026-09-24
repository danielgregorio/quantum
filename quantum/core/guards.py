"""Page guards (AUTH-6): a q:if at the top of a page whose branch has a q:redirect.

    <q:if condition="not session.authenticated">
      <q:redirect url="/login" />
    </q:if>

A q:action does not run the page's statements, so a guard written like this
used to protect only the GET — the POST ran the action without a session.
Guards now run before each action of the page as well as before the render.
"""

from typing import List

from quantum.core.ast_nodes import RedirectNode
from quantum.core.features.conditionals.src.ast_node import IfNode


def _branches(node: IfNode) -> List:
    body = list(node.if_body)
    for block in node.elseif_blocks:
        body += list(block.get('body', []))
    return body + list(node.else_body)


def _has_redirect(nodes) -> bool:
    return any(isinstance(n, RedirectNode) or (isinstance(n, IfNode) and _has_redirect(_branches(n)))
               for n in nodes)


def page_guards(component) -> List[IfNode]:
    """The top-level q:if statements that can redirect, in document order."""
    return [s for s in getattr(component, 'statements', [])
            if isinstance(s, IfNode) and _has_redirect(_branches(s))]


def guard_conditions(node: IfNode) -> List[str]:
    """Every condition a guard evaluates, nested q:if included."""
    conditions = [node.condition] + [b.get('condition', '') for b in node.elseif_blocks]
    for child in _branches(node):
        if isinstance(child, IfNode):
            conditions += guard_conditions(child)
    return [c for c in conditions if c]


def mark_guards(component) -> None:
    """Flag each guard, nested q:if included, so its condition fails closed (AUTH-6)."""
    def marcar(node):
        node.is_guard = True
        for child in _branches(node):
            if isinstance(child, IfNode):
                marcar(child)
    for guard in page_guards(component):
        marcar(guard)
