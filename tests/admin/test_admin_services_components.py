"""admin.components.* e admin.tests.* (quantum_admin/services/components.py)."""

import json

import pytest

from quantum_admin.services import components as svc

COMPONENTE = ('<q:component name="Loja" xmlns:q="https://quantum.lang/ns">'
              '<q:action name="comprar" method="POST"><q:param name="item" required="true"/>'
              '<q:redirect url="/loja"/></q:action>'
              '<q:query name="itens" datasource="db">SELECT 1</q:query><p>x</p></q:component>\n')


@pytest.fixture(autouse=True)
def raiz(admin_isolado):
    (admin_isolado / "components" / "sub").mkdir(parents=True)
    (admin_isolado / "components" / "loja.q").write_text(COMPONENTE, encoding="utf-8")
    (admin_isolado / "components" / "sub" / "b.q").write_text("<q:component name='B'><q:set name='x' value='1'/></q:component>", encoding="utf-8")
    (admin_isolado / "tests").mkdir()
    (admin_isolado / "tests" / "test_ok.py").write_text("def test_um():\n    assert True\n\ndef test_dois():\n    assert 1\n", encoding="utf-8")
    (admin_isolado / "tests" / "test_falha.py").write_text("def test_quebra():\n    assert False\n", encoding="utf-8")
    (admin_isolado / "tests" / "ajuda.py").write_text("x = 1\n", encoding="utf-8")
    return admin_isolado


def test_lista_componentes():
    r = svc.list_components()
    assert [c["path"] for c in r["components"]] == ["loja.q", "sub/b.q"]
    loja = r["components"][0]
    assert loja["group"] == "root" and loja["feature_tags"] == ["action", "query", "redirect"]
    assert r["directories"] == 2


def test_detalhe_do_componente():
    d = svc.get_component("components/loja")
    assert (d["name"], d["type"], d["actions"], d["queries"], d["test_file"]) == \
        ("Loja", "Quantum", ["comprar"], ["itens"], None)


@pytest.mark.parametrize("caminho", ["../fora.q", "components/../../fora.q"])
def test_detalhe_fora_da_raiz_e_erro(caminho):
    with pytest.raises(svc.ComponentError, match="outside"):
        svc.get_component(caminho)


def test_pasta_vizinha_com_mesmo_prefixo_e_recusada(raiz):
    # a tela usava realpath.startswith(base): <raiz>2/ passava
    vizinha = raiz.parent / (raiz.name + "2")
    vizinha.mkdir()
    (vizinha / "x.q").write_text("<q:component name='X'/>", encoding="utf-8")
    with pytest.raises(svc.ComponentError, match="outside"):
        svc.get_component(f"../{vizinha.name}/x.q")


def test_lista_testes():
    r = svc.list_tests()
    assert sorted(a["path"] for a in r["files"]) == ["test_falha.py", "test_ok.py"]
    assert r["total_functions"] == 3


class TestRodar:
    def test_arquivo_que_passa(self, raiz):
        r = svc.run_tests("tests/test_ok.py")
        assert r["passed"] is True and r["summary"]["passed"] == 2
        assert {t["name"] for t in r["tests"]} == {"test_um", "test_dois"}
        salvo = json.loads((raiz / "quantum_admin" / "settings" / "last_test_result.json").read_text(encoding="utf-8"))
        assert salvo["test_file"] == "tests/test_ok.py"

    def test_arquivo_que_falha(self):
        r = svc.run_tests("tests/test_falha.py")
        assert r["passed"] is False and r["summary"]["failed"] == 1

    def test_caminho_absoluto_fora_da_raiz_e_recusado(self, raiz, tmp_path_factory):
        # a tela barrava so ".." — um caminho absoluto rodava pytest em qualquer .py
        fora = tmp_path_factory.mktemp("fora") / "test_malicioso.py"
        fora.write_text("import pathlib\npathlib.Path(__file__).with_name('rodou').write_text('sim')\n", encoding="utf-8")
        with pytest.raises(svc.ComponentError, match="outside"):
            svc.run_tests(str(fora))
        assert not fora.with_name("rodou").exists()

    @pytest.mark.parametrize("caminho", ["tests/../components/loja.q", "tests/ajuda.py", "tests/nao_existe.py"])
    def test_so_test_py_dentro_de_tests(self, caminho):
        with pytest.raises(svc.ComponentError):
            svc.run_tests(caminho)


class TestGerar:
    def test_gera_e_o_teste_gerado_passa(self, raiz):
        r = svc.generate_tests("components/loja.q")
        assert r["test_file"] == "tests/test_components_loja.py"
        assert svc.get_component("components/loja.q")["test_file"] == "tests/test_components_loja.py"
        rodada = svc.run_tests(r["test_file"])
        assert rodada["passed"] is True and rodada["summary"]["passed"] >= 2, rodada["output"][-800:]

    def test_nao_sobrescreve_teste_existente_sem_pedir(self, raiz):
        destino = raiz / "tests" / "test_components_loja.py"
        destino.write_text("# editado a mao\n", encoding="utf-8")
        with pytest.raises(svc.ComponentError, match="already exists"):
            svc.generate_tests("components/loja.q")
        assert destino.read_text(encoding="utf-8") == "# editado a mao\n"
        assert svc.generate_tests("components/loja.q", overwrite=True)["overwritten"] is True

    def test_so_componentes_q(self):
        with pytest.raises(svc.ComponentError):
            svc.generate_tests("tests/test_ok.py")
