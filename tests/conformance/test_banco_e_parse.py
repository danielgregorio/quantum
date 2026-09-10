"""Conformidade: SPEC.md seções 0 (Parse) e 5a (Banco de dados)."""

import sqlite3

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError


def parse(corpo):
    return QuantumParser().parse(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>')


class TestTagsDesconhecidas:
    @pytest.mark.parametrize('corpo,sugestao', [
        ('<q:sett name="x" value="1"/>', '<q:set>'),
        ('<q:loop type="range" var="i" from="1" to="2"><q:retrun value="{i}"/></q:loop>', '<q:return>'),
        ('<div><q:lopp type="range" var="i" from="1" to="2"/></div>', '<q:loop>'),
    ])
    def test_erro_com_sugestao_em_qualquer_corpo(self, corpo, sugestao):
        # PARSE-1 (antes: descartada em silencio, o programa seguia sem ela)
        with pytest.raises(QuantumParseError, match=f'is not a Quantum tag. Did you mean {sugestao}'):
            parse(corpo)

    @pytest.mark.parametrize('tag', ['q:try', 'q:storedproc', 'q:fetch', 'q:include', 'q:throw'])
    def test_tags_que_a_doc_prometia_e_nunca_existiram(self, tag):
        # PARSE-1
        with pytest.raises(QuantumParseError, match='is not a Quantum tag'):
            parse(f'<{tag} name="x"/>')

    def test_outros_namespaces_e_html_nao_sao_afetados(self):
        # PARSE-1
        parse('<section><custom-element>x</custom-element></section>')


@pytest.fixture
def banco(tmp_path):
    caminho = tmp_path / 'app.db'
    conexao = sqlite3.connect(caminho)
    conexao.executescript(
        "create table users (id integer primary key, name text, status text);"
        "insert into users (name, status) values ('Ana','active'),('Bia','active'),('Caio','inactive');"
        "create table products (id integer primary key, stock integer);"
        "insert into products (stock) values (10);")
    conexao.commit()
    conexao.close()
    return caminho


@pytest.fixture
def rodar(banco, tmp_path):
    import contextlib
    import io
    from quantum.runtime.component import ComponentRuntime

    def executar(corpo):
        arquivo = tmp_path / 'q.q'
        arquivo.write_text(f'<q:component name="Q" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
                           encoding='utf-8')
        config = {'datasources': {'db': {'driver': 'sqlite', 'database': str(banco)}}}
        with contextlib.redirect_stdout(io.StringIO()):
            return ComponentRuntime(config=config).execute_component(
                QuantumParser().parse_file(str(arquivo)), {})
    return executar


class TestConsultas:
    def test_parametros_e_resultado(self, rodar):
        # DB-1
        r = rodar('<q:query name="u" datasource="db">SELECT name FROM users WHERE status = :s ORDER BY id'
                  '<q:param name="s" value="active" type="string"/></q:query>'
                  '<q:return value="{u_result}"/>')
        assert r['data'] == [{'name': 'Ana'}, {'name': 'Bia'}]
        assert r['success'] is True and r['recordCount'] == 2 and r['columnList'] == ['name']

    def test_uma_linha_expoe_os_campos(self, rodar):
        # DB-1
        assert rodar('<q:query name="u" datasource="db">SELECT name FROM users WHERE id = 1</q:query>'
                     '<q:return value="{u.name}"/>') == 'Ana'

    def test_escrita_informa_linhas_afetadas(self, rodar):
        # DB-1
        assert rodar('<q:query name="up" datasource="db">UPDATE users SET status = :s WHERE status = :v'
                     '<q:param name="s" value="x" type="string"/><q:param name="v" value="active" type="string"/>'
                     '</q:query><q:return value="{up_result.affectedRows}"/>') == 2

    def test_paginacao(self, rodar):
        # DB-2
        r = rodar('<q:query name="p" datasource="db" paginate="true" page="2" page_size="2">'
                  'SELECT name FROM users ORDER BY id</q:query><q:return value="{p_result.pagination}"/>')
        assert (r['totalRecords'], r['totalPages'], r['currentPage'], r['hasNextPage'], r['hasPreviousPage']) == \
            (3, 2, 2, False, True)

    def test_query_de_query(self, rodar):
        # DB-3
        assert rodar('<q:query name="todos" datasource="db">SELECT name, status FROM users</q:query>'
                     '<q:query name="ativos" source="todos">SELECT name FROM todos WHERE status = \'active\' '
                     'ORDER BY name</q:query><q:return value="{ativos}"/>') == [{'name': 'Ana'}, {'name': 'Bia'}]

    def test_transacao_herda_datasource_e_desfaz_na_falha(self, rodar):
        # DB-4 (antes: query sem datasource dentro da transacao nao parseava)
        with pytest.raises(Exception, match='rolled back'):
            rodar('<q:transaction datasource="db">'
                  '<q:query name="a">UPDATE products SET stock = 999 WHERE id = 1</q:query>'
                  '<q:query name="b">INSERT INTO nao_existe VALUES (1)</q:query></q:transaction>')
        assert rodar('<q:query name="s" datasource="db">SELECT stock FROM products</q:query>'
                     '<q:return value="{s.stock}"/>') == 10

    @pytest.mark.parametrize('atributo', ['cache="true"', 'ttl="60"', 'reactive="true"', 'interval="5"',
                                          'timeout="3"', 'maxrows="1"', 'batch="true"'])
    def test_atributos_que_nunca_funcionaram(self, atributo):
        # DB-5
        with pytest.raises(QuantumParseError, match='is not supported'):
            parse(f'<q:query name="x" datasource="db" {atributo}>SELECT 1</q:query>')
