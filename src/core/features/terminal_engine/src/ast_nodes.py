"""
AST Nodes for Terminal Engine (qt: namespace)

All terminal-specific AST nodes for the Quantum Terminal UI engine.
These represent TUI widgets, layouts, and interactions
that compile to Python Textual applications.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


# ============================================
# CORE TERMINAL NODES
# ============================================

class ScreenNode(QuantumNode):
    """Represents <qt:screen> - A full terminal screen (Textual Screen)."""

    def __init__(self, name: str):
        self.name = name
        self.title: Optional[str] = None
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_screen",
            "name": self.name,
            "title": self.title,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Screen name is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class PanelNode(QuantumNode):
    """Represents <qt:panel> - Container with border and title (Vertical + border CSS)."""

    def __init__(self):
        self.panel_id: Optional[str] = None
        self.title: Optional[str] = None
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_panel",
            "id": self.panel_id,
            "title": self.title,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class LayoutNode(QuantumNode):
    """Represents <qt:layout> - Horizontal/Vertical layout container."""

    def __init__(self):
        self.layout_id: Optional[str] = None
        self.direction: str = "vertical"  # horizontal, vertical
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_layout",
            "id": self.layout_id,
            "direction": self.direction,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if self.direction not in ('horizontal', 'vertical'):
            errors.append(f"Invalid layout direction: {self.direction}")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class TableNode(QuantumNode):
    """Represents <qt:table> - Data table (Textual DataTable)."""

    def __init__(self):
        self.table_id: Optional[str] = None
        self.data_source: Optional[str] = None
        self.zebra: bool = False
        self.columns: List['ColumnNode'] = []

    def add_column(self, col: 'ColumnNode'):
        self.columns.append(col)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_table",
            "id": self.table_id,
            "data_source": self.data_source,
            "zebra": self.zebra,
            "columns_count": len(self.columns),
        }

    def validate(self) -> List[str]:
        errors = []
        for col in self.columns:
            errors.extend(col.validate())
        return errors


class ColumnNode(QuantumNode):
    """Represents <qt:column> - Table column definition."""

    def __init__(self):
        self.name: str = ""
        self.key: str = ""
        self.width: Optional[int] = None
        self.align: str = "left"  # left, center, right

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_column",
            "name": self.name,
            "key": self.key,
            "width": self.width,
            "align": self.align,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Column name is required")
        if not self.key:
            errors.append("Column key is required")
        return errors


class TerminalInputNode(QuantumNode):
    """Represents <qt:input> - Text input field (Textual Input)."""

    def __init__(self):
        self.input_id: Optional[str] = None
        self.placeholder: Optional[str] = None
        self.on_submit: Optional[str] = None
        self.password: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_input",
            "id": self.input_id,
            "placeholder": self.placeholder,
            "on_submit": self.on_submit,
        }

    def validate(self) -> List[str]:
        return []


class ButtonNode(QuantumNode):
    """Represents <qt:button> - Clickable button (Textual Button)."""

    def __init__(self):
        self.button_id: Optional[str] = None
        self.label: str = ""
        self.variant: str = "default"  # default, primary, success, warning, error
        self.on_click: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_button",
            "id": self.button_id,
            "label": self.label,
            "variant": self.variant,
            "on_click": self.on_click,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.label:
            errors.append("Button label is required")
        return errors


class MenuNode(QuantumNode):
    """Represents <qt:menu> - Selection menu (Textual OptionList)."""

    def __init__(self):
        self.menu_id: Optional[str] = None
        self.on_select: Optional[str] = None
        self.options: List['OptionNode'] = []

    def add_option(self, opt: 'OptionNode'):
        self.options.append(opt)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_menu",
            "id": self.menu_id,
            "on_select": self.on_select,
            "options_count": len(self.options),
        }

    def validate(self) -> List[str]:
        return []


class OptionNode(QuantumNode):
    """Represents <qt:option> - Menu option item."""

    def __init__(self):
        self.value: str = ""
        self.label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_option",
            "value": self.value,
            "label": self.label,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.label:
            errors.append("Option label is required")
        return errors


class TextNode_Terminal(QuantumNode):
    """Represents <qt:text> - Styled text display (Textual Static with Rich markup)."""

    def __init__(self):
        self.text_id: Optional[str] = None
        self.content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_text",
            "id": self.text_id,
            "content": self.content,
        }

    def validate(self) -> List[str]:
        return []


class ProgressNode(QuantumNode):
    """Represents <qt:progress> - Progress bar (Textual ProgressBar)."""

    def __init__(self):
        self.progress_id: Optional[str] = None
        self.total: float = 100
        self.value_var: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_progress",
            "id": self.progress_id,
            "total": self.total,
            "value_var": self.value_var,
        }

    def validate(self) -> List[str]:
        return []


class TreeNode(QuantumNode):
    """Represents <qt:tree> - Tree view (Textual Tree/DirectoryTree)."""

    def __init__(self):
        self.tree_id: Optional[str] = None
        self.label: str = ""
        self.on_select: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_tree",
            "id": self.tree_id,
            "label": self.label,
            "on_select": self.on_select,
        }

    def validate(self) -> List[str]:
        return []


class TabsNode(QuantumNode):
    """Represents <qt:tabs> - Tabbed content container (Textual TabbedContent)."""

    def __init__(self):
        self.tabs_id: Optional[str] = None
        self.tabs: List['TabNode'] = []

    def add_tab(self, tab: 'TabNode'):
        self.tabs.append(tab)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_tabs",
            "id": self.tabs_id,
            "tabs_count": len(self.tabs),
        }

    def validate(self) -> List[str]:
        errors = []
        for tab in self.tabs:
            errors.extend(tab.validate())
        return errors


class TabNode(QuantumNode):
    """Represents <qt:tab> - Individual tab pane (Textual TabPane)."""

    def __init__(self):
        self.tab_id: Optional[str] = None
        self.title: str = ""
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_tab",
            "id": self.tab_id,
            "title": self.title,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.title:
            errors.append("Tab title is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class LogNode_Terminal(QuantumNode):
    """Represents <qt:log> - Scrollable log output (Textual RichLog)."""

    def __init__(self):
        self.log_id: Optional[str] = None
        self.auto_scroll: bool = True
        self.markup: bool = True
        self.max_lines: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_log",
            "id": self.log_id,
            "auto_scroll": self.auto_scroll,
            "markup": self.markup,
            "max_lines": self.max_lines,
        }

    def validate(self) -> List[str]:
        return []


class HeaderNode_Terminal(QuantumNode):
    """Represents <qt:header> - Fixed header bar (Textual Header)."""

    def __init__(self):
        self.title: Optional[str] = None
        self.show_clock: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_header",
            "title": self.title,
            "show_clock": self.show_clock,
        }

    def validate(self) -> List[str]:
        return []


class FooterNode(QuantumNode):
    """Represents <qt:footer> - Fixed footer bar (Textual Footer)."""

    def __init__(self):
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_footer",
        }

    def validate(self) -> List[str]:
        return []


class StatusNode(QuantumNode):
    """Represents <qt:status> - Status bar (Textual Static)."""

    def __init__(self):
        self.status_id: Optional[str] = None
        self.content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_status",
            "id": self.status_id,
            "content": self.content,
        }

    def validate(self) -> List[str]:
        return []


class KeybindingNode(QuantumNode):
    """Represents <qt:keybinding> - Keyboard shortcut (Textual Binding)."""

    def __init__(self):
        self.key: str = ""
        self.action: str = ""
        self.description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_keybinding",
            "key": self.key,
            "action": self.action,
            "description": self.description,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.key:
            errors.append("Keybinding key is required")
        if not self.action:
            errors.append("Keybinding action is required")
        return errors


class TimerNode_Terminal(QuantumNode):
    """Represents <qt:timer> - Periodic timer (set_interval)."""

    def __init__(self):
        self.timer_id: Optional[str] = None
        self.interval: float = 1.0
        self.action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_timer",
            "id": self.timer_id,
            "interval": self.interval,
            "action": self.action,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.action:
            errors.append("Timer action is required")
        if self.interval <= 0:
            errors.append("Timer interval must be positive")
        return errors


class ServiceNode(QuantumNode):
    """Represents <qt:service> - Background async worker."""

    def __init__(self):
        self.service_id: Optional[str] = None
        self.handler: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_service",
            "id": self.service_id,
            "handler": self.handler,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.handler:
            errors.append("Service handler is required")
        return errors


class CssNode(QuantumNode):
    """Represents <qt:css> - Textual CSS (TCSS) block."""

    def __init__(self):
        self.content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_css",
            "content_length": len(self.content),
        }

    def validate(self) -> List[str]:
        return []


class OnEventNode_Terminal(QuantumNode):
    """Represents <qt:on> - Event handler mapping."""

    def __init__(self):
        self.event: str = ""
        self.action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "terminal_on_event",
            "event": self.event,
            "action": self.action,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.event:
            errors.append("Event type is required")
        if not self.action:
            errors.append("Event action is required")
        return errors


class RawCodeNode_Terminal(QuantumNode):
    """Represents raw Python code inside a q:function in terminal context."""

    def __init__(self, code: str):
        self.code = code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "raw_code",
            "code": self.code,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.code or not self.code.strip():
            errors.append("RawCodeNode code is empty")
        return errors
