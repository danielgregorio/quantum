"""Conformance: a value outside an attribute's list is a parse error with the line (SPEC PARSE-5).

Each of these used to parse and then fail when it ran — or not fail at all: an
unknown authType sent the request with no credentials, an unknown q:param type
on a form field was plain text, an unknown validate= refused every value.
"""

import pytest

from quantum.core.parser import QuantumParser

NS = 'xmlns:q="https://quantum.lang/ns"'


def parse(body):
    return QuantumParser().parse(f'<q:component name="c" {NS}>\n{body}\n</q:component>')


@pytest.mark.parametrize('body,message', [
    ('<q:set name="a" value="1" operation="json"/>',
     'operation="json" does not exist; operation is one of: assign, increment'),
    ('<q:set name="a" value="1" scope="scene"/>',
     'scope="scene" does not exist; scope is one of: local, function, component, session, application, request'),
    ('<q:set name="a" value="x" validate="cpff"/>',
     'validate="cpff" does not exist; validate is one of: email'),
    ('<q:loop type="object" var="x" items="{[1]}"><p>{x}</p></q:loop>',
     'type="object"> does not exist; type is one of: range, array, list, query'),
    ('<q:function name="f"><q:param name="p" type="numbr"/><q:return value="1"/></q:function>',
     'type="numbr" does not exist'),
    ('<q:action name="a" method="POST"><q:param name="p" type="text-area"/></q:action>',
     'type="text-area" does not exist'),
    ('<q:query name="u" datasource="db">SELECT 1<q:param name="p" value="1" type="number"/></q:query>',
     '<q:query> <q:param name="p"> type="number" does not exist; type is one of: string, integer, decimal'),
    ('<q:invoke name="u" url="http://x" method="FETCH"/>',
     'method="FETCH" does not exist; method is one of: GET, POST'),
    ('<q:invoke name="u" url="http://x" authType="token" authToken="t"/>',
     'authType="token" does not exist; authType is one of: bearer, apikey, basic'),
    ('<q:invoke name="u" url="http://x"><q:param name="p" value="1" type="numbr"/></q:invoke>',
     'type="numbr" does not exist'),
])
def test_a_value_outside_the_list_is_a_parse_error_with_the_line(body, message):
    # PARSE-5
    with pytest.raises(Exception) as error:
        parse(body)
    assert message in str(error.value)
    assert getattr(error.value, 'line', None) == 2 and 'at line 2:' in str(error.value)


@pytest.mark.parametrize('body', [
    '<q:set name="a" value="1" operation="increment" scope="session"/>',
    '<q:set name="a" value="x@y.z" validate="email"/>',
    '<q:set name="a" value="123" validate="^[0-9]+$"/>',
    '<q:loop type="list" var="x" items="a,b"><p>{x}</p></q:loop>',
    '<q:action name="a" method="POST"><q:param name="d" type="date"/><q:param name="n" type="number"/>'
    '<q:param name="f" type="file"/></q:action>',
    '<q:query name="u" datasource="db">SELECT 1<q:param name="p" value="1" type="datetime"/></q:query>',
    '<q:invoke name="u" url="http://x" method="patch" authType="basic"/>',
])
def test_the_values_in_the_lists_parse(body):
    # PARSE-5
    parse(body)


@pytest.mark.parametrize('alias,value,expected', [
    ('int', '7', 7), ('long', '7', 7), ('numeric', '2.5', 2.5), ('float', '2', 2.0),
    ('double', '2.5', 2.5), ('text', '{1 + 1}', '2'),
])
def test_the_q_param_type_names_convert_in_q_set_too(run_body, alias, value, expected):
    # ERR-1: they used to be accepted and to convert nothing (type="int" stored the text "7")
    result = run_body(f'<q:set name="v" value="{value}" type="{alias}"/><q:return value="{{v}}"/>')
    assert result == expected and type(result) is type(expected)


@pytest.mark.parametrize('type_', ['date', 'datetime', 'struct', 'null'])
def test_another_q_set_type_is_a_parse_error(type_):
    # ERR-1, PARSE-5
    with pytest.raises(Exception) as error:
        parse(f'<q:set name="v" value="1" type="{type_}"/>')
    assert f'type="{type_}" does not exist' in str(error.value) and 'at line 2:' in str(error.value)
