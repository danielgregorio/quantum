"""
Testing Engine - Code Generator

Transforms Testing AST into pytest Python code.

Pipeline: TestSuiteNode -> pytest class with test methods
"""

from typing import List, Dict, Optional, Any

from runtime.terminal_templates import PyBuilder, py_string, py_id
from runtime.testing_templates import (
    TEST_TEMPLATE, BROWSER_IMPORTS, sanitize_test_name, sanitize_class_name,
)

from core.features.testing_engine.src.ast_nodes import (
    # Core
    QTestSuiteNode, QTestCaseNode, ExpectNode, MockNode_Testing,
    FixtureNode_Testing, SetupNode_Testing, TeardownNode_Testing,
    BeforeEachNode, AfterEachNode, GenerateNode,
    ScenarioNode, GivenNode, WhenNode, ThenNode,
    # Browser
    BrowserConfigNode, NavigateNode, ClickNode, DblClickNode,
    RightClickNode, HoverNode, FillNode, TypeNode_Testing,
    SelectNode_Testing, CheckNode, UncheckNode, KeyboardNode,
    DragNode, ScrollNode_Testing, UploadNode, DownloadNode,
    WaitForNode, ScreenshotNode, InterceptNode, InterceptRespondNode,
    FrameNode_Testing, PopupNode, AuthNode, SaveStateNode, PauseNode,
    # Advanced
    SnapshotNode, FuzzNode, PropertyNode, FuzzFieldNode,
    PerfNode, PerfMetricNode, A11yNode, ChaosNode, ChaosFailNode,
    GeolocationNode,
)


