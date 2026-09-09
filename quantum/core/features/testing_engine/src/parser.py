"""
Testing Engine Parser - Parse qtest: namespace elements into Testing AST nodes.

This module provides parse functions for all testing-specific tags.
It is called from the main QuantumParser when a qtest: prefixed tag is encountered.
"""

from xml.etree import ElementTree as ET
from typing import Optional, List

from .ast_nodes import (
    # Core testing nodes
    QTestSuiteNode, QTestCaseNode, ExpectNode, MockNode_Testing,
    FixtureNode_Testing, SetupNode_Testing, TeardownNode_Testing,
    BeforeEachNode, AfterEachNode, GenerateNode,
    ScenarioNode, GivenNode, WhenNode, ThenNode,
    # Browser testing nodes
    BrowserConfigNode, NavigateNode, ClickNode, DblClickNode,
    RightClickNode, HoverNode, FillNode, TypeNode_Testing,
    SelectNode_Testing, CheckNode, UncheckNode, KeyboardNode,
    DragNode, ScrollNode_Testing, UploadNode, DownloadNode,
    WaitForNode, ScreenshotNode, InterceptNode, InterceptRespondNode,
    FrameNode_Testing, PopupNode, AuthNode, SaveStateNode, PauseNode,
    # Advanced testing nodes
    SnapshotNode, FuzzNode, PropertyNode, FuzzFieldNode,
    PerfNode, PerfMetricNode, A11yNode, ChaosNode, ChaosFailNode,
    GeolocationNode,
)


class TestingParseError(Exception):
    """Testing-specific parse error."""
    pass


