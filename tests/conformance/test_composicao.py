"""Conformidade: SPEC.md seção 3b (Composição de componentes)."""

import re

import pytest

LAYOUT = ('<q:component name="Moldura" xmlns:q="https://quantum.lang/ns">'
          '<q:param name="titulo" required="true"/><q:param name="ativo" default=""/>'
          '<html><body><nav class="{\'sel\' if ativo == \'a\' else \'\'}">NAV</nav>'
          '<h1>{titulo}</h1><main><q:slot/></main></body></html></q:component>')


def texto(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


@pytest.fixture
def site(servidor, tmp_path):
    def montar(**paginas):
        (tmp_path / "components" / "partes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "components" / "partes" / "Moldura.q").write_text(LAYOUT, encoding="utf-8")
        return servidor(**paginas)
    return montar


def pagina(nome, corpo):
    return f'<q:component name="{nome}" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>'


class TestComposicao:
    def test_from_e_paths_components_da_config(self, site):
        # COMP-1 (antes: procurava ./components do diretorio do processo e ignorava from=)
        c = site(p=pagina("p", '<q:import component="Moldura" from="partes"/><Moldura titulo="Oi">x</Moldura>'))
        r = c.get("/p")
        assert r.status_code == 200 and "Oi" in texto(r.get_data(as_text=True))

    def test_componente_inexistente_e_erro(self, site):
        # COMP-1 (antes: comentario HTML e 200)
        c = site(p=pagina("p", '<q:import component="Fantasma" from="partes"/><Fantasma/>'))
        r = c.get("/p")
        assert r.status_code == 500

    def test_prop_e_expressao_e_prop_obrigatoria(self, site):
        # COMP-2
        c = site(p=pagina("p", '<q:import component="Moldura" from="partes"/><q:set name="n" value="2" type="number"/>'
                               '<Moldura titulo="Total {n + 1}" ativo="a">x</Moldura>'),
                 q=pagina("q", '<q:import component="Moldura" from="partes"/><Moldura>x</Moldura>'))
        html = c.get("/p").get_data(as_text=True)
        assert "Total 3" in texto(html) and 'class="sel"' in html
        assert c.get("/q").status_code == 500

    def test_slot_ve_as_variaveis_da_pagina(self, site):
        # COMP-3 (antes: o slot rodava no escopo do filho e o loop nao via os dados)
        c = site(p=pagina("p", '<q:import component="Moldura" from="partes"/>'
                               '<q:set name="itens" type="array" value=\'["um", "dois"]\'/>'
                               '<Moldura titulo="Lista"><ul><q:loop items="{itens}" var="i"><li>{i}</li></q:loop></ul>'
                               '<q:if condition="len(itens) == 2"><p>DOIS ITENS</p></q:if></Moldura>'))
        conteudo = texto(c.get("/p").get_data(as_text=True))
        assert "um dois" in conteudo and "DOIS ITENS" in conteudo

    def test_conteudo_de_uma_requisicao_nao_vaza_para_a_seguinte(self, site):
        # COMP-3 (antes: o enxerto mutava a AST do layout no cache do resolver)
        c = site(a=pagina("a", '<q:import component="Moldura" from="partes"/><Moldura titulo="A">SEGREDO DA PAGINA A</Moldura>'),
                 b=pagina("b", '<q:import component="Moldura" from="partes"/><Moldura titulo="B">conteudo da b</Moldura>'))
        assert "SEGREDO DA PAGINA A" in c.get("/a").get_data(as_text=True)
        segunda = c.get("/b").get_data(as_text=True)
        assert "SEGREDO DA PAGINA A" not in segunda and "conteudo da b" in segunda

    def test_filho_usa_a_configuracao_da_pagina(self, site, tmp_path):
        # COMP-4 (antes: ComponentRuntime() sem config — q:query no filho nao tinha datasource)
        import sqlite3
        banco = tmp_path / "c.db"
        sqlite3.connect(banco).executescript("create table t (v text); insert into t values ('DO BANCO');")
        (tmp_path / "components" / "partes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "components" / "partes" / "Linha.q").write_text(
            pagina("Linha", '<q:query name="r" datasource="db">SELECT v FROM t</q:query><span>{r.v}</span>'),
            encoding="utf-8")
        c = site(datasources_yaml=f"datasources:\n  db:\n    driver: sqlite\n    database: {banco.as_posix()}\n",
                 p=pagina("p", '<q:import component="Linha" from="partes"/><div><Linha/></div>'))
        r = c.get("/p")
        assert r.status_code == 200 and "DO BANCO" in r.get_data(as_text=True)
