"""
AST Nodes for UI Engine (ui: namespace)

All UI-specific AST nodes for the Quantum multi-target UI engine.
These represent containers, widgets, and layout primitives that
compile to HTML/CSS, Python Textual (TUI), or Desktop (pywebview).
"""

from typing import Dict, Any, List, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


# ============================================
# LAYOUT MIXIN
# ============================================

class UILayoutMixin:
    """Shared layout attributes for all UI containers and some widgets."""

    def _init_layout_attrs(self):
        self.gap: Optional[str] = None
        self.padding: Optional[str] = None
        self.margin: Optional[str] = None
        self.align: Optional[str] = None        # start, center, end, stretch
        self.justify: Optional[str] = None       # start, center, end, between, around
        self.width: Optional[str] = None         # auto, fill, number, percentage
        self.height: Optional[str] = None
        self.background: Optional[str] = None
        self.color: Optional[str] = None
        self.border: Optional[str] = None
        self.ui_id: Optional[str] = None
        self.ui_class: Optional[str] = None
        self.visible: Optional[str] = None

    def _layout_to_dict(self) -> Dict[str, Any]:
        """Return layout attributes as dict (for to_dict)."""
        d = {}
        for attr in ('gap', 'padding', 'margin', 'align', 'justify',
                      'width', 'height', 'background', 'color', 'border',
                      'ui_id', 'ui_class', 'visible'):
            val = getattr(self, attr, None)
            if val is not None:
                d[attr] = val
        return d

    def _validate_layout(self) -> List[str]:
        """Validate layout attributes."""
        errors = []
        if self.align and self.align not in ('start', 'center', 'end', 'stretch'):
            errors.append(f"Invalid align value: {self.align}")
        if self.justify and self.justify not in ('start', 'center', 'end', 'between', 'around'):
            errors.append(f"Invalid justify value: {self.justify}")
        return errors


# ============================================
# CONTAINERS
# ============================================

