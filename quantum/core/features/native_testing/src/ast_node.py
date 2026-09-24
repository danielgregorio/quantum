"""The nodes of a `.test.q` file (TEST-1..TEST-4).

A test file is not a page: it is a list of `q:test`, each a list of steps
(`test:given`, `test:as`, `test:visit`, `test:submit`, `test:expect`) that
`quantum test` runs in order against the app. The nodes keep their line so a
failure points at the step that failed (DEV-2).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TestStepNode:
    """One step: `kind` is the local name of the tag (given, as, visit, submit, expect)."""
    __test__ = False                     # not a pytest class
    kind: str
    attrs: Dict[str, str]
    line: Optional[int] = None

    def source(self) -> str:
        """The step as it was written, for the report."""
        attrs = ' '.join(f'{k}="{v}"' for k, v in self.attrs.items())
        return f'<test:{self.kind}{" " + attrs if attrs else ""}/>'


@dataclass
class TestCaseNode:
    """One `q:test`: a name, the page it starts on, and its steps."""
    __test__ = False                     # not a pytest class
    name: str
    page: str = '/'
    steps: List[TestStepNode] = field(default_factory=list)
    line: Optional[int] = None


@dataclass
class TestFileNode:
    """A `*.test.q` file: its tests, in the order they are written."""
    __test__ = False                     # not a pytest class
    path: str
    tests: List[TestCaseNode] = field(default_factory=list)
