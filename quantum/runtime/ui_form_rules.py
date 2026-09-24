"""Forms that know their action's rules (M1, UI-9).

A `<ui:form on-submit="create">` posts to `<q:action name="create">`, whose
`q:param`s already say what each field must be. The form takes those rules
as HTML attributes — `required`, `minlength`, `min`, `type="number"`… — so the
browser checks them before posting; the server still validates (ACT-2). When
the server's validation fails, the next render of that form shows the values
that were sent (never a password) and each error next to its field.

What a field gets is visible in the HTML it draws; `<ui:form rules="off">`
turns it off; an attribute written on the field always wins.
"""

import copy
import html
from typing import Dict, Optional, Tuple

from quantum.core.features.ui_engine.src.ast_nodes import (
    UICheckboxNode, UIInputNode, UIRadioNode, UISelectNode, UISwitchNode)

FIELDS = (UIInputNode, UISelectNode, UIRadioNode, UICheckboxNode, UISwitchNode)

# q:param type -> the input type the browser checks
_HTML_TYPE = {'integer': 'number', 'number': 'number', 'decimal': 'number', 'float': 'number',
              'email': 'email', 'url': 'url', 'date': 'date', 'file': 'file'}
# A browser never sends a file back, and a password is never shown again.
_NOT_REFILLED = ('password', 'file')


class FormContext:
    """What a form knows while its fields are drawn."""

    def __init__(self, params=None, state: Optional[dict] = None, rules: bool = True,
                 initial: Optional[dict] = None, action=None, config=None):
        self.all_params = list(params or [])
        self.params = {p.name: p for p in self.all_params} if rules else {}
        self.errors: Dict[str, str] = (state or {}).get('errors') or {}
        self.values: Optional[Dict[str, str]] = (state or {}).get('values') if state else None
        self.initial: Dict[str, object] = initial or {}          # UI-10: values="{row}"
        self.action = action
        self.config = config or {}


def form_context(renderer, form_node, action_name: Optional[str]) -> Optional[FormContext]:
    if not action_name:
        return None
    action = (getattr(renderer, '_ui_action_nodes', None) or {}).get(action_name)
    state = getattr(renderer, 'form_state', None)
    if not state or state.get('action') != action_name:
        state = None
    config = getattr(renderer, 'config', None) or {}
    params = []
    if action is not None:
        from quantum.runtime.table_params import TableParamsError, params_of
        try:
            params = params_of(action, config)
        except TableParamsError as exc:
            raise ValueError(f'<ui:form on-submit="{action_name}">: {exc}') from exc
    initial = {}
    expression = getattr(form_node, 'values', None)
    if expression:
        row = renderer._apply_databinding(expression)
        if isinstance(row, list) and len(row) == 1:
            row = row[0]                                  # a q:query of one row
        if row not in (None, ''):
            if not isinstance(row, dict):
                raise ValueError(f'<ui:form values="{expression}"> needs a row (a record), '
                                 f'got {type(row).__name__} (UI-10)')
            initial = row
    return FormContext(params, state, getattr(form_node, 'rules', None) != 'off', initial, action, config)


def prepare_field(node, ctx: Optional[FormContext], escape: bool) -> Tuple[object, Optional[str]]:
    """A copy of the field with the action's rules and the values sent, and its error.

    `escape`: the HTML renderer writes attribute values as they are, so a
    value sent back to the page is escaped here; the view tree is not (UI-3).
    """
    name = getattr(node, 'bind', None)
    if ctx is None or not name:
        return node, None
    field = copy.copy(node)
    param = ctx.params.get(name)
    if param is not None:
        if isinstance(field, UIInputNode):
            if param.required and not field.required:
                field.required = True
            for attr in ('minlength', 'maxlength'):
                value = getattr(param, attr, None)
                if getattr(field, attr) is None and value is not None:
                    setattr(field, attr, int(value))
            for attr in ('min', 'max'):
                value = getattr(param, attr, None)
                if getattr(field, attr) is None and value is not None:
                    setattr(field, attr, str(value))
            pattern = getattr(param, 'pattern', None) or ''
            # The server searches (re.search); HTML's pattern must match the
            # whole value. Only an anchored ^…$ pattern means the same in both.
            if not field.pattern and pattern.startswith('^') and pattern.endswith('$'):
                field.pattern = pattern[1:-1]
            html_type = _HTML_TYPE.get(str(getattr(param, 'type', '') or '').lower())
            if html_type and (field.input_type or 'text') == 'text':
                field.input_type = html_type
            if field.input_type == 'file' and not getattr(field, 'accept', None) and getattr(param, 'accept', None):
                field.accept = param.accept                     # UI-14
        elif isinstance(field, (UISelectNode, UIRadioNode)):
            if not field.options and not getattr(field, 'children', None) and getattr(param, 'enum', None):
                field.options = param.enum
    if ctx.values is None and name in ctx.initial:
        # UI-10: an edit form opens with the row's value (unless the field sets its own).
        initial = ctx.initial[name]
        if isinstance(field, (UICheckboxNode, UISwitchNode)):
            if getattr(field, 'checked', None) is None:
                field.checked = 'true' if initial not in (None, '', 0, '0', False, 'false') else 'false'
        elif getattr(field, 'value', None) in (None, '') and initial is not None                 and not (isinstance(field, UIInputNode) and field.input_type in _NOT_REFILLED):
            field.value = html.escape(str(initial), quote=True) if escape else str(initial)
    if ctx.values is not None:
        if isinstance(field, (UICheckboxNode, UISwitchNode)):
            # A browser sends a checked box and omits an unchecked one.
            field.checked = 'true' if name in ctx.values else 'false'
        elif name in ctx.values and not (isinstance(field, UIInputNode) and field.input_type in _NOT_REFILLED):
            value = str(ctx.values[name])
            field.value = html.escape(value, quote=True) if escape else value
    error = ctx.errors.get(name)
    if error:
        field.ui_class = ((getattr(field, 'ui_class', None) or '') + ' q-invalid').strip()
    return field, error