class QTestCodeGenerator:
    """Generates standalone pytest file from Testing AST nodes."""

    def __init__(self):
        self._has_browser_tests = False
        self._fixtures: List[FixtureNode_Testing] = []
        self._mocks: List[MockNode_Testing] = []
        self._auth_states: List[AuthNode] = []
        self._browser_config: Optional[BrowserConfigNode] = None

    def generate(
        self,
        suites: List[QTestSuiteNode],
        title: str = "Quantum Tests",
        browser_config: Optional[BrowserConfigNode] = None,
        fixtures: Optional[List[FixtureNode_Testing]] = None,
        mocks: Optional[List[MockNode_Testing]] = None,
        auth_states: Optional[List[AuthNode]] = None,
    ) -> str:
        """Generate a complete pytest file from test suites."""
        self._browser_config = browser_config
        self._fixtures = fixtures or []
        self._mocks = mocks or []
        self._auth_states = auth_states or []
        self._has_browser_tests = False

        # Detect if any suite/case uses browser
        for suite in suites:
            if suite.browser:
                self._has_browser_tests = True
                break
            for child in suite.children:
                if isinstance(child, QTestCaseNode) and child.browser:
                    self._has_browser_tests = True
                    break

        py = PyBuilder()

        # Generate fixtures
        self._generate_fixtures(py)

        # Generate mock fixtures
        self._generate_mocks(py)

        # Generate auth state fixtures
        self._generate_auth_states(py)

        # Generate browser config fixture
        if self._has_browser_tests and self._browser_config:
            self._generate_browser_config_fixture(py)

        # Generate test classes from suites
        for suite in suites:
            self._generate_suite(py, suite)

        # Build final output
        extra_imports = ""
        if self._has_browser_tests:
            extra_imports = BROWSER_IMPORTS

        test_code = py.build()

        return TEST_TEMPLATE.format(
            title=title,
            filename=f"test_{sanitize_test_name(title)}.py",
            extra_imports=extra_imports,
            test_code=test_code,
        )

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _generate_fixtures(self, py: PyBuilder):
        for fixture in self._fixtures:
            scope = fixture.scope or 'function'
            py.decorator(f'pytest.fixture(scope="{scope}")')
            py.func_def(fixture.name)
            if fixture.data:
                py.line(f"return json.loads({py_string(fixture.data)})")
            elif fixture.file:
                py.line(f'with open({py_string(fixture.file)}) as f:')
                py.indent()
                py.line("return json.load(f)")
                py.end_block()
            else:
                py.line("return {}")
            py.end_block()
            py.blank()

    def _generate_mocks(self, py: PyBuilder):
        for mock in self._mocks:
            name = f"mock_{py_id(mock.query or mock.service or 'unknown')}"
            py.decorator('pytest.fixture')
            py.func_def(name)
            py.line(f"mock = MagicMock()")
            if mock.return_value:
                py.line(f"mock.return_value = json.loads({py_string(mock.return_value)})")
            py.line(f"return mock")
            py.end_block()
            py.blank()

    def _generate_auth_states(self, py: PyBuilder):
        for auth in self._auth_states:
            if not auth.name:
                continue
            name = f"auth_{py_id(auth.name)}"
            py.decorator('pytest.fixture')
            py.func_def(name, 'browser')
            py.line(f'context = browser.new_context(storage_state="{py_id(auth.name)}_state.json")')
            py.line(f"page = context.new_page()")
            # Generate auth steps
            for child in auth.children:
                self._generate_action(py, child, "page")
            py.line(f'context.storage_state(path="{py_id(auth.name)}_state.json")')
            py.line("yield page")
            py.line("context.close()")
            py.end_block()
            py.blank()

    def _generate_browser_config_fixture(self, py: PyBuilder):
        config = self._browser_config
        py.decorator('pytest.fixture(scope="session")')
        py.func_def('browser_context_args', 'browser_context_args')
        py.line("args = dict(browser_context_args or {})")
        if config.viewport_width and config.viewport_height:
            py.line(f'args["viewport"] = {{"width": {config.viewport_width}, "height": {config.viewport_height}}}')
        if config.locale:
            py.line(f'args["locale"] = {py_string(config.locale)}')
        if config.timezone:
            py.line(f'args["timezone_id"] = {py_string(config.timezone)}')
        if config.video:
            py.line('args["record_video_dir"] = "test-videos/"')
        py.line("return args")
        py.end_block()
        py.blank()

        if config.base_url:
            py.decorator('pytest.fixture(scope="session")')
            py.func_def('base_url')
            py.line(f'return {py_string(config.base_url)}')
            py.end_block()
            py.blank()

    # ------------------------------------------------------------------
    # Suite generation
    # ------------------------------------------------------------------

    def _generate_suite(self, py: PyBuilder, suite: QTestSuiteNode):
        class_name = sanitize_class_name(suite.name)
        py.blank()
        py.class_def(class_name)
        py.docstring(f"Test suite: {suite.name}")
        py.blank()

        has_content = False

        for child in suite.children:
            if isinstance(child, SetupNode_Testing):
                self._generate_setup(py, child)
                has_content = True
            elif isinstance(child, TeardownNode_Testing):
                self._generate_teardown(py, child)
                has_content = True
            elif isinstance(child, BeforeEachNode):
                self._generate_before_each(py, child, suite.browser)
                has_content = True
            elif isinstance(child, AfterEachNode):
                self._generate_after_each(py, child, suite.browser)
                has_content = True
            elif isinstance(child, QTestCaseNode):
                is_browser = child.browser or suite.browser
                self._generate_test_case(py, child, is_browser)
                has_content = True
            elif isinstance(child, ScenarioNode):
                self._generate_scenario(py, child, suite.browser)
                has_content = True

        if not has_content:
            py.pass_stmt()

        py.end_block()
        py.blank()

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _generate_setup(self, py: PyBuilder, node: SetupNode_Testing):
        py.decorator('classmethod')
        py.method_def('setup_class', 'cls')
        if node.children:
            for child in node.children:
                self._generate_action(py, child, "cls")
        else:
            py.pass_stmt()
        py.end_block()
        py.blank()

    def _generate_teardown(self, py: PyBuilder, node: TeardownNode_Testing):
        py.decorator('classmethod')
        py.method_def('teardown_class', 'cls')
        if node.children:
            for child in node.children:
                self._generate_action(py, child, "cls")
        else:
            py.pass_stmt()
        py.end_block()
        py.blank()

    def _generate_before_each(self, py: PyBuilder, node: BeforeEachNode, browser: bool):
        if browser:
            py.method_def('setup_method', 'self, page: Page')
        else:
            py.method_def('setup_method', 'self')
        if node.children:
            for child in node.children:
                self._generate_action(py, child, "page" if browser else "self")
        else:
            py.pass_stmt()
        py.end_block()
        py.blank()

    def _generate_after_each(self, py: PyBuilder, node: AfterEachNode, browser: bool):
        if browser:
            py.method_def('teardown_method', 'self, page: Page')
        else:
            py.method_def('teardown_method', 'self')
        if node.children:
            for child in node.children:
                self._generate_action(py, child, "page" if browser else "self")
        else:
            py.pass_stmt()
        py.end_block()
        py.blank()

    # ------------------------------------------------------------------
    # Test case generation
    # ------------------------------------------------------------------

    def _generate_test_case(self, py: PyBuilder, case: QTestCaseNode, is_browser: bool):
        method_name = f"test_{sanitize_test_name(case.name)}"

        if is_browser:
            py.method_def(method_name, 'self, page: Page')
        else:
            py.method_def(method_name, 'self')

        if not case.children:
            py.pass_stmt()
            py.end_block()
            py.blank()
            return

        page_var = "page" if is_browser else None

        for child in case.children:
            self._generate_action(py, child, page_var)

        py.end_block()
        py.blank()

    def _generate_scenario(self, py: PyBuilder, scenario: ScenarioNode, is_browser: bool):
        method_name = f"test_{sanitize_test_name(scenario.name)}"

        if is_browser:
            py.method_def(method_name, 'self, page: Page')
        else:
            py.method_def(method_name, 'self')

        page_var = "page" if is_browser else None

        for child in scenario.children:
            if isinstance(child, GivenNode):
                py.comment(f"Given: {child.text}")
                for step in child.children:
                    self._generate_action(py, step, page_var)
            elif isinstance(child, WhenNode):
                py.comment(f"When: {child.text}")
                for step in child.children:
                    self._generate_action(py, step, page_var)
            elif isinstance(child, ThenNode):
                py.comment(f"Then: {child.text}")
                for step in child.children:
                    self._generate_action(py, step, page_var)
            else:
                self._generate_action(py, child, page_var)

        if not scenario.children:
            py.pass_stmt()

        py.end_block()
        py.blank()

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    def _generate_action(self, py: PyBuilder, node, page_var: Optional[str] = None):
        """Generate code for a single action node."""
        if isinstance(node, ExpectNode):
            self._gen_expect(py, node, page_var)
        elif isinstance(node, NavigateNode):
            self._gen_navigate(py, node, page_var)
        elif isinstance(node, ClickNode):
            self._gen_click(py, node, page_var)
        elif isinstance(node, DblClickNode):
            self._gen_dblclick(py, node, page_var)
        elif isinstance(node, RightClickNode):
            self._gen_right_click(py, node, page_var)
        elif isinstance(node, HoverNode):
            self._gen_hover(py, node, page_var)
        elif isinstance(node, FillNode):
            self._gen_fill(py, node, page_var)
        elif isinstance(node, TypeNode_Testing):
            self._gen_type(py, node, page_var)
        elif isinstance(node, SelectNode_Testing):
            self._gen_select(py, node, page_var)
        elif isinstance(node, CheckNode):
            self._gen_check(py, node, page_var)
        elif isinstance(node, UncheckNode):
            self._gen_uncheck(py, node, page_var)
        elif isinstance(node, KeyboardNode):
            self._gen_keyboard(py, node, page_var)
        elif isinstance(node, DragNode):
            self._gen_drag(py, node, page_var)
        elif isinstance(node, ScrollNode_Testing):
            self._gen_scroll(py, node, page_var)
        elif isinstance(node, UploadNode):
            self._gen_upload(py, node, page_var)
        elif isinstance(node, DownloadNode):
            self._gen_download(py, node, page_var)
        elif isinstance(node, WaitForNode):
            self._gen_wait_for(py, node, page_var)
        elif isinstance(node, ScreenshotNode):
            self._gen_screenshot(py, node, page_var)
        elif isinstance(node, InterceptNode):
            self._gen_intercept(py, node, page_var)
        elif isinstance(node, FrameNode_Testing):
            self._gen_frame(py, node, page_var)
        elif isinstance(node, PopupNode):
            self._gen_popup(py, node, page_var)
        elif isinstance(node, SaveStateNode):
            self._gen_save_state(py, node, page_var)
        elif isinstance(node, PauseNode):
            self._gen_pause(py, node, page_var)
        elif isinstance(node, SnapshotNode):
            self._gen_snapshot(py, node, page_var)
        elif isinstance(node, FuzzNode):
            self._gen_fuzz(py, node, page_var)
        elif isinstance(node, PerfNode):
            self._gen_perf(py, node, page_var)
        elif isinstance(node, A11yNode):
            self._gen_a11y(py, node, page_var)
        elif isinstance(node, ChaosNode):
            self._gen_chaos(py, node, page_var)
        elif isinstance(node, GeolocationNode):
            self._gen_geolocation(py, node, page_var)

    # ------------------------------------------------------------------
    # Expect generation
    # ------------------------------------------------------------------

    def _gen_expect(self, py: PyBuilder, node: ExpectNode, page_var: Optional[str]):
        negate = node.not_

        # Variable-based assertions (non-browser)
        if node.var and node.equals is not None:
            if negate:
                py.line(f"assert {node.var} != {node.equals}")
            else:
                py.line(f"assert {node.var} == {node.equals}")
            return

        if node.var and node.text_contains is not None:
            if negate:
                py.line(f"assert {py_string(node.text_contains)} not in str({node.var})")
            else:
                py.line(f"assert {py_string(node.text_contains)} in str({node.var})")
            return

        # URL assertions
        if node.url and page_var:
            if negate:
                py.line(f'expect({page_var}).not_to_have_url({py_string(node.url)})')
            else:
                py.line(f'expect({page_var}).to_have_url({py_string(node.url)})')
            return

        if node.url_contains and page_var:
            import re
            if negate:
                py.line(f'expect({page_var}).not_to_have_url(re.compile({py_string(node.url_contains)}))')
            else:
                py.line(f'expect({page_var}).to_have_url(re.compile({py_string(node.url_contains)}))')
            return

        # Selector-based assertions (browser)
        if node.selector and page_var:
            locator = f'{page_var}.locator({py_string(node.selector)})'

            if node.visible is not None:
                if (node.visible and not negate) or (not node.visible and negate):
                    py.line(f"expect({locator}).to_be_visible()")
                else:
                    py.line(f"expect({locator}).not_to_be_visible()")

            if node.hidden is not None:
                if (node.hidden and not negate) or (not node.hidden and negate):
                    py.line(f"expect({locator}).to_be_hidden()")
                else:
                    py.line(f"expect({locator}).not_to_be_hidden()")

            if node.text is not None:
                if negate:
                    py.line(f"expect({locator}).not_to_have_text({py_string(node.text)})")
                else:
                    py.line(f"expect({locator}).to_have_text({py_string(node.text)})")

            if node.text_contains is not None:
                if negate:
                    py.line(f"expect({locator}).not_to_contain_text({py_string(node.text_contains)})")
                else:
                    py.line(f"expect({locator}).to_contain_text({py_string(node.text_contains)})")

            if node.count is not None:
                if negate:
                    py.line(f"expect({locator}).not_to_have_count({node.count})")
                else:
                    py.line(f"expect({locator}).to_have_count({node.count})")

            if node.value is not None:
                if negate:
                    py.line(f"expect({locator}).not_to_have_value({py_string(node.value)})")
                else:
                    py.line(f"expect({locator}).to_have_value({py_string(node.value)})")

            if node.enabled is not None:
                if (node.enabled and not negate) or (not node.enabled and negate):
                    py.line(f"expect({locator}).to_be_enabled()")
                else:
                    py.line(f"expect({locator}).to_be_disabled()")

            if node.disabled is not None:
                if (node.disabled and not negate) or (not node.disabled and negate):
                    py.line(f"expect({locator}).to_be_disabled()")
                else:
                    py.line(f"expect({locator}).to_be_enabled()")

            if node.checked is not None:
                if (node.checked and not negate) or (not node.checked and negate):
                    py.line(f"expect({locator}).to_be_checked()")
                else:
                    py.line(f"expect({locator}).not_to_be_checked()")

            if node.has_class is not None:
                if negate:
                    py.line(f"expect({locator}).not_to_have_class(re.compile({py_string(node.has_class)}))")
                else:
                    py.line(f"expect({locator}).to_have_class(re.compile({py_string(node.has_class)}))")

            if node.has_attribute is not None:
                if negate:
                    py.line(f"expect({locator}).not_to_have_attribute({py_string(node.has_attribute)})")
                else:
                    py.line(f"expect({locator}).to_have_attribute({py_string(node.has_attribute)})")

    # ------------------------------------------------------------------
    # Browser action generation
    # ------------------------------------------------------------------

    def _gen_navigate(self, py: PyBuilder, node: NavigateNode, page_var: Optional[str]):
        if not page_var:
            return
        if node.to:
            wait_arg = f', wait_until={py_string(node.wait)}' if node.wait else ''
            py.line(f'{page_var}.goto({py_string(node.to)}{wait_arg})')
        elif node.back:
            py.line(f'{page_var}.go_back()')
        elif node.forward:
            py.line(f'{page_var}.go_forward()')

    def _get_locator(self, node, page_var: str) -> str:
        """Build a Playwright locator expression from a node with selector/text/role/test_id."""
        if hasattr(node, 'test_id') and node.test_id:
            return f'{page_var}.get_by_test_id({py_string(node.test_id)})'
        if hasattr(node, 'role') and node.role:
            name_arg = f', name={py_string(node.text)}' if hasattr(node, 'text') and node.text else ''
            return f'{page_var}.get_by_role({py_string(node.role)}{name_arg})'
        if hasattr(node, 'text') and node.text and not (hasattr(node, 'selector') and node.selector):
            return f'{page_var}.get_by_text({py_string(node.text)})'
        if hasattr(node, 'xpath') and node.xpath:
            return f'{page_var}.locator({py_string("xpath=" + node.xpath)})'
        if hasattr(node, 'selector') and node.selector:
            return f'{page_var}.locator({py_string(node.selector)})'
        return f'{page_var}.locator("body")'

    def _gen_click(self, py: PyBuilder, node: ClickNode, page_var: Optional[str]):
        if not page_var:
            return
        locator = self._get_locator(node, page_var)
        py.line(f'{locator}.click()')

    def _gen_dblclick(self, py: PyBuilder, node: DblClickNode, page_var: Optional[str]):
        if not page_var:
            return
        locator = self._get_locator(node, page_var)
        py.line(f'{locator}.dblclick()')

    def _gen_right_click(self, py: PyBuilder, node: RightClickNode, page_var: Optional[str]):
        if not page_var:
            return
        locator = self._get_locator(node, page_var)
        py.line(f'{locator}.click(button="right")')

    def _gen_hover(self, py: PyBuilder, node: HoverNode, page_var: Optional[str]):
        if not page_var:
            return
        locator = self._get_locator(node, page_var)
        py.line(f'{locator}.hover()')

    def _gen_fill(self, py: PyBuilder, node: FillNode, page_var: Optional[str]):
        if not page_var:
            return
        sel = py_string(node.selector) if node.selector else '"input"'
        if node.clear:
            py.line(f'{page_var}.locator({sel}).fill({py_string(node.value)})')
        else:
            py.line(f'{page_var}.locator({sel}).type({py_string(node.value)})')

    def _gen_type(self, py: PyBuilder, node: TypeNode_Testing, page_var: Optional[str]):
        if not page_var:
            return
        sel = py_string(node.selector) if node.selector else '"input"'
        delay_arg = f', delay={node.delay}' if node.delay else ''
        py.line(f'{page_var}.locator({sel}).type({py_string(node.text)}{delay_arg})')

    def _gen_select(self, py: PyBuilder, node: SelectNode_Testing, page_var: Optional[str]):
        if not page_var:
            return
        sel = py_string(node.selector) if node.selector else '"select"'
        if node.values:
            values = [py_string(v.strip()) for v in node.values.split(',')]
            py.line(f'{page_var}.locator({sel}).select_option([{", ".join(values)}])')
        elif node.value:
            py.line(f'{page_var}.locator({sel}).select_option({py_string(node.value)})')

    def _gen_check(self, py: PyBuilder, node: CheckNode, page_var: Optional[str]):
        if not page_var:
            return
        sel = py_string(node.selector) if node.selector else '"input"'
        py.line(f'{page_var}.locator({sel}).check()')

    def _gen_uncheck(self, py: PyBuilder, node: UncheckNode, page_var: Optional[str]):
        if not page_var:
            return
        sel = py_string(node.selector) if node.selector else '"input"'
        py.line(f'{page_var}.locator({sel}).uncheck()')

    def _gen_keyboard(self, py: PyBuilder, node: KeyboardNode, page_var: Optional[str]):
        if not page_var:
            return
        if node.press:
            py.line(f'{page_var}.keyboard.press({py_string(node.press)})')
        if node.type_text:
            delay_arg = f', delay={node.delay}' if node.delay else ''
            py.line(f'{page_var}.keyboard.type({py_string(node.type_text)}{delay_arg})')

    def _gen_drag(self, py: PyBuilder, node: DragNode, page_var: Optional[str]):
        if not page_var:
            return
        py.line(f'{page_var}.drag_and_drop({py_string(node.from_sel)}, {py_string(node.to_sel)})')

    def _gen_scroll(self, py: PyBuilder, node: ScrollNode_Testing, page_var: Optional[str]):
        if not page_var:
            return
        if node.to_element:
            py.line(f'{page_var}.locator({py_string(node.to_element)}).scroll_into_view_if_needed()')
        elif node.to_top:
            py.line(f'{page_var}.evaluate("window.scrollTo(0, 0)")')
        elif node.amount:
            delta = node.amount if node.direction == 'down' else -node.amount
            py.line(f'{page_var}.mouse.wheel(0, {delta})')
        else:
            py.line(f'{page_var}.mouse.wheel(0, 300)')

    def _gen_upload(self, py: PyBuilder, node: UploadNode, page_var: Optional[str]):
        if not page_var:
            return
        sel = py_string(node.selector) if node.selector else '"input[type=file]"'
        if node.files:
            files = [py_string(f.strip()) for f in node.files.split(',')]
            py.line(f'{page_var}.locator({sel}).set_input_files([{", ".join(files)}])')
        elif node.file:
            py.line(f'{page_var}.locator({sel}).set_input_files({py_string(node.file)})')

    def _gen_download(self, py: PyBuilder, node: DownloadNode, page_var: Optional[str]):
        if not page_var:
            return
        py.line(f'with {page_var}.expect_download() as download_info:')
        py.indent()
        py.line(f'{page_var}.locator({py_string(node.trigger_click)}).click()')
        py.end_block()
        py.line('download = download_info.value')
        if node.save_as:
            py.line(f'download.save_as({py_string(node.save_as)})')

    def _gen_wait_for(self, py: PyBuilder, node: WaitForNode, page_var: Optional[str]):
        if not page_var:
            return
        if node.selector:
            args = []
            if node.state:
                args.append(f'state={py_string(node.state)}')
            if node.timeout:
                args.append(f'timeout={node.timeout}')
            args_str = ', '.join(args)
            py.line(f'{page_var}.locator({py_string(node.selector)}).wait_for({args_str})')
        elif node.url:
            timeout_arg = f', timeout={node.timeout}' if node.timeout else ''
            py.line(f'{page_var}.wait_for_url({py_string(node.url)}{timeout_arg})')
        elif node.request:
            timeout_arg = f', timeout={node.timeout}' if node.timeout else ''
            py.line(f'{page_var}.expect_request({py_string(node.request)}{timeout_arg})')
        elif node.response:
            timeout_arg = f', timeout={node.timeout}' if node.timeout else ''
            py.line(f'{page_var}.expect_response({py_string(node.response)}{timeout_arg})')
        elif node.condition:
            timeout_arg = f', timeout={node.timeout}' if node.timeout else ''
            py.line(f'{page_var}.wait_for_function({py_string(node.condition)}{timeout_arg})')

    def _gen_screenshot(self, py: PyBuilder, node: ScreenshotNode, page_var: Optional[str]):
        if not page_var:
            return
        name = node.name or 'screenshot'
        if node.selector:
            py.line(f'{page_var}.locator({py_string(node.selector)}).screenshot(path={py_string(name + ".png")})')
        else:
            full_page_arg = ', full_page=True' if node.full_page else ''
            py.line(f'{page_var}.screenshot(path={py_string(name + ".png")}{full_page_arg})')

    def _gen_intercept(self, py: PyBuilder, node: InterceptNode, page_var: Optional[str]):
        if not page_var:
            return

        # Find respond child
        respond = None
        for child in node.children:
            if isinstance(child, InterceptRespondNode):
                respond = child
                break

        url_pattern = py_string(node.url) if node.url else '"**/*"'

        if node.spy:
            py.line(f'requests_log = []')
            py.line(f'{page_var}.on("request", lambda req: requests_log.append(req))')
        elif respond:
            body = respond.body or '{}'
            py.line(f'def handle_route(route):')
            py.indent()
            if node.delay:
                py.line(f'time.sleep({node.delay / 1000})')
            py.line(f'route.fulfill(status={respond.status}, content_type={py_string(respond.content_type)}, body={py_string(body)})')
            py.end_block()
            py.line(f'{page_var}.route({url_pattern}, handle_route)')
        elif node.passthrough:
            py.line(f'{page_var}.route({url_pattern}, lambda route: route.continue_())')

    def _gen_frame(self, py: PyBuilder, node: FrameNode_Testing, page_var: Optional[str]):
        if not page_var:
            return
        py.line(f'frame = {page_var}.frame_locator({py_string(node.selector)})')
        for child in node.children:
            self._generate_action(py, child, "frame")

    def _gen_popup(self, py: PyBuilder, node: PopupNode, page_var: Optional[str]):
        if not page_var:
            return
        py.line(f'with {page_var}.expect_popup() as popup_info:')
        py.indent()
        if node.children:
            self._generate_action(py, node.children[0], page_var)
        else:
            py.pass_stmt()
        py.end_block()
        py.line('popup = popup_info.value')
        for child in node.children[1:]:
            self._generate_action(py, child, "popup")

    def _gen_save_state(self, py: PyBuilder, node: SaveStateNode, page_var: Optional[str]):
        if not page_var:
            return
        py.line(f'{page_var}.context.storage_state(path={py_string(node.file)})')

    def _gen_pause(self, py: PyBuilder, node: PauseNode, page_var: Optional[str]):
        if page_var:
            py.line(f'{page_var}.pause()')
        else:
            py.line('import pdb; pdb.set_trace()')

    # ------------------------------------------------------------------
    # Advanced testing generation
    # ------------------------------------------------------------------

    def _gen_snapshot(self, py: PyBuilder, node: SnapshotNode, page_var: Optional[str]):
        if not page_var:
            return
        name = node.name or 'snapshot'
        py.line(f'expect({page_var}).to_have_screenshot({py_string(name + ".png")}, threshold={node.threshold})')

    def _gen_fuzz(self, py: PyBuilder, node: FuzzNode, page_var: Optional[str]):
        py.line(f'import random, string')
        py.blank()
        py.comment(f"Fuzz testing: {node.target} ({node.iterations} iterations)")
        py.for_block('_fuzz_i', f'range({node.iterations})')

        # Generate random values for fields
        for child in node.children:
            if isinstance(child, FuzzFieldNode):
                gen = child.generator or 'string'
                if gen == 'string':
                    py.line(f'{py_id(child.name)} = "".join(random.choices(string.ascii_letters, k=random.randint(1, 100)))')
                elif gen == 'int':
                    py.line(f'{py_id(child.name)} = random.randint(-1000000, 1000000)')
                elif gen == 'email':
                    py.line(f'{py_id(child.name)} = "".join(random.choices(string.ascii_lowercase, k=8)) + "@test.com"')
                elif gen == 'xss':
                    py.line(f'{py_id(child.name)} = random.choice(["<script>alert(1)</script>", "<img onerror=alert(1)>", "\\" onmouseover=\\"alert(1)"])')
                elif gen == 'sqli':
                    py.line(f"""{py_id(child.name)} = random.choice(["' OR 1=1--", "'; DROP TABLE users;--", "1 UNION SELECT * FROM users"])""")
                else:
                    py.line(f'{py_id(child.name)} = "fuzz_" + str(_fuzz_i)')

            elif isinstance(child, PropertyNode):
                py.line(f'assert {child.text}  # Property check')

        py.end_block()

    def _gen_perf(self, py: PyBuilder, node: PerfNode, page_var: Optional[str]):
        py.comment("Performance test")
        py.line('_perf_start = time.time()')

        for child in node.children:
            if isinstance(child, PerfMetricNode):
                if child.name == 'lcp' and page_var:
                    py.line(f'_lcp = {page_var}.evaluate("() => {{ const entries = performance.getEntriesByType(\'largest-contentful-paint\'); return entries.length ? entries[entries.length - 1].startTime : 0; }}")')
                    if child.max_value:
                        py.line(f'assert _lcp <= {child.max_value}, f"LCP {{_lcp}}ms exceeds {child.max_value}ms"')
                elif child.name == 'fcp' and page_var:
                    py.line(f'_fcp = {page_var}.evaluate("() => {{ const entries = performance.getEntriesByType(\'paint\').filter(e => e.name === \'first-contentful-paint\'); return entries.length ? entries[0].startTime : 0; }}")')
                    if child.max_value:
                        py.line(f'assert _fcp <= {child.max_value}, f"FCP {{_fcp}}ms exceeds {child.max_value}ms"')
                elif child.name and child.max_value:
                    py.line(f'# Metric: {child.name} max={child.max_value}')
            else:
                self._generate_action(py, child, page_var)

        py.line('_perf_elapsed = (time.time() - _perf_start) * 1000')
        if node.regression_threshold:
            py.line(f'# Regression threshold: {node.regression_threshold * 100}%')

    def _gen_a11y(self, py: PyBuilder, node: A11yNode, page_var: Optional[str]):
        if not page_var:
            return
        py.comment(f"Accessibility check: {node.standard}")
        py.line(f'_a11y_results = {page_var}.evaluate("""() => {{')
        py.line(f'    // Inject axe-core and run check')
        py.line(f'    return new Promise((resolve) => {{')
        py.line(f'        const script = document.createElement("script");')
        py.line(f'        script.src = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.0/axe.min.js";')
        py.line(f'        script.onload = () => axe.run().then(resolve);')
        py.line(f'        document.head.appendChild(script);')
        py.line(f'    }});')
        py.line(f'}}""")')
        py.line(f'assert len(_a11y_results.get("violations", [])) == 0, f"Accessibility violations: {{_a11y_results.get(\'violations\', [])}}"')

    def _gen_chaos(self, py: PyBuilder, node: ChaosNode, page_var: Optional[str]):
        py.comment("Chaos testing")
        has_fail = any(isinstance(child, ChaosFailNode) for child in node.children)
        if has_fail:
            py.line(f'import random')
        for child in node.children:
            if isinstance(child, ChaosFailNode):
                py.comment(f"Simulate failure: {child.service} (probability: {child.probability})")
                py.if_block(f'random.random() < {child.probability}')
                if child.delay:
                    py.line(f'time.sleep({child.delay / 1000})')
                py.line(f'# Service {child.service} is unavailable')
                py.end_block()
            else:
                self._generate_action(py, child, page_var)

    def _gen_geolocation(self, py: PyBuilder, node: GeolocationNode, page_var: Optional[str]):
        if not page_var:
            return
        py.line(f'{page_var}.context.set_geolocation({{"latitude": {node.latitude}, "longitude": {node.longitude}, "accuracy": {node.accuracy}}})')
        py.line(f'{page_var}.context.grant_permissions(["geolocation"])')
