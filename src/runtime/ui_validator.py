"""
UI Engine - Cross-Target Validator

Analyzes UI AST to detect features that may not translate well between
different targets (HTML, Textual). Returns compatibility reports and warnings.

Usage:
    from runtime.ui_validator import UIValidator

    validator = UIValidator()
    report = validator.validate(app.ui_windows, app.ui_children)

    print(f"Compatibility Score: {report.compatibility_score}%")
    for warning in report.warnings:
        print(f"  - {warning}")
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from enum import Enum

from core.ast_nodes import QuantumNode
from core.features.ui_engine.src.ast_nodes import (
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


class Severity(Enum):
    """Warning severity levels."""
    INFO = "info"        # FYI, no impact
    WARNING = "warning"  # Works differently
    ERROR = "error"      # Does not work


@dataclass
class CompatibilityIssue:
    """Single compatibility issue."""
    feature: str
    message: str
    severity: Severity
    target: str  # Which target is affected
    node_type: str
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report."""
    issues: List[CompatibilityIssue] = field(default_factory=list)
    features_used: Set[str] = field(default_factory=set)
    widgets_count: int = 0
    containers_count: int = 0

    @property
    def compatibility_score(self) -> int:
        """Calculate compatibility score (0-100) based on issues."""
        if not self.issues:
            return 100

        # Weight by severity
        error_count = sum(1 for i in self.issues if i.severity == Severity.ERROR)
        warning_count = sum(1 for i in self.issues if i.severity == Severity.WARNING)
        info_count = sum(1 for i in self.issues if i.severity == Severity.INFO)

        # Calculate penalty
        total_elements = max(1, self.widgets_count + self.containers_count)
        penalty = (error_count * 20 + warning_count * 5 + info_count * 1)
        score = max(0, 100 - penalty)

        return score

    @property
    def html_compatible(self) -> bool:
        """Check if fully HTML compatible."""
        return not any(i.target == 'html' and i.severity == Severity.ERROR
                      for i in self.issues)

    @property
    def textual_compatible(self) -> bool:
        """Check if fully Textual compatible."""
        return not any(i.target == 'textual' and i.severity == Severity.ERROR
                      for i in self.issues)

    @property
    def warnings(self) -> List[str]:
        """Get formatted warning messages."""
        return [f"[{i.severity.value}] {i.feature}: {i.message}"
                for i in self.issues]


# Feature compatibility matrix
FEATURE_COMPAT = {
    # Feature: (html_support, textual_support, message, suggestion)
    'image': (True, 'degraded',
              "Images display as placeholder text in terminal",
              "Consider using ASCII art or omit images for TUI target"),

    'link_external': (True, 'degraded',
                      "External links are not clickable in terminal",
                      "Link URL is shown as text instead"),

    'gap': (True, False,
            "CSS gap property is not supported in Textual",
            "Layout may differ; children won't have automatic spacing"),

    'justify_between': (True, False,
                        "justify-content: space-between not available in Textual",
                        "Items will be centered instead"),

    'justify_around': (True, False,
                       "justify-content: space-around not available in Textual",
                       "Items will be centered instead"),

    'font_size': (True, False,
                  "Font sizes cannot be changed in terminal",
                  "Use text weight (bold) for emphasis instead"),

    'pixel_units': (True, 'converted',
                    "Pixel values are converted to character cells (÷8)",
                    "Results may vary; prefer tokens like 'sm', 'md', 'lg'"),

    'animation': (True, False,
                  "CSS animations are not supported in terminal",
                  None),

    'gradient': (True, False,
                 "CSS gradients are not supported in terminal",
                 "Use solid colors instead"),

    'shadow': (True, False,
               "Box shadows are not supported in terminal",
               None),

    'border_radius': (True, False,
                      "Border radius is not supported in terminal",
                      "Borders will appear rectangular"),
}


