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
    """Represents <ui:form> - Form container."""

    def __init__(self):
        self.on_submit: Optional[str] = None
        self.children: List[QuantumNode] = []
        self._init_layout_attrs()

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_form", "on_submit": self.on_submit,
             "children_count": len(self.children)}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        errors = self._validate_layout()
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
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
    """Represents <ui:input> - Text input widget."""

    def __init__(self):
        self.bind: Optional[str] = None
        self.placeholder: Optional[str] = None
        self.input_type: str = "text"    # text, password, email, number
        self.on_change: Optional[str] = None
        self.on_submit: Optional[str] = None
        self._init_layout_attrs()

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": "ui_input", "bind": self.bind,
             "placeholder": self.placeholder, "input_type": self.input_type}
        d.update(self._layout_to_dict())
        return d

    def validate(self) -> List[str]:
        return self._validate_layout()


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
