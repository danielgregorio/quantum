"""A page's `<ui:validator>`s, checked by the server when the form is sent (UI-21).

In a standalone build (UI-8) a validator is a rule the page's script checks in the browser. In a page every
renderer sends the same post, so the server checks it: the action whose form holds validators runs only when
they pass, and when one fails the form comes back with each error next to its field, as the action's own
q:param rules do (UI-9). A rule:

- `type="pattern"` (or a `pattern`): the whole value matches the regular expression;
- `type="email"`, `type="url"`, `type="phone"`: the value has that form;
- `match="other"`: the value is the same as field `other`'s (a password typed twice);
- `min`, `max`: the number is at least, at most; `minlength`, `maxlength`: the text is that long;
- `server-expression="{...}"`: an expression of the form's fields that must be true.

An empty field passes every rule but its own q:param's `required`. `expression=`, a check in the browser's
script, is an error in a page (write `server-expression`).
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_URL = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
_PHONE = re.compile(r'^\+?[\d\s().-]{7,20}$')


def form_validators(nodes, action: str) -> List[Any]:
    """The validators of every ui:form in `nodes` (a page's statements) that sends `action`."""
    from quantum.core.features.ui_engine.src.ast_nodes import UIFormNode
    found: List[Any] = []

    def walk(items) -> None:
        for node in items or []:
            if isinstance(node, UIFormNode) and (node.on_submit or '').strip().rstrip('()') == action:
                found.extend(getattr(node, 'validators', None) or [])
            for attr in ('children', 'statements', 'body', 'if_body', 'else_body'):
                walk(getattr(node, attr, None))
            for block in getattr(node, 'elseif_blocks', None) or []:
                walk(block.get('body') if isinstance(block, dict) else getattr(block, 'body', None))

    walk(nodes)
    return found


def _number(text: Any) -> Optional[float]:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def failures(validators: List[Any], fields: Dict[str, Any],
             evaluate: Callable[[str, Dict[str, Any]], Any]) -> Dict[str, str]:
    """Each field whose validator fails, with its message (the first failure of a field wins)."""
    errors: Dict[str, str] = {}
    for v in validators:
        field = v.field or v.name
        if not field:
            raise ValueError('<ui:validator> names its field: field="name" (UI-21)')
        if v.expression and not v.server_expression:
            raise ValueError(f'<ui:validator field="{field}" expression=...> is a check in a standalone build\'s '
                             f'script; in a page the server checks it: write server-expression="{{...}}" (UI-21)')
        if field in errors:
            continue
        value = fields.get(field)
        text = '' if value is None else str(value)
        problem = None
        kind = (v.rule_type or '').strip().lower()
        if text != '':
            if (kind == 'pattern' or v.pattern) and v.pattern and not re.fullmatch(v.pattern, text):
                problem = 'does not match the pattern'
            elif kind == 'email' and not _EMAIL.match(text):
                problem = 'is not an email address'
            elif kind == 'url' and not _URL.match(text):
                problem = 'is not a web address'
            elif kind == 'phone' and not _PHONE.match(text):
                problem = 'is not a phone number'
            elif v.minlength is not None and len(text) < int(v.minlength):
                problem = f'is shorter than {v.minlength} characters'
            elif v.maxlength is not None and len(text) > int(v.maxlength):
                problem = f'is longer than {v.maxlength} characters'
            elif v.min not in (None, '') and (_number(text) is None or _number(text) < _number(v.min)):
                problem = f'is less than {v.min}'
            elif v.max not in (None, '') and (_number(text) is None or _number(text) > _number(v.max)):
                problem = f'is more than {v.max}'
        if problem is None and v.match and text != str(fields.get(v.match) or ''):
            problem = f'is not the same as {v.match}'
        if problem is None and v.server_expression:
            if not evaluate(v.server_expression, fields):
                problem = 'is not valid'
        if problem is not None:
            errors[field] = v.message or f'{field} {problem}'
    return errors