class UIWindowNode(QuantumNode, UILayoutMixin):
    """Represents <ui:window> - Top-level window container."""

    def __init__(self, title: Optional[str] = None):
        self.title = title
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_window", "title": self.title,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIHBoxNode(QuantumNode, UILayoutMixin):
    """Represents <ui:hbox> - Horizontal flex container."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_hbox", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIVBoxNode(QuantumNode, UILayoutMixin):
    """Represents <ui:vbox> - Vertical flex container."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_vbox", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIPanelNode(QuantumNode, UILayoutMixin):
    """Represents <ui:panel> - Bordered container with optional title."""

    def __init__(self):
        self.title: Optional[str] = None
        self.collapsible: bool = False
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_panel", "title": self.title,
             "collapsible": self.collapsible, "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UITabPanelNode(QuantumNode, UILayoutMixin):
    """Represents <ui:tabpanel> - Tabbed content container."""

    def __init__(self):
        self.children: List[QuantumNode] = []  # Should contain UITabNode
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_tabpanel", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UITabNode(QuantumNode, UILayoutMixin):
    """Represents <ui:tab> - Individual tab inside a tabpanel."""

    def __init__(self):
        self.title: str = ""
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_tab", "title": self.title,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if not self.title:
            errors.append("Tab title is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIGridNode(QuantumNode, UILayoutMixin):
    """Represents <ui:grid> - CSS grid container."""

    def __init__(self):
        self.columns: Optional[str] = None  # e.g. "3", "1fr 2fr 1fr"
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_grid", "columns": self.columns,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIAccordionNode(QuantumNode, UILayoutMixin):
    """Represents <ui:accordion> - Collapsible sections container."""

    def __init__(self):
        self.children: List[QuantumNode] = []  # Should contain UISectionNode
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_accordion", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UISectionNode(QuantumNode, UILayoutMixin):
    """Represents <ui:section> - Collapsible section (inside accordion)."""

    def __init__(self):
        self.title: str = ""
        self.expanded: bool = False
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_section", "title": self.title,
             "expanded": self.expanded, "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if not self.title:
            errors.append("Section title is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIDividedBoxNode(QuantumNode, UILayoutMixin):
    """Represents <ui:dividedbox> - Resizable split container."""

    def __init__(self):
        self.direction: str = "horizontal"  # horizontal, vertical
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_dividedbox", "direction": self.direction,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.direction not in ('horizontal', 'vertical'):
            errors.append(f"Invalid dividedbox direction: {self.direction}")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIFormNode(QuantumNode, UILayoutMixin):
    """Represents <ui:form> - Form container with validation support."""

    def __init__(self):
        self.on_submit: Optional[str] = None
        self.children: List[QuantumNode] = []

        # Validation mode: 'client', 'server', or 'both' (default)
        self.validation_mode: str = "both"

        # Show validation feedback inline (default) or in summary
        self.error_display: str = "inline"  # 'inline', 'summary', 'both'

        # Disable HTML5 native validation (use custom JS instead)
        self.novalidate: bool = False

        # Custom validators defined at form level
        self.validators: List['UIValidatorNode'] = []

        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def add_validator(self, validator: 'UIValidatorNode'):
        """Add a custom validator to the form."""
        self.validators.append(validator)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_form", "on_submit": self.on_submit,
             "validation_mode": self.validation_mode,
             "error_display": self.error_display,
             "novalidate": self.novalidate,
             "validators_count": len(self.validators),
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.validation_mode not in ('client', 'server', 'both'):
            errors.append(f"Invalid validation_mode: {self.validation_mode}")
        if self.error_display not in ('inline', 'summary', 'both'):
            errors.append(f"Invalid error_display: {self.error_display}")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        for validator in self.validators:
            if hasattr(validator, 'validate'):
                errors.extend(validator.validate())
        return errors


class UIValidatorNode(QuantumNode):
    """
    Represents <ui:validator> - Custom validation rule.

    Can be defined at form level (reusable) or inline in an input.

    Examples:
        <ui:validator name="phone" pattern="^\d{10,11}$" message="Invalid phone number" />
        <ui:validator name="passwordMatch" field="password" match="confirm_password"
                      message="Passwords must match" />
        <ui:validator name="customEmail" type="email" message="Please enter a valid email" />
    """

    def __init__(self):
        # Validator identification
        self.name: Optional[str] = None              # Unique name for reference

        # Validation rule types
        self.rule_type: Optional[str] = None         # 'pattern', 'email', 'url', 'phone', 'match', 'custom'
        self.pattern: Optional[str] = None           # Regex pattern
        self.match: Optional[str] = None             # Field name to match against
        self.min: Optional[str] = None               # Min value
        self.max: Optional[str] = None               # Max value
        self.minlength: Optional[int] = None         # Min length
        self.maxlength: Optional[int] = None         # Max length

        # Custom validation function (for 'custom' type)
        self.expression: Optional[str] = None        # Custom JS expression
        self.server_expression: Optional[str] = None # Custom server-side expression

        # Error handling
        self.message: Optional[str] = None           # Error message to display
        self.field: Optional[str] = None             # Target field (for form-level validators)

        # When to trigger validation
        self.trigger: str = "submit"                 # 'blur', 'change', 'input', 'submit'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ui_validator",
            "name": self.name,
            "rule_type": self.rule_type,
            "pattern": self.pattern,
            "match": self.match,
            "min": self.min,
            "max": self.max,
            "minlength": self.minlength,
            "maxlength": self.maxlength,
            "expression": self.expression,
            "message": self.message,
            "field": self.field,
            "trigger": self.trigger,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Validator requires 'name' attribute")
        if self.trigger not in ('blur', 'change', 'input', 'submit'):
            errors.append(f"Invalid validator trigger: {self.trigger}")
        # Must have at least one validation rule
        has_rule = (self.pattern or self.match or self.rule_type or
                    self.min or self.max or self.minlength or self.maxlength or
                    self.expression)
        if not has_rule:
            errors.append(f"Validator '{self.name}' must define at least one validation rule")
        return errors


class UIFormItemNode(QuantumNode, UILayoutMixin):
    """Represents <ui:formitem> - Form item with label."""

    def __init__(self):
        self.label: Optional[str] = None
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_formitem", "label": self.label,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UISpacerNode(QuantumNode, UILayoutMixin):
    """Represents <ui:spacer> - Flexible space filler."""

    def __init__(self):
        self.size: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_spacer", "size": self.size}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIScrollBoxNode(QuantumNode, UILayoutMixin):
    """Represents <ui:scrollbox> - Scrollable container."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_scrollbox", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


# ============================================
# WIDGETS
# ============================================

class UITextNode(QuantumNode, UILayoutMixin):
    """Represents <ui:text> - Text display widget."""

    def __init__(self):
        self.content: str = ""
        self.size: Optional[str] = None      # xs, sm, md, lg, xl, 2xl
        self.weight: Optional[str] = None    # normal, bold, light
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_text", "content": self.content,
             "size": self.size, "weight": self.weight}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIButtonNode(QuantumNode, UILayoutMixin):
    """Represents <ui:button> - Clickable button widget."""

    def __init__(self):
        self.content: str = ""
        self.on_click: Optional[str] = None
        self.variant: Optional[str] = None    # primary, secondary, danger, success
        self.disabled: bool = False
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_button", "content": self.content,
             "on_click": self.on_click, "variant": self.variant,
             "disabled": self.disabled}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIInputNode(QuantumNode, UILayoutMixin):
    """Represents <ui:input> - Text input widget with validation support."""

    def __init__(self):
        self.bind: Optional[str] = None
        self.placeholder: Optional[str] = None
        self.input_type: str = "text"    # text, password, email, number
        self.on_change: Optional[str] = None
        self.on_submit: Optional[str] = None

        # Validation attributes (HTML5 + server-side)
        self.required: bool = False
        self.min: Optional[str] = None           # Min value (number/date)
        self.max: Optional[str] = None           # Max value (number/date)
        self.minlength: Optional[int] = None     # Min string length
        self.maxlength: Optional[int] = None     # Max string length
        self.pattern: Optional[str] = None       # Regex pattern
        self.error_message: Optional[str] = None # Custom error message

        # Custom validators (references to ui:validator rules)
        self.validators: List[str] = []

        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_input", "bind": self.bind,
             "placeholder": self.placeholder, "input_type": self.input_type,
             "required": self.required, "min": self.min, "max": self.max,
             "minlength": self.minlength, "maxlength": self.maxlength,
             "pattern": self.pattern, "error_message": self.error_message,
             "validators": self.validators}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        # Validate that minlength <= maxlength if both specified
        if self.minlength is not None and self.maxlength is not None:
            if self.minlength > self.maxlength:
                errors.append(f"Input minlength ({self.minlength}) cannot exceed maxlength ({self.maxlength})")
        return errors


class UICheckboxNode(QuantumNode, UILayoutMixin):
    """Represents <ui:checkbox> - Checkbox widget."""

    def __init__(self):
        self.bind: Optional[str] = None
        self.label: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_checkbox", "bind": self.bind, "label": self.label}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIRadioNode(QuantumNode, UILayoutMixin):
    """Represents <ui:radio> - Radio button group."""

    def __init__(self):
        self.bind: Optional[str] = None
        self.options: Optional[str] = None  # comma-separated or source ref
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_radio", "bind": self.bind, "options": self.options}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UISwitchNode(QuantumNode, UILayoutMixin):
    """Represents <ui:switch> - Toggle switch widget."""

    def __init__(self):
        self.bind: Optional[str] = None
        self.label: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_switch", "bind": self.bind, "label": self.label}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UISelectNode(QuantumNode, UILayoutMixin):
    """Represents <ui:select> - Dropdown select widget."""

    def __init__(self):
        self.bind: Optional[str] = None
        self.options: Optional[str] = None
        self.source: Optional[str] = None
        self.children: List[QuantumNode] = []  # UIOptionNode children
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_select", "bind": self.bind,
             "options": self.options, "source": self.source,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UITableNode(QuantumNode, UILayoutMixin):
    """Represents <ui:table> - Data table widget."""

    def __init__(self):
        self.source: Optional[str] = None
        self.children: List[QuantumNode] = []  # UIColumnNode children
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_table", "source": self.source,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIColumnNode(QuantumNode):
    """Represents <ui:column> - Table column definition."""

    def __init__(self):
        self.key: Optional[str] = None
        self.label: Optional[str] = None
        self.column_width: Optional[str] = None
        self.align: Optional[str] = None  # left, center, right

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "ui_column", "key": self.key,
                "label": self.label, "width": self.column_width,
                "align": self.align}

    def validate(self) -> List[str]:
        errors = []
        if not self.key:
            errors.append("Column key is required")
        return errors


class UIListNode(QuantumNode, UILayoutMixin):
    """Represents <ui:list> - Repeating list widget."""

    def __init__(self):
        self.source: Optional[str] = None
        self.as_var: Optional[str] = None  # loop variable name
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_list", "source": self.source,
             "as": self.as_var, "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIItemNode(QuantumNode, UILayoutMixin):
    """Represents <ui:item> - List item container."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_item", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIImageNode(QuantumNode, UILayoutMixin):
    """Represents <ui:image> - Image display widget."""

    def __init__(self):
        self.src: Optional[str] = None
        self.alt: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_image", "src": self.src, "alt": self.alt}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if not self.src:
            errors.append("Image src is required")
        return errors


class UILinkNode(QuantumNode, UILayoutMixin):
    """Represents <ui:link> - Hyperlink widget."""

    def __init__(self):
        self.to: Optional[str] = None
        self.external: bool = False
        self.content: str = ""
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_link", "to": self.to,
             "external": self.external, "content": self.content}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if not self.to:
            errors.append("Link 'to' attribute is required")
        return errors


class UIProgressNode(QuantumNode, UILayoutMixin):
    """Represents <ui:progress> - Progress bar widget."""

    def __init__(self):
        self.value: Optional[str] = None
        self.max: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_progress", "value": self.value, "max": self.max}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UITreeNode(QuantumNode, UILayoutMixin):
    """Represents <ui:tree> - Tree view widget."""

    def __init__(self):
        self.source: Optional[str] = None
        self.on_select: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_tree", "source": self.source,
             "on_select": self.on_select}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIMenuNode(QuantumNode, UILayoutMixin):
    """Represents <ui:menu> - Menu container."""

    def __init__(self):
        self.children: List[QuantumNode] = []  # UIOptionNode children
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_menu", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIOptionNode(QuantumNode):
    """Represents <ui:option> - Menu/select option."""

    def __init__(self):
        self.value: Optional[str] = None
        self.label: Optional[str] = None
        self.on_click: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "ui_option", "value": self.value,
                "label": self.label, "on_click": self.on_click}

    def validate(self) -> List[str]:
        return []


