"""Generate vscode-quantum's Core/AI tag schema from quantum-lsp's.

    python scripts/generate-editor-schemas.py          # rewrite the generated parts
    python scripts/generate-editor-schemas.py --check  # exit 1 if they are not current

quantum-lsp/quantum_lsp/schema/core_tags.py is the one hand-kept description
of the Core and AI tags; tests/conformance/test_editor_schemas.py checks it
against the parser. This script writes, from it:

- the block between the GENERATED markers of the `quantumTags` array in
  vscode-quantum/src/language/quantumSchema.ts;
- the q: tag alternations of vscode-quantum/syntaxes/quantum.tmLanguage.json.

Everything outside the markers (Laboratory and Experimental tags, ui:) stays
hand-written.
"""

import importlib
import importlib.util
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def load_schema():
    """quantum_lsp.schema, without quantum_lsp/__init__.py (which starts the server and needs pygls)."""
    name = 'quantum_lsp_schema'
    if name not in sys.modules:
        folder = REPO / 'quantum-lsp' / 'quantum_lsp' / 'schema'
        spec = importlib.util.spec_from_file_location(name, folder / '__init__.py',
                                                      submodule_search_locations=[str(folder)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


CORE_AI_TAGS = importlib.import_module(load_schema().__name__ + '.core_tags').CORE_AI_TAGS

SCHEMA = REPO / 'vscode-quantum' / 'src' / 'language' / 'quantumSchema.ts'
GRAMMAR = REPO / 'vscode-quantum' / 'syntaxes' / 'quantum.tmLanguage.json'
BEGIN = '    // BEGIN GENERATED: Core and AI tags — python scripts/generate-editor-schemas.py (do not edit)\n'
END = '    // END GENERATED\n'

TS_TYPES = {'integer': 'number', 'decimal': 'number', 'boolean': 'boolean', 'expression': 'expression',
            'enum': 'enum'}


def ts(value) -> str:
    return "'" + str(value).replace('\\', '\\\\').replace("'", "\\'") + "'"


def attribute(info) -> str:
    parts = [f'name: {ts(info.name)}', f'description: {ts(info.description)}']
    if info.required:
        parts.append('required: true')
    parts.append(f"type: {ts(TS_TYPES.get(info.type.value, 'string'))}")
    if info.enum_values:
        parts.append('values: [' + ', '.join(ts(v) for v in info.enum_values) + ']')
    if info.default is not None:
        parts.append(f'default: {ts(info.default)}')
    return '            { ' + ', '.join(parts) + ' },\n'


def entry(info) -> str:
    lines = ['    {\n', f'        name: {ts(info.name)},\n', "        namespace: 'q',\n",
             f'        description: {ts(info.description)},\n', "        category: 'Core',\n"]
    if info.self_closing:
        lines.append('        selfClosing: true,\n')
    if info.children:
        lines.append('        allowedChildren: [' + ', '.join(ts(c) for c in info.children) + '],\n')
    lines.append('        attributes: [\n')
    lines.extend(attribute(a) for a in info.attributes.values())
    lines.append('        ]\n    },\n')
    return ''.join(lines)


def generated_block() -> str:
    return BEGIN + ''.join(entry(info) for info in CORE_AI_TAGS.values()) + END


def schema_text(current: str) -> str:
    start, end = current.index(BEGIN), current.index(END) + len(END)
    return current[:start] + generated_block() + current[end:]


def q_tag_names(schema: str) -> list:
    """Every q: tag the schema describes, generated or hand-written."""
    block = schema[schema.index('export const quantumTags'):schema.index('export const uiTags')]
    return sorted(set(re.findall(r"\n        name: '([\w-]+)',\n        namespace: 'q'", block)))


def grammar_text(current: str, names: list) -> str:
    alternation = '|'.join(names)
    return re.sub(r'(\(q:\)\()[\w|-]+(\))', lambda m: m.group(1) + alternation + m.group(2), current)


def main() -> int:
    schema = SCHEMA.read_text(encoding='utf-8')
    grammar = GRAMMAR.read_text(encoding='utf-8')
    new_schema = schema_text(schema)
    new_grammar = grammar_text(grammar, q_tag_names(new_schema))
    json.loads(new_grammar)
    if '--check' in sys.argv:
        stale = [p.name for p, old, new in ((SCHEMA, schema, new_schema), (GRAMMAR, grammar, new_grammar))
                 if old != new]
        if stale:
            print('not current:', ', '.join(stale), '— run python scripts/generate-editor-schemas.py')
            return 1
        return 0
    SCHEMA.write_text(new_schema, encoding='utf-8')
    GRAMMAR.write_text(new_grammar, encoding='utf-8')
    print('wrote', SCHEMA.relative_to(REPO), 'and', GRAMMAR.relative_to(REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
