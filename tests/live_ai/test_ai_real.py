"""
AI against a REAL model (decision D6: the AI tests must be real).

These tests do not run in the ordinary CI — GitHub's runner cannot reach the
model server. They run before every release, on any machine with access to
Ollama:

    QUANTUM_LIVE_AI=1 QUANTUM_LLM_BASE_URL=http://<host>:11434 pytest tests/live_ai

Models: QUANTUM_LIVE_AI_MODEL (default phi3) and QUANTUM_LIVE_AI_EMBED
(default nomic-embed-text).

Structural assertions, never the exact text: a real model is not
deterministic. What is checked is THAT the tool was called and with which
arguments, THAT the right chunk was retrieved, THAT the number shows in the
answer. No automatic retry — a wobble shows as a failure and is investigated.

Every AI bug found on 2026-09-10 by running against a real model server has a test
here:
- IA-1: q:llm and q:agent used DIFFERENT servers in the same program.
- IA-2: q:knowledge reused the base persisted under the name and ignored new
        sources (it answered with text from an old run).
- IA-3: a RAG failure came back as the ANSWER ("Error generating answer...").
        q:query mode="rag" is gone since (IA-3 now); the same guard covers
        q:llm knowledge=.

And the P0 fixes of the AI proposal (0.22):
- IA-9: vector search always returns the `top` nearest chunks, so found=false
        only happened on an EMPTY base; minRelevance is the floor.
- IA-1: a tag without model= asked for 'phi3', whatever was configured.
"""

import contextlib
import io
import os
import pathlib
import socket
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(os.environ.get('QUANTUM_LIVE_AI') != '1',
                       reason='real AI: set QUANTUM_LIVE_AI=1 and QUANTUM_LLM_BASE_URL'),
]

MODEL = os.environ.get('QUANTUM_LIVE_AI_MODEL', 'phi3')
EMBED = os.environ.get('QUANTUM_LIVE_AI_EMBED', 'nomic-embed-text')


def run_body(body, config=None):
    """Runs a component and returns the context's variables."""
    path = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    path.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
        encoding='utf-8')
    runtime = ComponentRuntime(config=config if config is not None else {})
    with contextlib.redirect_stdout(io.StringIO()):
        runtime.execute_component(QuantumParser().parse_file(str(path)), {})
    return runtime.execution_context.get_all_variables()


def closed_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestLlm:
    def test_completes_text_with_databinding(self):
        v = run_body(
            f'<q:set name="product" value="Quantum"/>'
            f'<q:llm name="slogan" model="{MODEL}" temperature="0" maxTokens="60">'
            f'<q:prompt>Write a one-sentence slogan for {{product}}, a web framework.</q:prompt>'
            f'</q:llm>')
        assert isinstance(v['slogan'], str) and v['slogan'].strip()

    def test_a_json_answer_becomes_an_object(self):
        v = run_body(
            f'<q:llm name="data" model="{MODEL}" responseFormat="json" temperature="0">'
            f'<q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".'
            f'</q:prompt></q:llm>')
        data = v['data']
        assert isinstance(data, dict), data
        assert str(data.get('age')) == '34'


    def test_chat_mode_with_messages(self):
        v = run_body(
            f'<q:llm name="r" model="{MODEL}" temperature="0" maxTokens="60">'
            '<q:message role="system">Answer with a single word.</q:message>'
            '<q:message role="user">What color is the clear daytime sky?</q:message>'
            '</q:llm>')
        assert 'blue' in str(v['r']).lower()


def render(body):
    """Runs and renders — what the page really shows."""
    from quantum.runtime.renderer import HTMLRenderer
    path = pathlib.Path(tempfile.mkdtemp()) / 'p.q'
    path.write_text(
        f'<q:component name="P" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
        encoding='utf-8')
    runtime = ComponentRuntime(config={})
    node = QuantumParser().parse_file(str(path))
    with contextlib.redirect_stdout(io.StringIO()):
        runtime.execute_component(node, {})
        return HTMLRenderer(runtime.execution_context).render(node)


class TestWhatThePageShows:
    def test_json_fields_on_the_page(self):
        html = render(
            f'<q:llm name="data" model="{MODEL}" responseFormat="json" temperature="0">'
            f'<q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".'
            f'</q:prompt></q:llm><p>AGE={{data.age}}</p>')
        assert 'AGE=34' in html

    def test_the_rag_answer_on_the_page_in_memory(self):
        # IA-6
        html = render(
            f'<q:knowledge name="manual" embedModel="{EMBED}" persist="false">'
            '<q:source type="text">Quantum pages are served on port 8080 by default.</q:source>'
            '</q:knowledge>'
            f'<q:llm name="reply" model="{MODEL}" knowledge="manual" timeout="240">'
            '<q:prompt>What is the default port?</q:prompt></q:llm>'
            '<p>ANSWER={reply}</p>')
        assert 'ANSWER=' in html and '8080' in html.split('ANSWER=', 1)[1]