class UILogNode(QuantumNode, UILayoutMixin):
    """Represents <ui:log> - Scrollable log output widget."""

    def __init__(self):
        self.auto_scroll: bool = True
        self.max_lines: Optional[int] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_log", "auto_scroll": self.auto_scroll,
             "max_lines": self.max_lines}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIMarkdownNode(QuantumNode, UILayoutMixin):
    """Represents <ui:markdown> - Markdown rendered content."""

    def __init__(self):
        self.content: str = ""
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_markdown", "content_length": len(self.content)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIHeaderNode(QuantumNode, UILayoutMixin):
    """Represents <ui:header> - Page/window header."""

    def __init__(self):
        self.title: Optional[str] = None
        self.content: str = ""
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_header", "title": self.title,
             "content": self.content, "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIFooterNode(QuantumNode, UILayoutMixin):
    """Represents <ui:footer> - Page/window footer."""

    def __init__(self):
        self.content: str = ""
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_footer", "content": self.content,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIRuleNode(QuantumNode):
    """Represents <ui:rule> - Horizontal rule/separator."""

    def __init__(self):
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "ui_rule"}

    def validate(self) -> List[str]:
        return []


class UILoadingNode(QuantumNode, UILayoutMixin):
    """Represents <ui:loading> - Loading indicator widget."""

    def __init__(self):
        self.text: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_loading", "text": self.text}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UIBadgeNode(QuantumNode, UILayoutMixin):
    """Represents <ui:badge> - Small status badge."""

    def __init__(self):
        self.content: str = ""
        self.variant: Optional[str] = None  # primary, secondary, danger, success, warning
        self.badge_color: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_badge", "content": self.content,
             "variant": self.variant, "color": self.badge_color}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


