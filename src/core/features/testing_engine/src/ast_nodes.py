"""
AST Nodes for Testing Engine (qtest: namespace)

All testing-specific AST nodes for the Quantum Testing Engine.
These represent test suites, cases, assertions, browser interactions,
and advanced testing features that compile to pytest + Playwright Python code.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


# ============================================
# CORE TESTING NODES
# ============================================

class QTestSuiteNode(QuantumNode):
    """Represents <qtest:suite> - Top-level test suite container."""

    def __init__(self, name: str):
        self.name = name
        self.browser: bool = False
        self.parallel: bool = False
        self.workers: int = 1
        self.browsers: Optional[str] = None  # comma-separated: "chromium,firefox"
        self.device: Optional[str] = None
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_suite",
            "name": self.name,
            "browser": self.browser,
            "parallel": self.parallel,
            "workers": self.workers,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Test suite name is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class QTestCaseNode(QuantumNode):
    """Represents <qtest:case> - Individual test case."""

    def __init__(self, name: str):
        self.name = name
        self.browser: bool = False
        self.auth: Optional[str] = None
        self.device: Optional[str] = None
        self.viewports: Optional[str] = None  # comma-separated
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_case",
            "name": self.name,
            "browser": self.browser,
            "auth": self.auth,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Test case name is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class ExpectNode(QuantumNode):
    """Represents <qtest:expect> - Assertion."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.visible: Optional[bool] = None
        self.hidden: Optional[bool] = None
        self.text: Optional[str] = None
        self.text_contains: Optional[str] = None
        self.equals: Optional[str] = None
        self.count: Optional[int] = None
        self.url: Optional[str] = None
        self.url_contains: Optional[str] = None
        self.var: Optional[str] = None
        self.value: Optional[str] = None
        self.enabled: Optional[bool] = None
        self.disabled: Optional[bool] = None
        self.checked: Optional[bool] = None
        self.has_class: Optional[str] = None
        self.has_attribute: Optional[str] = None
        self.not_: bool = False  # negate assertion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_expect",
            "selector": self.selector,
            "visible": self.visible,
            "text": self.text,
            "equals": self.equals,
            "var": self.var,
            "not": self.not_,
        }

    def validate(self) -> List[str]:
        errors = []
        has_assertion = any([
            self.visible is not None, self.hidden is not None,
            self.text is not None, self.text_contains is not None,
            self.equals is not None, self.count is not None,
            self.url is not None, self.url_contains is not None,
            self.value is not None, self.enabled is not None,
            self.disabled is not None, self.checked is not None,
            self.has_class is not None, self.has_attribute is not None,
        ])
        if not has_assertion and not self.selector:
            errors.append("Expect requires at least one assertion attribute or a selector")
        if self.visible is True and self.hidden is True:
            errors.append("Expect has contradictory assertions: visible=True and hidden=True")
        return errors


class MockNode_Testing(QuantumNode):
    """Represents <qtest:mock> - Mock services/queries."""

    def __init__(self):
        self.query: Optional[str] = None
        self.service: Optional[str] = None
        self.auto_generate: bool = False
        self.when: Optional[str] = None
        self.return_value: Optional[str] = None  # inline text content
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_mock",
            "query": self.query,
            "service": self.service,
            "auto_generate": self.auto_generate,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.query and not self.service:
            errors.append("Mock requires 'query' or 'service' attribute")
        return errors


class FixtureNode_Testing(QuantumNode):
    """Represents <qtest:fixture> - Test data fixture."""

    def __init__(self, name: str):
        self.name = name
        self.file: Optional[str] = None
        self.scope: str = "function"  # function, class, module, session
        self.data: Optional[str] = None  # inline JSON content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_fixture",
            "name": self.name,
            "file": self.file,
            "scope": self.scope,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Fixture name is required")
        if self.scope not in ('function', 'class', 'module', 'session'):
            errors.append(f"Invalid fixture scope: {self.scope}")
        return errors


class SetupNode_Testing(QuantumNode):
    """Represents <qtest:setup> - Before-all hook."""

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_setup",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class TeardownNode_Testing(QuantumNode):
    """Represents <qtest:teardown> - After-all hook."""

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_teardown",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class BeforeEachNode(QuantumNode):
    """Represents <qtest:before-each> - Before-each test hook."""

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_before_each",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class AfterEachNode(QuantumNode):
    """Represents <qtest:after-each> - After-each test hook."""

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_after_each",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class GenerateNode(QuantumNode):
    """Represents <qtest:generate> - Auto-generate tests."""

    def __init__(self):
        self.component: Optional[str] = None
        self.coverage: Optional[str] = None  # "full", "basic"
        self.include: Optional[str] = None  # comma-separated features

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_generate",
            "component": self.component,
            "coverage": self.coverage,
            "include": self.include,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.component:
            errors.append("Generate requires 'component' attribute")
        return errors


