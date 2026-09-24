"""
Known semantic gaps — the Phase 0.3 inventory, executable.

Each test describes the PROPOSED behavior and is marked `xfail(strict=True)`:
today the runtime does something else. When someone fixes it, the test passes
unexpectedly and `strict` fails the suite — the gap must leave this file and
become a rule with an ID in the SPEC, with the test moved to that rule's
section.

The expected behavior is a PROPOSAL, not a decision. The rule chosen may be a
different one; then the test changes with it. What must not happen is a gap
disappearing without anyone deciding.

Every case was reproduced by running it on 2026-09-10.
"""

import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

REPO = pathlib.Path(__file__).resolve().parents[2]


def run_body(body, params=None):
    path = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    path.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
        encoding='utf-8')
    return ComponentRuntime().execute_component(
        QuantumParser().parse_file(str(path)), params or {})


def gap(reason):
    return pytest.mark.xfail(strict=True, reason=reason)


# None open: G19 became EXPR-16 (tests/conformance/test_expressions_and_invoke.py).