# ============================================
# ANIMATION MIXIN
# ============================================

class UIAnimationMixin:
    """Shared animation attributes for UI components that support animations."""

    # Valid animation types
    ANIMATION_TYPES = ('fade', 'slide', 'scale', 'rotate', 'slide-left', 'slide-right',
                       'slide-up', 'slide-down', 'fade-in', 'fade-out', 'scale-in',
                       'scale-out', 'bounce', 'pulse', 'shake')

    # Valid animation triggers
    ANIMATION_TRIGGERS = ('on-load', 'on-hover', 'on-click', 'on-visible', 'none')

    # Valid easing functions
    EASING_FUNCTIONS = ('ease', 'ease-in', 'ease-out', 'ease-in-out', 'linear',
                        'spring', 'bounce')

    def _init_animation_attrs(self):
        """Initialize animation attributes."""
        self.animate: Optional[str] = None          # Animation preset (e.g., 'slide-in-left')
        self.transition: Optional[str] = None       # Transition shorthand (e.g., 'scale:0.95:100ms')
        self.anim_type: Optional[str] = None        # Animation type for ui:animate
        self.anim_duration: Optional[str] = None    # Duration in ms or CSS format
        self.anim_delay: Optional[str] = None       # Delay in ms or CSS format
        self.anim_easing: Optional[str] = None      # Easing function
        self.anim_repeat: Optional[str] = None      # Repeat count ('1', '2', 'infinite')
        self.anim_trigger: Optional[str] = None     # Trigger: on-load, on-hover, on-click, on-visible
        self.anim_direction: Optional[str] = None   # normal, reverse, alternate, alternate-reverse

    def _animation_to_dict(self) -> Dict[str, Any]:
        """Return animation attributes as dict."""
        d = {}
        for attr in ('animate', 'transition', 'anim_type', 'anim_duration',
                     'anim_delay', 'anim_easing', 'anim_repeat', 'anim_trigger',
                     'anim_direction'):
            val = getattr(self, attr, None)
            if val is not None:
                d[attr] = val
        return d

    def _validate_animation(self) -> List[str]:
        """Validate animation attributes."""
        errors = []
        if self.anim_type and self.anim_type not in self.ANIMATION_TYPES:
            errors.append(f"Invalid animation type: {self.anim_type}")
        if self.anim_trigger and self.anim_trigger not in self.ANIMATION_TRIGGERS:
            errors.append(f"Invalid animation trigger: {self.anim_trigger}")
        if self.anim_easing and self.anim_easing not in self.EASING_FUNCTIONS:
            errors.append(f"Invalid easing function: {self.anim_easing}")
        return errors

    def has_animation(self) -> bool:
        """Check if this node has any animation configured."""
        return any([
            self.animate,
            self.transition,
            self.anim_type,
        ])