class ScenarioNode(QuantumNode):
    """Represents <qtest:scenario> - BDD scenario."""

    def __init__(self, name: str):
        self.name = name
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_scenario",
            "name": self.name,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Scenario name is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class GivenNode(QuantumNode):
    """Represents <qtest:given> - BDD given step."""

    def __init__(self, text: str):
        self.text = text
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_given",
            "text": self.text,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.text:
            errors.append("Given step text is required")
        return errors


class WhenNode(QuantumNode):
    """Represents <qtest:when> - BDD when step."""

    def __init__(self, text: str):
        self.text = text
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_when",
            "text": self.text,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.text:
            errors.append("When step text is required")
        return errors


class ThenNode(QuantumNode):
    """Represents <qtest:then> - BDD then step."""

    def __init__(self, text: str):
        self.text = text
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_then",
            "text": self.text,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.text:
            errors.append("Then step text is required")
        return errors


# ============================================
# BROWSER TESTING NODES
# ============================================

class BrowserConfigNode(QuantumNode):
    """Represents <qtest:browser-config> - Browser configuration."""

    def __init__(self):
        self.engine: str = "chromium"  # chromium, firefox, webkit
        self.headless: bool = True
        self.viewport_width: int = 1280
        self.viewport_height: int = 720
        self.locale: Optional[str] = None
        self.timezone: Optional[str] = None
        self.base_url: Optional[str] = None
        self.timeout: int = 30000
        self.video: bool = False
        self.trace: bool = False
        self.screenshot: Optional[str] = None  # "on", "off", "only-on-failure"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_browser_config",
            "engine": self.engine,
            "headless": self.headless,
            "base_url": self.base_url,
            "timeout": self.timeout,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.engine not in ('chromium', 'firefox', 'webkit'):
            errors.append(f"Invalid browser engine: {self.engine}")
        return errors


class NavigateNode(QuantumNode):
    """Represents <qtest:navigate> - Browser navigation."""

    def __init__(self):
        self.to: Optional[str] = None
        self.back: bool = False
        self.forward: bool = False
        self.wait: Optional[str] = None  # "load", "domcontentloaded", "networkidle"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_navigate",
            "to": self.to,
            "back": self.back,
            "forward": self.forward,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.to and not self.back and not self.forward:
            errors.append("Navigate requires 'to', 'back', or 'forward'")
        return errors


class ClickNode(QuantumNode):
    """Represents <qtest:click> - Click action."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.text: Optional[str] = None
        self.role: Optional[str] = None
        self.test_id: Optional[str] = None
        self.xpath: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_click",
            "selector": self.selector,
            "text": self.text,
            "role": self.role,
            "test_id": self.test_id,
        }

    def validate(self) -> List[str]:
        errors = []
        if not any([self.selector, self.text, self.role, self.test_id, self.xpath]):
            errors.append("Click requires a target (selector, text, role, test_id, or xpath)")
        return errors


class DblClickNode(QuantumNode):
    """Represents <qtest:dblclick> - Double click action."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.text: Optional[str] = None
        self.role: Optional[str] = None
        self.test_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_dblclick",
            "selector": self.selector,
        }

    def validate(self) -> List[str]:
        errors = []
        if not any([self.selector, self.text, self.role, self.test_id]):
            errors.append("DblClick requires a target")
        return errors


class RightClickNode(QuantumNode):
    """Represents <qtest:right-click> - Right click action."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.text: Optional[str] = None
        self.role: Optional[str] = None
        self.test_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_right_click",
            "selector": self.selector,
        }

    def validate(self) -> List[str]:
        errors = []
        if not any([self.selector, self.text, self.role, self.test_id]):
            errors.append("RightClick requires a target")
        return errors


class HoverNode(QuantumNode):
    """Represents <qtest:hover> - Hover action."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.text: Optional[str] = None
        self.role: Optional[str] = None
        self.test_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_hover",
            "selector": self.selector,
        }

    def validate(self) -> List[str]:
        errors = []
        if not any([self.selector, self.text, self.role, self.test_id]):
            errors.append("Hover requires a target")
        return errors


class FillNode(QuantumNode):
    """Represents <qtest:fill> - Form fill action."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.value: str = ""
        self.clear: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_fill",
            "selector": self.selector,
            "value": self.value,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Fill requires 'selector' attribute")
        return errors


class TypeNode_Testing(QuantumNode):
    """Represents <qtest:type> - Type text with delay."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.text: str = ""
        self.delay: int = 0  # ms between keystrokes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_type",
            "selector": self.selector,
            "text": self.text,
            "delay": self.delay,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Type requires 'selector' attribute")
        return errors


