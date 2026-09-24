"""Parse a `*.test.q` file into TestFileNode (TEST-1, TEST-4).

The vocabulary is deliberately small, and anything outside it is a parse
error that says what is allowed — never a step that silently does nothing
(PARSE-3). The old `qtest:` engine grew to ~50 tags that addressed CSS
selectors; this one speaks the app's own concepts (action, table, flash,
session) and every tag and attribute below has an effect.

A file holds one or more `q:test` elements side by side; it needs no root
element and no namespace declarations — `q:` and `test:` are declared for it.
"""

import re
from pathlib import Path
from typing import Dict, Optional
from xml.etree import ElementTree as ET

from quantum.core.parser import QuantumParseError
from quantum.core.xml_lines import fromstring_with_lines

from .ast_node import TestCaseNode, TestFileNode, TestStepNode

Q_NS = 'https://quantum.lang/ns'
TEST_NS = 'https://quantum.lang/test'

STEP_KINDS = ('given', 'as', 'visit', 'submit', 'expect')

# test:expect — each attribute is one assertion (all must hold) or a detail of one.
EXPECT_ASSERTIONS = ('redirect', 'flash', 'status', 'text', 'no-text', 'error',
                     'table', 'var', 'history', 'queries')
# detail -> the assertions it belongs to
EXPECT_DETAILS = {
    'message': ('error',),
    'value': ('var',),
    'count': ('table', 'history'),
    'where': ('table', 'history'),
    'datasource': ('table', 'history'),
    'action': ('history',),
    'op': ('history',),
    'user': ('history',),
}
HISTORY_OPS = ('insert', 'update', 'delete')
QUERIES = re.compile(r'\s*(at most\s+)?(\d+)\s*$')


class TestParseError(QuantumParseError):
    """A .test.q file that is not valid; carries `file` and `line` (DEV-2)."""
    __test__ = False                     # not a pytest class

    def __init__(self, message: str, file: Optional[str] = None, line: Optional[int] = None,
                 source: Optional[str] = None):
        where = ''
        if line:
            snippet = ''
            if source:
                lines = source.splitlines()
                snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ''
            where = f'\n  at line {line}: {snippet}' if snippet else f' (line {line})'
        super().__init__(f'{message}{where}')
        self.file = file
        self.line = line


def is_test_file(path) -> bool:
    """A `*.test.q` file: a test suite, never a page (ROUTE-4)."""
    return str(path).replace('\\', '/').endswith('.test.q')


def _local(tag: str):
    """(prefix, local name) of an element tag; prefix is 'q', 'test' or the raw URI."""
    if tag.startswith('{'):
        uri, local = tag[1:].split('}', 1)
        prefix = {Q_NS: 'q', TEST_NS: 'test'}.get(uri, uri)
        return prefix, local
    return '', tag


def _wrap(source: str) -> str:
    """Several q:test side by side become one document; line numbers are kept."""
    body = re.sub(r'^\s*<\?xml[^>]*\?>', lambda m: '\n' * m.group(0).count('\n'), source)
    return (f'<quantum-tests xmlns:q="{Q_NS}" xmlns:test="{TEST_NS}">'
            f'{body}</quantum-tests>')


def parse_test_source(source: str, path: str = '<test>') -> TestFileNode:
    """The tests of a .test.q file's text."""
    try:
        root = fromstring_with_lines(_wrap(source))
    except ET.ParseError as exc:
        line = getattr(exc, 'position', (None, None))[0]
        raise TestParseError(f'{path}: XML parse error: {exc}', path, line, source) from None

    def fail(message: str, element) -> TestParseError:
        return TestParseError(f'{path}: {message}', path, getattr(element, 'sourceline', None), source)

    if (root.text or '').strip():
        raise fail('text outside a <q:test>: a test file holds only <q:test> elements', root)
    result = TestFileNode(path=path)
    names = set()
    for element in root:
        prefix, local = _local(element.tag)
        if (prefix, local) != ('q', 'test'):
            raise fail(f'<{prefix}:{local}> at the top of a test file: only <q:test> is allowed here', element)
        if (element.tail or '').strip():
            raise fail('text outside a <q:test>: a test file holds only <q:test> elements', element)
        test = _parse_test(element, fail)
        if test.name in names:
            raise fail(f'two tests are called "{test.name}": each q:test needs its own name', element)
        names.add(test.name)
        result.tests.append(test)
    if not result.tests:
        raise TestParseError(f'{path}: no <q:test> in this file', path, None, source)
    return result


def parse_test_file(path) -> TestFileNode:
    path = Path(path)
    return parse_test_source(path.read_text(encoding='utf-8'), str(path))