class UIValidator:
    """Validates UI AST for cross-target compatibility."""

    def __init__(self):
        self._report: ValidationReport = None
        self._target: str = 'all'  # 'html', 'textual', or 'all'

    def validate(self, windows: List[QuantumNode],
                 ui_children: List[QuantumNode],
                 target: str = 'all') -> ValidationReport:
        """
        Validate UI AST for target compatibility.

        Args:
            windows: List of UIWindowNode
            ui_children: List of top-level UI nodes
            target: 'html', 'textual', or 'all' (check both)

        Returns:
            ValidationReport with issues and compatibility score
        """
        self._report = ValidationReport()
        self._target = target

        # Walk all windows
        for window in windows:
            self._validate_node(window)

        # Walk top-level children
        for child in ui_children:
            self._validate_node(child)

        return self._report

    def _validate_node(self, node: QuantumNode):
        """Recursively validate a node and its children."""
        if node is None:
            return

        # Classify node
        if self._is_container(node):
            self._report.containers_count += 1
            self._validate_container(node)
        elif self._is_widget(node):
            self._report.widgets_count += 1
            self._validate_widget(node)

        # Validate layout attributes common to all nodes
        self._validate_layout_attrs(node)

        # Recurse into children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._validate_node(child)

    def _is_container(self, node) -> bool:
        """Check if node is a container type."""
        return isinstance(node, (
            UIWindowNode, UIHBoxNode, UIVBoxNode, UIPanelNode,
            UITabPanelNode, UITabNode, UIGridNode, UIAccordionNode,
            UISectionNode, UIDividedBoxNode, UIFormNode, UIFormItemNode,
            UIScrollBoxNode, UIListNode, UIItemNode, UIMenuNode,
        ))

    def _is_widget(self, node) -> bool:
        """Check if node is a widget type."""
        return isinstance(node, (
            UITextNode, UIButtonNode, UIInputNode, UICheckboxNode,
            UIRadioNode, UISwitchNode, UISelectNode, UITableNode,
            UIProgressNode, UITreeNode, UILogNode, UIMarkdownNode,
            UIHeaderNode, UIFooterNode, UIRuleNode, UILoadingNode,
            UIImageNode, UILinkNode, UIBadgeNode, UISpacerNode,
            UIColumnNode, UIOptionNode,
        ))

    def _validate_container(self, node):
        """Validate container-specific features."""
        pass  # Containers generally work well across targets

    def _validate_widget(self, node):
        """Validate widget-specific features."""
        # Image - limited in terminal
        if isinstance(node, UIImageNode):
            self._add_feature_issue('image', type(node).__name__)

        # External link - not clickable in terminal
        if isinstance(node, UILinkNode):
            if node.external:
                self._add_feature_issue('link_external', type(node).__name__)

        # Markdown - supported in both but rendering differs
        if isinstance(node, UIMarkdownNode):
            self._report.features_used.add('markdown')

    def _validate_layout_attrs(self, node):
        """Validate layout attributes for compatibility."""
        node_type = type(node).__name__

        # Gap
        if hasattr(node, 'gap') and node.gap:
            self._add_feature_issue('gap', node_type)

        # Justify
        if hasattr(node, 'justify') and node.justify:
            if node.justify == 'between':
                self._add_feature_issue('justify_between', node_type)
            elif node.justify == 'around':
                self._add_feature_issue('justify_around', node_type)

        # Pixel values
        if hasattr(node, 'width') and node.width:
            if self._is_pixel_value(node.width):
                self._add_feature_issue('pixel_units', node_type)

        if hasattr(node, 'height') and node.height:
            if self._is_pixel_value(node.height):
                self._add_feature_issue('pixel_units', node_type)

        if hasattr(node, 'padding') and node.padding:
            if self._is_pixel_value(node.padding):
                self._add_feature_issue('pixel_units', node_type)

        if hasattr(node, 'margin') and node.margin:
            if self._is_pixel_value(node.margin):
                self._add_feature_issue('pixel_units', node_type)

        # Font size
        if hasattr(node, 'size') and node.size:
            # For text nodes
            self._add_feature_issue('font_size', node_type)

    def _is_pixel_value(self, value: str) -> bool:
        """Check if value is a raw pixel value (not a token)."""
        if not value:
            return False
        value = str(value).strip().lower()
        # Check if it's a number or ends with 'px'
        if value.endswith('px'):
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _add_feature_issue(self, feature: str, node_type: str):
        """Add a feature compatibility issue to the report."""
        if feature in self._report.features_used:
            return  # Already reported

        self._report.features_used.add(feature)

        if feature not in FEATURE_COMPAT:
            return

        html_support, textual_support, message, suggestion = FEATURE_COMPAT[feature]

        # Determine severity for Textual target
        if textual_support is False:
            severity = Severity.WARNING
        elif textual_support == 'degraded':
            severity = Severity.INFO
        elif textual_support == 'converted':
            severity = Severity.INFO
        else:
            return  # Fully supported

        # Only add if checking this target
        if self._target in ('all', 'textual'):
            self._report.issues.append(CompatibilityIssue(
                feature=feature,
                message=message,
                severity=severity,
                target='textual',
                node_type=node_type,
                suggestion=suggestion,
            ))


def validate_cross_target(windows: List[QuantumNode],
                          ui_children: List[QuantumNode]) -> ValidationReport:
    """
    Convenience function to validate UI for cross-target compatibility.

    Args:
        windows: List of UIWindowNode
        ui_children: List of top-level UI nodes

    Returns:
        ValidationReport with compatibility score and issues
    """
    validator = UIValidator()
    return validator.validate(windows, ui_children)


def print_validation_report(report: ValidationReport):
    """Print a formatted validation report."""
    print(f"\n{'='*60}")
    print(f"UI Cross-Target Compatibility Report")
    print(f"{'='*60}")
    print(f"Containers: {report.containers_count}")
    print(f"Widgets: {report.widgets_count}")
    print(f"Compatibility Score: {report.compatibility_score}%")
    print(f"HTML Compatible: {'Yes' if report.html_compatible else 'No'}")
    print(f"Textual Compatible: {'Yes' if report.textual_compatible else 'No'}")

    if report.issues:
        print(f"\nIssues ({len(report.issues)}):")
        for issue in report.issues:
            icon = {'info': 'ℹ', 'warning': '⚠', 'error': '✖'}.get(issue.severity.value, '•')
            print(f"  {icon} [{issue.target}] {issue.feature}: {issue.message}")
            if issue.suggestion:
                print(f"    └─ Suggestion: {issue.suggestion}")
    else:
        print("\nNo compatibility issues found!")

    print(f"{'='*60}\n")
