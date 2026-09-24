"""Conformance: SPEC.md sections 6a (Types in q:set) and 9 (quantum run)."""

import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


class TestTypeConversion:
    @pytest.mark.parametrize('value,type_,expected', [
        ('{5 / 2}', 'number', 2.5),        # was 2: int() truncated
        ('{6 / 2}', 'integer', 3),
        ('42', 'integer', 42),
        ('2.5', 'decimal', 2.5),
        ('yes', 'boolean', True),
        ('0', 'boolean', False),
        ('', 'boolean', False),
        ('[1, 2]', 'array', [1, 2]),
        ('{"a": 1}', 'object', {'a': 1}),
    ])
    def test_values_that_convert(self, run_body, value, type_, expected):
        # ERR-1
        r = run_body(f"<q:set name=\"x\" value='{value}' type=\"{type_}\"/><q:return value=\"{{x}}\"/>")
        assert r == expected and type(r) is type(expected)

    def test_an_integer_with_a_fraction_is_an_error(self, run_body):
        # ERR-1 (was 3, silently)
        with pytest.raises(Exception, match='3.5 is not a whole number.*round'):
            run_body('<q:set name="x" value="{7 / 2}" type="integer"/>')

    def test_text_with_expressions_shows_how_to_combine(self, run_body):
        # ERR-1 (was G3: "could not convert string to float: '10 + 20'")
        with pytest.raises(Exception) as error:
            run_body('<q:set name="a" value="10"/><q:set name="b" value="20"/>'
                     '<q:set name="r" value="{a} + {b}" type="number"/>')
        assert 'value="{a + b}"' in str(error.value)
        assert 'float' not in str(error.value)

    def test_json_with_single_quotes_says_to_use_double_quotes(self, run_body):
        # ERR-1 (was G13: "Expecting property name enclosed in double quotes")
        with pytest.raises(Exception) as error:
            run_body('''<q:set name="a" type="array" value="[{'x': 1}]"/>''')
        assert 'double quotes' in str(error.value)
        assert 'Expecting property name' not in str(error.value)

    def test_an_unknown_boolean_is_an_error(self, run_body):
        # ERR-1 (was False, silently)
        with pytest.raises(Exception, match="'flase' is not a boolean"):
            run_body('<q:set name="b" value="flase" type="boolean"/>')


class TestDefault:
    @pytest.mark.parametrize('value,expected', [('{session.clicks}', 0), ('{empty}', 0), ('7', 7)])
    def test_default_when_value_resolves_to_nothing(self, run_body, value, expected):
        # SET-1 (before: value="{session.x}" default="0" stored '')
        assert run_body('<q:set name="empty" value=""/>'
                        f'<q:set name="c" value="{value}" default="0" type="number"/>'
                        '<q:return value="{c}"/>') == expected

    @pytest.mark.parametrize('attribute', ['persist="local"', 'persistKey="k"', 'persistTtl="60"'])
    def test_browser_persistence_is_gone(self, run_body, attribute):
        # SET-2 (before: accepted on a page, with no effect at all)
        with pytest.raises(Exception, match=r'persist\w*= was removed in Quantum 0.16: .* session\.theme'):
            run_body(f'<q:set name="theme" value="dark" {attribute}/>')

    def test_q_persist_is_gone(self):
        # SET-2
        from quantum.core.parser import QuantumParser
        with pytest.raises(Exception, match=r'<q:persist> was removed in Quantum 0.16 \(SET-2\)'):
            QuantumParser().parse('<q:component name="c" xmlns:q="https://quantum.lang/ns">'
                                  '<q:persist scope="local"><q:var name="x"/></q:persist></q:component>')

    def test_adding_text_and_a_number_explains(self, run_body):
        # EXPR-7 (before: "can only concatenate str (not \"int\") to str")
        with pytest.raises(Exception, match=r"'\+' needs two numbers, two texts or two lists"):
            run_body('<q:set name="t" value="abc"/><q:return value="{t + 1}"/>')