def _parse_test(element, fail) -> TestCaseNode:
    attrs = dict(element.attrib)
    unknown = sorted(set(attrs) - {'name', 'page'})
    if unknown:
        raise fail(f'<q:test> has no attribute {", ".join(unknown)} (it takes name and page)', element)
    name = (attrs.get('name') or '').strip()
    if not name:
        raise fail('<q:test> needs a name="…"', element)
    page = attrs.get('page') or '/'
    if not page.startswith('/'):
        raise fail(f'<q:test page="{page}">: a page is a path that starts with "/"', element)
    if (element.text or '').strip():
        raise fail(f'text inside <q:test name="{name}">: a test holds only test: steps', element)
    test = TestCaseNode(name=name, page=page, line=getattr(element, 'sourceline', None))
    for child in element:
        prefix, local = _local(child.tag)
        if prefix != 'test' or local not in STEP_KINDS:
            shown = f'{prefix}:{local}' if prefix else local
            raise fail(f'<{shown}> is not a test step. The steps are: '
                       + ', '.join(f'test:{k}' for k in STEP_KINDS), child)
        if len(child) or (child.text or '').strip():
            raise fail(f'<test:{local}> takes attributes only, no content', child)
        if (child.tail or '').strip():
            raise fail(f'text inside <q:test name="{name}">: a test holds only test: steps', child)
        step = TestStepNode(kind=local, attrs={_attr_name(k): v for k, v in child.attrib.items()},
                            line=getattr(child, 'sourceline', None))
        _check_step(step, child, fail)
        test.steps.append(step)
    if not test.steps:
        raise fail(f'<q:test name="{name}"> has no steps', element)
    return test


def _attr_name(key: str) -> str:
    return key.split('}', 1)[1] if key.startswith('{') else key


def _check_step(step: TestStepNode, element, fail) -> None:
    a = step.attrs
    kind = step.kind
    if kind == 'given':
        if not a.get('table'):
            raise fail('<test:given> needs table="…" (and the row\'s columns as attributes)', element)
    elif kind == 'as':
        if not a:
            raise fail('<test:as> needs user="…", role="…" or session values', element)
    elif kind == 'visit':
        path = a.get('path')
        if path is not None and not path.startswith('/'):
            raise fail(f'<test:visit path="{path}">: a path starts with "/"', element)
    elif kind == 'submit':
        if not a.get('action'):
            raise fail('<test:submit> needs action="…" (the q:action to post) and the fields as attributes',
                       element)
    elif kind == 'expect':
        _check_expect(a, element, fail)


def _check_expect(a: Dict[str, str], element, fail) -> None:
    known = set(EXPECT_ASSERTIONS) | set(EXPECT_DETAILS)
    unknown = sorted(set(a) - known)
    if unknown:
        raise fail(f'<test:expect> has no assertion {", ".join(unknown)}. The assertions are: '
                   + ', '.join(EXPECT_ASSERTIONS) + ' (with ' + ', '.join(EXPECT_DETAILS) + ')', element)
    for detail, owners in EXPECT_DETAILS.items():
        if detail in a and not any(o in a for o in owners):
            raise fail(f'<test:expect {detail}="…"> belongs to ' + ' or '.join(owners)
                       + f': say which, e.g. {owners[0]}="…"', element)
    if not any(k in a for k in EXPECT_ASSERTIONS):
        raise fail('<test:expect> asserts nothing: give one of ' + ', '.join(EXPECT_ASSERTIONS), element)
    if 'table' in a and 'history' in a:
        raise fail('<test:expect> with both table and history: write one test:expect for each', element)
    if 'var' in a and 'value' not in a:
        raise fail(f'<test:expect var="{a["var"]}"> needs value="…"', element)
    if 'status' in a and not a['status'].strip().isdigit():
        raise fail(f'<test:expect status="{a["status"]}">: a status is a number, like 302', element)
    if 'count' in a and not a['count'].strip().isdigit():
        raise fail(f'<test:expect count="{a["count"]}">: a count is a number', element)
    if 'queries' in a and not QUERIES.match(a['queries']):
        raise fail(f'<test:expect queries="{a["queries"]}">: write a number or "at most N"', element)
    if 'op' in a and a['op'] not in HISTORY_OPS:
        raise fail(f'<test:expect op="{a["op"]}">: op is one of ' + ', '.join(HISTORY_OPS), element)
    if 'redirect' in a and not a['redirect'].startswith('/'):
        raise fail(f'<test:expect redirect="{a["redirect"]}">: a redirect is a path that starts with "/"',
                   element)
