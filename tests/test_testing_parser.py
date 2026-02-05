"""
Tests for Testing Engine Parser

Verifies that testing XML (qtest: namespace) is correctly parsed into Testing AST nodes.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ApplicationNode
from core.features.testing_engine.src.ast_nodes import (
    TestSuiteNode, TestCaseNode, ExpectNode, MockNode_Testing,
    FixtureNode_Testing, SetupNode_Testing, TeardownNode_Testing,
    BeforeEachNode, AfterEachNode, GenerateNode,
    ScenarioNode, GivenNode, WhenNode, ThenNode,
    BrowserConfigNode, NavigateNode, ClickNode, DblClickNode,
    RightClickNode, HoverNode, FillNode, TypeNode_Testing,
    SelectNode_Testing, CheckNode, UncheckNode, KeyboardNode,
    DragNode, ScrollNode_Testing, UploadNode, DownloadNode,
    WaitForNode, ScreenshotNode, InterceptNode, InterceptRespondNode,
    FrameNode_Testing, PopupNode, AuthNode, SaveStateNode, PauseNode,
    SnapshotNode, FuzzNode, PropertyNode, FuzzFieldNode,
    PerfNode, PerfMetricNode, A11yNode, ChaosNode, ChaosFailNode,
    GeolocationNode,
)


@pytest.fixture
def parser():
    return QuantumParser()


class TestNamespaceInjection:
    """Test automatic namespace injection for qtest: prefix."""

    def test_auto_inject_qtest_namespace(self, parser):
        src = '''<q:application id="test" type="testing">
            <qtest:suite name="basic">
                <qtest:case name="it works">
                    <qtest:expect var="1+1" equals="2" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert isinstance(ast, ApplicationNode)
        assert ast.app_type == 'testing'

    def test_testing_app_has_suites(self, parser):
        src = '''<q:application id="test" type="testing">
            <qtest:suite name="MySuite">
                <qtest:case name="t1">
                    <qtest:expect var="True" equals="True" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.test_suites) == 1
        assert isinstance(ast.test_suites[0], TestSuiteNode)
        assert ast.test_suites[0].name == 'MySuite'


class TestSuiteParsing:
    """Test <qtest:suite> parsing."""

    def test_suite_attributes(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="BrowserSuite" browser="true" parallel="true" workers="4">
                <qtest:case name="x">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        suite = ast.test_suites[0]
        assert suite.name == 'BrowserSuite'
        assert suite.browser is True
        assert suite.parallel is True
        assert suite.workers == 4

    def test_multiple_suites(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="Suite1">
                <qtest:case name="t1">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
            <qtest:suite name="Suite2">
                <qtest:case name="t2">
                    <qtest:expect var="2" equals="2" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.test_suites) == 2
        assert ast.test_suites[0].name == 'Suite1'
        assert ast.test_suites[1].name == 'Suite2'


class TestCaseParsing:
    """Test <qtest:case> parsing."""

    def test_case_attributes(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="test login" browser="true" auth="admin">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        suite = ast.test_suites[0]
        case = suite.children[0]
        assert isinstance(case, TestCaseNode)
        assert case.name == 'test login'
        assert case.browser is True
        assert case.auth == 'admin'

    def test_case_children(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="nav test" browser="true">
                    <qtest:navigate to="/home" />
                    <qtest:click selector="#btn" />
                    <qtest:expect selector="h1" visible="true" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        case = ast.test_suites[0].children[0]
        assert len(case.children) == 3
        assert isinstance(case.children[0], NavigateNode)
        assert isinstance(case.children[1], ClickNode)
        assert isinstance(case.children[2], ExpectNode)


class TestExpectParsing:
    """Test <qtest:expect> parsing."""

    def test_expect_var_equals(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect var="result" equals="42" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        expect = ast.test_suites[0].children[0].children[0]
        assert isinstance(expect, ExpectNode)
        assert expect.var == 'result'
        assert expect.equals == '42'

    def test_expect_selector_visible(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect selector=".modal" visible="true" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        expect = ast.test_suites[0].children[0].children[0]
        assert expect.selector == '.modal'
        assert expect.visible is True

    def test_expect_text_contains(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect selector="h1" text-contains="Welcome" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        expect = ast.test_suites[0].children[0].children[0]
        assert expect.text_contains == 'Welcome'

    def test_expect_count(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect selector=".item" count="5" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        expect = ast.test_suites[0].children[0].children[0]
        assert expect.count == 5

    def test_expect_negate(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect selector=".error" visible="true" not="true" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        expect = ast.test_suites[0].children[0].children[0]
        assert expect.not_ is True


class TestBrowserNodeParsing:
    """Test browser action node parsing."""

    def test_browser_config(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:browser-config engine="firefox" headless="false" base-url="http://localhost:3000" timeout="5000" />
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert ast.test_config is not None
        assert isinstance(ast.test_config, BrowserConfigNode)
        assert ast.test_config.engine == 'firefox'
        assert ast.test_config.headless is False
        assert ast.test_config.base_url == 'http://localhost:3000'
        assert ast.test_config.timeout == 5000

    def test_navigate_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:navigate to="/about" wait="networkidle" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        nav = ast.test_suites[0].children[0].children[0]
        assert isinstance(nav, NavigateNode)
        assert nav.to == '/about'
        assert nav.wait == 'networkidle'

    def test_click_variants(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:click selector="#btn" />
                    <qtest:click text="Submit" role="button" />
                    <qtest:click test-id="login-btn" />
                    <qtest:dblclick selector=".item" />
                    <qtest:right-click selector=".context-target" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        children = ast.test_suites[0].children[0].children
        assert isinstance(children[0], ClickNode)
        assert children[0].selector == '#btn'
        assert isinstance(children[1], ClickNode)
        assert children[1].text == 'Submit'
        assert children[1].role == 'button'
        assert isinstance(children[2], ClickNode)
        assert children[2].test_id == 'login-btn'
        assert isinstance(children[3], DblClickNode)
        assert isinstance(children[4], RightClickNode)

    def test_fill_and_type(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:fill selector="#email" value="test@test.com" />
                    <qtest:type selector="#search" text="quantum" delay="50" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        children = ast.test_suites[0].children[0].children
        assert isinstance(children[0], FillNode)
        assert children[0].selector == '#email'
        assert children[0].value == 'test@test.com'
        assert isinstance(children[1], TypeNode_Testing)
        assert children[1].text == 'quantum'
        assert children[1].delay == 50

    def test_select_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:select selector="#country" value="BR" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        sel = ast.test_suites[0].children[0].children[0]
        assert isinstance(sel, SelectNode_Testing)
        assert sel.selector == '#country'
        assert sel.value == 'BR'

    def test_wait_for_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:wait-for selector=".loaded" state="visible" timeout="5000" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        wf = ast.test_suites[0].children[0].children[0]
        assert isinstance(wf, WaitForNode)
        assert wf.selector == '.loaded'
        assert wf.state == 'visible'
        assert wf.timeout == 5000

    def test_screenshot_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:screenshot name="homepage" full-page="true" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        ss = ast.test_suites[0].children[0].children[0]
        assert isinstance(ss, ScreenshotNode)
        assert ss.name == 'homepage'
        assert ss.full_page is True


class TestInterceptParsing:
    """Test <qtest:intercept> parsing with <qtest:respond>."""

    def test_intercept_with_respond(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:intercept url="**/api/users" method="GET">
                        <qtest:respond status="200" content-type="application/json">
                            [{"id": 1, "name": "Alice"}]
                        </qtest:respond>
                    </qtest:intercept>
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        intercept = ast.test_suites[0].children[0].children[0]
        assert isinstance(intercept, InterceptNode)
        assert intercept.url == '**/api/users'
        assert intercept.method == 'GET'
        assert len(intercept.children) == 1
        respond = intercept.children[0]
        assert isinstance(respond, InterceptRespondNode)
        assert respond.status == 200
        assert respond.content_type == 'application/json'
        assert '[{"id": 1, "name": "Alice"}]' in respond.body

    def test_intercept_spy(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:intercept url="**/api/track" spy="true" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        intercept = ast.test_suites[0].children[0].children[0]
        assert intercept.spy is True


class TestMockAndFixtureParsing:
    """Test mock and fixture parsing."""

    def test_fixture_inline(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:fixture name="users" scope="module">
                [{"id": 1, "name": "Alice"}]
            </qtest:fixture>
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.test_fixtures) == 1
        fixture = ast.test_fixtures[0]
        assert isinstance(fixture, FixtureNode_Testing)
        assert fixture.name == 'users'
        assert fixture.scope == 'module'
        assert '"Alice"' in fixture.data

    def test_mock_query(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:mock query="getUsers">
                [{"id": 1, "name": "Alice"}]
            </qtest:mock>
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.test_mocks) == 1
        mock = ast.test_mocks[0]
        assert isinstance(mock, MockNode_Testing)
        assert mock.query == 'getUsers'
        assert '"Alice"' in mock.return_value


class TestHooksParsing:
    """Test setup/teardown/before-each/after-each parsing."""

    def test_setup_teardown(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:setup>
                    <qtest:navigate to="/setup" />
                </qtest:setup>
                <qtest:teardown>
                    <qtest:navigate to="/cleanup" />
                </qtest:teardown>
                <qtest:case name="t">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        suite = ast.test_suites[0]
        setup = [c for c in suite.children if isinstance(c, SetupNode_Testing)]
        teardown = [c for c in suite.children if isinstance(c, TeardownNode_Testing)]
        assert len(setup) == 1
        assert len(teardown) == 1
        assert len(setup[0].children) == 1
        assert isinstance(setup[0].children[0], NavigateNode)

    def test_before_after_each(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:before-each>
                    <qtest:navigate to="/" />
                </qtest:before-each>
                <qtest:after-each>
                    <qtest:screenshot name="after" />
                </qtest:after-each>
                <qtest:case name="t">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        suite = ast.test_suites[0]
        before = [c for c in suite.children if isinstance(c, BeforeEachNode)]
        after = [c for c in suite.children if isinstance(c, AfterEachNode)]
        assert len(before) == 1
        assert len(after) == 1


class TestScenarioParsing:
    """Test BDD scenario parsing."""

    def test_scenario_given_when_then(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:scenario name="user login">
                    <qtest:given>a registered user</qtest:given>
                    <qtest:when>they enter valid credentials</qtest:when>
                    <qtest:then>they should see the dashboard
                        <qtest:expect var="True" equals="True" />
                    </qtest:then>
                </qtest:scenario>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        scenario = ast.test_suites[0].children[0]
        assert isinstance(scenario, ScenarioNode)
        assert scenario.name == 'user login'
        assert len(scenario.children) == 3
        assert isinstance(scenario.children[0], GivenNode)
        assert scenario.children[0].text == 'a registered user'
        assert isinstance(scenario.children[1], WhenNode)
        assert scenario.children[1].text == 'they enter valid credentials'
        assert isinstance(scenario.children[2], ThenNode)
        assert len(scenario.children[2].children) == 1


class TestAdvancedNodesParsing:
    """Test advanced testing node parsing."""

    def test_fuzz_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:fuzz target="search_input" iterations="50">
                        <qtest:field name="query" generator="string" />
                        <qtest:property>len(result) >= 0</qtest:property>
                    </qtest:fuzz>
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        fuzz = ast.test_suites[0].children[0].children[0]
        assert isinstance(fuzz, FuzzNode)
        assert fuzz.target == 'search_input'
        assert fuzz.iterations == 50
        assert len(fuzz.children) == 2
        assert isinstance(fuzz.children[0], FuzzFieldNode)
        assert fuzz.children[0].name == 'query'
        assert isinstance(fuzz.children[1], PropertyNode)

    def test_perf_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:perf regression-threshold="0.2">
                        <qtest:metric name="lcp" max-value="2500" />
                        <qtest:metric name="fcp" max-value="1500" />
                    </qtest:perf>
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        perf = ast.test_suites[0].children[0].children[0]
        assert isinstance(perf, PerfNode)
        assert perf.regression_threshold == 0.2
        assert len(perf.children) == 2
        assert isinstance(perf.children[0], PerfMetricNode)
        assert perf.children[0].name == 'lcp'
        assert perf.children[0].max_value == 2500.0

    def test_a11y_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:a11y standard="wcag2aa" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        a11y = ast.test_suites[0].children[0].children[0]
        assert isinstance(a11y, A11yNode)
        assert a11y.standard == 'wcag2aa'

    def test_geolocation_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:geolocation latitude="-23.5505" longitude="-46.6333" accuracy="50" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        geo = ast.test_suites[0].children[0].children[0]
        assert isinstance(geo, GeolocationNode)
        assert geo.latitude == -23.5505
        assert geo.longitude == -46.6333
        assert geo.accuracy == 50.0

    def test_auth_node(self, parser):
        src = '''<q:application id="t" type="testing">
            <qtest:auth name="admin" reuse="true">
                <qtest:navigate to="/login" />
                <qtest:fill selector="#user" value="admin" />
                <qtest:fill selector="#pass" value="secret" />
                <qtest:click selector="#submit" />
            </qtest:auth>
            <qtest:suite name="S">
                <qtest:case name="t">
                    <qtest:expect var="1" equals="1" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.test_auth_states) == 1
        auth = ast.test_auth_states[0]
        assert isinstance(auth, AuthNode)
        assert auth.name == 'admin'
        assert auth.reuse is True
        assert len(auth.children) == 4


class TestFullIntegration:
    """Full integration test - parse a complete testing .q file."""

    def test_full_testing_app(self, parser):
        src = '''<q:application id="full-tests" type="testing">
            <qtest:browser-config engine="chromium" headless="true" base-url="http://localhost:8080" />

            <qtest:fixture name="test_data" scope="session">
                {"users": [{"name": "Alice"}, {"name": "Bob"}]}
            </qtest:fixture>

            <qtest:mock query="getUsers">
                [{"id": 1, "name": "Alice"}]
            </qtest:mock>

            <qtest:suite name="UnitTests">
                <qtest:case name="math works">
                    <qtest:expect var="2 + 2" equals="4" />
                </qtest:case>
            </qtest:suite>

            <qtest:suite name="BrowserTests" browser="true">
                <qtest:before-each>
                    <qtest:navigate to="/" />
                </qtest:before-each>

                <qtest:case name="homepage loads" browser="true">
                    <qtest:expect selector="h1" visible="true" />
                    <qtest:click text="Login" role="link" />
                    <qtest:wait-for url="**/login" />
                    <qtest:fill selector="#email" value="test@test.com" />
                    <qtest:click selector="button[type=submit]" />
                    <qtest:screenshot name="after-login" />
                </qtest:case>
            </qtest:suite>
        </q:application>'''
        ast = parser.parse(src)
        assert ast.app_type == 'testing'
        assert ast.test_config is not None
        assert len(ast.test_fixtures) == 1
        assert len(ast.test_mocks) == 1
        assert len(ast.test_suites) == 2

        # Check unit test suite
        unit_suite = ast.test_suites[0]
        assert unit_suite.name == 'UnitTests'
        assert unit_suite.browser is False

        # Check browser test suite
        browser_suite = ast.test_suites[1]
        assert browser_suite.name == 'BrowserTests'
        assert browser_suite.browser is True

        # Check browser test case children
        before_each = [c for c in browser_suite.children if isinstance(c, BeforeEachNode)]
        assert len(before_each) == 1
        cases = [c for c in browser_suite.children if isinstance(c, TestCaseNode)]
        assert len(cases) == 1
        assert len(cases[0].children) == 6  # expect, click, wait-for, fill, click, screenshot


class TestValidation:
    """Test AST validation."""

    def test_suite_requires_name(self):
        suite = TestSuiteNode('')
        errors = suite.validate()
        assert any('name' in e.lower() for e in errors)

    def test_case_requires_name(self):
        case = TestCaseNode('')
        errors = case.validate()
        assert any('name' in e.lower() for e in errors)

    def test_fixture_invalid_scope(self):
        fixture = FixtureNode_Testing('test')
        fixture.scope = 'invalid'
        errors = fixture.validate()
        assert any('scope' in e.lower() for e in errors)

    def test_browser_config_invalid_engine(self):
        config = BrowserConfigNode()
        config.engine = 'invalid'
        errors = config.validate()
        assert any('engine' in e.lower() for e in errors)

    def test_expect_contradictory_validation(self):
        """ExpectNode with visible=True + hidden=True generates warning in validate()."""
        expect = ExpectNode()
        expect.selector = '.element'
        expect.visible = True
        expect.hidden = True
        errors = expect.validate()
        assert any('contradictory' in e.lower() for e in errors)
