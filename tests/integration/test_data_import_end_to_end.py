"""
q:data de ponta a ponta: arquivo real, .q real, o valor que chega à página.

Três defeitos passavam pela suíte e pelo FEATURE_STATUS, porque os exemplos
TERMINAVAM sem erro — só não faziam o que diziam:

1. q:compute nunca criava o campo. O executor montava a operação com
   op['type'] = 'compute' e depois sobrescrevia a mesma chave com o tipo do
   resultado ('decimal'); a operação deixava de ser reconhecida e era pulada.
2. q:field lia o atributo `path`, mas todo exemplo e a referência usam
   `xpath`. `xpath="@id"` virava o caminho "id" (atributo vinha None) e o
   `type` era descartado (números vinham como texto).
3. O import de XML devolvia success=False mesmo dando certo, então nenhuma
   transformação rodava sobre XML. E `titulo/text()` quebrava no ElementTree,
   que não entende text() — só funcionava porque o bug 2 mandava "titulo".

Achados escrevendo docs/guide/data-import.md e rodando cada exemplo.
"""

import io
import contextlib
import pathlib

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    dados = tmp_path / 'data'
    dados.mkdir()
    (dados / 'clientes.csv').write_text(
        'id,nome,idade,ativo\n1,Ana,28,true\n2,Bruno,35,true\n3,Carla,42,false\n',
        encoding='utf-8')
    (dados / 'produtos.json').write_text(
        '[{"id": 1, "nome": "Caneca", "preco": 30.0},'
        ' {"id": 2, "nome": "Camiseta", "preco": 80.0},'
        ' {"id": 3, "nome": "Adesivo", "preco": 5.0}]', encoding='utf-8')
    (dados / 'livros.xml').write_text(
        '<livros><livro id="1"><titulo>Dom Casmurro</titulo><ano>1899</ano>'
        '<editora sigla="GAR"/></livro>'
        '<livro id="2"><titulo>Vidas Secas</titulo><ano>1938</ano>'
        '<editora sigla="JO"/></livro></livros>', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    return tmp_path


def executar(pasta, corpo):
    arquivo = pasta / 'c.q'
    arquivo.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
        encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime().execute_component(
            QuantumParser().parse_file(str(arquivo)), {})


XML_CAMPOS = ('<q:field name="id" xpath="@id" type="integer"/>'
              '<q:field name="titulo" xpath="titulo/text()" type="string"/>'
              '<q:field name="ano" xpath="ano/text()" type="integer"/>')


class TestCompute:
    def test_o_campo_calculado_existe(self, pasta):
        produtos = executar(pasta,
            '<q:data name="p" source="data/produtos.json" type="json"><q:transform>'
            '<q:compute field="comDesconto" expression="{preco} * 0.9" type="decimal"/>'
            '</q:transform></q:data><q:return value="{p}"/>')
        assert [p['comDesconto'] for p in produtos] == pytest.approx([27.0, 72.0, 4.5])


class TestXml:
    def test_atributo_e_tipos(self, pasta):
        livros = executar(pasta,
            f'<q:data name="l" source="data/livros.xml" type="xml" xpath=".//livro">'
            f'{XML_CAMPOS}</q:data><q:return value="{{l}}"/>')
        assert livros == [
            {'id': 1, 'titulo': 'Dom Casmurro', 'ano': 1899},
            {'id': 2, 'titulo': 'Vidas Secas', 'ano': 1938},
        ]

    def test_atributo_de_um_filho(self, pasta):
        livros = executar(pasta,
            '<q:data name="l" source="data/livros.xml" type="xml" xpath=".//livro">'
            '<q:field name="editora" xpath="editora/@sigla"/></q:data>'
            '<q:return value="{l}"/>')
        assert [l['editora'] for l in livros] == ['GAR', 'JO']

    def test_transformacao_roda_sobre_xml(self, pasta):
        livros = executar(pasta,
            f'<q:data name="l" source="data/livros.xml" type="xml" xpath=".//livro">'
            f'{XML_CAMPOS}<q:transform><q:filter condition="ano > 1900"/></q:transform>'
            f'</q:data><q:return value="{{l}}"/>')
        assert [l['titulo'] for l in livros] == ['Vidas Secas']


class TestCsvEFiltro:
    def test_filtro_com_a_mesma_sintaxe_do_q_if(self, pasta):
        colunas = ('<q:column name="id" type="integer"/><q:column name="nome"/>'
                   '<q:column name="idade" type="integer"/><q:column name="ativo" type="boolean"/>')
        ativos = executar(pasta,
            f'<q:data name="c" source="data/clientes.csv" type="csv">{colunas}'
            f'<q:transform><q:filter condition="ativo and idade > 30"/></q:transform>'
            f'</q:data><q:return value="{{c}}"/>')
        assert [c['nome'] for c in ativos] == ['Bruno']


class TestFalha:
    def test_arquivo_ausente_fica_no_resultado(self, pasta):
        # A falha não interrompe a página: o motivo fica em {nome_result}.
        # (Se isso deve virar erro é decisão da spec — G16.)
        mensagem = executar(pasta,
            '<q:data name="x" source="data/naoexiste.csv" type="csv"/>'
            '<q:if condition="x_result.success"><q:return value="ok"/></q:if>'
            '<q:return value="{x_result.error.message}"/>')
        assert 'naoexiste.csv' in str(mensagem)
