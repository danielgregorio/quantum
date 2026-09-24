"""Conformance: q:llm knowledge= (M5, SPEC IA-6) — the parts that need no model.

The answers themselves are tested against a real model in tests/live_ai (D6).
"""

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

NS = 'xmlns:q="https://quantum.lang/ns"'


def test_a_knowledge_base_that_is_not_on_the_page_is_an_error(monkeypatch):
    # IA-6
    monkeypatch.setenv('QUANTUM_LLM_BASE_URL', 'http://127.0.0.1:9')
    with pytest.raises(Exception, match=r'<q:llm knowledge="docs">: there is no <q:knowledge name="docs">'):
        ComponentRuntime(config={}).execute_component(QuantumParser().parse(
            f'<q:component name="c" {NS}><q:llm name="a" model="phi3" knowledge="docs"><q:prompt>x</q:prompt></q:llm>'
            '</q:component>'), {})


def test_top_is_a_number():
    # IA-6
    with pytest.raises(Exception, match=r'top="many"'):
        QuantumParser().parse(f'<q:component name="c" {NS}><q:llm name="a" knowledge="docs" top="many">'
                              '<q:prompt>x</q:prompt></q:llm></q:component>')


def test_an_empty_base_answers_nothing_and_asks_no_model(monkeypatch, tmp_path):
    # IA-6: with nothing retrieved, no call — never an answer from memory, uncited
    import importlib.util
    if importlib.util.find_spec('chromadb') is None:
        pytest.skip('the [rag] extra is not installed')
    from tests.fake_ollama import FakeOllama
    monkeypatch.chdir(tmp_path)
    with FakeOllama() as ollama:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', ollama.url)
        result = ComponentRuntime(config={}).execute_component(QuantumParser().parse(
            f'<q:component name="c" {NS}><q:knowledge name="empty" persist="false"></q:knowledge>'
            '<q:llm name="a" model="phi3" knowledge="empty"><q:prompt>anything</q:prompt></q:llm>'
            '<q:return value="{[a, a_result.found, a_result.sources, a_result.cited]}"/></q:component>'), {})
        assert result == ['', False, [], []]
        assert '/api/chat' not in ollama.paths() and '/api/generate' not in ollama.paths()


def test_without_timeout_q_llm_waits_60_seconds(monkeypatch):
    # IA-8: the seconds sent to the model server when timeout= is not declared
    import requests
    from tests.fake_ollama import FakeOllama
    seen = []
    real_post = requests.post

    def post(*args, **kwargs):
        seen.append(kwargs.get('timeout'))
        return real_post(*args, **kwargs)

    with FakeOllama() as ollama:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', ollama.url)
        monkeypatch.setattr(requests, 'post', post)
        ComponentRuntime(config={}).execute_component(QuantumParser().parse(
            f'<q:component name="c" {NS}><q:llm name="a" model="phi3"><q:prompt>hi</q:prompt></q:llm>'
            '</q:component>'), {})
    assert seen == [60]
