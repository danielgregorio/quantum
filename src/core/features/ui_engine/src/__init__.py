"""
UI Engine - Multi-target UI components (ui: namespace)

Compiles declarative XML to HTML/CSS, Python Textual (TUI), or Desktop (pywebview).
"""

from .ast_nodes import (
    UIWindowNode, UIHBoxNode, UIVBoxNode, UIPanelNode,
    UITabPanelNode, UITabNode, UIGridNode, UIAccordionNode,
    UISectionNode, UIDividedBoxNode, UIFormNode, UIFormItemNode,
    UISpacerNode, UIScrollBoxNode,
    UITextNode, UIButtonNode, UIInputNode, UICheckboxNode,
    UIRadioNode, UISwitchNode, UISelectNode, UITableNode,
    UIColumnNode, UIListNode, UIItemNode, UIImageNode,
    UILinkNode, UIProgressNode, UITreeNode, UIMenuNode,
    UIOptionNode, UILogNode, UIMarkdownNode, UIHeaderNode,
    UIFooterNode, UIRuleNode, UILoadingNode, UIBadgeNode,
)

from .parser import UIParser, UIParseError