class TestASingleServer:
    """IA-1: every AI tag uses the same server — the environment variable's."""

    def test_a_different_config_does_not_divert_q_llm(self):
        # The config points to a closed port; the environment, to the real
        # server. q:llm read the config and failed while q:agent used the
        # environment.
        config = {'llm': {'base_url': f'http://127.0.0.1:{closed_port()}'}}
        v = run_body(f'<q:llm name="ok" model="{MODEL}" temperature="0" maxTokens="10">'
                     f'<q:prompt>Say ok.</q:prompt></q:llm>', config=config)
        assert v['ok']


class TestKnowledge:
    SOURCES = ('<q:source type="text">Quantum pages are served on port 8080 by default. '
               'The quantum stop command stops the server.</q:source>'
               '<q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>')

    def base(self, folder, sources, name='test-base'):
        return (f'<q:knowledge name="{name}" embedModel="{EMBED}" '
                f'chunkSize="200" chunkOverlap="20" persistPath="{folder.as_posix()}">'
                f'{sources}</q:knowledge>')

    def test_the_search_retrieves_the_right_chunk(self, tmp_path):
        v = run_body(self.base(tmp_path, self.SOURCES) +
                     '<q:query name="t" datasource="knowledge:test-base">'
                     'SELECT content, relevance FROM chunks WHERE content SIMILAR TO :p LIMIT 1'
                     '<q:param name="p" value="Which port does the server use?" type="string"/>'
                     '</q:query>')
        assert '8080' in v['t'][0]['content']

    def test_rag_answers_from_the_chunk(self, tmp_path):
        # IA-6
        v = run_body(self.base(tmp_path, self.SOURCES) +
                     f'<q:llm name="r" model="{MODEL}" knowledge="test-base" timeout="240">'
                     '<q:prompt>What is the default port?</q:prompt></q:llm>')
        assert '8080' in v['r']

    def test_new_sources_reindex_the_persisted_base(self, tmp_path):
        # IA-2: the same base, the same path, a changed source.
        old = '<q:source type="text">The secret code is BANANA.</q:source>'
        new = '<q:source type="text">The secret code is PITANGA.</q:source>'
        query = ('<q:query name="t" datasource="knowledge:test-base">'
                 'SELECT content FROM chunks WHERE content SIMILAR TO :p LIMIT 1'
                 '<q:param name="p" value="secret code" type="string"/></q:query>')
        run_body(self.base(tmp_path, old) + query)
        v = run_body(self.base(tmp_path, new) + query)
        assert 'PITANGA' in v['t'][0]['content']

    def test_a_short_name_works(self, tmp_path):
        # ChromaDB requires 3+ characters in a collection name; name="kb"
        # broke with its validation message.
        v = run_body(self.base(tmp_path, self.SOURCES, name='kb') +
                     '<q:query name="t" datasource="knowledge:kb">'
                     'SELECT content FROM chunks WHERE content SIMILAR TO :p LIMIT 1'
                     '<q:param name="p" value="port" type="string"/></q:query>')
        assert v['t']

    def test_a_rag_failure_is_an_error_not_an_answer(self, tmp_path):
        # IA-3, IA-5: the search works (real embedding) and the GENERATION
        # fails, because the model does not exist on the server. With
        # mode="rag" the error came back as the answer: "Error generating
        # answer: ...", with confidence 0. A closed port does not provoke this
        # — the search would break first.
        with pytest.raises(Exception) as error:
            run_body(self.base(tmp_path, self.SOURCES) +
                     '<q:llm name="r" model="a-model-that-does-not-exist" knowledge="test-base">'
                     '<q:prompt>What is the default port?</q:prompt></q:llm>')
        assert 'Error generating answer' not in str(error.value)
        assert 'a-model-that-does-not-exist' in str(error.value)


