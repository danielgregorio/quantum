"""Servicos da tela de aplicacao: projeto, config, ambientes, servidor e connectors do projeto."""

import socket
import time
import urllib.request

import pytest
import yaml

from quantum_admin.services import apps, connectors
from quantum_admin.services import projects as proj


@pytest.fixture(autouse=True)
def isolado(admin_isolado):
    return admin_isolado


@pytest.fixture
def loja():
    return proj.create_project("loja", "vende coisas")


class TestProjeto:
    def test_atualizar_nome_descricao_status(self, loja):
        r = apps.update_project(loja["id"], name="loja-nova", description="outra", status="archived")
        assert (r["name"], r["description"], r["status"]) == ("loja-nova", "outra", "archived")

    def test_nome_de_outro_projeto_e_erro(self, loja):
        proj.create_project("blog")
        with pytest.raises(proj.ProjectError, match="already exists"):
            apps.update_project(loja["id"], name="BLOG")

    def test_status_invalido(self, loja):
        with pytest.raises(proj.ProjectError, match="status must be"):
            apps.update_project(loja["id"], status="deleted")


class TestConfig:
    def test_ler_e_salvar_texto(self, loja, isolado):
        texto = "# minha config\nserver:\n  port: 9100\n"
        r = apps.save_project_config(loja["id"], texto)
        assert r["server"] == {"port": 9100} and r["text"] == texto
        assert (isolado / "projects" / "loja" / "quantum.config.yaml").read_text(encoding="utf-8") == texto

    @pytest.mark.parametrize("texto,motivo", [("server: [aberto", "invalid YAML"), ("- lista\n- solta\n", "mapping")])
    def test_yaml_invalido_nao_grava(self, loja, isolado, texto, motivo):
        antes = (isolado / "projects" / "loja" / "quantum.config.yaml").read_text(encoding="utf-8")
        with pytest.raises(proj.ProjectError, match=motivo):
            apps.save_project_config(loja["id"], texto)
        assert (isolado / "projects" / "loja" / "quantum.config.yaml").read_text(encoding="utf-8") == antes


class TestAmbientes:
    def test_criar_com_variaveis_listar_atualizar_remover(self, loja):
        env = apps.create_environment(loja["id"], "Staging", port=8200, variables="DB_HOST=db\n# comentario\nMODO = teste\n")
        assert (env["name"], env["display_name"], env["port"], env["variables"]) == \
            ("staging", "Staging", 8200, {"DB_HOST": "db", "MODO": "teste"})
        env = apps.update_environment(env["id"], port=8300, variables={"X": "1"})
        assert env["port"] == 8300 and env["variables"] == {"X": "1"}
        assert [e["name"] for e in apps.list_environments(loja["id"])] == ["staging"]
        apps.delete_environment(env["id"])
        assert apps.list_environments(loja["id"]) == []

    def test_nome_repetido_e_linha_invalida(self, loja):
        apps.create_environment(loja["id"], "dev")
        with pytest.raises(proj.ProjectError, match="already exists"):
            apps.create_environment(loja["id"], "DEV")
        with pytest.raises(proj.ProjectError, match="NAME=value"):
            apps.create_environment(loja["id"], "prod", variables="SEM_IGUAL")

    def test_padroes(self, loja):
        assert [e["name"] for e in apps.create_default_environments(loja["id"])] == \
            ["development", "staging", "production"]


def test_connector_do_projeto_e_desligar(loja):
    c = connectors.create_connector(name="pg", type="database", provider="postgres", application_id=loja["id"])
    assert proj.get_project(loja["id"])["connector_count"] == 1
    solto = connectors.detach_connector(c["id"])
    assert solto["scope"] == "public" and solto["application_id"] is None
    assert proj.get_project(loja["id"])["connector_count"] == 0


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _responde(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status, r.read().decode()
    except OSError:
        return None, ""


class TestServidor:
    def test_sem_config_e_erro(self):
        p = proj.create_project("vazio")
        (proj.raiz() / "projects" / "vazio" / "quantum.config.yaml").unlink()
        with pytest.raises(proj.ProjectError, match="not found"):
            apps.start_server(p["id"])

    def test_sobe_serve_e_para_de_verdade_com_reloader(self, isolado):
        # "iniciar" rodava src/cli/runner.py (inexistente); "parar" no Windows nao derrubava o filho do reloader
        p = proj.create_project("site")
        pasta = isolado / "projects" / "site"
        porta = _porta_livre()
        (pasta / "components" / "index.q").write_text(
            '<q:component name="index" xmlns:q="https://quantum.lang/ns"><p>SITE NO AR</p></q:component>',
            encoding="utf-8")
        (pasta / "quantum.config.yaml").write_text(yaml.safe_dump({
            "server": {"port": porta, "host": "127.0.0.1", "reload": True, "debug": False},
            "paths": {"components": "./components"},
            "logging": {"level": "ERROR", "console": False, "file": False}}), encoding="utf-8")
        try:
            apps.start_server(p["id"], wait=30)
            url = f"http://127.0.0.1:{porta}/"
            limite = time.time() + 30
            while time.time() < limite and _responde(url)[0] != 200:
                time.sleep(0.3)
            status, corpo = _responde(url)
            assert status == 200 and "SITE NO AR" in corpo, apps.server_log(p["id"], 40)["text"]
            assert apps.server_status(p["id"])["running"] is True
            with pytest.raises(proj.ProjectError, match="already running"):
                apps.start_server(p["id"])
        finally:
            apps.stop_server(p["id"])
        limite = time.time() + 15
        while time.time() < limite and _responde(url)[0] is not None:
            time.sleep(0.3)
        assert _responde(url)[0] is None, "a porta continua respondendo depois de parar"
        assert apps.server_status(p["id"])["running"] is False

    def test_config_quebrada_falha_com_o_log(self, isolado):
        p = proj.create_project("quebrado")
        (isolado / "projects" / "quebrado" / "quantum.config.yaml").write_text("server: [aberto", encoding="utf-8")
        with pytest.raises(proj.ProjectError, match="exited with code"):
            apps.start_server(p["id"], wait=30)
