"""Servicos das telas de leitura (quantum_admin/services/repository.py)."""

import hashlib
import sqlite3

import pytest

from quantum_admin.services import repository as svc


@pytest.fixture(autouse=True)
def raiz(admin_isolado):
    base = admin_isolado
    (base / "components").mkdir()
    (base / "components" / "a.q").write_text(
        '<q:component name="A"><q:agent name="ajudante" model="phi3" provider="ollama"/></q:component>', encoding="utf-8")
    (base / "examples").mkdir()
    (base / "examples" / "e.q").write_text('<q:component name="E"><q:team name="time" supervisor="chefe"/></q:component>',
                                          encoding="utf-8")
    (base / "tests").mkdir()
    (base / "tests" / "test_x.py").write_text("def test_x():\n    pass\n", encoding="utf-8")
    (base / "README.md").write_text("# oi\nlinha 2\n", encoding="utf-8")
    (base / ".env").write_text("SENHA=segredo\n", encoding="utf-8")
    return base


def test_dashboard_mede_de_verdade():
    # a tela procurava src/core/... e mostrava 0 features, 0 parsers, 0 executores
    s = svc.dashboard_stats()
    assert (s["components"], s["tests"], s["examples"]) == (1, 1, 1)
    assert s["features"] > 10 and s["parser_tags"] > 20 and s["executors"] > 20


def test_features_vem_dos_manifests_reais():
    r = svc.list_features()
    nomes = {f["name"] for f in r["features"]}
    assert {"conditionals", "loops"} <= nomes
    assert sum(r["by_status"].values()) == len(r["features"])


def test_agentes_e_times_declarados():
    r = svc.list_agents()
    assert r["agents"] == [{"name": "ajudante", "model": "phi3", "provider": "ollama", "source": "components/a.q"}]
    assert r["teams"] == [{"name": "time", "supervisor": "chefe", "source": "examples/e.q"}]


class TestFonte:
    def test_le_arquivo_da_raiz(self):
        r = svc.read_source("README.md")
        assert (r["type"], r["lines"], r["content"]) == ("Markdown", 3, "# oi\nlinha 2\n")

    @pytest.mark.parametrize("caminho", [".env", "quantum_admin/settings/connectors.yaml", "dados.db"])
    def test_arquivos_com_credenciais_sao_recusados(self, raiz, caminho):
        (raiz / "dados.db").write_bytes(b"")
        (raiz / "quantum_admin" / "settings" / "connectors.yaml").write_text("- password: x\n", encoding="utf-8")
        with pytest.raises(svc.RepositoryError, match="credentials"):
            svc.read_source(caminho)

    def test_fora_da_raiz_e_pasta_vizinha(self, raiz):
        vizinha = raiz.parent / (raiz.name + "2")
        vizinha.mkdir()
        (vizinha / "x.txt").write_text("x", encoding="utf-8")
        for caminho in ("../x.txt", f"../{vizinha.name}/x.txt"):
            with pytest.raises(svc.RepositoryError, match="outside"):
                svc.read_source(caminho)


def test_bancos_abertos_somente_leitura(raiz):
    banco = raiz / "app.db"
    conexao = sqlite3.connect(banco)
    conexao.executescript("create table itens (id integer); insert into itens values (1), (2);")
    conexao.commit()
    conexao.close()
    antes = hashlib.sha256(banco.read_bytes()).hexdigest()
    r = svc.list_databases()
    [b] = r["databases"]
    assert b["path"] == "app.db" and b["tables"] == [{"name": "itens", "rows": 2}]
    assert hashlib.sha256(banco.read_bytes()).hexdigest() == antes
    assert not (raiz / "app.db-journal").exists() and not (raiz / "app.db-wal").exists()


def test_fila_de_jobs(raiz):
    assert svc.list_jobs()["found"] is False
    conexao = sqlite3.connect(raiz / "quantum_jobs.db")
    conexao.executescript(
        "create table quantum_jobs (id integer primary key autoincrement, name text, queue text, status text,"
        " attempts integer, max_attempts integer, created_at text, error text);"
        "insert into quantum_jobs (name, queue, status, attempts, max_attempts) values"
        " ('a','q','pending',0,3), ('b','q','failed',3,3), ('c','q','pending',0,3);")
    conexao.commit()
    conexao.close()
    r = svc.list_jobs(limit=2)
    assert r["counts"] == {"pending": 2, "running": 0, "completed": 0, "failed": 1} and r["total"] == 3
    assert [j["name"] for j in r["jobs"]] == ["c", "b"]
