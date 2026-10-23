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
    assert ExpressionEvaluator().evaluate('urlencode(q)', {'q': 'café au lait? & more'}) == \
        'caf%C3%A9+au+lait%3F+%26+more'


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


# ------------------------------------------------------------------ IA-10: a base per board, its values bound

@pytest.mark.parametrize('sql,message', [
    ("SELECT text FROM notes WHERE board = {board}", r'direct \{var\} interpolation'),
    ("SELECT text FROM notes WHERE board = :board", r':board have no <q:param>'),
])
def test_a_query_source_takes_its_values_as_params_or_is_a_parse_error(sql, message):
    # IA-10 (before: its SQL was databound like text — {id} from the URL went into the SQL as written)
    with pytest.raises(Exception, match=message):
        QuantumParser().parse(f'<q:component name="c" {NS}><q:knowledge name="kb">'
                              f'<q:source type="query" datasource="db">{sql}</q:source></q:knowledge></q:component>')


def test_a_base_per_board_answers_from_that_board_only(ollama, tmp_path):
    # IA-10: name="notes{board}" and a bound :board — two boards, two bases, never each other's rows
    import sqlite3
    db = tmp_path / 'notes.db'
    c = sqlite3.connect(db)
    c.executescript("CREATE TABLE notes (board INTEGER, text TEXT);"
                    "INSERT INTO notes VALUES (1, 'Ana has the domain of the site.'),"
                    " (2, 'Bruno has the domain of the app.');")
    c.commit()
    ollama.reply = 'From the notes [1].'
    seen = {}
    for board in ('1', '2', "1 OR 1 = 1"):
        runtime = ComponentRuntime(config={'datasources': {'db': {'driver': 'sqlite', 'database': str(db)}}})
        page = (f'<q:component name="c" {NS}><q:set name="board" value="{board}"/>'
                '<q:knowledge name="notes{board}" persist="false" onerror="continue">'
                '<q:source type="query" datasource="db">SELECT text FROM notes WHERE board = :board'
                '<q:param name="board" value="{board}" type="integer"/></q:source></q:knowledge>'
                '<q:llm name="answer" model="phi3" knowledge="notes{board}" onerror="continue">'
                '<q:prompt>Who has the domain?</q:prompt></q:llm></q:component>')
        runtime.execute_component(QuantumParser().parse(page), {})
        get = runtime.execution_context.get_variable
        seen[board] = (get(f'notes{board}_info'), get('answer_result'))
    assert [s['text'] for s in seen['1'][1]['sources']] == ['Ana has the domain of the site.']
    assert [s['text'] for s in seen['2'][1]['sources']] == ['Bruno has the domain of the app.']
    info, answer = seen['1 OR 1 = 1']
    assert info['success'] is False and 'board' in info['error'] and not answer['success']
