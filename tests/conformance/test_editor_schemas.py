"""The editor tooling describes the language the parser accepts (PARSE-1, PARSE-3).

quantum-lsp and vscode-quantum listed tags and attributes by hand and drifted:
vscode's q:llm had no knowledge/top/minRelevance, both offered q:persist and
q:route (removed), q:component's basePath/health/metrics/trace (refused) and
q:query mode="rag". Here:

- quantum-lsp's Core/AI tags have exactly the attributes the parser reads and
  does not refuse (editor_schema_inventory.py measures them by parsing);
- every q: tag either tool describes is one the parser knows;
- vscode-quantum's Core/AI block and grammar are what
  scripts/generate-editor-schemas.py writes from quantum-lsp;
- every q: snippet of vscode-quantum parses.
"""

import importlib.util
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import editor_schema_inventory as inventory  # noqa: E402
from quantum.core.parser import QuantumParser  # noqa: E402


def generator():
    spec = importlib.util.spec_from_file_location('gen', REPO / 'scripts' / 'generate-editor-schemas.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# quantum-lsp's schema, loaded without the server (CI does not install pygls).
QUANTUM_TAGS = generator().load_schema().QUANTUM_TAGS
CORE_AI_TAGS = generator().CORE_AI_TAGS
ACCEPTED = inventory.accepted()


def known_q_tags():
    parser = QuantumParser()
    registry = parser.parser_registry
    names = {t for t in registry.registered_tags
             if type(registry.get_parser(t)).__name__ != 'HTMLParser'}
    # Resolved by the root parser or by a parent's parser, not the registry.
    return names | set(ACCEPTED) | {'component', 'application', 'return', 'else', 'elseif', 'script', 'onEvent',
                                    'prompt', 'system', 'body', 'instruction', 'transform'}


@pytest.mark.parametrize('name', sorted(CORE_AI_TAGS))
def test_the_lsp_lists_exactly_the_attributes_the_parser_accepts(name):
    # PARSE-3: an attribute the parser refuses is not offered; one it reads is documented
    listed = set(CORE_AI_TAGS[name].attributes)
    accepted = set(ACCEPTED.get(name[2:], []))
    assert listed == accepted, (f'{name}: only in quantum-lsp {sorted(listed - accepted)}, '
                                f'only in the parser {sorted(accepted - listed)}')


def test_every_tag_the_parser_reads_is_described():
    # PARSE-1
    missing = sorted(f'q:{t}' for t in ACCEPTED if f'q:{t}' not in CORE_AI_TAGS)
    assert not missing, f'q: tags the parser reads that quantum-lsp does not describe: {missing}'


def test_no_tool_offers_a_tag_the_parser_does_not_know():
    # PARSE-1 (q:persist and q:route were offered long after they left)
    known = known_q_tags()
    lsp = {name[2:] for name, info in QUANTUM_TAGS.items() if info.namespace == 'q'}
    vscode = set(generator().q_tag_names(generator().SCHEMA.read_text(encoding='utf-8')))
    assert sorted(lsp - known) == [] and sorted(vscode - known) == []


def test_vscode_is_generated_from_the_lsp_schema():
    gen = generator()
    schema = gen.SCHEMA.read_text(encoding='utf-8')
    grammar = gen.GRAMMAR.read_text(encoding='utf-8')
    assert schema == gen.schema_text(schema), 'run python scripts/generate-editor-schemas.py'
    assert grammar == gen.grammar_text(grammar, gen.q_tag_names(schema)), \
        'run python scripts/generate-editor-schemas.py'


def snippets():
    data = json.loads((REPO / 'vscode-quantum' / 'snippets' / 'quantum.json').read_text(encoding='utf-8'))
    for title, snippet in data.items():
        body = '\n'.join(snippet['body']) if isinstance(snippet['body'], list) else snippet['body']
        if '<q:' in body and '<q:application' not in body:
            yield pytest.param(body, id=title)


def fill(body):
    """A snippet with its placeholders filled in: ${1:x} -> x, ${1|a,b|} -> a, $1/$0 -> ''."""
    body = re.sub(r'\$\{\d+\|([^,|}]*)[^}]*\|\}', r'\1', body)
    while re.search(r'\$\{\d+:([^{}]*)\}', body):
        body = re.sub(r'\$\{\d+:([^{}]*)\}', r'\1', body)
    return re.sub(r'\$\{?\d+\}?', '', body)


@pytest.mark.parametrize('body', list(snippets()))
def test_every_snippet_parses(body):
    # PARSE-1, PARSE-3
    source = fill(body)
    if source.lstrip().startswith('<q:flash'):
        source = f'<q:action name="a" method="POST">{source}</q:action>'      # ACT-3: only in an action
    if '<q:component' not in source:
        source = f'<q:component name="Snippet">{source}</q:component>'
    source = source.replace('<q:component ', '<q:component xmlns:q="https://quantum.lang/ns" ', 1)
    QuantumParser(use_cache=False).parse(source)


# ------------------------------------------------------------------ the values of the attributes

def closed_lists():
    """(tag, attribute) -> the values the parser accepts, from the constants it checks against (PARSE-5)."""
    from quantum.core.parsers.control_flow.loop_parser import LOOP_TYPES
    from quantum.core.parsers.control_flow.set_parser import OPERATIONS, SCOPES
    from quantum.core.parsers.data.invoke_parser import AUTH_TYPES, HTTP_METHODS
    from quantum.runtime.executors.control_flow.set_executor import SET_TYPES
    from quantum.runtime.param_validation import PARAM_TYPES, QUERY_PARAM_TYPES, RETURN_TYPES
    from quantum.runtime.validators import QuantumValidators
    return {
        ('q:param', 'type'): set(PARAM_TYPES) | set(QUERY_PARAM_TYPES),
        ('q:function', 'returnType'): set(RETURN_TYPES),
        ('q:set', 'type'): set(SET_TYPES),
        ('q:set', 'operation'): set(OPERATIONS),
        ('q:set', 'scope'): set(SCOPES),
        ('q:set', 'validate'): set(QuantumValidators.PATTERNS),
        ('q:param', 'validate'): set(QuantumValidators.PATTERNS),
        ('q:loop', 'type'): set(LOOP_TYPES),
        ('q:invoke', 'method'): set(HTTP_METHODS),
        ('q:invoke', 'authType'): set(AUTH_TYPES),
    }


@pytest.mark.parametrize('tag,attribute', sorted(closed_lists()))
def test_the_lsp_offers_the_values_the_parser_accepts(tag, attribute):
    # PARSE-5 (q:param offered datetime everywhere, and not time)
    offered = set(CORE_AI_TAGS[tag].attributes[attribute].enum_values)
    accepted = closed_lists()[(tag, attribute)]
    assert offered == accepted, (f'{tag} {attribute}: only offered {sorted(offered - accepted)}, '
                                 f'only accepted {sorted(accepted - offered)}')


def test_a_param_type_says_which_types_only_a_query_takes():
    # PARSE-5: one q:param entry serves every context; the description names the difference
    from quantum.runtime.param_validation import PARAM_TYPES, QUERY_PARAM_TYPES
    description = CORE_AI_TAGS['q:param'].attributes['type'].description
    assert all(f'`{t}`' in description for t in set(QUERY_PARAM_TYPES) - set(PARAM_TYPES))


@pytest.mark.parametrize('tag', ['q:set', 'q:param'])
def test_validate_takes_a_regular_expression_too(tag):
    # SET-4: `^...` is accepted besides the named validators, so the value is not an enum
    info = CORE_AI_TAGS[tag].attributes['validate']
    assert '`^`' in info.description and info.type.value != 'enum'
