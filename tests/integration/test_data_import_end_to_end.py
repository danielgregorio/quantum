"""
q:data end to end: a real file, a real .q, the value that reaches the page.

Three defects got past the suite and FEATURE_STATUS, because the examples
FINISHED without an error — they just did not do what they said:

1. q:compute never created the field. The executor built the operation with
   op['type'] = 'compute' and then overwrote the same key with the result's
   type ('decimal'); the operation was no longer recognized and was skipped.
2. q:field read the `path` attribute, but every example and the reference use
   `xpath`. `xpath="@id"` became the path "id" (the attribute came as None)
   and the `type` was dropped (numbers came as text).
3. The XML import returned success=False even when it worked, so no
   transformation ran over XML. And `title/text()` broke in ElementTree,
   which does not understand text() — it only worked because bug 2 sent "title".

Found while writing docs/guide/data-import.md and running each example.
"""

import contextlib
import io

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


@pytest.fixture
def folder(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'customers.csv').write_text(
        'id,name,age,active\n1,Ana,28,true\n2,Bruno,35,true\n3,Carla,42,false\n',
        encoding='utf-8')
    (data / 'products.json').write_text(
        '[{"id": 1, "name": "Mug", "price": 30.0},'
        ' {"id": 2, "name": "T-shirt", "price": 80.0},'
        ' {"id": 3, "name": "Sticker", "price": 5.0}]', encoding='utf-8')
    (data / 'books.xml').write_text(
        '<books><book id="1"><title>Dom Casmurro</title><year>1899</year>'
        '<publisher code="GAR"/></book>'
        '<book id="2"><title>Vidas Secas</title><year>1938</year>'
        '<publisher code="JO"/></book></books>', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run_body(folder, body):
    path = folder / 'c.q'
    path.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
        encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime().execute_component(
            QuantumParser().parse_file(str(path)), {})


XML_FIELDS = ('<q:field name="id" xpath="@id" type="integer"/>'
              '<q:field name="title" xpath="title/text()" type="string"/>'
              '<q:field name="year" xpath="year/text()" type="integer"/>')


class TestCompute:
    def test_the_computed_field_exists(self, folder):
        products = run_body(folder,
            '<q:data name="p" source="data/products.json" type="json"><q:transform>'
            '<q:compute field="discounted" expression="{price} * 0.9" type="decimal"/>'
            '</q:transform></q:data><q:return value="{p}"/>')
        assert [p['discounted'] for p in products] == pytest.approx([27.0, 72.0, 4.5])


class TestXml:
    def test_attribute_and_types(self, folder):
        books = run_body(folder,
            f'<q:data name="l" source="data/books.xml" type="xml" xpath=".//book">'
            f'{XML_FIELDS}</q:data><q:return value="{{l}}"/>')
        assert books == [
            {'id': 1, 'title': 'Dom Casmurro', 'year': 1899},
            {'id': 2, 'title': 'Vidas Secas', 'year': 1938},
        ]

    def test_an_attribute_of_a_child(self, folder):
        books = run_body(folder,
            '<q:data name="l" source="data/books.xml" type="xml" xpath=".//book">'
            '<q:field name="publisher" xpath="publisher/@code"/></q:data>'
            '<q:return value="{l}"/>')
        assert [b['publisher'] for b in books] == ['GAR', 'JO']

    def test_a_transformation_runs_over_xml(self, folder):
        books = run_body(folder,
            f'<q:data name="l" source="data/books.xml" type="xml" xpath=".//book">'
            f'{XML_FIELDS}<q:transform><q:filter condition="year > 1900"/></q:transform>'
            f'</q:data><q:return value="{{l}}"/>')
        assert [b['title'] for b in books] == ['Vidas Secas']


class TestCsvAndFilter:
    def test_a_filter_with_the_same_syntax_as_q_if(self, folder):
        columns = ('<q:column name="id" type="integer"/><q:column name="name"/>'
                   '<q:column name="age" type="integer"/><q:column name="active" type="boolean"/>')
        active = run_body(folder,
            f'<q:data name="c" source="data/customers.csv" type="csv">{columns}'
            f'<q:transform><q:filter condition="active and age > 30"/></q:transform>'
            f'</q:data><q:return value="{{c}}"/>')
        assert [c['name'] for c in active] == ['Bruno']


class TestFailure:
    def test_a_missing_file_is_in_the_result(self, folder):
        # With onerror="continue" the failure does not stop the page: the reason
        # is in {name_result}. Without it, it is an error (DATA-4, decided from G16).
        message = run_body(folder,
            '<q:data name="x" source="data/missing.csv" type="csv" onerror="continue"/>'
            '<q:if condition="x_result.success"><q:return value="ok"/></q:if>'
            '<q:return value="{x_result.error.message}"/>')
        assert 'missing.csv' in str(message)
