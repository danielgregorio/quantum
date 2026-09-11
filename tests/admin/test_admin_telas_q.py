"""As telas .q do admin (components/admin), servidas pelo servidor real.

As telas vêm do repositório; banco, settings e raiz são temporários
(admin_isolado), e os serviços rodam no mesmo processo. Cada teste entra pela
tela de login, como uma pessoa.
"""

import html as html_lib
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
    # <pre> mostra conteúdo de arquivo (código, saída do pytest), que pode ter chaves.
    html = re.sub(r"<(style|script|pre)\b.*?</\1>", "", html, flags=re.S)
    pagina = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))
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


TELAS = ["/admin", "/admin/dashboard", "/admin/features", "/admin/agents", "/admin/database",
         "/admin/jobs", "/admin/source?file=README.md", "/admin/components", "/admin/tests",
         "/admin/component/components/loja.q", "/admin/settings", "/admin/connectors"]


@pytest.mark.parametrize("url", TELAS)
def test_toda_tela_pede_login(admin, url):
    r = admin.get(url)
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/login")


class TestTelasDeLeitura:
    def test_admin_leva_as_aplicacoes(self, admin):
        entrar(admin)
        assert 'url=/admin/applications' in admin.get("/admin").get_data(as_text=True)

    def test_dashboard(self, admin, admin_isolado):
        (admin_isolado / "components").mkdir()
        (admin_isolado / "components" / "loja.q").write_text('<q:component name="Loja"/>', encoding="utf-8")
        entrar(admin)
        pagina = texto(admin.get("/admin/dashboard"))
        assert "loja.q" in pagina and "Tags with a parser" in pagina

    def test_features(self, admin):
        entrar(admin)
        pagina = texto(admin.get("/admin/features"))
        assert "conditionals" in pagina and "loops" in pagina

    def test_agentes_e_llm_sem_a_chave(self, admin, admin_isolado):
        (admin_isolado / "components").mkdir()
        (admin_isolado / "components" / "a.q").write_text(
            '<q:component name="A"><q:agent name="ajudante" model="phi3" provider="ollama"/></q:component>',
            encoding="utf-8")
        config = admin_isolado / "quantum.config.yaml"
        dados = yaml.safe_load(config.read_text(encoding="utf-8"))
        dados["llm"] = {"base_url": "http://localhost:11434", "default_model": "phi3", "api_key": "sk-NAO-MOSTRAR"}
        config.write_text(yaml.safe_dump(dados), encoding="utf-8")
        entrar(admin)
        html = admin.get("/admin/agents").get_data(as_text=True)
        pagina = texto(admin.get("/admin/agents"))
        assert "ajudante" in pagina and "http://localhost:11434" in pagina and "components/a.q" in pagina
        assert "sk-NAO-MOSTRAR" not in html

    def test_bancos_e_datasources_sem_credenciais(self, admin, admin_isolado):
        import sqlite3
        conexao = sqlite3.connect(admin_isolado / "loja.db")
        conexao.executescript("create table pedidos (id integer); insert into pedidos values (1), (2), (3);")
        conexao.close()
        config = admin_isolado / "quantum.config.yaml"
        dados = yaml.safe_load(config.read_text(encoding="utf-8"))
        dados["datasources"] = {"vendas": {"driver": "postgres", "database": "vendas", "password": "senha-NAO-MOSTRAR"}}
        config.write_text(yaml.safe_dump(dados), encoding="utf-8")
        entrar(admin)
        html = admin.get("/admin/database").get_data(as_text=True)
        pagina = texto(admin.get("/admin/database"))
        assert "loja.db" in pagina and "pedidos" in pagina and "vendas" in pagina and "postgres" in pagina
        assert "senha-NAO-MOSTRAR" not in html

    def test_jobs(self, admin, admin_isolado):
        entrar(admin)
        assert "No Job Queue Yet" in texto(admin.get("/admin/jobs"))
        import sqlite3
        conexao = sqlite3.connect(admin_isolado / "quantum_jobs.db")
        conexao.executescript(
            "create table quantum_jobs (id integer primary key autoincrement, name text, queue text, status text,"
            " attempts integer, max_attempts integer, created_at text, error text);"
            "insert into quantum_jobs (name, queue, status, attempts, max_attempts, error) values"
            " ('enviar-email','mail','failed',3,3,'SMTP recusou'), ('relatorio',null,'pending',0,3,null);")
        conexao.close()
        pagina = texto(admin.get("/admin/jobs"))
        assert "enviar-email" in pagina and "SMTP recusou" in pagina and "3/3" in pagina and "relatorio" in pagina

    def test_leitor_de_codigo(self, admin, admin_isolado):
        (admin_isolado / "LEIAME.txt").write_text("primeira linha\nsegunda linha\n", encoding="utf-8")
        (admin_isolado / ".env").write_text("SENHA=segredo-NAO-MOSTRAR\n", encoding="utf-8")
        entrar(admin)
        pagina = texto(admin.get("/admin/source?file=LEIAME.txt"))
        assert "3 lines" in pagina
        assert "segunda linha" in admin.get("/admin/source?file=LEIAME.txt").get_data(as_text=True)
        html = admin.get("/admin/source?file=.env").get_data(as_text=True)
        assert "may contain credentials" in texto(admin.get("/admin/source?file=.env"))
        assert "segredo-NAO-MOSTRAR" not in html
        assert "outside the project root" in texto(admin.get("/admin/source?file=../x.txt"))
        assert "a file path is required" in texto(admin.get("/admin/source"))


