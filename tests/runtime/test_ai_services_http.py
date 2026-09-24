"""The AI services against a model server that speaks HTTP (tests/fake_ollama.py).

Mocks replace a method and prove only that it was called; here every request
leaves the process, so the payloads, the parsing of the answers and the
failure paths are the real ones. What a real model does with them is tested
in tests/live_ai.
"""

import importlib.util
import uuid

import pytest

from tests.conformance.conftest import serve_pages  # noqa: F401 (fixture)
from tests.fake_ollama import FakeOllama

NS = 'xmlns:q="https://quantum.lang/ns"'


@pytest.fixture
def ollama(monkeypatch):
    with FakeOllama() as server:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', server.url)
        yield server


# ---------------------------------------------------------------- LLMService

class TestLLMService:
    def service(self, ollama, **kw):
        from quantum.runtime.llm_service import LLMService
        return LLMService(base_url=ollama.url, **kw)

    def test_generate_sends_the_options_and_reads_the_answer(self, ollama):
        ollama.reply = 'forty-two'
        result = self.service(ollama).generate('what?', model='phi3', system='be brief',
                                               temperature=0.2, max_tokens=5)
        assert result['success'] and result['data'] == 'forty-two' and result['model'] == 'phi3'
        path, body = ollama.received[-1]
        assert path == '/api/generate' and body['system'] == 'be brief' and body['stream'] is False
        assert body['options'] == {'temperature': 0.2, 'num_predict': 5}

    def test_json_answers_are_parsed_or_marked_unparsed(self, ollama):
        service = self.service(ollama)
        ollama.reply = '{"n": 1}'
        assert service.generate('x', response_format='json')['parsed'] == {'n': 1}
        assert ollama.received[-1][1]['format'] == 'json'
        ollama.reply = 'not json'
        assert service.chat([{'role': 'user', 'content': 'x'}], response_format='json')['parsed'] is None

    def test_chat_sends_the_messages(self, ollama):
        ollama.reply = lambda messages: f"you said {messages[-1]['content']}"
        result = self.service(ollama).chat([{'role': 'user', 'content': 'hi'}], temperature=0,
                                           max_tokens=9)
        assert result['data'] == 'you said hi' and result['role'] == 'assistant'
        assert ollama.received[-1][1]['options'] == {'temperature': 0, 'num_predict': 9}

    @pytest.mark.parametrize('call', ['generate', 'chat'])
    def test_an_http_error_is_an_llm_error_with_the_status(self, ollama, call):
        from quantum.runtime.llm_service import LLMError
        ollama.fail['/api/' + call] = (500, 'model not found')
        with pytest.raises(LLMError, match='500 - model not found'):
            getattr(self.service(ollama), call)('x' if call == 'generate' else [{'role': 'user', 'content': 'x'}])

    @pytest.mark.parametrize('call', ['generate', 'chat'])
    def test_a_timeout_says_how_long_it_waited(self, ollama, call):
        from quantum.runtime.llm_service import LLMError
        ollama.delay = 2
        with pytest.raises(LLMError, match='timed out after 1s'):
            getattr(self.service(ollama, timeout=1), call)(
                'x' if call == 'generate' else [{'role': 'user', 'content': 'x'}])

    @pytest.mark.parametrize('call', ['generate', 'chat', 'list_models', 'pull_model'])
    def test_no_server_is_a_connection_error(self, call):
        from quantum.runtime.llm_service import LLMError, LLMService
        service = LLMService(base_url='http://127.0.0.1:9')
        args = {'generate': ('x',), 'chat': ([],), 'list_models': (), 'pull_model': ('phi3',)}[call]
        with pytest.raises(LLMError, match='Cannot connect'):
            getattr(service, call)(*args)

    def test_models_pull_and_connection(self, ollama):
        service = self.service(ollama)
        assert [m['name'] for m in service.list_models()['models']] == ['phi3', 'nomic-embed-text']
        assert service.pull_model('qwen2') == {'success': True, 'model': 'qwen2'}
        assert ollama.received[-1] == ('/api/pull', {'name': 'qwen2', 'stream': False})
        assert service.test_connection()['model_count'] == 2
        ollama.fail['/api/tags'] = (500, 'down')
        assert service.test_connection()['online'] is False
        from quantum.runtime.llm_service import LLMError
        with pytest.raises(LLMError, match='Error listing models'):
            service.list_models()
        ollama.fail['/api/pull'] = (404, 'no such model')
        with pytest.raises(LLMError, match='Error pulling model x'):
            service.pull_model('x')

    def test_the_defaults_come_from_the_environment(self, monkeypatch):
        from quantum.runtime.llm_service import LLMService
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', 'http://example:1/')
        monkeypatch.setenv('QUANTUM_LLM_DEFAULT_MODEL', 'qwen2')
        monkeypatch.setenv('QUANTUM_LLM_TIMEOUT', '7')
        service = LLMService()
        assert (service.base_url, service.default_model, service.timeout) == ('http://example:1', 'qwen2', 7)


# ----------------------------------------------------------- Ollama provider

