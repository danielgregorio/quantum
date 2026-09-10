"""Servicos admin.connectors.* sobre quantum_admin/backend/connector_service.py.

Tudo com a fixture admin_isolado: connectors.yaml numa pasta temporaria.
Os testes de conexao batem em servidores reais locais (http.server), nao em mocks.
"""

import http.server
import json
import sqlite3
import threading

import pytest
import yaml

from quantum_admin.backend import connector_service
from quantum_admin.services import connectors as svc


@pytest.fixture(autouse=True)
def isolado(admin_isolado):
    return admin_isolado


def _arquivo(isolado):
    return isolado / "quantum_admin" / "settings" / "connectors.yaml"


@pytest.fixture
def servidor_http():
    """Servidor local; guarda os cabecalhos recebidos. Responde conforme a rota."""
    recebidos = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            recebidos.append((self.path, dict(self.headers)))
            if self.path == "/api/tags":
                corpo = {"models": [{"name": "phi3"}, {"name": "qwen2:7b"}]}
            elif self.path == "/v1/models" and self.headers.get("x-api-key") == "chave-certa":
                corpo = {"data": [{"id": "claude-x"}]}
            else:
                self.send_response(401)
                self.end_headers()
                return
            dados = json.dumps(corpo).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def log_message(self, *args):
            pass

    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield servidor.server_address[1], recebidos
    servidor.shutdown()
    servidor.server_close()


class TestCrud:
    def test_obrigatorios(self):
        with pytest.raises(svc.ConnectorError, match="required"):
            svc.create_connector(name="", type="database", provider="postgres")

    def test_provider_desconhecido(self):
        with pytest.raises(svc.ConnectorError, match="unknown provider"):
            svc.create_connector(name="x", type="database", provider="oracle")

    def test_senha_cifrada_no_arquivo_e_nunca_devolvida(self, isolado):
        # a tela .q gravava a senha em texto puro no YAML
        c = svc.create_connector(name="pg", type="database", provider="postgres", password="segredo-123")
        assert "segredo-123" not in _arquivo(isolado).read_text(encoding="utf-8")
        assert c["has_password"] is True and "password" not in c and "password_masked" not in c
        assert all("segredo" not in json.dumps(x) for x in svc.list_connectors())

    def test_porta_padrao_do_provider(self):
        assert svc.create_connector(name="pg", type="database", provider="postgres")["port"] == 5432

    def test_padrao_desmarca_os_outros_do_mesmo_tipo(self):
        a = svc.create_connector(name="a", type="cache", provider="redis", is_default=True)
        b = svc.create_connector(name="b", type="cache", provider="redis", is_default=True)
        estado = {c["name"]: c["is_default"] for c in svc.list_connectors()}
        assert estado == {"a": False, "b": True}
        svc.update_connector(a["id"], is_default=True)
        assert {c["name"]: c["is_default"] for c in svc.list_connectors()} == {"a": True, "b": False}
        assert b["id"] != a["id"]

    def test_editar_com_senha_em_branco_mantem_a_atual(self, isolado):
        c = svc.create_connector(name="pg", type="database", provider="postgres", password="velha")
        antes = yaml.safe_load(_arquivo(isolado).read_text(encoding="utf-8"))[0]["password"]
        svc.update_connector(c["id"], name="pg2", password="")
        depois = yaml.safe_load(_arquivo(isolado).read_text(encoding="utf-8"))[0]
        assert depois["password"] == antes and depois["name"] == "pg2"

    def test_filtro_por_aplicacao_inclui_publicos(self):
        svc.create_connector(name="publico", type="cache", provider="redis")
        svc.create_connector(name="da-app", type="database", provider="postgres", application_id=7)
        svc.create_connector(name="de-outra", type="database", provider="postgres", application_id=8)
        assert sorted(c["name"] for c in svc.list_connectors(application_id=7)) == ["da-app", "publico"]
        assert [c["name"] for c in svc.list_connectors(type="cache")] == ["publico"]

    def test_remover_e_inexistente(self):
        c = svc.create_connector(name="pg", type="database", provider="postgres")
        assert svc.delete_connector(c["id"]) == {"deleted": c["id"]}
        with pytest.raises(svc.ConnectorError, match="no connector"):
            svc.delete_connector(c["id"])