# ============================================
# ANIMATION NODE
# ============================================

class UIAnimateNode(QuantumNode, UILayoutMixin, UIAnimationMixin):
    """
    Represents <ui:animate> - Animation wrapper container.

    Wraps child elements and applies animation effects.

    Syntax examples:
        <ui:animate type="fade" duration="300" trigger="on-load">
            <ui:panel>Content fades in</ui:panel>
        </ui:animate>

        <ui:animate type="slide-left" delay="200" easing="ease-out">
            <ui:text>Slides in from left</ui:text>
        </ui:animate>
    """

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()
        self._init_animation_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "type": "ui_animate",
            "children_count": len(self.children),
        }
        d.update(self._layout_to_dict())
        d.update(self._animation_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        errors.extend(self._validate_animation())
        if not self.anim_type and not self.animate:
            errors.append("ui:animate requires 'type' or 'animate' attribute")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


# ============================================
# COMPONENT LIBRARY NODES
# ============================================

class UICardNode(QuantumNode, UILayoutMixin):
    """Represents <ui:card> - Card with header, body, footer."""

    def __init__(self):
        self.title: Optional[str] = None
        self.subtitle: Optional[str] = None
        self.image: Optional[str] = None  # Header image URL
        self.variant: Optional[str] = None  # default, elevated, outlined
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_card", "title": self.title,
             "subtitle": self.subtitle, "image": self.image,
             "variant": self.variant, "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UICardHeaderNode(QuantumNode, UILayoutMixin):
    """Represents <ui:card-header> - Card header section."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_card_header", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UICardBodyNode(QuantumNode, UILayoutMixin):
    """Represents <ui:card-body> - Card body section."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_card_body", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UICardFooterNode(QuantumNode, UILayoutMixin):
    """Represents <ui:card-footer> - Card footer section."""

    def __init__(self):
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_card_footer", "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIModalNode(QuantumNode, UILayoutMixin):
    """Represents <ui:modal> - Modal/dialog with open/close."""

    def __init__(self):
        self.title: Optional[str] = None
        self.modal_id: Optional[str] = None  # Unique ID for targeting
        self.open: bool = False  # Initial state
        self.closable: bool = True  # Show close button
        self.size: Optional[str] = None  # sm, md, lg, xl, full
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_modal", "title": self.title,
             "modal_id": self.modal_id, "open": self.open,
             "closable": self.closable, "size": self.size,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIChartNode(QuantumNode, UILayoutMixin):
    """Represents <ui:chart> - Simple charts (bar, line, pie)."""

    def __init__(self):
        self.chart_type: str = "bar"  # bar, line, pie, doughnut
        self.source: Optional[str] = None  # Data source binding
        self.labels: Optional[str] = None  # Comma-separated labels
        self.values: Optional[str] = None  # Comma-separated values
        self.title: Optional[str] = None
        self.colors: Optional[str] = None  # Comma-separated colors
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_chart", "chart_type": self.chart_type,
             "source": self.source, "labels": self.labels,
             "values": self.values, "title": self.title,
             "colors": self.colors}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.chart_type not in ('bar', 'line', 'pie', 'doughnut'):
            errors.append(f"Invalid chart type: {self.chart_type}")
        return errors