def run_file(tmp_path, source):
    path = tmp_path / 'app.q'
    path.write_text(source, encoding='utf-8')
    return subprocess.run(
        [sys.executable, '-m', 'quantum.cli.runner', 'run', str(path)],
        capture_output=True, text=True, cwd=tmp_path, timeout=120,
        env=dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8'))


class TestQuantumRun:
    def test_a_handled_failure_shows_no_traceback(self, tmp_path):
        # RUN-2 (was G5)
        result = run_file(tmp_path,
                          '<q:component name="I" xmlns:q="https://quantum.lang/ns">'
                          '<q:function name="add"><q:param name="a" type="number" required="true"/>'
                          '<q:set name="r" value="{a} + 1" type="number"/><q:return value="{r}"/>'
                          '</q:function>'
                          '<q:invoke name="x" function="add" onerror="continue"><q:param name="a" default="1"/></q:invoke>'
                          '<q:return value="{x_result.error.message}"/></q:component>')
        output = result.stdout + result.stderr
        assert 'Traceback (most recent call last)' not in output
        assert 'value="{a + 1}"' in output
        assert '[DEBUG]' not in output          # RUN-1: no internal log in the output

    def test_it_creates_no_files_the_program_does_not_use(self, tmp_path):
        # RUN-1 (before: ./logs/ and ./quantum_jobs.db on every run)
        result = run_file(tmp_path, '<q:component name="Hi" xmlns:q="https://quantum.lang/ns">'
                                    '<q:return value="hi"/></q:component>')
        assert result.returncode == 0 and 'hi' in result.stdout
        assert sorted(p.name for p in tmp_path.iterdir()) == ['app.q']


class TestOneInstancePerService:
    def test_the_runtime_and_the_container_share(self, tmp_path):
        # RUN-1: q:job (runtime.job_executor) and q:schedule (services.job_executor)
        # ran on different JobExecutors. (A job database of its own: the default
        # one is ./quantum_jobs.db, and this test left it in the repository.)
        from quantum.runtime.component import ComponentRuntime
        rt = ComponentRuntime(config={'job_db_path': str(tmp_path / 'jobs.db')})
        assert rt.job_executor is rt.services.job_executor
        assert rt.llm_service is rt.services.llm
        assert rt.database_service is rt.services.database


# ------------------------------------------------------------------ SET-3: operations and scope

@pytest.mark.parametrize('body,expected', [
    ('<q:set name="c" value="1" type="number"/><q:set name="c" operation="increment" step="5"/>', 6),
    ('<q:set name="c" operation="increment"/>', 1),
    ('<q:set name="c" operation="decrement"/>', -1),
    ('<q:set name="c" value="10" type="number"/><q:set name="c" operation="add" value="5"/>', 15),
    ('<q:set name="c" value="10" type="number"/><q:set name="c" operation="multiply" value="3"/>', 30),
    ('<q:set name="c" operation="append" value="a"/><q:set name="c" operation="append" value="b"/>'
     '<q:set name="c" operation="prepend" value="z"/>', ['z', 'a', 'b']),
    ('<q:set name="c" value=\'["a", "b", "a"]\' type="array"/><q:set name="c" operation="remove" value="a"/>', ['b', 'a']),
    ('<q:set name="c" value=\'["a", "b", "c"]\' type="array"/><q:set name="c" operation="removeAt" index="1"/>', ['a', 'c']),
    ('<q:set name="c" value="[3, 1, 3, 2]" type="array"/><q:set name="c" operation="unique"/>'
     '<q:set name="c" operation="sort"/><q:set name="c" operation="reverse"/>', [3, 2, 1]),
    ('<q:set name="c" value="[1]" type="array"/><q:set name="c" operation="clear"/>', []),
    ('<q:set name="c" value=\'{"a": 1}\' type="object"/><q:set name="c" operation="merge" value=\'{"b": 2}\'/>',
     {'a': 1, 'b': 2}),
    ('<q:set name="c" value=\'{"a": 1}\' type="object"/><q:set name="c" operation="setProperty" key="b" value="2"/>'
     '<q:set name="c" operation="deleteProperty" key="a"/>', {'b': '2'}),
    ('<q:set name="o" value=\'{"a": 1}\' type="object"/><q:set name="c" operation="clone" source="o"/>'
     '<q:set name="c" operation="setProperty" key="b" value="2"/><q:set name="c" value="{[o, c]}" type="array"/>',
     [{'a': 1}, {'a': 1, 'b': '2'}]),
    ('<q:set name="c" value="  Ab  "/><q:set name="c" operation="trim"/><q:set name="c" operation="uppercase"/>', 'AB'),
    ('<q:set name="c" value="Ab"/><q:set name="c" operation="lowercase"/>', 'ab'),
    ('<q:set name="x" value="7"/><q:set name="c" operation="format" value="[{x}]"/>', '[7]'),
])
def test_operations(run_body, body, expected):
    # SET-3
    assert run_body(body + '<q:return value="{c}"/>') == expected


@pytest.mark.parametrize('body,message', [
    ('<q:set name="c" value="abc"/><q:set name="c" operation="add" value="1"/>', "Set execution error for 'c'"),
    ('<q:set name="c" value="1" type="number"/><q:set name="c" operation="append" value="1"/>', 'non-array'),
    ('<q:set name="c" value="x" operation="explode"/>', 'operation="explode" does not exist'),   # PARSE-5
    ('<q:set name="c" value="1" scope="galaxy"/>', 'scope="galaxy" does not exist'),            # PARSE-5
])
def test_an_operation_on_the_wrong_kind_or_unknown_is_an_error(run_body, body, message):
    # SET-3
    with pytest.raises(Exception, match=message):
        run_body(body + '<q:return value="{c}"/>')


@pytest.mark.parametrize('scope,read', [('component', 'c'), ('session', 'session.c'),
                                        ('application', 'application.c'), ('request', 'request.c')])
def test_the_scopes(run_body, scope, read):
    # SET-3
    assert run_body(f'<q:set name="c" value="1" scope="{scope}"/><q:return value="{{{read}}}"/>') == '1'


# ------------------------------------------------------------------ SET-4: the value is checked

@pytest.mark.parametrize('attributes,message', [
    ('value="" required="true"', 'cannot be empty'),
    ('value="{None}" nullable="false"', 'cannot be null'),
    ('value="nope" validate="email"', 'Invalid email'),
    ('value="12345" validate="phone"', 'Invalid phone'),
    ('value="111.111.111-11" validate="cpf"', 'Invalid CPF'),
    ('value="abc" pattern="^[0-9]+$"', 'does not match pattern'),
    ('value="50" type="number" range="1..10"', 'between 1 and 10'),
    ('value="x" enum="a,b"', 'one of: a, b'),
    ('value="50" type="number" max="10"', 'at most 10'),
    ('value="ab" minlength="3"', 'at least 3 characters'),
])
def test_a_value_that_does_not_pass_is_an_error(run_body, attributes, message):
    # SET-4
    with pytest.raises(Exception, match=rf"Set execution error for 'c'.*{message}"):
        run_body(f'<q:set name="c" {attributes}/><q:return value="{{c}}"/>')


@pytest.mark.parametrize('attributes', ['value="a@b.co" validate="email"', 'value="5" type="number" range="1..10"',
                                        'value="a" enum="a,b"', 'value="123" pattern="^[0-9]+$"'])
def test_a_value_that_passes_is_stored(run_body, attributes):
    # SET-4
    run_body(f'<q:set name="c" {attributes}/><q:return value="{{c}}"/>')


@pytest.mark.parametrize('rule,bad,good', [
    ('url', 'not a url', 'https://example.com/a'), ('phone', '12345', '(11) 91234-5678'),
    ('cep', '123', '01310-100'), ('cnpj', '1', '11.222.333/0001-81'),
    ('uuid', 'x', '123e4567-e89b-12d3-a456-426614174000'), ('creditcard', '12', '4111 1111 1111 1111'),
    ('ipv4', '1.2.3', '10.0.0.1'), ('ipv6', 'zz', '2001:0db8:0000:0000:0000:ff00:0042:8329'),
])
def test_each_named_validator(run_body, rule, bad, good):
    # SET-4
    assert run_body(f'<q:set name="c" value="{good}" validate="{rule}"/><q:return value="{{c}}"/>') == good
    with pytest.raises(Exception, match=r"Set execution error for 'c'"):
        run_body(f'<q:set name="c" value="{bad}" validate="{rule}"/><q:return value="{{c}}"/>')


class TestTheTypeOfAnUntypedSet:
    """SET-5: without type=, one expression keeps its type — like RET-2 and COMP-2."""

    def test_one_expression_keeps_its_type(self, run_body):
        # SET-5 (a list used to be stored as its text, and len() counted characters)
        assert run_body('<q:set name="l" value="{[1, 2]}"/><q:set name="n" value="{len(l)}"/>'
                        '<q:return value="{[l, n, n + 1]}"/>') == [[1, 2], 2, 3]

    def test_text_with_several_parts_stays_text(self, run_body):
        # SET-5
        assert run_body('<q:set name="n" value="{1 + 1}"/><q:set name="t" value="{n} items"/>'
                        '<q:set name="lit" value="007"/><q:return value="{[t, lit]}"/>') == ['2 items', '007']

    def test_a_declared_type_still_converts(self, run_body):
        # SET-5, ERR-1
        assert run_body('<q:set name="s" value="{[1, 2]}" type="string"/><q:return value="{s}"/>') == '[1, 2]'
