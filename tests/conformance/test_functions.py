"""Conformance: SPEC.md section 2b (Functions)."""

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError

DOUBLE = ('<q:function name="double"><q:param name="x" type="number" required="true"/>'
          '<q:return value="{x * 2}"/></q:function>')


class TestParameters:
    def test_an_argument_is_converted_to_the_type(self, run_body):
        # FN-1: "21" becomes a number before the body
        assert run_body(DOUBLE + '<q:set name="t" value="21"/><q:return value="{double(t)}"/>') == 42

    @pytest.mark.parametrize('call,reason', [
        ("reg('not-an-email', 30)", "must be a valid email"),
        ("reg('a@b.co', 150)", "must be at most 100"),
        ("reg('a@b.co', 'abc')", "must be a number"),
    ])
    def test_the_param_rules_always_apply(self, run_body, call, reason):
        # FN-1 (before: only with validate="true", and even then without email and min/max)
        with pytest.raises(Exception, match=reason):
            run_body('<q:function name="reg"><q:param name="email" type="email" required="true"/>'
                     '<q:param name="age" type="number" min="0" max="100"/>'
                     '<q:return value="ok"/></q:function>'
                     f'<q:return value="{{{call}}}"/>')

    def test_a_missing_required_argument_is_an_error(self, run_body):
        # FN-1
        with pytest.raises(Exception, match="Required parameter 'x' not provided"):
            run_body(DOUBLE + '<q:return value="{double()}"/>')

    def test_an_argument_by_name(self, run_body):
        # FN-1
        assert run_body('<q:function name="f"><q:param name="a"/><q:param name="b" default="B"/>'
                        '<q:return value="{a}-{b}"/></q:function>'
                        '<q:return value="{f(b=\'y\', a=\'x\')} {f(\'z\')}"/>') == 'x-y z-B'


class TestAttributesThatNeverWorked:
    def test_description_and_hint_are_accepted(self):
        # FN-2
        QuantumParser().parse('<q:component name="C" xmlns:q="https://quantum.lang/ns">'
                              '<q:function name="f" description="Doubles" hint="n * 2"><q:return value="1"/>'
                              '</q:function></q:component>')

    @pytest.mark.parametrize('attribute', [
        'memoize="true"', 'cache="60s"', 'async="true"', 'pure="true"', 'retry="3"',
        'access="private"', 'endpoint="/api/x"', 'scope="global"', 'validate="true"'])
    def test_they_are_parse_errors(self, attribute):
        # FN-2
        with pytest.raises(QuantumParseError, match='is not supported'):
            QuantumParser().parse(f'<q:component name="C" xmlns:q="https://quantum.lang/ns">'
                                  f'<q:function name="f" {attribute}><q:return value="1"/></q:function>'
                                  '</q:component>')


class TestFunctionInHtml:
    def test_a_call_in_the_page_content(self, serve_pages):
        # FN-3 (before: <p>{double(21)}</p> came out literal)
        client = serve_pages(p='<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                               + DOUBLE + '<p>R={double(21)}</p></q:component>')
        assert 'R=42' in client.get('/p').get_data(as_text=True)


class TestReturnType:
    @pytest.mark.parametrize('type_,value,expected', [
        ('number', '{2 + 3}', 5), ('integer', '7', 7), ('string', 'hi', 'hi'),
        ('boolean', 'true', True), ('any', 'x', 'x'),
    ])
    def test_the_return_is_converted_to_the_type(self, run_body, type_, value, expected):
        # FN-4 (before: returnType was accepted and never read)
        assert run_body(f'<q:function name="f" returnType="{type_}"><q:return value="{value}"/></q:function>'
                        '<q:return value="{f()}"/>') == expected

    def test_a_return_not_of_the_type_is_an_error(self, run_body):
        # FN-4
        with pytest.raises(Exception, match='declares returnType="number" but returned'):
            run_body('<q:function name="f" returnType="number"><q:return value="abc"/></q:function>'
                     '<q:return value="{f()}"/>')

    def test_a_type_that_does_not_exist_is_a_parse_error(self):
        # FN-4
        with pytest.raises(QuantumParseError, match='returnType="numbr" is not a type'):
            QuantumParser().parse('<q:component name="c" xmlns:q="https://quantum.lang/ns">'
                                  '<q:function name="f" returnType="numbr"><q:return value="1"/></q:function></q:component>')

    def test_void_requires_that_nothing_is_returned(self, run_body):
        # FN-4
        assert run_body('<q:function name="f" returnType="void"><q:set name="a" value="1"/></q:function>'
                        '<q:set name="r" value="{f()}"/><q:return value="done"/>') == 'done'
        with pytest.raises(Exception, match='declares returnType="void" but returned'):
            run_body('<q:function name="f" returnType="void"><q:return value="1"/></q:function>'
                     '<q:return value="{f()}"/>')


@pytest.mark.parametrize('param,call,message', [
    ('<q:param name="n" enum="a,b"/>', "f('c')", 'one of'),
    ('<q:param name="n" type="email"/>', "f('x')", 'valid email'),
])
def test_enum_and_email_on_a_param(run_body, param, call, message):
    # FN-1
    with pytest.raises(Exception, match=message):
        run_body(f'<q:function name="f">{param}<q:return value="{{n}}"/></q:function><q:return value="{{{call}}}"/>')