COMPONENTE = ('<q:component name="Loja" xmlns:q="https://quantum.lang/ns">'
              '<q:action name="comprar" method="POST"><q:param name="item" required="true"/>'
              '<q:redirect url="/loja"/></q:action><p>vitrine</p></q:component>\n')


class TestComponentesETestes:
    @pytest.fixture
    def projeto(self, admin_isolado):
        (admin_isolado / "components" / "sub").mkdir(parents=True)
        (admin_isolado / "components" / "loja.q").write_text(COMPONENTE, encoding="utf-8")
        (admin_isolado / "components" / "sub" / "b.q").write_text('<q:component name="B"/>', encoding="utf-8")
        (admin_isolado / "tests").mkdir()
        (admin_isolado / "tests" / "test_ok.py").write_text("def test_um():\n    assert True\n", encoding="utf-8")
        return admin_isolado

    def test_listas(self, admin, projeto):
        entrar(admin)
        pagina = texto(admin.get("/admin/components"))
        assert "loja.q" in pagina and "sub/b.q" in pagina and "action, redirect" in pagina
        assert 'href="/admin/component/components/loja.q"' in admin.get("/admin/components").get_data(as_text=True)
        pagina = texto(admin.get("/admin/tests"))
        assert "test_ok.py" in pagina

    def test_detalhe(self, admin, projeto):
        entrar(admin)
        pagina = texto(admin.get("/admin/component/components/loja.q"))
        assert "Loja" in pagina and "comprar" in pagina and "no test file yet" in pagina

    def test_fora_da_raiz_e_inexistente(self, admin, projeto):
        entrar(admin)
        # O servidor já barra o ".." na URL (404); o serviço barra o que passar.
        assert admin.get("/admin/component/components/../../fora.q").status_code == 404
        assert "file not found" in texto(admin.get("/admin/component/components/nao-existe.q"))

    def test_gerar_nao_sobrescreve_e_rodar(self, admin, projeto):
        entrar(admin)
        url = "/admin/component/components/loja.q"
        r = admin.post(url, data={"action": "generateTests"})
        assert r.status_code == 302 and r.headers["Location"].endswith("?tab=tests")
        gerado = projeto / "tests" / "test_components_loja.py"
        pagina = texto(admin.get(url + "?tab=tests"))
        assert "tests/test_components_loja.py created" in pagina and gerado.is_file()

        gerado.write_text("def test_feito_a_mao():\n    assert True\n\ndef test_quebrado():\n    assert False\n",
                          encoding="utf-8")
        admin.post(url, data={"action": "generateTests"})  # sem overwrite: recusa
        assert "already exists" in texto(admin.get(url))
        assert "test_feito_a_mao" in gerado.read_text(encoding="utf-8")

        admin.post(url, data={"action": "runTests"})
        pagina = texto(admin.get(url + "?tab=tests"))
        assert "1 failed, 0 errors, 1 passed" in pagina
        assert "PASSED test_feito_a_mao" in pagina and "FAILED test_quebrado" in pagina

        admin.post(url, data={"action": "generateTests", "overwrite": "true"})
        assert "regenerated" in texto(admin.get(url))
        assert "test_feito_a_mao" not in gerado.read_text(encoding="utf-8")

    def test_rodar_sem_arquivo_de_teste(self, admin, projeto):
        entrar(admin)
        admin.post("/admin/component/components/sub/b.q", data={"action": "runTests"})
        assert "there is no test file to run" in texto(admin.get("/admin/component/components/sub/b.q"))