class UIAvatarNode(QuantumNode, UILayoutMixin):
    """Represents <ui:avatar> - User avatar with image/initials."""

    def __init__(self):
        self.src: Optional[str] = None  # Image URL
        self.name: Optional[str] = None  # Name for initials fallback
        self.size: Optional[str] = None  # xs, sm, md, lg, xl
        self.shape: str = "circle"  # circle, square
        self.status: Optional[str] = None  # online, offline, away, busy
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_avatar", "src": self.src,
             "name": self.name, "size": self.size,
             "shape": self.shape, "status": self.status}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.shape not in ('circle', 'square'):
            errors.append(f"Invalid avatar shape: {self.shape}")
        return errors


class UITooltipNode(QuantumNode, UILayoutMixin):
    """Represents <ui:tooltip> - Tooltip on hover."""

    def __init__(self):
        self.content: str = ""  # Tooltip text
        self.position: str = "top"  # top, bottom, left, right
        self.children: List[QuantumNode] = []  # Element to attach tooltip to
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_tooltip", "content": self.content,
             "position": self.position, "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.position not in ('top', 'bottom', 'left', 'right'):
            errors.append(f"Invalid tooltip position: {self.position}")
        return errors


class UIDropdownNode(QuantumNode, UILayoutMixin):
    """Represents <ui:dropdown> - Dropdown menu."""

    def __init__(self):
        self.label: Optional[str] = None  # Trigger button label
        self.trigger: str = "click"  # click, hover
        self.dropdown_align: str = "left"  # left, right
        self.children: List[QuantumNode] = []  # UIOptionNode children
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_dropdown", "label": self.label,
             "trigger": self.trigger, "dropdown_align": self.dropdown_align,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.trigger not in ('click', 'hover'):
            errors.append(f"Invalid dropdown trigger: {self.trigger}")
        return errors


