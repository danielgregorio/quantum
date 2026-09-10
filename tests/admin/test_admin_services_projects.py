"""Servicos admin.projects.* (quantum_admin/services/projects.py).

Os comportamentos vieram de components/admin/applications.q, que os fazia em
q:python sobre settings/projects.yaml. Cada teste roda com um banco novo e
uma raiz temporaria — nunca o banco nem a pasta reais do admin.
"""

import logging
import os

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantum_admin.backend import database, models
from quantum_admin.services import _base
from quantum_admin.services import projects as svc


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'admin.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    monkeypatch.setattr(_base, "_iniciado", False)
    monkeypatch.setenv("QUANTUM_ADMIN_ROOT", str(tmp_path))
    yield tmp_path
    engine.dispose()


class TestCriar:
    def test_registra_e_cria_a_pasta_com_config_padrao(self, isolado):
        p = svc.create_project("loja", "minha loja")
        pasta = isolado / "projects" / "loja"
        assert (pasta / "components").is_dir() and (pasta / "static").is_dir()
        config = yaml.safe_load((pasta / "quantum.config.yaml").read_text(encoding="utf-8"))
        assert config["server"] == {"port": 8080, "host": "127.0.0.1", "debug": False}
        assert p["source_path"] == "projects/loja" and p["has_config"] and p["status"] == "active"

    def test_nao_sobrescreve_config_existente(self, isolado):
        pasta = isolado / "apps" / "velho"
        pasta.mkdir(parents=True)
        (pasta / "quantum.config.yaml").write_text("server:\n  port: 9999\n", encoding="utf-8")
        p = svc.create_project("velho", source_path="apps/velho")
        assert p["port"] == 9999

    @pytest.mark.parametrize("nome", ["", "a", "  "])
    def test_nome_curto_e_erro(self, nome):
        # a tela antiga ignorava e redirecionava com "Application created"
        with pytest.raises(svc.ProjectError, match="at least 2"):
            svc.create_project(nome)

    def test_nome_repetido_sem_diferenciar_maiusculas_e_erro(self):
        svc.create_project("Loja")
        with pytest.raises(svc.ProjectError, match="already exists"):
            svc.create_project("loja")

    def test_caminho_fora_da_raiz_e_erro(self, isolado):
        with pytest.raises(svc.ProjectError, match="inside"):
            svc.create_project("fuga", source_path="../fora")
        assert not (isolado.parent / "fora").exists()


class TestListar:
    def test_campos_da_tela(self, isolado):
        svc.create_project("loja", "vende coisas")
        componentes = isolado / "projects" / "loja" / "components"
        (componentes / "index.q").write_text("<q:component/>", encoding="utf-8")
        (componentes / "sub").mkdir()
        (componentes / "sub" / "b.q").write_text("", encoding="utf-8")
        (isolado / "projects" / "loja" / "fora.q").write_text("", encoding="utf-8")
        [p] = svc.list_projects()
        assert (p["name"], p["initial"], p["component_count"], p["port"], p["running"]) == \
            ("loja", "L", 2, 8080, False)

    def test_busca_por_nome_ou_descricao(self):
        svc.create_project("loja", "vende coisas")
        svc.create_project("blog", "textos")
        assert [p["name"] for p in svc.list_projects("VENDE")] == ["loja"]
        assert [p["name"] for p in svc.list_projects("blo")] == ["blog"]

    def test_processo_vivo_e_pid_velho(self, isolado):
        svc.create_project("rodando")
        svc.create_project("parado")
        pids = isolado / "quantum_admin" / "settings" / "pids"
        pids.mkdir(parents=True)
        (pids / "rodando.pid").write_text(str(os.getpid()), encoding="utf-8")
        (pids / "parado.pid").write_text("999999", encoding="utf-8")
        estado = {p["name"]: p["running"] for p in svc.list_projects()}
        assert estado == {"rodando": True, "parado": False}
        assert not (pids / "parado.pid").exists()      # pid de processo morto e limpo

    def test_conta_connectors_do_projeto(self):
        p = svc.create_project("loja")
        with _base.sessao() as db:
            db.add(models.Connector(id="c1", name="pg", type="database", provider="postgres",
                                    owner_project_id=p["id"]))
        assert svc.list_projects()[0]["connector_count"] == 1
        assert svc.summary()["connectors"] == 1


class TestRemoverESincronizar:
    def test_remover_apaga_o_registro_e_deixa_os_arquivos(self, isolado):
        p = svc.create_project("loja")
        assert svc.delete_project(p["id"]) == {"deleted": p["id"]}
        assert svc.list_projects() == []
        assert (isolado / "projects" / "loja" / "quantum.config.yaml").is_file()

    def test_remover_inexistente_e_erro(self):
        with pytest.raises(svc.ProjectError, match="no project"):
            svc.delete_project(42)

    def test_sincronizar_registra_pastas_novas_e_ignora_ocultas(self, isolado):
        for nome in ("alfa", "beta", ".git", "_rascunho"):
            (isolado / "projects" / nome).mkdir(parents=True)
        (isolado / "projects" / "arquivo.txt").write_text("x", encoding="utf-8")
        svc.create_project("alfa")
        assert svc.sync_projects() == {"created": ["beta"], "total": 2}
        assert svc.sync_projects()["created"] == []          # idempotente

    def test_resumo(self):
        svc.create_project("alfa")
        svc.create_project("beta")
        assert svc.summary() == {"total": 2, "active": 2, "running": 0, "with_config": 2, "connectors": 0}


@pytest.fixture
def servidor_admin(isolado):
    from quantum.runtime.web_server import QuantumWebServer
    pasta = isolado / "components"
    pasta.mkdir(exist_ok=True)
    config = isolado / "quantum.config.yaml"
    config.write_text(f"server:\n  debug: true\npaths:\n  components: {pasta.as_posix()}\n"
                      "logging:\n  level: ERROR\n  console: false\n  file: false\n"
                      "services:\n  - quantum_admin.services.projects\n", encoding="utf-8")

    def render(corpo):
        (pasta / "p.q").write_text(
            f'<q:component name="p" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>', encoding="utf-8")
        logging.disable(logging.CRITICAL)
        try:
            r = QuantumWebServer(str(config)).app.test_client().get("/p")
        finally:
            logging.disable(logging.NOTSET)
        assert r.status_code == 200, r.get_data(as_text=True)[-600:]
        return r.get_data(as_text=True)
    return render


def test_tela_chama_o_servico(servidor_admin):
    """De ponta a ponta: pagina .q -> q:invoke service= -> banco do admin."""
    svc.create_project("loja", "vende coisas")
    html = servidor_admin('<q:invoke name="ps" service="admin.projects.list"/>'
                          '<ul><q:loop items="{ps}" var="p"><li>{p.name}: {p.component_count}</li></q:loop></ul>')
    assert "loja: 0" in html