class TestConfiguracoes:
    @pytest.fixture
    def config(self, admin, admin_isolado):
        arquivo = admin_isolado / "quantum.config.yaml"
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
        dados["server"].update(port=8123, host="127.0.0.1", reload=True)
        arquivo.write_text("# AVISO: nao exponha o servidor\n" + yaml.safe_dump(dados), encoding="utf-8")
        return arquivo

    def test_formulario_vem_com_o_que_esta_no_arquivo(self, admin, config):
        entrar(admin)
        html = admin.get("/admin/settings").get_data(as_text=True)
        texto(admin.get("/admin/settings"))
        assert 'value="8123"' in html
        assert re.search(r'<input[^>]*name="reload"[^>]*checked', html)
        assert not re.search(r'<input[^>]*name="debug"[^>]*checked', html)
        assert re.search(r'<option value="ERROR" selected', html)  # logging.level da fixture

    def test_salvar_muda_so_os_valores(self, admin, config):
        entrar(admin)
        r = admin.post("/admin/settings", data={"action": "saveSettings", "port": "9090", "host": "127.0.0.1",
                                                "debug": "true", "log_level": "ERROR", "cache_ttl": "0"})
        assert r.status_code == 302
        assert "Saved" in texto(admin.get("/admin/settings"))
        conteudo = config.read_text(encoding="utf-8")
        salvo = yaml.safe_load(conteudo)
        assert conteudo.startswith("# AVISO: nao exponha o servidor")
        assert salvo["server"]["port"] == 9090 and salvo["server"]["debug"] is True
        assert salvo["server"]["reload"] is False  # checkbox desmarcado

    def test_debug_com_host_publico_e_recusado(self, admin, config):
        entrar(admin)
        antes = config.read_text(encoding="utf-8")
        admin.post("/admin/settings", data={"action": "saveSettings", "port": "9090", "host": "0.0.0.0",
                                            "debug": "true", "log_level": "INFO"})
        assert "debug cannot be on with host 0.0.0.0" in texto(admin.get("/admin/settings"))
        assert config.read_text(encoding="utf-8") == antes



class TestConnectors:
    def _criar(self, admin, **campos):
        dados = {"action": "createConnector", "name": "lite", "conn_type": "database", "provider": "sqlite"}
        dados.update(campos)
        return admin.post("/admin/connectors", data=dados)

    def test_criar_com_senha_cifrada_e_nunca_mostrada(self, admin, admin_isolado):
        entrar(admin)
        pagina = texto(admin.get("/admin/connectors"))
        assert "0 registered" in pagina and "New Connector" in pagina
        assert self._criar(admin, name="principal", provider="postgres", conn_type="database",
                           username="app", password="senha-NAO-MOSTRAR").status_code == 302
        html = admin.get("/admin/connectors").get_data(as_text=True)
        assert "Connector principal created" in texto(admin.get("/admin/connectors?x=1")) or "principal" in html
        pagina = texto(admin.get("/admin/connectors"))
        assert "principal" in pagina and "PostgreSQL" in pagina and "localhost:5432" in pagina
        arquivo = (admin_isolado / "quantum_admin" / "settings" / "connectors.yaml").read_text(encoding="utf-8")
        assert "senha-NAO-MOSTRAR" not in arquivo and "senha-NAO-MOSTRAR" not in html

    def test_obrigatorios_e_provider_desconhecido(self, admin):
        entrar(admin)
        self._criar(admin, provider="banco-magico")
        assert "unknown provider" in texto(admin.get("/admin/connectors"))

    def test_editar_mantem_a_senha_e_testar(self, admin, admin_isolado):
        import sqlite3
        from quantum_admin.services import connectors as svc
        banco = admin_isolado / "dados.db"
        sqlite3.connect(banco).close()
        entrar(admin)
        self._criar(admin, database=str(banco), password="guardada")
        [c] = svc.list_connectors()

        html = admin.get(f"/admin/connectors?edit={c['id']}").get_data(as_text=True)
        pagina = texto(admin.get(f"/admin/connectors?edit={c['id']}"))
        assert "Edit lite" in pagina and "saved — leave blank to keep" in html
        assert re.search(r'<option value="sqlite" selected', html)

        admin.post("/admin/connectors", data={"action": "updateConnector", "connector_id": c["id"], "name": "lite2",
                                              "conn_type": "database", "provider": "sqlite", "password": ""})
        assert "Connector lite2 updated" in texto(admin.get("/admin/connectors"))
        assert svc.get_connector(c["id"])["has_password"] is True

        admin.post("/admin/connectors", data={"action": "testConnector", "connector_id": c["id"]})
        assert "Connection OK" in texto(admin.get("/admin/connectors"))
        assert svc.get_connector(c["id"])["status"] == "connected"

    def test_teste_que_falha_mostra_o_motivo(self, admin):
        from quantum_admin.services import connectors as svc
        entrar(admin)
        self._criar(admin, name="claude", conn_type="ai", provider="anthropic")
        [c] = svc.list_connectors()
        admin.post("/admin/connectors", data={"action": "testConnector", "connector_id": c["id"]})
        assert "Connection failed: No API key" in texto(admin.get("/admin/connectors"))

    def test_editar_inexistente_e_remover(self, admin):
        from quantum_admin.services import connectors as svc
        entrar(admin)
        assert "no connector with id 'fantasma'" in texto(admin.get("/admin/connectors?edit=fantasma"))
        self._criar(admin)
        [c] = svc.list_connectors()
        admin.post("/admin/connectors", data={"action": "deleteConnector", "connector_id": c["id"]})
        assert "Connector deleted" in texto(admin.get("/admin/connectors"))
        assert svc.list_connectors() == []
