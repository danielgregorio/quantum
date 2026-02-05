"""
Testing Engine - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="testing") -> extract suites/config/fixtures/mocks -> TestingCodeGenerator -> test_*.py

Usage:
    builder = TestingBuilder()
    python_code = builder.build(app_node)
    builder.build_to_file(app_node, "test_output.py")
"""

from pathlib import Path
from typing import Optional

from core.ast_nodes import ApplicationNode
from core.features.testing_engine.src.ast_nodes import (
    TestSuiteNode, BrowserConfigNode, FixtureNode_Testing,
    MockNode_Testing, AuthNode,
)
from runtime.testing_code_generator import TestingCodeGenerator


class TestingBuildError(Exception):
    """Error during testing app build."""
    pass


class TestingBuilder:
    """Builds a standalone pytest file from a Quantum testing ApplicationNode."""

    def build(self, app: ApplicationNode) -> str:
        """Build Python test source string from an ApplicationNode with type='testing'.

        The ApplicationNode is expected to have:
        - app.test_suites: list of TestSuiteNode
        - app.test_config: optional BrowserConfigNode
        - app.test_fixtures: list of FixtureNode_Testing
        - app.test_mocks: list of MockNode_Testing
        - app.test_auth_states: list of AuthNode
        """
        suites = getattr(app, 'test_suites', [])
        config = getattr(app, 'test_config', None)
        fixtures = getattr(app, 'test_fixtures', [])
        mocks = getattr(app, 'test_mocks', [])
        auth_states = getattr(app, 'test_auth_states', [])

        if not suites:
            raise TestingBuildError("No test suites found in testing application")

        valid_suites = [s for s in suites if isinstance(s, TestSuiteNode)]
        if not valid_suites:
            raise TestingBuildError("No valid TestSuiteNode found in testing application")

        generator = TestingCodeGenerator()
        python_code = generator.generate(
            suites=valid_suites,
            title=app.app_id,
            browser_config=config if isinstance(config, BrowserConfigNode) else None,
            fixtures=[f for f in fixtures if isinstance(f, FixtureNode_Testing)],
            mocks=[m for m in mocks if isinstance(m, MockNode_Testing)],
            auth_states=[a for a in auth_states if isinstance(a, AuthNode)],
        )
        return python_code

    def build_to_file(self, app: ApplicationNode, output_path: Optional[str] = None) -> str:
        """Build and write test_*.py file. Returns the output file path."""
        python_code = self.build(app)

        if output_path is None:
            output_path = f"test_{app.app_id}.py"

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(python_code, encoding='utf-8')

        return str(path.resolve())
