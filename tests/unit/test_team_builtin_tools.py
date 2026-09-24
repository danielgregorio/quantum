"""
A q:team could not hand off, because no agent had the handoff tool.

The built-ins required an explicit <q:tool name="handoff" builtin="true" /> on
every agent, and nobody wrote it. examples/multi_agent_support.q — the shipped
demo — advertises "Built-in handoff, readShared, writeShared, listAgents
tools" in its header and instructs its router to "use the handoff tool", while
declaring none of them. So the tool did not exist, the model could not call
it, and the team ended at its first agent reporting success.

A q:team exists in order to hand off. Making that opt-in was boilerplate
everyone forgets, so the builtins are provided automatically now — without
shadowing an agent's own tool of the same name.
"""

import pathlib
import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.executors.ai.team_executor import _team_tools, _TEAM_BUILTINS


def _walk(node):
    for s in getattr(node, "statements", []) or []:
        yield s
        yield from _walk(s)


@pytest.fixture
def team():
    root = pathlib.Path(__file__).resolve().parents[2]
    src = (root / "examples" / "multi_agent_support.q").read_text(
        encoding="utf-8", errors="ignore")
    ast = QuantumParser().parse(src)
    return next(s for s in _walk(ast) if type(s).__name__ == "AgentTeamNode")


class TestTheShippedTeamCanHandOff:
    def test_every_agent_gets_handoff(self, team):
        for agent in team.agents:
            names = {t["name"] for t in _team_tools(agent)}
            assert "handoff" in names, f"{agent.name} cannot hand off"

    @pytest.mark.parametrize("builtin", _TEAM_BUILTINS)
    def test_every_agent_gets_each_builtin(self, team, builtin):
        for agent in team.agents:
            assert builtin in {t["name"] for t in _team_tools(agent)}

    def test_declared_tools_survive(self, team):
        """The agents' own tools must not be lost."""
        all_names = {t["name"] for a in team.agents for t in _team_tools(a)}
        assert "lookupInvoice" in all_names
        assert "searchKnowledgeBase" in all_names

    def test_no_duplicates(self, team):
        for agent in team.agents:
            names = [t["name"] for t in _team_tools(agent)]
            assert len(names) == len(set(names)), names


class TestAnExplicitDeclarationWins:
    def test_an_agent_tool_named_handoff_is_not_shadowed(self):
        src = ('<q:component name="T">'
               '<q:team name="t"><q:agent name="a" model="m">'
               '<q:instruction>x</q:instruction>'
               '<q:tool name="handoff" description="minha versao">'
               '<q:param name="agent" type="string" /></q:tool>'
               '</q:agent>'
               '<q:execute task="t" /></q:team></q:component>')
        ast = QuantumParser().parse(src)
        team = next(s for s in _walk(ast) if type(s).__name__ == "AgentTeamNode")
        tools = _team_tools(team.agents[0])
        handoffs = [t for t in tools if t["name"] == "handoff"]
        assert len(handoffs) == 1
        assert handoffs[0]["description"] == "minha versao"


class TestTheServiceCanActuallyRunThem:
    """The bug class this codebase keeps producing: a tool the service does
    not implement."""

    @pytest.mark.parametrize("name", _TEAM_BUILTINS)
    def test_the_builtin_is_defined_in_the_service(self, name):
        from quantum.runtime.agent_service import BUILTIN_TOOLS
        assert name in BUILTIN_TOOLS