def sends_files(fields, ctx: Optional[FormContext]) -> bool:
    """UI-14: whether a form has a file field — then it must post multipart,
    or the browser sends only the file's name."""
    file_fields = {n for n, p in (ctx.params if ctx else {}).items()
                   if str(getattr(p, 'type', '') or '').lower() == 'file'}
    pending = list(fields or [])
    while pending:
        field = pending.pop()
        if isinstance(field, UIInputNode) and (field.input_type == 'file' or field.bind in file_fields):
            return True
        pending.extend(getattr(field, 'children', None) or [])
    return False


FORM_CSS = """
/* UI-9: a field the server's validation refused, and its message */
.q-invalid, .q-invalid input { border-color: var(--q-danger, #dc2626) !important; }
.q-field-error { display: block; color: var(--q-danger, #dc2626); font-size: 13px; margin-top: 4px; }
"""


def has_fields(nodes) -> bool:
    """Whether a form's markup already has fields of its own."""
    for node in nodes or []:
        if isinstance(node, FIELDS) or has_fields(getattr(node, 'children', None)):
            return True
    return False


def has_button(nodes) -> bool:
    from quantum.core.features.ui_engine.src.ast_nodes import UIButtonNode
    for node in nodes or []:
        if isinstance(node, UIButtonNode) or has_button(getattr(node, 'children', None)):
            return True
    return False


def generated_fields(form_node, ctx: Optional[FormContext]) -> list:
    """UI-10: a form with no fields draws one per param of its action, and a button."""
    from quantum.core.features.ui_engine.src.ast_nodes import (
        UIButtonNode, UIFormItemNode, UIOptionNode)
    from quantum.runtime.table_params import humanize, reference_options
    children = list(getattr(form_node, 'children', None) or [])
    if ctx is None or not ctx.params or has_fields(children):
        if getattr(form_node, 'submit', None) and not has_button(children):
            # submit= was ignored when the form had fields of its own: a form
            # with a multi-line field and no button could not be sent at all.
            button = UIButtonNode()
            button.content, button.variant = form_node.submit, 'primary'
            return children + [button]
        return children
    generated = []
    for param in ctx.all_params:
        label = humanize(param.name)
        if str(param.type).lower() == 'boolean':
            field = UICheckboxNode()
            field.bind, field.label = param.name, label
            generated.append(field)
            continue
        reference = getattr(param, 'references', None)
        if reference and ctx.action is not None:
            field = UISelectNode()
            field.bind = param.name
            if not param.required:
                empty = UIOptionNode()
                empty.value, empty.label = '', '—'
                field.children.append(empty)
            for value, text in reference_options(ctx.config, ctx.action.table_datasource, reference):
                option = UIOptionNode()
                option.value, option.label = value, text
                field.children.append(option)
        elif param.enum:
            field = UISelectNode()
            field.bind = param.name
        else:
            field = UIInputNode()
            field.bind = param.name
        item = UIFormItemNode()
        item.label = label
        item.children.append(field)
        generated.append(item)
    if not has_button(children):
        button = UIButtonNode()
        button.content = getattr(form_node, 'submit', None) or 'Save'
        button.variant = 'primary'
        generated.append(button)
    return children + generated