class SelectNode_Testing(QuantumNode):
    """Represents <qtest:select> - Dropdown select."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.value: Optional[str] = None
        self.values: Optional[str] = None  # comma-separated for multi-select

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_select",
            "selector": self.selector,
            "value": self.value,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Select requires 'selector' attribute")
        if not self.value and not self.values:
            errors.append("Select requires 'value' or 'values' attribute")
        return errors


class CheckNode(QuantumNode):
    """Represents <qtest:check> - Check checkbox."""

    def __init__(self):
        self.selector: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_check",
            "selector": self.selector,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Check requires 'selector' attribute")
        return errors


class UncheckNode(QuantumNode):
    """Represents <qtest:uncheck> - Uncheck checkbox."""

    def __init__(self):
        self.selector: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_uncheck",
            "selector": self.selector,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Uncheck requires 'selector' attribute")
        return errors


class KeyboardNode(QuantumNode):
    """Represents <qtest:keyboard> - Keyboard actions."""

    def __init__(self):
        self.press: Optional[str] = None
        self.type_text: Optional[str] = None
        self.delay: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_keyboard",
            "press": self.press,
            "type_text": self.type_text,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.press and not self.type_text:
            errors.append("Keyboard requires 'press' or 'type' attribute")
        return errors


class DragNode(QuantumNode):
    """Represents <qtest:drag> - Drag & drop action."""

    def __init__(self):
        self.from_sel: Optional[str] = None
        self.to_sel: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_drag",
            "from": self.from_sel,
            "to": self.to_sel,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.from_sel:
            errors.append("Drag requires 'from' attribute")
        if not self.to_sel:
            errors.append("Drag requires 'to' attribute")
        return errors


class ScrollNode_Testing(QuantumNode):
    """Represents <qtest:scroll> - Scroll action."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.direction: str = "down"  # up, down, left, right
        self.amount: Optional[int] = None
        self.to_element: Optional[str] = None
        self.to_top: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_scroll",
            "selector": self.selector,
            "direction": self.direction,
        }

    def validate(self) -> List[str]:
        return []


class UploadNode(QuantumNode):
    """Represents <qtest:upload> - File upload test."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.file: Optional[str] = None
        self.files: Optional[str] = None  # comma-separated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_upload",
            "selector": self.selector,
            "file": self.file,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Upload requires 'selector' attribute")
        if not self.file and not self.files:
            errors.append("Upload requires 'file' or 'files' attribute")
        return errors


class DownloadNode(QuantumNode):
    """Represents <qtest:download> - Download test."""

    def __init__(self):
        self.trigger_click: Optional[str] = None
        self.save_as: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_download",
            "trigger_click": self.trigger_click,
            "save_as": self.save_as,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.trigger_click:
            errors.append("Download requires 'trigger_click' attribute")
        return errors


class WaitForNode(QuantumNode):
    """Represents <qtest:wait-for> - Wait strategy."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.state: Optional[str] = None  # visible, hidden, attached, detached
        self.url: Optional[str] = None
        self.request: Optional[str] = None
        self.response: Optional[str] = None
        self.condition: Optional[str] = None
        self.timeout: Optional[int] = None
        self.has_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_wait_for",
            "selector": self.selector,
            "state": self.state,
            "url": self.url,
            "timeout": self.timeout,
        }

    def validate(self) -> List[str]:
        errors = []
        if not any([self.selector, self.url, self.request, self.response, self.condition]):
            errors.append("WaitFor requires a wait target")
        return errors


class ScreenshotNode(QuantumNode):
    """Represents <qtest:screenshot> - Take screenshot."""

    def __init__(self):
        self.name: Optional[str] = None
        self.selector: Optional[str] = None
        self.full_page: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_screenshot",
            "name": self.name,
            "selector": self.selector,
            "full_page": self.full_page,
        }

    def validate(self) -> List[str]:
        return []


class InterceptNode(QuantumNode):
    """Represents <qtest:intercept> - Network interception."""

    def __init__(self):
        self.method: Optional[str] = None
        self.url: Optional[str] = None
        self.delay: Optional[int] = None
        self.passthrough: bool = False
        self.spy: bool = False
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_intercept",
            "method": self.method,
            "url": self.url,
            "spy": self.spy,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.url:
            errors.append("Intercept requires 'url' attribute")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class InterceptRespondNode(QuantumNode):
    """Represents <qtest:respond> - Mock response for intercepted request."""

    def __init__(self):
        self.status: int = 200
        self.content_type: str = "application/json"
        self.file: Optional[str] = None
        self.body: Optional[str] = None  # inline response body

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_intercept_respond",
            "status": self.status,
            "content_type": self.content_type,
        }

    def validate(self) -> List[str]:
        return []


