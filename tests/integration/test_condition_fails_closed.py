"""
A q:if condition that cannot be evaluated must be FALSE, not true.

Two independent audit dimensions reported this as an authorization bypass:

    <q:if condition="session.user.is_admin">
        ...admin panel...
    <q:else> ...public... </q:else>

For a logged-out visitor whose session has no `user`, the condition could not
be evaluated. Both databinding passes then fell back to interpolating the
variable NAMES into a string, got back the literal 'session.user.is_admin',
and took its truthiness — a non-empty string is true — so the admin branch
rendered and the q:else never fired.

A condition failing open is a bypass by construction. Both passes now return
False for anything they cannot evaluate, and agree with each other.
"""

import pytest

from quantum.runtime.component import ComponentRuntime
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.renderer import HTMLRenderer


@pytest.fixture
def runtime():
    return ComponentRuntime()


@pytest.fixture
def renderer():
    return HTMLRenderer(ExecutionContext())


# (condition, context, expected) — the empty-context cases are the bypass.
CASES = [
    ("session.user.is_admin", {}, False),
    ("user.role == 'admin'", {}, False),
    ("currentUser.isAdmin", {}, False),
    ("saldo > 100", {}, False),
    ("isAdmin", {}, False),
    ("a.b.c.d", {}, False),
    # Controls: real conditions still evaluate correctly.
    ("1 == 1", {}, True),
    ("1 == 2", {}, False),
    ("saldo > 100", {"saldo": 200}, True),
    ("saldo > 100", {"saldo": 50}, False),
    ("role == 'admin'", {"role": "admin"}, True),
    ("role == 'admin'", {"role": "guest"}, False),
    ("flag", {"flag": True}, True),
    ("flag", {"flag": False}, False),
]


class TestExecutorFailsClosed:
    @pytest.mark.parametrize("cond,ctx,expected", CASES)
    def test_executor(self, runtime, cond, ctx, expected):
        assert runtime._evaluate_condition(cond, ctx) is expected


class TestRendererFailsClosed:
    @pytest.mark.parametrize("cond,ctx,expected", CASES)
    def test_renderer(self, renderer, cond, ctx, expected):
        for k, v in ctx.items():
            renderer.context.set_variable(k, v)
        assert renderer._evaluate_condition(cond) is expected


class TestBothPassesAgree:
    @pytest.mark.parametrize("cond,ctx,_", CASES)
    def test_agree(self, runtime, cond, ctx, _):
        r = HTMLRenderer(ExecutionContext())
        for k, v in ctx.items():
            r.context.set_variable(k, v)
        assert runtime._evaluate_condition(cond, ctx) == r._evaluate_condition(cond)


class TestTheAdminBranchDoesNotRenderLoggedOut:
    """End to end through the real render pass: the exact shape the audit used."""

    def test_q_else_fires_when_the_guard_cannot_be_evaluated(self):
        from quantum.core.parser import QuantumParser
        src = (
            '<q:component name="Guarded">'
            '<q:if condition="session.user.is_admin">'
            '<div>SECRET-ADMIN-PANEL</div>'
            '<q:else><div>PUBLIC</div></q:else>'
            '</q:if>'
            '</q:component>'
        )
        ast = QuantumParser().parse(src)
        rt = ComponentRuntime()
        rt.execute_component(ast)
        html = HTMLRenderer(rt.execution_context).render(ast)
        assert "SECRET-ADMIN-PANEL" not in html
        assert "PUBLIC" in html
