"""Conformance: knowledge sources are read or the page says why (SPEC IA-8), and urlencode (EXPR-12)."""

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

NS = 'xmlns:q="https://quantum.lang/ns"'


def run(sources, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('QUANTUM_LLM_BASE_URL', 'http://127.0.0.1:9')
    return ComponentRuntime(config={}).execute_component(QuantumParser().parse(
        f'<q:component name="c" {NS}><q:knowledge name="kb" persist="false">{sources}</q:knowledge>'
        '</q:component>'), {})


@pytest.mark.parametrize('source,message', [
    ('<q:source type="file" path="missing.md"/>', r'path="missing.md">: no such file'),
    ('<q:source type="directory" path="nowhere"/>', r'path="nowhere">: no such folder'),
    ('<q:source type="directory" path="." pattern="*.nothing"/>', r"no file matches '\*\.nothing'"),
])
def test_a_source_that_cannot_be_read_is_an_error(tmp_path, monkeypatch, source, message):
    # IA-8 (before: a warning in the log, and a smaller base)
    with pytest.raises(Exception, match=message):
        run(source, tmp_path, monkeypatch)


@pytest.mark.parametrize('kind', ['url', 'pdf'])
def test_a_source_type_that_reads_nothing_is_a_parse_error(kind):
    # IA-8 (before: type="url" was accepted and read nothing)
    with pytest.raises(Exception, match=rf'<q:source type="{kind}">: use text, file, directory or query'):
        QuantumParser().parse(f'<q:component name="c" {NS}><q:knowledge name="kb">'
                              f'<q:source type="{kind}" url="http://x"/></q:knowledge></q:component>')


def test_urlencode():
    # EXPR-12
    from quantum.core.expressions import ExpressionEvaluator
    assert ExpressionEvaluator().evaluate('urlencode(q)', {'q': 'é a ação? & mais'}) == \
        '%C3%A9+a+a%C3%A7%C3%A3o%3F+%26+mais'


# ------------------------------------------------------------------ IA-2, on a model server that speaks HTTP

@pytest.fixture
def ollama(monkeypatch, tmp_path):
    import importlib.util
    if importlib.util.find_spec('chromadb') is None:
        pytest.skip('the [rag] extra is not installed')
    from tests.fake_ollama import FakeOllama
    monkeypatch.chdir(tmp_path)
    with FakeOllama() as server:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', server.url)
        yield server


def build(tmp_path, text, name='kb', attrs=''):
    """Runs a page with a persisted base and returns how many chunks were embedded."""
    ComponentRuntime(config={}).execute_component(QuantumParser().parse(
        f'<q:component name="c" {NS}><q:knowledge name="{name}" persistPath="{tmp_path.as_posix()}/kb" {attrs}>'
        f'<q:source type="text">{text}</q:source></q:knowledge></q:component>'), {})


def embeds(ollama):
    return ollama.paths().count('/api/embed')


def test_a_persisted_base_is_reused_while_nothing_changed(ollama, tmp_path):
    # IA-2: the second run embeds nothing
    build(tmp_path, 'Quantum pages are .q files.')
    first = embeds(ollama)
    build(tmp_path, 'Quantum pages are .q files.')
    assert first > 0 and embeds(ollama) == first


@pytest.mark.parametrize('change', [
    {'text': 'Quantum pages are served on port 8080.'},
    {'attrs': 'embedModel="other-embed"'},
    {'attrs': 'chunkSize="10" chunkOverlap="2"'},
])
def test_a_changed_source_model_or_chunking_indexes_again(ollama, tmp_path, change):
    # IA-2 (before: the base persisted under the name was reused and new sources were ignored)
    build(tmp_path, 'Quantum pages are .q files.')
    first = embeds(ollama)
    build(tmp_path, change.get('text', 'Quantum pages are .q files.'), attrs=change.get('attrs', ''))
    assert embeds(ollama) > first


@pytest.mark.parametrize('name', ['k', 'my base', 'bases/2026'])
def test_any_name_is_accepted(ollama, tmp_path, name):
    # IA-2: ChromaDB's collection-name rules are not the page's problem
    build(tmp_path, 'Quantum pages are .q files.', name=name)