class TestingParser:
    """Parser for qtest: namespace testing elements."""

    def __init__(self, parent_parser):
        """
        Args:
            parent_parser: The main QuantumParser instance, used to parse
                           q: namespace children (q:set, q:function, etc.)
        """
        self.parent = parent_parser

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    TESTING_TAG_MAP = {
        # Core testing
        'suite': '_parse_testing_suite',
        'case': '_parse_testing_case',
        'expect': '_parse_testing_expect',
        'mock': '_parse_testing_mock',
        'fixture': '_parse_testing_fixture',
        'setup': '_parse_testing_setup',
        'teardown': '_parse_testing_teardown',
        'before-each': '_parse_testing_before_each',
        'after-each': '_parse_testing_after_each',
        'generate': '_parse_testing_generate',
        'scenario': '_parse_testing_scenario',
        'given': '_parse_testing_given',
        'when': '_parse_testing_when',
        'then': '_parse_testing_then',
        # Browser testing
        'browser-config': '_parse_testing_browser_config',
        'navigate': '_parse_testing_navigate',
        'click': '_parse_testing_click',
        'dblclick': '_parse_testing_dblclick',
        'right-click': '_parse_testing_right_click',
        'hover': '_parse_testing_hover',
        'fill': '_parse_testing_fill',
        'type': '_parse_testing_type',
        'select': '_parse_testing_select',
        'check': '_parse_testing_check',
        'uncheck': '_parse_testing_uncheck',
        'keyboard': '_parse_testing_keyboard',
        'drag': '_parse_testing_drag',
        'scroll': '_parse_testing_scroll',
        'upload': '_parse_testing_upload',
        'download': '_parse_testing_download',
        'wait-for': '_parse_testing_wait_for',
        'screenshot': '_parse_testing_screenshot',
        'intercept': '_parse_testing_intercept',
        'respond': '_parse_testing_respond',
        'frame': '_parse_testing_frame',
        'popup': '_parse_testing_popup',
        'auth': '_parse_testing_auth',
        'save-state': '_parse_testing_save_state',
        'pause': '_parse_testing_pause',
        # Advanced testing
        'snapshot': '_parse_testing_snapshot',
        'fuzz': '_parse_testing_fuzz',
        'property': '_parse_testing_property',
        'field': '_parse_testing_field',
        'perf': '_parse_testing_perf',
        'metric': '_parse_testing_metric',
        'a11y': '_parse_testing_a11y',
        'chaos': '_parse_testing_chaos',
        'fail': '_parse_testing_fail',
        'geolocation': '_parse_testing_geolocation',
    }

    def parse_testing_element(self, local_name: str, element: ET.Element):
        """Dispatch a qtest: element to the correct parse method."""
        method_name = self.TESTING_TAG_MAP.get(local_name)
        if method_name is None:
            raise TestingParseError(f"Unknown testing tag: qtest:{local_name}")
        method = getattr(self, method_name)
        return method(element)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_local_name(self, element: ET.Element) -> str:
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[-1]
        if ':' in tag:
            return tag.split(':')[-1]
        return tag

    def _get_namespace(self, element: ET.Element) -> Optional[str]:
        tag = element.tag
        if '{https://quantum.lang/testing}' in tag:
            return 'testing'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('qtest:'):
            return 'testing'
        if tag.startswith('q:'):
            return 'quantum'
        return None

    def _parse_float(self, value: Optional[str], default: float = 0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _parse_int(self, value: Optional[str], default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _parse_bool(self, value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes')

    # ------------------------------------------------------------------
    # Parse children - dispatches both qtest: and q: tags
    # ------------------------------------------------------------------

    def _parse_child(self, child: ET.Element):
        """Parse a child element that can be either qtest: or q: namespace."""
        ns = self._get_namespace(child)
        local = self._get_local_name(child)

        if ns == 'testing':
            return self.parse_testing_element(local, child)
        elif ns == 'quantum':
            return self.parent._parse_statement(child)
        return None

    # ------------------------------------------------------------------
    # Core testing nodes
    # ------------------------------------------------------------------

    def _parse_testing_suite(self, element: ET.Element) -> QTestSuiteNode:
        name = element.get('name', 'default')
        node = QTestSuiteNode(name)
        node.browser = self._parse_bool(element.get('browser'))
        node.parallel = self._parse_bool(element.get('parallel'))
        node.workers = self._parse_int(element.get('workers'), 1)
        node.browsers = element.get('browsers')
        node.device = element.get('device')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_case(self, element: ET.Element) -> QTestCaseNode:
        name = element.get('name', '')
        node = QTestCaseNode(name)
        node.browser = self._parse_bool(element.get('browser'))
        node.auth = element.get('auth')
        node.device = element.get('device')
        node.viewports = element.get('viewports')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_expect(self, element: ET.Element) -> ExpectNode:
        node = ExpectNode()
        node.selector = element.get('selector')
        node.visible = self._parse_bool(element.get('visible')) if element.get('visible') else None
        node.hidden = self._parse_bool(element.get('hidden')) if element.get('hidden') else None
        node.text = element.get('text')
        node.text_contains = element.get('text-contains')
        node.equals = element.get('equals')
        node.count = self._parse_int(element.get('count')) if element.get('count') else None
        node.url = element.get('url')
        node.url_contains = element.get('url-contains')
        node.var = element.get('var')
        node.value = element.get('value')
        node.enabled = self._parse_bool(element.get('enabled')) if element.get('enabled') else None
        node.disabled = self._parse_bool(element.get('disabled')) if element.get('disabled') else None
        node.checked = self._parse_bool(element.get('checked')) if element.get('checked') else None
        node.has_class = element.get('has-class')
        node.has_attribute = element.get('has-attribute')
        node.not_ = self._parse_bool(element.get('not'))
        return node

    def _parse_testing_mock(self, element: ET.Element) -> MockNode_Testing:
        node = MockNode_Testing()
        node.query = element.get('query')
        node.service = element.get('service')
        node.auto_generate = self._parse_bool(element.get('auto-generate'))
        node.when = element.get('when')
        node.return_value = (element.text or '').strip() or None

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_fixture(self, element: ET.Element) -> FixtureNode_Testing:
        name = element.get('name', '')
        node = FixtureNode_Testing(name)
        node.file = element.get('file')
        node.scope = element.get('scope', 'function')
        node.data = (element.text or '').strip() or None
        return node

    def _parse_testing_setup(self, element: ET.Element) -> SetupNode_Testing:
        node = SetupNode_Testing()
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_teardown(self, element: ET.Element) -> TeardownNode_Testing:
        node = TeardownNode_Testing()
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_before_each(self, element: ET.Element) -> BeforeEachNode:
        node = BeforeEachNode()
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_after_each(self, element: ET.Element) -> AfterEachNode:
        node = AfterEachNode()
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_generate(self, element: ET.Element) -> GenerateNode:
        node = GenerateNode()
        node.component = element.get('component')
        node.coverage = element.get('coverage')
        node.include = element.get('include')
        return node

    def _parse_testing_scenario(self, element: ET.Element) -> ScenarioNode:
        name = element.get('name', '')
        node = ScenarioNode(name)
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_given(self, element: ET.Element) -> GivenNode:
        text = (element.text or '').strip()
        node = GivenNode(text)
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_when(self, element: ET.Element) -> WhenNode:
        text = (element.text or '').strip()
        node = WhenNode(text)
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_then(self, element: ET.Element) -> ThenNode:
        text = (element.text or '').strip()
        node = ThenNode(text)
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    # ------------------------------------------------------------------
    # Browser testing nodes
    # ------------------------------------------------------------------

    def _parse_testing_browser_config(self, element: ET.Element) -> BrowserConfigNode:
        node = BrowserConfigNode()
        node.engine = element.get('engine', 'chromium')
        node.headless = self._parse_bool(element.get('headless'), True)
        node.viewport_width = self._parse_int(element.get('viewport-width'), 1280)
        node.viewport_height = self._parse_int(element.get('viewport-height'), 720)
        node.locale = element.get('locale')
        node.timezone = element.get('timezone')
        node.base_url = element.get('base-url')
        node.timeout = self._parse_int(element.get('timeout'), 30000)
        node.video = self._parse_bool(element.get('video'))
        node.trace = self._parse_bool(element.get('trace'))
        node.screenshot = element.get('screenshot')
        return node

    def _parse_testing_navigate(self, element: ET.Element) -> NavigateNode:
        node = NavigateNode()
        node.to = element.get('to')
        node.back = self._parse_bool(element.get('back'))
        node.forward = self._parse_bool(element.get('forward'))
        node.wait = element.get('wait')
        return node

    def _parse_testing_click(self, element: ET.Element) -> ClickNode:
        node = ClickNode()
        node.selector = element.get('selector')
        node.text = element.get('text')
        node.role = element.get('role')
        node.test_id = element.get('test-id')
        node.xpath = element.get('xpath')
        return node

    def _parse_testing_dblclick(self, element: ET.Element) -> DblClickNode:
        node = DblClickNode()
        node.selector = element.get('selector')
        node.text = element.get('text')
        node.role = element.get('role')
        node.test_id = element.get('test-id')
        return node

    def _parse_testing_right_click(self, element: ET.Element) -> RightClickNode:
        node = RightClickNode()
        node.selector = element.get('selector')
        node.text = element.get('text')
        node.role = element.get('role')
        node.test_id = element.get('test-id')
        return node

    def _parse_testing_hover(self, element: ET.Element) -> HoverNode:
        node = HoverNode()
        node.selector = element.get('selector')
        node.text = element.get('text')
        node.role = element.get('role')
        node.test_id = element.get('test-id')
        return node

    def _parse_testing_fill(self, element: ET.Element) -> FillNode:
        node = FillNode()
        node.selector = element.get('selector')
        node.value = element.get('value', '')
        node.clear = self._parse_bool(element.get('clear'), True)
        return node

    def _parse_testing_type(self, element: ET.Element) -> TypeNode_Testing:
        node = TypeNode_Testing()
        node.selector = element.get('selector')
        node.text = element.get('text', '')
        node.delay = self._parse_int(element.get('delay'))
        return node

    def _parse_testing_select(self, element: ET.Element) -> SelectNode_Testing:
        node = SelectNode_Testing()
        node.selector = element.get('selector')
        node.value = element.get('value')
        node.values = element.get('values')
        return node

    def _parse_testing_check(self, element: ET.Element) -> CheckNode:
        node = CheckNode()
        node.selector = element.get('selector')
        return node

    def _parse_testing_uncheck(self, element: ET.Element) -> UncheckNode:
        node = UncheckNode()
        node.selector = element.get('selector')
        return node

    def _parse_testing_keyboard(self, element: ET.Element) -> KeyboardNode:
        node = KeyboardNode()
        node.press = element.get('press')
        node.type_text = element.get('type')
        node.delay = self._parse_int(element.get('delay'))
        return node

    def _parse_testing_drag(self, element: ET.Element) -> DragNode:
        node = DragNode()
        node.from_sel = element.get('from')
        node.to_sel = element.get('to')
        return node

    def _parse_testing_scroll(self, element: ET.Element) -> ScrollNode_Testing:
        node = ScrollNode_Testing()
        node.selector = element.get('selector')
        node.direction = element.get('direction', 'down')
        node.amount = self._parse_int(element.get('amount')) if element.get('amount') else None
        node.to_element = element.get('to-element')
        node.to_top = self._parse_bool(element.get('to-top'))
        return node

    def _parse_testing_upload(self, element: ET.Element) -> UploadNode:
        node = UploadNode()
        node.selector = element.get('selector')
        node.file = element.get('file')
        node.files = element.get('files')
        return node

    def _parse_testing_download(self, element: ET.Element) -> DownloadNode:
        node = DownloadNode()
        node.trigger_click = element.get('trigger-click')
        node.save_as = element.get('save-as')
        return node

    def _parse_testing_wait_for(self, element: ET.Element) -> WaitForNode:
        node = WaitForNode()
        node.selector = element.get('selector')
        node.state = element.get('state')
        node.url = element.get('url')
        node.request = element.get('request')
        node.response = element.get('response')
        node.condition = element.get('condition')
        node.timeout = self._parse_int(element.get('timeout')) if element.get('timeout') else None
        node.has_text = element.get('has-text')
        return node

    def _parse_testing_screenshot(self, element: ET.Element) -> ScreenshotNode:
        node = ScreenshotNode()
        node.name = element.get('name')
        node.selector = element.get('selector')
        node.full_page = self._parse_bool(element.get('full-page'))
        return node

    def _parse_testing_intercept(self, element: ET.Element) -> InterceptNode:
        node = InterceptNode()
        node.method = element.get('method')
        node.url = element.get('url')
        node.delay = self._parse_int(element.get('delay')) if element.get('delay') else None
        node.passthrough = self._parse_bool(element.get('passthrough'))
        node.spy = self._parse_bool(element.get('spy'))

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_respond(self, element: ET.Element) -> InterceptRespondNode:
        node = InterceptRespondNode()
        node.status = self._parse_int(element.get('status'), 200)
        node.content_type = element.get('content-type', 'application/json')
        node.file = element.get('file')
        node.body = (element.text or '').strip() or None
        return node

    def _parse_testing_frame(self, element: ET.Element) -> FrameNode_Testing:
        node = FrameNode_Testing()
        node.selector = element.get('selector')
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_popup(self, element: ET.Element) -> PopupNode:
        node = PopupNode()
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_auth(self, element: ET.Element) -> AuthNode:
        node = AuthNode()
        node.name = element.get('name')
        node.reuse = self._parse_bool(element.get('reuse'), True)
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_save_state(self, element: ET.Element) -> SaveStateNode:
        node = SaveStateNode()
        node.file = element.get('file')
        return node

    def _parse_testing_pause(self, element: ET.Element) -> PauseNode:
        return PauseNode()

    # ------------------------------------------------------------------
    # Advanced testing nodes
    # ------------------------------------------------------------------

    def _parse_testing_snapshot(self, element: ET.Element) -> SnapshotNode:
        node = SnapshotNode()
        node.name = element.get('name')
        node.threshold = self._parse_float(element.get('threshold'), 0.1)
        node.ai_ignore = element.get('ai-ignore')
        node.viewports = element.get('viewports')
        node.mask_selectors = element.get('mask-selectors')
        return node

    def _parse_testing_fuzz(self, element: ET.Element) -> FuzzNode:
        node = FuzzNode()
        node.target = element.get('target')
        node.iterations = self._parse_int(element.get('iterations'), 100)
        node.generators = element.get('generators')
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_property(self, element: ET.Element) -> PropertyNode:
        text = (element.text or '').strip()
        return PropertyNode(text)

    def _parse_testing_field(self, element: ET.Element) -> FuzzFieldNode:
        node = FuzzFieldNode()
        node.name = element.get('name')
        node.generator = element.get('generator')
        return node

    def _parse_testing_perf(self, element: ET.Element) -> PerfNode:
        node = PerfNode()
        node.baseline = element.get('baseline')
        node.regression_threshold = self._parse_float(element.get('regression-threshold'), 0.1)
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_metric(self, element: ET.Element) -> PerfMetricNode:
        node = PerfMetricNode()
        node.name = element.get('name')
        node.max_value = self._parse_float(element.get('max-value')) if element.get('max-value') else None
        return node

    def _parse_testing_a11y(self, element: ET.Element) -> A11yNode:
        node = A11yNode()
        node.standard = element.get('standard', 'wcag2aa')
        node.check = element.get('check')
        node.ignore = element.get('ignore')
        return node

    def _parse_testing_chaos(self, element: ET.Element) -> ChaosNode:
        node = ChaosNode()
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_testing_fail(self, element: ET.Element) -> ChaosFailNode:
        node = ChaosFailNode()
        node.service = element.get('service')
        node.probability = self._parse_float(element.get('probability'), 1.0)
        node.delay = self._parse_int(element.get('delay')) if element.get('delay') else None
        return node

    def _parse_testing_geolocation(self, element: ET.Element) -> GeolocationNode:
        node = GeolocationNode()
        node.latitude = self._parse_float(element.get('latitude'))
        node.longitude = self._parse_float(element.get('longitude'))
        node.accuracy = self._parse_float(element.get('accuracy'), 100.0)
        return node