class UIAlertNode(QuantumNode, UILayoutMixin):
    """Represents <ui:alert> - Alert/notification box."""

    def __init__(self):
        self.content: str = ""
        self.title: Optional[str] = None
        self.variant: str = "info"  # info, success, warning, danger
        self.dismissible: bool = False
        self.icon: Optional[str] = None  # Icon name
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_alert", "content": self.content,
             "title": self.title, "variant": self.variant,
             "dismissible": self.dismissible, "icon": self.icon,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.variant not in ('info', 'success', 'warning', 'danger'):
            errors.append(f"Invalid alert variant: {self.variant}")
        return errors


class UIBreadcrumbNode(QuantumNode, UILayoutMixin):
    """Represents <ui:breadcrumb> - Navigation breadcrumbs."""

    def __init__(self):
        self.separator: str = "/"  # Separator character
        self.children: List[QuantumNode] = []  # UIBreadcrumbItemNode children
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_breadcrumb", "separator": self.separator,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UIBreadcrumbItemNode(QuantumNode):
    """Represents <ui:breadcrumb-item> - Individual breadcrumb item."""

    def __init__(self):
        self.label: str = ""
        self.to: Optional[str] = None  # Link URL (None = current/last item)
        self.icon: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "ui_breadcrumb_item", "label": self.label,
                "to": self.to, "icon": self.icon}

    def validate(self) -> List[str]:
        return []


class UIPaginationNode(QuantumNode, UILayoutMixin):
    """Represents <ui:pagination> - Pagination controls."""

    def __init__(self):
        self.total: Optional[str] = None  # Total items
        self.page_size: str = "10"  # Items per page
        self.current: str = "1"  # Current page
        self.bind: Optional[str] = None  # Binding for current page
        self.on_change: Optional[str] = None  # Callback on page change
        self.show_total: bool = False  # Show total items count
        self.show_jump: bool = False  # Show page jump input
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_pagination", "total": self.total,
             "page_size": self.page_size, "current": self.current,
             "bind": self.bind, "on_change": self.on_change,
             "show_total": self.show_total, "show_jump": self.show_jump}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


class UISkeletonNode(QuantumNode, UILayoutMixin):
    """Represents <ui:skeleton> - Loading skeleton placeholder."""

    def __init__(self):
        self.variant: str = "text"  # text, circle, rect, card
        self.lines: int = 1  # Number of lines for text variant
        self.animated: bool = True  # Animate the skeleton
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_skeleton", "variant": self.variant,
             "lines": self.lines, "animated": self.animated}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        if self.variant not in ('text', 'circle', 'rect', 'card'):
            errors.append(f"Invalid skeleton variant: {self.variant}")
        return errors