class TestAgent:
    def test_calls_the_tool_and_uses_the_result(self):
        # IA-4
        v = run_body(
            f'<q:agent name="calc" model="{MODEL}" maxIterations="4" timeout="240000">'
            '<q:instruction>Use the add tool, then answer with the number.</q:instruction>'
            '<q:tool name="add" description="Add two numbers">'
            '<q:param name="a" type="number" required="true"/>'
            '<q:param name="b" type="number" required="true"/>'
            '<q:function name="doAdd"><q:set name="s" value="{a + b}" type="number"/>'
            '<q:return value="{s}"/></q:function></q:tool>'
            '<q:execute task="What is 17 plus 25?"/></q:agent>')
        result = v['calc_result']
        assert result['success'], result.get('error')
        calls = [a for a in result['actions'] if a['tool'] == 'add']
        assert calls and calls[0]['result'] == 42
        assert '42' in str(v['calc'])


class TestTheServerIsDown:
    def test_q_llm_fails_with_an_error_that_names_the_server(self, monkeypatch):
        port = closed_port()
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', f'http://127.0.0.1:{port}')
        with pytest.raises(Exception) as error:
            run_body(f'<q:llm name="x" model="{MODEL}"><q:prompt>hi</q:prompt></q:llm>')
        assert str(port) in str(error.value) or 'connect' in str(error.value).lower()


class TestGroundedAnswers:
    """IA-6 (M5): q:llm knowledge= answers from a knowledge base and cites it."""

    BASE = ('<q:knowledge name="docs" persist="false" embedModel="{embed}">'
            '<q:source type="text">A q:action handles a form post. It validates its q:param fields '
            'and ends with q:redirect.</q:source>'
            '<q:source type="text">The /_dev panel lists the queries of the last requests when '
            'server.debug is true.</q:source></q:knowledge>')

    def test_the_answer_comes_with_numbered_sources_and_citations(self):
        # IA-6
        v = run_body(self.BASE.format(embed=EMBED) +
                     f'<q:llm name="answer" model="{MODEL}" knowledge="docs" top="2" timeout="240">'
                     '<q:message role="user">How is a form post handled?</q:message></q:llm>')
        result = v['answer_result']
        assert result['found'] is True and [s['n'] for s in result['sources']] == [1, 2]
        assert 'q:action' in result['sources'][0]['text']          # the right chunk comes first
        assert v['answer'].strip()
        assert set(result['cited']) <= {1, 2}
        if MODEL == 'phi3':                                      # a model that follows the instruction
            assert result['cited'], v['answer']

    def test_with_nothing_to_answer_from_the_model_is_not_asked(self):
        # IA-6: an empty base — no call, found=false, never an uncited answer
        v = run_body(f'<q:knowledge name="empty" persist="false" embedModel="{EMBED}"></q:knowledge>'
                     f'<q:llm name="answer" model="{MODEL}" knowledge="empty" timeout="60">'
                     '<q:prompt>anything</q:prompt></q:llm>')
        assert v['answer'] == '' and v['answer_result']['found'] is False and v['answer_result']['sources'] == []

    def test_a_question_the_base_says_nothing_about_is_not_sent_to_the_model(self):
        # IA-9: without the floor, both chunks came back and the model answered anyway.
        # 0.73 is this two-sentence base's scale with nomic-embed-text; the
        # docs assistant's long chunks need 0.79 (docs/guide/ai.md).
        v = run_body(self.BASE.format(embed=EMBED) +
                     f'<q:llm name="answer" model="{MODEL}" knowledge="docs" top="2" '
                     'minRelevance="0.73" timeout="240">'
                     '<q:message role="user">What is the capital of France?</q:message></q:llm>')
        result = v['answer_result']
        assert result['found'] is False and v['answer'] == '' and result['grounded'] is False

    def test_a_related_question_passes_the_floor(self):
        # IA-9
        v = run_body(self.BASE.format(embed=EMBED) +
                     f'<q:llm name="answer" model="{MODEL}" knowledge="docs" top="2" '
                     'minRelevance="0.73" timeout="240">'
                     '<q:message role="user">How is a form post handled?</q:message></q:llm>')
        result = v['answer_result']
        assert result['found'] is True and 'q:action' in result['sources'][0]['text']
        assert all(s['relevance'] >= 0.73 for s in result['sources'])
        assert result['grounded'] is bool(result['cited'])
        if MODEL == 'phi3':
            assert result['grounded'] is True, v['answer']


class TestTheConfiguredModel:
    def test_a_tag_without_model_uses_llm_model(self, monkeypatch):
        # IA-1
        monkeypatch.delenv('QUANTUM_LLM_DEFAULT_MODEL', raising=False)
        v = run_body('<q:llm name="ok" temperature="0" maxTokens="10"><q:prompt>Say ok.</q:prompt></q:llm>',
                     config={'llm': {'model': MODEL}})
        assert v['ok'] and v['ok_result']['model'] == MODEL