class FrameNode_Testing(QuantumNode):
    """Represents <qtest:frame> - iFrame context."""

    def __init__(self):
        self.selector: Optional[str] = None
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_frame",
            "selector": self.selector,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.selector:
            errors.append("Frame requires 'selector' attribute")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class PopupNode(QuantumNode):
    """Represents <qtest:popup> - Popup/new window context."""

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_popup",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class AuthNode(QuantumNode):
    """Represents <qtest:auth> - Authentication state."""

    def __init__(self):
        self.name: Optional[str] = None
        self.reuse: bool = True
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_auth",
            "name": self.name,
            "reuse": self.reuse,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Auth requires 'name' attribute")
        return errors


class SaveStateNode(QuantumNode):
    """Represents <qtest:save-state> - Save browser state."""

    def __init__(self):
        self.file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_save_state",
            "file": self.file,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.file:
            errors.append("SaveState requires 'file' attribute")
        return errors


class PauseNode(QuantumNode):
    """Represents <qtest:pause> - Debug pause."""

    def __init__(self):
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "test_pause"}

    def validate(self) -> List[str]:
        return []


# ============================================
# ADVANCED TESTING NODES
# ============================================

class SnapshotNode(QuantumNode):
    """Represents <qtest:snapshot> - Visual regression testing."""

    def __init__(self):
        self.name: Optional[str] = None
        self.threshold: float = 0.1
        self.ai_ignore: Optional[str] = None  # comma-separated selectors to ignore
        self.viewports: Optional[str] = None  # comma-separated viewport sizes
        self.mask_selectors: Optional[str] = None  # comma-separated selectors to mask

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_snapshot",
            "name": self.name,
            "threshold": self.threshold,
        }

    def validate(self) -> List[str]:
        return []


class FuzzNode(QuantumNode):
    """Represents <qtest:fuzz> - Fuzz testing."""

    def __init__(self):
        self.target: Optional[str] = None
        self.iterations: int = 100
        self.generators: Optional[str] = None
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_fuzz",
            "target": self.target,
            "iterations": self.iterations,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.target:
            errors.append("Fuzz requires 'target' attribute")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class PropertyNode(QuantumNode):
    """Represents <qtest:property> - Fuzz property assertion."""

    def __init__(self, text: str):
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_property",
            "text": self.text,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.text:
            errors.append("Property text is required")
        return errors


class FuzzFieldNode(QuantumNode):
    """Represents <qtest:field> - Field fuzz configuration."""

    def __init__(self):
        self.name: Optional[str] = None
        self.generator: Optional[str] = None  # "string", "int", "email", "xss", "sqli"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_fuzz_field",
            "name": self.name,
            "generator": self.generator,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Fuzz field 'name' is required")
        return errors


class PerfNode(QuantumNode):
    """Represents <qtest:perf> - Performance testing."""

    def __init__(self):
        self.baseline: Optional[str] = None
        self.regression_threshold: float = 0.1
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_perf",
            "baseline": self.baseline,
            "regression_threshold": self.regression_threshold,
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class PerfMetricNode(QuantumNode):
    """Represents <qtest:metric> - Performance metric."""

    def __init__(self):
        self.name: Optional[str] = None
        self.max_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_perf_metric",
            "name": self.name,
            "max_value": self.max_value,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Metric name is required")
        return errors


class A11yNode(QuantumNode):
    """Represents <qtest:a11y> - Accessibility testing."""

    def __init__(self):
        self.standard: str = "wcag2aa"  # wcag2a, wcag2aa, wcag2aaa
        self.check: Optional[str] = None  # comma-separated specific checks
        self.ignore: Optional[str] = None  # comma-separated rules to ignore

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_a11y",
            "standard": self.standard,
            "check": self.check,
            "ignore": self.ignore,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.standard not in ('wcag2a', 'wcag2aa', 'wcag2aaa'):
            errors.append(f"Invalid a11y standard: {self.standard}")
        return errors


class ChaosNode(QuantumNode):
    """Represents <qtest:chaos> - Chaos testing container."""

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_chaos",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class ChaosFailNode(QuantumNode):
    """Represents <qtest:fail> - Simulate service failure."""

    def __init__(self):
        self.service: Optional[str] = None
        self.probability: float = 1.0
        self.delay: Optional[int] = None  # ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_chaos_fail",
            "service": self.service,
            "probability": self.probability,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.service:
            errors.append("ChaosField requires 'service' attribute")
        return errors


class GeolocationNode(QuantumNode):
    """Represents <qtest:geolocation> - Mock geolocation."""

    def __init__(self):
        self.latitude: float = 0.0
        self.longitude: float = 0.0
        self.accuracy: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "test_geolocation",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
        }

    def validate(self) -> List[str]:
        return []
