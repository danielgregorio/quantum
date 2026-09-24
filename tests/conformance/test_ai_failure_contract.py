"""Conformance: the failure contract of the AI tags (SPEC IA-5).

Runs without a model server on purpose: the server here does not exist, which
is exactly the failure being specified.
"""

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

NS = 'xmlns:q="https://quantum.lang/ns"'


@pytest.fixture(autouse=True)
def no_model_server(monkeypatch):
    monkeypatch.setenv('QUANTUM_LLM_BASE_URL', 'http://127.0.0.1:9')


def run(body):
    return ComponentRuntime(config={}).execute_component(
        QuantumParser().parse(f'<q:component name="c" {NS}>{body}</q:component>'), {})


LLM = '<q:llm name="answer" model="phi3" timeout="3" {extra}><q:prompt>hi</q:prompt></q:llm>'
# persist="false": the base is never built here, but opening its store at the
# default ./.quantum/knowledge wrote into the repository.
KB = '<q:knowledge name="kb" persist="false" {extra}><q:source type="text">Quantum pages are .q files.</q:source></q:knowledge>'
RAG = ('<q:query name="rag" datasource="knowledge:kb" {extra}>'
       'SELECT content FROM chunks WHERE content SIMILAR TO :q'
       '<q:param name="q" value="what is quantum"/></q:query>')
AGENT = ('<q:agent name="helper" model="phi3" maxIterations="2" {extra}>'
         '<q:instruction>Use the tool.</q:instruction>'
         '<q:tool name="one" description="Returns one"><q:function name="f"><q:return value="1"/></q:function></q:tool>'
         '<q:execute task="hi"/></q:agent>')


def test_an_llm_failure_stops_the_page_and_says_how_to_handle_it():
    # IA-5
    with pytest.raises(Exception, match=r'Cannot connect to .*127\.0\.0\.1:9.*onerror="continue"'):
        run(LLM.format(extra=''))


def test_an_llm_failure_can_be_handled_by_the_page():
    # IA-5
    result = run(LLM.format(extra='onerror="continue"') +
                 '<q:return value="{[answer, answer_result.success, answer_result.error.message]}"/>')
    assert result[0] == '' and result[1] is False and 'Cannot connect' in result[2]


def test_a_knowledge_base_that_cannot_be_built_is_never_answered_as_loading():
    # IA-5 (before: the rag query answered "Knowledge base is still loading", success=True)
    with pytest.raises(Exception, match=r"knowledge base 'kb' could not be built: "):
        run(KB.format(extra='onerror="continue"') + RAG.format(extra=''))


def test_the_page_can_handle_both_failures():
    # IA-5
    result = run(KB.format(extra='onerror="continue"') + RAG.format(extra='onerror="continue"') +
                 '<q:return value="{[kb_info.success, rag_result.success, rag_result.error.message, len(rag)]}"/>')
    assert result[0] is False and result[1] is False and 'could not be built' in result[2] and result[3] == 0


def test_a_failing_sql_query_can_be_handled_too():
    # IA-5
    result = run('<q:query name="q" datasource="nowhere" onerror="continue">SELECT 1</q:query>'
                 '<q:return value="{[q_result.success, q_result.recordCount, len(q)]}"/>')
    assert result[0] is False and result[1] == 0 and result[2] == 0


@pytest.mark.parametrize("tag", [LLM, KB, RAG, AGENT])
def test_onerror_takes_fail_or_continue(tag):
    # IA-5
    with pytest.raises(Exception, match=r'onerror must be "fail" or "continue"'):
        QuantumParser().parse(f'<q:component name="c" {NS}>{tag.format(extra="onerror=\"ignore\"")}</q:component>')


@pytest.mark.parametrize('tag', [LLM.format(extra='').replace('timeout="3"', 'timeout="1"'),
                                 AGENT.format(extra='timeout="1500"')])
def test_the_declared_timeout_is_the_one_waited(monkeypatch, tag):
    # IA-5, IA-8: timeout= was read and never used — every request waited 60 seconds.
    # q:agent's timeout (1500 ms) is the whole run's budget: the model call gets 1s.
    import socket
    import time
    silent = socket.socket()
    silent.bind(('127.0.0.1', 0))
    silent.listen(4)                       # accepts the connection, never answers
    monkeypatch.setenv('QUANTUM_LLM_BASE_URL', f'http://127.0.0.1:{silent.getsockname()[1]}')
    started = time.monotonic()
    try:
        with pytest.raises(Exception, match=r'timed out after 1s'):
            run(tag)
    finally:
        silent.close()
    assert time.monotonic() - started < 10


def test_an_agent_failure_stops_the_page():
    # IA-5 (before: success=false and an empty answer on a page that went on)
    with pytest.raises(Exception, match=r'Agent "helper" failed: .*Cannot connect.*onerror="continue"'):
        run(AGENT.format(extra=''))


def test_an_agent_failure_can_be_handled_by_the_page():
    # IA-5
    result = run(AGENT.format(extra='onerror="continue"') +
                 '<q:return value="{[helper, helper_result.success, helper_result.error.message]}"/>')
    assert result[0] == '' and result[1] is False and 'Cannot connect' in result[2]


def test_max_iterations_is_spelled_maxiterations():
    # IA-5 (before: max_iterations="4", as the guide wrote it, was ignored)
    with pytest.raises(Exception, match=r'the attribute is maxIterations'):
        QuantumParser().parse(f'<q:component name="c" {NS}>'
                              f'{AGENT.replace("maxIterations", "max_iterations").format(extra="")}</q:component>')