class TestArquivoProtegido:
    def test_entrada_invalida_nao_e_apagada_na_proxima_gravacao(self, isolado):
        # antes: a entrada que nao carregava sumia do arquivo no save seguinte
        _arquivo(isolado).write_text(yaml.safe_dump([
            {"id": "ok", "name": "bom", "type": "cache", "provider": "redis"},
            {"id": "x", "name": "estranho", "type": "cache", "provider": "redis", "campo_novo": 1},
        ]), encoding="utf-8")
        original = _arquivo(isolado).read_text(encoding="utf-8")
        with pytest.raises(connector_service.ConnectorFileError, match="estranho"):
            svc.create_connector(name="novo", type="cache", provider="redis")
        assert _arquivo(isolado).read_text(encoding="utf-8") == original

    def test_arquivo_ilegivel_nao_e_esvaziado(self, isolado):
        _arquivo(isolado).write_text("- id: [aberto\n  nome: ruim", encoding="utf-8")
        original = _arquivo(isolado).read_text(encoding="utf-8")
        with pytest.raises(connector_service.ConnectorFileError, match="could not be read"):
            svc.create_connector(name="novo", type="cache", provider="redis")
        assert _arquivo(isolado).read_text(encoding="utf-8") == original


class TestConexao:
    def test_sqlite_real_grava_status(self, isolado):
        banco = isolado / "dados.db"
        sqlite3.connect(banco).close()
        c = svc.create_connector(name="lite", type="database", provider="sqlite", database=str(banco))
        r = svc.test_connector(c["id"])
        assert r["success"] is True and "SQLite" in r["details"]["version"]
        gravado = svc.get_connector(c["id"])
        assert gravado["status"] == "connected" and gravado["last_tested"]

    def test_ollama_lista_modelos(self, servidor_http):
        porta, _ = servidor_http
        c = svc.create_connector(name="ollama", type="ai", provider="ollama", host="127.0.0.1", port=porta)
        r = svc.test_connector(c["id"])
        assert r["success"] is True and r["details"]["models"] == ["phi3", "qwen2:7b"]

    def test_anthropic_sem_chave_nao_e_verde(self):
        # antes: CONNECTED e modelos inventados, sem requisicao nenhuma
        c = svc.create_connector(name="claude", type="ai", provider="anthropic")
        r = svc.test_connector(c["id"])
        assert r["success"] is False and "No API key" in r["error"]
        assert svc.get_connector(c["id"])["status"] == "error"

    def test_anthropic_consulta_a_api_com_a_chave(self, servidor_http):
        porta, recebidos = servidor_http
        base = f"http://127.0.0.1:{porta}/v1"
        certa = svc.create_connector(name="certa", type="ai", provider="anthropic", password="chave-certa")
        errada = svc.create_connector(name="errada", type="ai", provider="anthropic", password="chave-errada")
        servico = connector_service.get_connector_service()
        for conector_id in (certa["id"], errada["id"]):
            atual = servico.get_connector(conector_id)
            atual.options = {"endpoint": base}
            servico.update_connector(conector_id, {"options": atual.options})
        assert svc.test_connector(certa["id"]) == {"success": True, "error": None, "details": {"models": ["claude-x"]}}
        falha = svc.test_connector(errada["id"])
        assert falha["success"] is False and "401" in falha["error"]
        assert recebidos[0][1].get("x-api-key") == "chave-certa"

    def test_inexistente(self):
        with pytest.raises(svc.ConnectorError, match="no connector"):
            svc.test_connector("nao-existe")
