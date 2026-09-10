"""As telas .q do admin (components/admin), servidas pelo servidor real.

As telas vêm do repositório; banco, settings e raiz são temporários
(admin_isolado), e os serviços rodam no mesmo processo. Cada teste entra pela
tela de login, como uma pessoa.
"""

import logging
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
SENHA = "uma-senha-de-teste-suficientemente-longa"
MODULOS = ["quantum_admin.services.projects", "quantum_admin.services.yaml_import",
           "quantum_admin.services.connectors", "quantum_admin.services.settings",
           "quantum_admin.services.components", "quantum_admin.services.apps",
           "quantum_admin.services.repository", "quantum_admin.services.auth"]


def texto(resposta):
    html = resposta.get_data(as_text=True)
    html = re.sub(r"<(style|script)\b.*?</\1>", "", html, flags=re.S)
    pagina = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    # Uma expressão que falha no conteúdo HTML fica como texto (EXPR-4): numa
    # tela do admin isso é sempre um defeito da tela. Vale para texto e atributos.
    cruas = re.findall(r"\{[^{}]*\}", pagina) + re.findall(r'="[^"]*(\{[^"{}]*\})[^"]*"', html)
    assert not cruas, f"expressões não resolvidas na tela: {cruas[:5]}"
    return pagina


@pytest.fixture
def admin(admin_isolado, monkeypatch):
    from quantum import services
    from quantum.runtime.web_server import QuantumWebServer
    from quantum_admin.backend import auth_service
    from quantum_admin.services import auth

    monkeypatch.setenv("ADMIN_PASSWORD", SENHA)
    monkeypatch.setenv("JWT_SECRET_KEY", "k" * 64)
    monkeypatch.setattr(auth_service, "_auth_service", None)
    auth._reset()
    services._reset()
    config = admin_isolado / "quantum.config.yaml"
    config.write_text(yaml.safe_dump({
        "server": {"debug": False},
        "paths": {"components": (REPO / "components").as_posix()},
        "logging": {"level": "ERROR", "console": False, "file": False},
        "services": MODULOS,
    }), encoding="utf-8")
    logging.disable(logging.CRITICAL)
    app = QuantumWebServer(str(config)).app
    app.config["TESTING"] = True
    yield app.test_client()
    logging.disable(logging.NOTSET)
    services._reset()


def entrar(cliente, senha=SENHA):
    return cliente.post("/admin/login", data={"action": "signIn", "username": "admin", "password": senha})


class TestLogin:
    def test_tela_protegida_manda_para_o_login_do_admin(self, admin):
        r = admin.get("/admin/applications")
        assert r.status_code == 302 and r.headers["Location"].endswith("/admin/login")

    def test_senha_errada_volta_com_mensagem(self, admin):
        r = entrar(admin, "errada")
        assert r.status_code == 302 and r.headers["Location"].endswith("/admin/login")
        assert "invalid username or password" in texto(admin.get("/admin/login"))
        assert admin.get("/admin/applications").status_code == 302

    def test_entrar_e_sair(self, admin):
        r = entrar(admin)
        assert r.status_code == 302 and r.headers["Location"].endswith("/admin/applications")
        assert admin.get("/admin/applications").status_code == 200
        admin.post("/admin/logout", data={"action": "signOut"})
        assert admin.get("/admin/applications").status_code == 302


class TestAplicacoes:
    def test_lista_cria_e_remove(self, admin, admin_isolado):
        entrar(admin)
        pagina = texto(admin.get("/admin/applications"))
        assert "Applications" in pagina and "No Applications Found" in pagina

        r = admin.post("/admin/applications", data={"action": "createProject", "name": "loja", "description": "vende"})
        assert r.status_code == 302
        pagina = texto(admin.get("/admin/applications"))
        assert "Application loja created" in pagina and "loja" in pagina and "vende" in pagina
        assert (admin_isolado / "projects" / "loja" / "quantum.config.yaml").is_file()

        from quantum_admin.services import projects
        [p] = projects.list_projects()
        admin.post("/admin/applications", data={"action": "deleteProject", "project_id": str(p["id"])})
        assert "Application record removed" in texto(admin.get("/admin/applications"))
        assert projects.list_projects() == []

    def test_nome_repetido_mostra_o_erro_do_servico(self, admin):
        entrar(admin)
        admin.post("/admin/applications", data={"action": "createProject", "name": "loja"})
        admin.get("/admin/applications")
        admin.post("/admin/applications", data={"action": "createProject", "name": "LOJA"})
        assert "already exists" in texto(admin.get("/admin/applications"))

    def test_busca(self, admin):
        entrar(admin)
        for nome in ("loja", "blog"):
            admin.post("/admin/applications", data={"action": "createProject", "name": nome})
        pagina = texto(admin.get("/admin/applications?search=blo"))
        assert "blog" in pagina and "loja" not in pagina

    def test_importar_do_yaml_antigo(self, admin, admin_isolado):
        (admin_isolado / "quantum_admin" / "settings" / "projects.yaml").write_text(
            yaml.safe_dump([{"id": "u1", "name": "antigo", "source_path": "projects/antigo"}]), encoding="utf-8")
        entrar(admin)
        assert "exist only in the old settings/projects.yaml" in texto(admin.get("/admin/applications"))
        admin.post("/admin/applications", data={"action": "importYaml"})
        pagina = texto(admin.get("/admin/applications"))
        assert "1 application(s) imported" in pagina and "antigo" in pagina
        assert "exist only in the old" not in pagina
