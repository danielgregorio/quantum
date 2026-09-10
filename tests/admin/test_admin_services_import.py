"""admin.import.*: os projetos do YAML antigo das telas .q entram no banco sem perder nada."""

import hashlib

import pytest
import yaml
from sqlalchemy import create_engine

from quantum_admin.backend import models
from quantum_admin.services import _base
from quantum_admin.services import projects, yaml_import

PROJETOS = [
    {"id": "uuid-blog", "name": "blog", "description": "o blog", "status": "active",
     "source_path": "projects/blog", "created_at": "2026-01-02T03:04:05", "updated_at": "2026-02-03T04:05:06",
     "config": {"port": 8081}, "environments": []},
    {"id": "uuid-rag", "name": "quantum-rag", "description": "", "status": "archived",
     "source_path": "projects\\quantum-rag", "created_at": "2026-01-01T00:00:00"},
]
CONNECTORS = [
    {"id": "c-redis", "name": "cache", "type": "cache", "provider": "redis", "scope": "public"},
    {"id": "c-pg", "name": "pg do blog", "type": "database", "provider": "postgres",
     "scope": "application", "application_id": "uuid-blog"},
]


@pytest.fixture(autouse=True)
def isolado(admin_isolado):
    pasta = admin_isolado / "quantum_admin" / "settings"
    (pasta / "projects.yaml").write_text(yaml.safe_dump(PROJETOS), encoding="utf-8")
    (pasta / "connectors.yaml").write_text(yaml.safe_dump(CONNECTORS), encoding="utf-8")
    return admin_isolado


def _hash(pasta):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(pasta.glob("*.yaml"))}


def test_pendente_lista_projetos_que_faltam_e_connectors_presos_a_id_antigo():
    projects.create_project("Blog")          # ja existe no banco (caixa diferente conta como igual)
    assert yaml_import.pending() == {"projects": ["quantum-rag"],
                                     "connectors_to_review": ["pg do blog (project blog)"]}


def test_importa_preservando_campos():
    r = yaml_import.run()
    assert r["projects"] == ["blog", "quantum-rag"]
    with _base.sessao() as db:
        blog = db.query(models.Project).filter_by(name="blog").one()
        rag = db.query(models.Project).filter_by(name="quantum-rag").one()
        assert (blog.description, blog.created_at.isoformat(), rag.status, rag.source_path) == \
            ("o blog", "2026-01-02T03:04:05", "archived", "projects/quantum-rag")


def test_connectors_nao_vao_para_o_banco():
    # a tabela connectors do banco nao e usada pelo backend; eles ficam no YAML
    yaml_import.run()
    with _base.sessao() as db:
        assert db.query(models.Connector).count() == 0
    assert len(_base.connectors().list_connectors()) == 2


def test_backup_antes_e_yaml_intacto(isolado):
    projects.create_project("existente")     # o banco ja tem dado: o backup precisa conte-lo
    antes = _hash(isolado / "quantum_admin" / "settings")
    r = yaml_import.run()
    assert r["backup"]
    copia = create_engine(f"sqlite:///{r['backup']}")
    with copia.connect() as conexao:
        nomes = [linha[0] for linha in conexao.exec_driver_sql("select name from projects")]
    copia.dispose()
    assert nomes == ["existente"]
    assert _hash(isolado / "quantum_admin" / "settings") == antes


def test_idempotente():
    yaml_import.run()
    segunda = yaml_import.run()
    assert segunda["backup"] is None and segunda["projects"] == []
    assert len(projects.list_projects()) == 2
