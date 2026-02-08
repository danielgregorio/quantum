"""
Tests for Testing Engine Code Generator

Verifies that Testing AST nodes compile correctly to pytest Python code.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser
from core.features.testing_engine.src.ast_nodes import (
    QTestSuiteNode, QTestCaseNode, ExpectNode, MockNode_Testing,
    FixtureNode_Testing, SetupNode_Testing, TeardownNode_Testing,
    BeforeEachNode, AfterEachNode,
    ScenarioNode, GivenNode, WhenNode, ThenNode,
    BrowserConfigNode, NavigateNode, ClickNode, FillNode,
    WaitForNode, ScreenshotNode, InterceptNode, InterceptRespondNode,
    FrameNode_Testing, KeyboardNode, AuthNode, DownloadNode,
    FuzzNode, FuzzFieldNode, PropertyNode,
    PerfNode, PerfMetricNode, A11yNode, GeolocationNode,
    SnapshotNode, PauseNode, ChaosNode, ChaosFailNode,
)
from runtime.testing_code_generator import QTestCodeGenerator


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def codegen():
    return QTestCodeGenerator()


class TestBasicGeneration:
    """Test basic pytest code generation."""

    def test_generates_pytest_file(self, codegen):
        suite = QTestSuiteNode('Basic')
        case = QTestCaseNode('addition works')
        expect = ExpectNode()
        expect.var = '1 + 1'
        expect.equals = '2'
        case.add_child(expect)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'import pytest' in code
        assert 'class TestBasic' in code
        assert 'def test_addition_works' in code
        assert 'assert 1 + 1 == 2' in code

    def test_class_naming(self, codegen):
        suite = QTestSuiteNode('User Authentication')
        case = QTestCaseNode('t')
        expect = ExpectNode()
        expect.var = '1'
        expect.equals = '1'
        case.add_child(expect)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'class TestUserAuthentication' in code

    def test_method_naming(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('it should handle special characters!')
        expect = ExpectNode()
        expect.var = '1'
        expect.equals = '1'
        case.add_child(expect)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'def test_it_should_handle_special_characters' in code

    def test_multiple_assertions(self, codegen):
        suite = QTestSuiteNode('Math')
        case = QTestCaseNode('operations')
        e1 = ExpectNode()
        e1.var = '1 + 1'
        e1.equals = '2'
        e2 = ExpectNode()
        e2.var = '3 * 4'
        e2.equals = '12'
        case.add_child(e1)
        case.add_child(e2)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'assert 1 + 1 == 2' in code
        assert 'assert 3 * 4 == 12' in code


class TestBrowserTestGeneration:
    """Test browser test (playwright) code generation."""

    def test_browser_test_has_page_param(self, codegen):
        suite = QTestSuiteNode('Browser')
        suite.browser = True
        case = QTestCaseNode('loads page')
        case.browser = True
        nav = NavigateNode()
        nav.to = '/'
        case.add_child(nav)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'page: Page' in code
        assert 'from playwright.sync_api' in code

    def test_navigate_generation(self, codegen):
        suite = QTestSuiteNode('Nav')
        suite.browser = True
        case = QTestCaseNode('goes to page')
        case.browser = True
        nav = NavigateNode()
        nav.to = '/about'
        case.add_child(nav)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'page.goto("/about")' in code

    def test_navigate_back(self, codegen):
        suite = QTestSuiteNode('Nav')
        suite.browser = True
        case = QTestCaseNode('goes back')
        case.browser = True
        nav = NavigateNode()
        nav.back = True
        case.add_child(nav)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'page.go_back()' in code

    def test_click_generation(self, codegen):
        suite = QTestSuiteNode('Click')
        suite.browser = True
        case = QTestCaseNode('clicks btn')
        case.browser = True
        click = ClickNode()
        click.selector = '#submit-btn'
        case.add_child(click)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'locator("#submit-btn")' in code
        assert '.click()' in code

    def test_click_by_test_id(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        click = ClickNode()
        click.test_id = 'login-btn'
        case.add_child(click)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'get_by_test_id("login-btn")' in code

    def test_click_by_role(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        click = ClickNode()
        click.role = 'button'
        click.text = 'Submit'
        case.add_child(click)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'get_by_role("button"' in code
        assert 'name="Submit"' in code

    def test_fill_generation(self, codegen):
        suite = QTestSuiteNode('Form')
        suite.browser = True
        case = QTestCaseNode('fills form')
        case.browser = True
        fill = FillNode()
        fill.selector = '#email'
        fill.value = 'test@test.com'
        case.add_child(fill)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'locator("#email")' in code
        assert '.fill("test@test.com")' in code


class TestAssertGeneration:
    """Test all ExpectNode assertion variants."""

    def test_expect_var_equals(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = 'result'
        e.equals = '42'
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'assert result == 42' in code

    def test_expect_var_text_contains(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = 'output'
        e.text_contains = 'success'
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert '"success" in str(output)' in code

    def test_expect_selector_visible(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.selector = 'h1'
        e.visible = True
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'to_be_visible()' in code

    def test_expect_selector_text(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.selector = 'h1'
        e.text = 'Welcome'
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'to_have_text("Welcome")' in code

    def test_expect_selector_count(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.selector = '.item'
        e.count = 5
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'to_have_count(5)' in code

    def test_expect_negate(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.selector = '.error'
        e.visible = True
        e.not_ = True
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'not_to_be_visible()' in code

    def test_expect_url(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.url = 'http://localhost/dashboard'
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'to_have_url(' in code
        assert 'dashboard' in code


class TestFixtureGeneration:
    """Test fixture code generation."""

    def test_inline_fixture(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = '1'
        e.equals = '1'
        case.add_child(e)
        suite.add_child(case)

        fixture = FixtureNode_Testing('test_data')
        fixture.data = '{"key": "value"}'
        fixture.scope = 'module'

        code = codegen.generate([suite], fixtures=[fixture])
        assert '@pytest.fixture(scope="module")' in code
        assert 'def test_data' in code
        assert 'json.loads' in code

    def test_file_fixture(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = '1'
        e.equals = '1'
        case.add_child(e)
        suite.add_child(case)

        fixture = FixtureNode_Testing('config')
        fixture.file = 'test_config.json'

        code = codegen.generate([suite], fixtures=[fixture])
        assert 'open("test_config.json")' in code
        assert 'json.load(f)' in code


class TestMockGeneration:
    """Test mock code generation."""

    def test_query_mock(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = '1'
        e.equals = '1'
        case.add_child(e)
        suite.add_child(case)

        mock = MockNode_Testing()
        mock.query = 'getUsers'
        mock.return_value = '[{"id": 1}]'

        code = codegen.generate([suite], mocks=[mock])
        assert '@pytest.fixture' in code
        assert 'mock_getUsers' in code
        assert 'MagicMock()' in code
        assert 'json.loads' in code


class TestInterceptGeneration:
    """Test network intercept code generation."""

    def test_intercept_with_respond(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True

        intercept = InterceptNode()
        intercept.url = '**/api/users'
        intercept.method = 'GET'
        respond = InterceptRespondNode()
        respond.status = 200
        respond.content_type = 'application/json'
        respond.body = '[{"id": 1}]'
        intercept.add_child(respond)
        case.add_child(intercept)
        suite.add_child(case)

        code = codegen.generate([suite])
        assert 'page.route(' in code
        assert 'route.fulfill(' in code
        assert 'status=200' in code

    def test_intercept_spy(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True

        intercept = InterceptNode()
        intercept.url = '**/api/track'
        intercept.spy = True
        case.add_child(intercept)
        suite.add_child(case)

        code = codegen.generate([suite])
        assert 'requests_log' in code
        assert 'page.on("request"' in code


class TestAuthGeneration:
    """Test auth state code generation."""

    def test_auth_fixture(self, codegen):
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = '1'
        e.equals = '1'
        case.add_child(e)
        suite.add_child(case)

        auth = AuthNode()
        auth.name = 'admin'
        nav = NavigateNode()
        nav.to = '/login'
        fill = FillNode()
        fill.selector = '#user'
        fill.value = 'admin'
        auth.add_child(nav)
        auth.add_child(fill)

        code = codegen.generate([suite], auth_states=[auth])
        assert 'auth_admin' in code
        assert 'storage_state' in code
        assert 'page.goto("/login")' in code


class TestHookGeneration:
    """Test setup/teardown hook generation."""

    def test_setup_class(self, codegen):
        suite = QTestSuiteNode('S')
        setup = SetupNode_Testing()
        suite.add_child(setup)
        case = QTestCaseNode('t')
        e = ExpectNode()
        e.var = '1'
        e.equals = '1'
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'setup_class' in code
        assert '@classmethod' in code

    def test_before_each_browser(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        before = BeforeEachNode()
        nav = NavigateNode()
        nav.to = '/'
        before.add_child(nav)
        suite.add_child(before)
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.selector = 'h1'
        e.visible = True
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'setup_method' in code
        assert 'page: Page' in code


class TestScenarioGeneration:
    """Test BDD scenario code generation."""

    def test_scenario_comments(self, codegen):
        suite = QTestSuiteNode('S')
        scenario = ScenarioNode('user logs in')
        given = GivenNode('a registered user')
        when = WhenNode('they enter credentials')
        then = ThenNode('they see dashboard')
        e = ExpectNode()
        e.var = 'True'
        e.equals = 'True'
        then.add_child(e)
        scenario.add_child(given)
        scenario.add_child(when)
        scenario.add_child(then)
        suite.add_child(scenario)
        code = codegen.generate([suite])
        assert '# Given: a registered user' in code
        assert '# When: they enter credentials' in code
        assert '# Then: they see dashboard' in code
        assert 'test_user_logs_in' in code


class TestAdvancedFeatureGeneration:
    """Test advanced testing features code generation."""

    def test_screenshot(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        ss = ScreenshotNode()
        ss.name = 'homepage'
        ss.full_page = True
        case.add_child(ss)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'screenshot(' in code
        assert 'homepage.png' in code
        assert 'full_page=True' in code

    def test_geolocation(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        geo = GeolocationNode()
        geo.latitude = -23.55
        geo.longitude = -46.63
        case.add_child(geo)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'set_geolocation' in code
        assert '-23.55' in code
        assert '-46.63' in code
        assert 'grant_permissions' in code

    def test_keyboard(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        kb = KeyboardNode()
        kb.press = 'Enter'
        case.add_child(kb)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'keyboard.press("Enter")' in code

    def test_wait_for(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        wf = WaitForNode()
        wf.selector = '.loaded'
        wf.state = 'visible'
        wf.timeout = 5000
        case.add_child(wf)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'wait_for(' in code
        assert 'timeout=5000' in code

    def test_snapshot(self, codegen):
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        snap = SnapshotNode()
        snap.name = 'visual_test'
        snap.threshold = 0.05
        case.add_child(snap)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'to_have_screenshot' in code
        assert 'visual_test.png' in code
        assert 'threshold=0.05' in code


class TestFullPipeline:
    """Full pipeline test: parse .q -> generate pytest."""

    def test_basic_pipeline(self, parser, codegen):
        src = '''<q:application id="pipeline-test" type="testing">
            <qtest:suite name="Basic">
                <qtest:case name="math works">
                    <qtest:expect var="1 + 1" equals="2" />
                    <qtest:expect var="3 * 3" equals="9" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        code = codegen.generate(
            suites=ast.test_suites,
            title=ast.app_id,
            browser_config=ast.test_config,
            fixtures=ast.test_fixtures,
            mocks=ast.test_mocks,
        )
        assert 'import pytest' in code
        assert 'class TestBasic' in code
        assert 'def test_math_works' in code
        assert 'assert 1 + 1 == 2' in code
        assert 'assert 3 * 3 == 9' in code

    def test_browser_pipeline(self, parser, codegen):
        src = '''<q:application id="browser-pipeline" type="testing">
            <qtest:browser-config engine="chromium" headless="true" base-url="http://localhost:8080" />
            <qtest:suite name="HomePage" browser="true">
                <qtest:case name="loads page" browser="true">
                    <qtest:navigate to="/" />
                    <qtest:expect selector="h1" visible="true" />
                    <qtest:click text="About" role="link" />
                    <qtest:wait-for url="**/about" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        code = codegen.generate(
            suites=ast.test_suites,
            title=ast.app_id,
            browser_config=ast.test_config,
        )
        assert 'from playwright.sync_api' in code
        assert 'class TestHomePage' in code
        assert 'page: Page' in code
        assert 'page.goto("/")' in code
        assert 'to_be_visible()' in code
        assert 'get_by_role("link"' in code

    def test_generated_code_is_valid_python(self, parser, codegen):
        """Verify generated code can be compiled by Python."""
        src = '''<q:application id="valid-python" type="testing">
            <qtest:suite name="Unit">
                <qtest:case name="basic assertion">
                    <qtest:expect var="True" equals="True" />
                </qtest:case>
                <qtest:case name="string check">
                    <qtest:expect var="'hello'" text-contains="hell" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        code = codegen.generate(suites=ast.test_suites, title=ast.app_id)
        # This should not raise SyntaxError
        compile(code, '<test>', 'exec')


class TestBugFixCoverage:
    """Tests covering bug fixes and gap coverage."""

    def test_expect_multiple_assertions_same_node(self, codegen):
        """ExpectNode with visible + text + count generates 3 assertions."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        e = ExpectNode()
        e.selector = '.card'
        e.visible = True
        e.text = 'Hello'
        e.count = 3
        case.add_child(e)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'to_be_visible()' in code
        assert 'to_have_text("Hello")' in code
        assert 'to_have_count(3)' in code

    def test_wait_for_state_without_timeout(self, codegen):
        """wait_for with state='visible' but no timeout."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        wf = WaitForNode()
        wf.selector = '.item'
        wf.state = 'visible'
        wf.timeout = None
        case.add_child(wf)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'wait_for(state="visible")' in code
        assert 'timeout' not in code.split('wait_for(')[1].split(')')[0]

    def test_wait_for_timeout_without_state(self, codegen):
        """wait_for with timeout but no state - should not produce leading comma."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        wf = WaitForNode()
        wf.selector = '.loaded'
        wf.state = None
        wf.timeout = 5000
        case.add_child(wf)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'wait_for(timeout=5000)' in code
        # Must NOT have leading comma: wait_for(, timeout=5000)
        assert 'wait_for(,' not in code

    def test_wait_for_selector_only(self, codegen):
        """wait_for with only selector, no state or timeout."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        wf = WaitForNode()
        wf.selector = '#spinner'
        wf.state = None
        wf.timeout = None
        case.add_child(wf)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'wait_for()' in code

    def test_perf_without_browser(self, codegen):
        """PerfNode in non-browser suite still generates timing code."""
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        perf = PerfNode()
        metric = PerfMetricNode()
        metric.name = 'lcp'
        metric.max_value = 2500
        perf.add_child(metric)
        case.add_child(perf)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert '_perf_start = time.time()' in code
        assert '_perf_elapsed' in code
        # lcp requires page_var, so should NOT generate evaluate call
        assert 'evaluate' not in code

    def test_intercept_with_delay(self, codegen):
        """Intercept with delay generates time.sleep."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        intercept = InterceptNode()
        intercept.url = '**/api/slow'
        intercept.delay = 2000
        respond = InterceptRespondNode()
        respond.status = 200
        respond.content_type = 'application/json'
        respond.body = '{"ok": true}'
        intercept.add_child(respond)
        case.add_child(intercept)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'time.sleep(2.0)' in code
        assert 'route.fulfill(' in code

    def test_frame_with_nested_actions(self, codegen):
        """Frame with click + fill + expect inside."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        frame = FrameNode_Testing()
        frame.selector = '#myframe'
        click = ClickNode()
        click.selector = '.btn'
        fill = FillNode()
        fill.selector = '#input'
        fill.value = 'test'
        expect = ExpectNode()
        expect.selector = '.result'
        expect.visible = True
        frame.add_child(click)
        frame.add_child(fill)
        frame.add_child(expect)
        case.add_child(frame)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'frame_locator("#myframe")' in code
        assert 'frame.locator(".btn").click()' in code
        assert 'frame.locator("#input")' in code
        assert 'expect(frame.locator(".result")).to_be_visible()' in code

    def test_download_without_save_as(self, codegen):
        """Download without save_as generates only trigger."""
        suite = QTestSuiteNode('S')
        suite.browser = True
        case = QTestCaseNode('t')
        case.browser = True
        dl = DownloadNode()
        dl.trigger_click = '#download-btn'
        dl.save_as = None
        case.add_child(dl)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert 'expect_download()' in code
        assert '#download-btn' in code
        assert 'save_as' not in code

    def test_chaos_multiple_failures(self, codegen):
        """ChaosNode with 2+ ChaosFailNode children - import random only once."""
        suite = QTestSuiteNode('S')
        case = QTestCaseNode('t')
        chaos = ChaosNode()
        fail1 = ChaosFailNode()
        fail1.service = 'db'
        fail1.probability = 0.5
        fail2 = ChaosFailNode()
        fail2.service = 'cache'
        fail2.probability = 0.3
        fail2.delay = 1000
        chaos.add_child(fail1)
        chaos.add_child(fail2)
        case.add_child(chaos)
        suite.add_child(case)
        code = codegen.generate([suite])
        assert code.count('import random') == 1
        assert 'random.random() < 0.5' in code
        assert 'random.random() < 0.3' in code
        assert 'time.sleep(1.0)' in code