class TestStreamedAnswers:
    """IA-7 (M5): the answer arrives as it is written."""

    PAGE = ('<q:component name="a" xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui">'
            '<q:llm name="answer" model="{model}" stream="true" timeout="240">'
            '<q:message role="user">Count from one to ten in words.</q:message></q:llm>'
            '<ui:window title="A"><ui:stream for="answer"/></ui:window></q:component>')

    def app(self, tmp_path, monkeypatch):
        from quantum.runtime.web_server import QuantumWebServer
        (tmp_path / 'components').mkdir()
        (tmp_path / 'components' / 'a.q').write_text(self.PAGE.format(model=MODEL), encoding='utf-8')
        (tmp_path / 'quantum.config.yaml').write_text('paths: {components: ./components}\n', encoding='utf-8')
        monkeypatch.chdir(tmp_path)
        return QuantumWebServer('quantum.config.yaml').app

    def test_the_answer_comes_in_pieces(self, tmp_path, monkeypatch):
        # IA-7
        import re
        client = self.app(tmp_path, monkeypatch).test_client()
        url = re.search(r'data-q-stream="([^"]+)"', client.get('/a').get_data(as_text=True)).group(1)
        pieces = list(client.get(url).response)
        text = b''.join(pieces).decode('utf-8')
        assert len(pieces) > 1 and '\x00ERROR:' not in text and text.strip()

    def test_a_browser_shows_it_as_it_arrives(self, tmp_path, monkeypatch):
        # IA-7: the framework's script fills <ui:stream>, no JavaScript written by the page
        playwright = pytest.importorskip('playwright.sync_api')
        import threading
        from werkzeug.serving import make_server
        server = make_server('127.0.0.1', 0, self.app(tmp_path, monkeypatch), threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with playwright.sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/a')
                page.wait_for_selector('.q-stream.q-stream-done', timeout=240_000)
                assert page.inner_text('.q-stream-text').strip()
                browser.close()
        finally:
            server.shutdown()


@pytest.fixture
def docs_assistant(tmp_path, monkeypatch):
    """projects/docs-assistant served from a copy, with the repository's guide beside it.

    The app persists its index in ./.quantum/knowledge; served from the real
    project folder, the live run wrote it into the repository. Its source is
    ../../docs/guide, so the copy keeps that layout.
    """
    import shutil
    repo = pathlib.Path(__file__).resolve().parents[2]
    app = tmp_path / 'repo' / 'projects' / 'docs-assistant'
    shutil.copytree(repo / 'projects' / 'docs-assistant', app, ignore=shutil.ignore_patterns('.quantum'))
    shutil.copytree(repo / 'docs' / 'guide', tmp_path / 'repo' / 'docs' / 'guide')
    monkeypatch.chdir(app)
    from quantum.runtime.web_server import QuantumWebServer
    return QuantumWebServer('quantum.config.yaml').app.test_client()


def test_docs_assistant_answers_from_the_guide(docs_assistant):
    # IA-6 + IA-7: projects/docs-assistant, end to end, on the real guide
    import re
    client = docs_assistant
    page = client.get('/?q=How+do+I+paginate+a+query%3F').get_data(as_text=True)
    assert 'query.md' in page or 'ui.md' in page                     # the right guide pages
    url = re.search(r'data-q-stream="([^"]+)"', page).group(1)
    answer = b''.join(client.get(url).response).decode('utf-8')
    assert answer.strip() and '\x00ERROR:' not in answer


def test_docs_assistant_says_when_the_guide_has_nothing(docs_assistant):
    # IA-9: "The guide says nothing about that" only showed on an empty index
    client = docs_assistant
    page = client.get('/?q=Who+won+the+1998+World+Cup%3F').get_data(as_text=True)
    assert 'id="not-found"' in page and 'data-q-stream' not in page


def test_shop_agent_answers_from_the_database(tmp_path, monkeypatch):
    # IA-4 + IA-5: projects/shop-agent, end to end, with a real model
    import html
    import re
    import shutil
    app_dir = pathlib.Path(__file__).resolve().parents[2] / 'projects' / 'shop-agent'
    project = tmp_path / 'shop'
    shutil.copytree(app_dir, project, ignore=shutil.ignore_patterns('data'))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(project).up()
    from quantum.runtime.web_server import QuantumWebServer
    client = QuantumWebServer('quantum.config.yaml').app.test_client()
    page = client.get('/?q=How+many+open+orders+are+there%3F').get_data(as_text=True)
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))
    assert 'could not answer' not in text
    assert 'orders_by_status(status=open)' in text          # the tool, called with the right argument
