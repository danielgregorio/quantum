"""
Testing Engine - AST nodes and parser for the qtest: namespace.
"""

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

__all__ = [
    # Core testing nodes
    'QTestSuiteNode', 'QTestCaseNode', 'ExpectNode', 'MockNode_Testing',
    'FixtureNode_Testing', 'SetupNode_Testing', 'TeardownNode_Testing',
    'BeforeEachNode', 'AfterEachNode', 'GenerateNode',
    'ScenarioNode', 'GivenNode', 'WhenNode', 'ThenNode',
    # Browser testing nodes
    'BrowserConfigNode', 'NavigateNode', 'ClickNode', 'DblClickNode',
    'RightClickNode', 'HoverNode', 'FillNode', 'TypeNode_Testing',
    'SelectNode_Testing', 'CheckNode', 'UncheckNode', 'KeyboardNode',
    'DragNode', 'ScrollNode_Testing', 'UploadNode', 'DownloadNode',
    'WaitForNode', 'ScreenshotNode', 'InterceptNode', 'InterceptRespondNode',
    'FrameNode_Testing', 'PopupNode', 'AuthNode', 'SaveStateNode', 'PauseNode',
    # Advanced testing nodes
    'SnapshotNode', 'FuzzNode', 'PropertyNode', 'FuzzFieldNode',
    'PerfNode', 'PerfMetricNode', 'A11yNode', 'ChaosNode', 'ChaosFailNode',
    'GeolocationNode',
]
