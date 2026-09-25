"""The Cookbook's AI recipes against a REAL model (decision D6).

In CI, scripts/generate-cookbook.py runs examples/cookbook/ai/ against a
stand-in model server (tests/fake_ollama.py) — the report on each page comes
from that run. Before every release they run here against a real one, with
the same tests: the recipes assert structure (which source was retrieved,
that a tool was called, that a failure is shown), never the model's words.

    QUANTUM_LIVE_AI=1 QUANTUM_LLM_BASE_URL=http://<host>:11434 pytest tests/live_ai

The model is QUANTUM_LIVE_AI_MODEL (default phi3); the recipes embed with
nomic-embed-text. A recipe's minRelevance was chosen on the stand-in's scale,
which imitates nomic-embed-text's (unrelated text about 0.75); a failure of
honest-i-dont-know or knowledge-from-a-table here means the floor needs the
real model's numbers.
"""

import os
import pathlib

import pytest

from quantum.runtime.app_testing import run_tests

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(os.environ.get('QUANTUM_LIVE_AI') != '1',
                       reason='real AI: set QUANTUM_LIVE_AI=1 and QUANTUM_LLM_BASE_URL'),
]

RECIPES = sorted(p.parent for p in (pathlib.Path(__file__).resolve().parents[2]
                                    / 'examples' / 'cookbook' / 'ai').glob('*/quantum.config.yaml'))


def test_there_are_ai_recipes():
    assert len(RECIPES) >= 5


@pytest.mark.parametrize('recipe', RECIPES, ids=[r.name for r in RECIPES])
def test_the_recipe_passes_against_a_real_model(recipe, monkeypatch):
    monkeypatch.setenv('QUANTUM_LLM_DEFAULT_MODEL', os.environ.get('QUANTUM_LIVE_AI_MODEL', 'phi3'))
    lines = []
    code = run_tests([str(recipe)], out=lambda *a: lines.append(' '.join(str(x) for x in a)))
    assert code == 0, '\n'.join(lines)