class TestOllamaProvider:
    def provider(self, ollama):
        from quantum.runtime.llm_providers import OllamaProvider
        return OllamaProvider(base_url=ollama.url)

    def test_chat(self, ollama):
        ollama.reply = 'hello'
        response = self.provider(ollama).chat([{'role': 'user', 'content': 'hi'}], model='phi3',
                                              temperature=0.5, max_tokens=3, response_format='json')
        assert response.content == 'hello' and response.usage['total_tokens'] == 10
        assert ollama.received[-1][1]['format'] == 'json'

    def test_stream_chat_yields_the_pieces(self, ollama):
        # IA-7
        ollama.reply = 'one two three'
        pieces = list(self.provider(ollama).stream_chat([{'role': 'user', 'content': 'x'}],
                                                        temperature=0, max_tokens=5))
        assert pieces == ['one ', 'two ', 'three'] and ollama.received[-1][1]['stream'] is True

    def test_stream_chat_failures(self, ollama):
        from quantum.runtime.llm_providers import LLMProviderError
        provider = self.provider(ollama)
        ollama.fail['/api/chat'] = (404, 'model "x" not found')
        with pytest.raises(LLMProviderError, match='404'):
            list(provider.stream_chat([]))
        ollama.fail.clear()
        ollama.delay = 2
        with pytest.raises(LLMProviderError, match='timed out after 1s'):
            list(provider.stream_chat([], timeout=1))              # per request (IA-8)

    def test_chat_failures(self, ollama):
        from quantum.runtime.llm_providers import LLMProviderError
        provider = self.provider(ollama)
        ollama.fail['/api/chat'] = (500, 'boom')
        with pytest.raises(LLMProviderError, match='500 - boom'):
            provider.chat([])
        ollama.fail.clear()
        ollama.delay = 2
        with pytest.raises(LLMProviderError, match='timed out after 1s'):
            provider.chat([], timeout=1)

    def test_list_models(self, ollama):
        provider = self.provider(ollama)
        assert provider.list_models() == ['phi3', 'nomic-embed-text']
        ollama.fail['/api/tags'] = (500, 'x')
        assert provider.list_models() == []


# ---------------------------------------------------------- KnowledgeService

needs_chromadb = pytest.mark.skipif(importlib.util.find_spec('chromadb') is None,
                                    reason='the [rag] extra is not installed')


@pytest.fixture
def knowledge(ollama, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from quantum.runtime.knowledge_service import KnowledgeService
    from quantum.runtime.llm_service import LLMService
    return KnowledgeService(llm_service=LLMService(base_url=ollama.url))


def text_source(text):
    from quantum.core.features.knowledge_base.src.ast_node import KnowledgeSourceNode
    return KnowledgeSourceNode(source_type='text', content=text)


DOCS = ['Pagination: q:query paginate="true" pageSize="10" splits the rows into pages.',
        'Sessions keep values between requests of the same visitor.',
        'A knowledge base answers questions from documents.']


@needs_chromadb
class TestKnowledgeService:
    def index(self, knowledge, name, texts=DOCS, **kw):
        knowledge.index_knowledge(name, [text_source(t) for t in texts], persist=False, **kw)

    def test_search_finds_the_document_that_shares_the_words(self, knowledge):
        name = f'kb-{uuid.uuid4().hex[:8]}'
        self.index(knowledge, name)
        hits = knowledge.search(name, 'how do pages and pagination work', n_results=2)
        assert 'Pagination' in hits[0]['content'] and 0 <= hits[0]['relevance'] <= 1
        assert len(hits) == 2 and hits[0]['source']

    def test_an_unchanged_base_is_not_embedded_again(self, knowledge, ollama):
        name = f'kb-{uuid.uuid4().hex[:8]}'
        self.index(knowledge, name)
        embeds = ollama.paths().count('/api/embed')
        self.index(knowledge, name)
        assert ollama.paths().count('/api/embed') == embeds
        self.index(knowledge, name, texts=DOCS + ['Something new.'])
        assert ollama.paths().count('/api/embed') > embeds

    def test_embedding_failures_are_errors(self, knowledge, ollama):
        from quantum.runtime.knowledge_service import KnowledgeError
        ollama.fail['/api/embed'] = (404, 'model "nomic-embed-text" not found')
        with pytest.raises(KnowledgeError, match='404'):
            self.index(knowledge, f'kb-{uuid.uuid4().hex[:8]}')
        ollama.fail.clear()
        ollama.embed_count = 1
        with pytest.raises(KnowledgeError, match='Embedding count mismatch'):
            self.index(knowledge, f'kb-{uuid.uuid4().hex[:8]}')

    def test_an_unknown_base_is_an_error(self, knowledge):
        from quantum.runtime.knowledge_service import KnowledgeError
        with pytest.raises(KnowledgeError, match="'nowhere' not found"):
            knowledge.search('nowhere', 'x')

    def test_long_text_is_chunked_with_overlap(self, knowledge):
        text = ' '.join(f'Sentence number {i} is here.' for i in range(60))
        chunks = knowledge._chunk_text(text, chunk_size=120, chunk_overlap=20)
        assert len(chunks) > 5 and all(len(c) <= 160 for c in chunks)
        assert knowledge._chunk_text('', 100) == [] and knowledge._chunk_text('short', 100) == ['short']

    def test_a_page_answers_with_sources(self, ollama, serve_pages):
        # IA-6, end to end over HTTP
        ollama.reply = 'Pages come from paginate [1].'
        page = (f'<q:component name="a" {NS} xmlns:ui="https://quantum.lang/ui">'
                f'<q:knowledge name="kb{uuid.uuid4().hex[:6]}" persist="false">'
                + ''.join(f'<q:source type="text">{d}</q:source>' for d in DOCS) +
                '</q:knowledge>'
                '<q:llm name="answer" model="phi3" knowledge="KB" top="2">'
                '<q:message role="user">pagination rows</q:message></q:llm>'
                '<p id="a">{answer}|{answer_result.cited}|{answer_result.sources[0].name}</p></q:component>')
        kb = page.split('name="kb', 1)[1].split('"', 1)[0]
        page = page.replace('knowledge="KB"', f'knowledge="kb{kb}"')
        html = serve_pages(a=page).get('/a').get_data(as_text=True)
        assert 'Pages come from paginate [1].|[1]|' in html
        grounding = [b for p, b in ollama.received if p == '/api/chat'][-1]['messages'][0]['content']
        assert 'Pagination: q:query' in grounding
