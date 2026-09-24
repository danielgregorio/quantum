"""Conformance: SPEC.md section 2a (Conditionals)."""

import re

import pytest

SIBLING = ('<q:if condition="n % 2 == 0"><q:return value="{n} even"/></q:if>'
           '<q:elseif condition="n == 3"><q:return value="{n} three"/></q:elseif>'
           '<q:else><q:return value="{n} odd"/></q:else>')

NESTED = ('<q:if condition="n % 2 == 0"><q:return value="{n} even"/>'
          '<q:elseif condition="n == 3"><q:return value="{n} three"/></q:elseif>'
          '<q:else><q:return value="{n} odd"/></q:else></q:if>')


class TestSiblingAndNestedElse:
    @pytest.mark.parametrize('form', [SIBLING, NESTED], ids=['sibling', 'nested'])
    def test_in_the_component_body(self, run_body, form):
        # IF-1
        assert run_body('<q:set name="n" value="3" type="number"/>' + form) == '3 three'

    @pytest.mark.parametrize('form', [SIBLING, NESTED], ids=['sibling', 'nested'])
    def test_inside_a_loop(self, run_body, form):
        # IF-1 (before: the sibling else inside q:loop was dropped)
        assert run_body(f'<q:loop type="range" var="n" from="1" to="4">{form}</q:loop>') == \
            ['1 odd', '2 even', '3 three', '4 even']

    @pytest.mark.parametrize('form', [SIBLING, NESTED], ids=['sibling', 'nested'])
    def test_inside_a_function(self, run_body, form):
        # IF-1 (before: a q:function with a sibling elseif/else returned None)
        assert run_body(f'<q:function name="f"><q:param name="n" type="number"/>{form}</q:function>'
                        '<q:return value="{f(1)}|{f(2)}|{f(3)}"/>') == '1 odd|2 even|3 three'

    def test_inside_the_else_of_another_if(self, run_body):
        # IF-1
        assert run_body('<q:set name="a" value="false" type="boolean"/><q:set name="n" value="5" type="number"/>'
                        '<q:if condition="a"><q:return value="a"/></q:if>'
                        f'<q:else>{SIBLING}</q:else>') == '5 odd'

    def test_in_rendered_html(self, serve_pages):
        # IF-1 (before: the else's <li> never showed on the page)
        client = serve_pages(list=(
            '<q:component name="list" xmlns:q="https://quantum.lang/ns"><ul>'
            '<q:loop type="range" var="n" from="1" to="3">'
            '<q:if condition="n == 2"><li>two</li></q:if>'
            '<q:else><li>other {n}</li></q:else>'
            '</q:loop></ul></q:component>'))
        html = client.get('/list').get_data(as_text=True)
        assert re.findall(r'<li>\s*(.*?)\s*</li>', html) == ['other 1', 'two', 'other 3']

    @pytest.mark.parametrize('body', [
        '<q:else><q:return value="x"/></q:else>',
        '<q:loop type="range" var="n" from="1" to="2"><q:set name="x" value="1"/>'
        '<q:elseif condition="n"><q:return value="x"/></q:elseif></q:loop>',
    ], ids=['top', 'loop'])
    def test_an_else_without_an_if_before_it_is_an_error(self, run_body, body):
        # IF-1
        with pytest.raises(Exception, match='has no matching <q:if>'):
            run_body(body)


class TestNumericCondition:
    @pytest.mark.parametrize('condition,expected', [
        ('1', 'yes'), ('2', 'yes'), ('{1}', 'yes'), ('0', 'no'), ('{0}', 'no'),
    ])
    def test_a_literal_number_follows_the_value_truth(self, run_body, condition, expected):
        # IF-2 (before: "1", "2" and "{1}" were read as regex quantifiers and were false)
        assert run_body(f'<q:if condition="{condition}"><q:return value="yes"/></q:if>'
                        '<q:return value="no"/>') == expected

    def test_the_same_on_a_rendered_page(self, serve_pages):
        # IF-2: the same condition in markup
        client = serve_pages(p=(
            '<q:component name="p" xmlns:q="https://quantum.lang/ns">'
            '<q:if condition="1"><b>one</b></q:if><q:if condition="0"><b>zero</b></q:if>'
            '</q:component>'))
        assert re.findall(r'<b>(.*?)</b>', client.get('/p').get_data(as_text=True)) == ['one']


class TestTextInABranch:
    @pytest.mark.parametrize('x,expected', [('1', 'Tag 1'), ('', 'All')])
    def test_direct_text_in_a_branch_is_content(self, serve_pages, x, expected):
        # IF-3 (before: only child elements were read; <h2><q:if ...>Text</q:if></h2> came out empty)
        c = serve_pages(p=('<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                           '<q:set name="x" value="{query.x}" default=""/>'
                           '<h2><q:if condition="x">Tag {x}</q:if><q:else>All</q:else></h2></q:component>'))
        html = c.get(f'/p?x={x}').get_data(as_text=True)
        assert re.search(r'<h2>\s*' + expected + r'\s*</h2>', html)


class TestDanglingElse:
    INNER = '<q:if condition="{a}"><q:if condition="{b}"><p>ab</p></q:if>{branch}</q:if>'

    @pytest.mark.parametrize('branch', ['<q:else><p>x</p></q:else>',
                                        '<q:elseif condition="{c}"><p>x</p></q:elseif>'])
    def test_else_after_an_inner_if_is_an_error_with_its_line(self, branch):
        # IF-4 (before: it silently belonged to the outer if)
        from quantum.core.parser import QuantumParser, QuantumParseError
        source = ('<q:component name="c" xmlns:q="https://quantum.lang/ns">\n'
                  + self.INNER.replace('{branch}', '\n' + branch) + '</q:component>')
        with pytest.raises(QuantumParseError, match=r'ambiguous \(IF-4\)') as error:
            QuantumParser().parse(source)
        assert error.value.line == 3

    def test_the_two_unambiguous_forms_parse(self, run_body):
        # IF-4: the inner else inside the inner if; the outer else before the inner if
        inner = ('<q:set name="a" value="1"/><q:set name="b" value=""/>'
                 '<q:if condition="{a}"><q:if condition="{b}"><q:return value="ab"/>'
                 '<q:else><q:return value="a"/></q:else></q:if></q:if>')
        assert run_body(inner) == 'a'

    def test_a_sibling_else_after_a_nested_if_is_not_ambiguous(self, run_body):
        # IF-4 + IF-1: the else after the OUTER </q:if> is the outer one's
        page = ('<q:set name="a" value=""/>'
                '<q:if condition="{a}"><q:if condition="{a}"><q:return value="aa"/></q:if></q:if>'
                '<q:else><q:return value="not a"/></q:else>')
        assert run_body(page) == 'not a'
