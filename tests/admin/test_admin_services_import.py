"""admin.import.*: os YAML antigos das telas .q entram no banco sem perder nada."""

import hashlib

import pytest
import yaml
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantum_admin.backend import database, models
from quantum_admin.backend.secret_manager import SecretManager
from quantum_admin.services import _base
from quantum_admin.services import projects, yaml_import

PROJETOS = [
    {"id": "uuid-blog", "name": "blog", "description": "o blog", "status": "active",
     "source_path": "projects/blog", "created_at": "2026-01-02T03:04:05", "updated_at": "2026-02-03T04:05:06",
     "config": {"port": 8081}, "environments": []},
    {"id": "uuid-rag", "name": "quantum-rag", "description": "", "status": "archived",
     "source_path": "projects\\quantum-rag", "created_at": "2026-01-01T00:00:00"},
]


def connectors(token_estrangeiro):
    return [
        {"id": "c-redis", "name": "cache", "type": "cache", "provider": "redis", "host": "localhost",
         "port": 6379, "password": "", "options": {"db": 0}, "scope": "public"},
        {"id": "c-pg", "name": "pg do blog", "type": "database", "provider": "postgres", "port": 5432,
         "password": "segredo-em-texto-puro", "scope": "application", "application_id": "uuid-blog"},
        {"id": "c-mq", "name": "fila", "type": "mq", "provider": "rabbitmq", "password": token_estrangeiro},
    ]


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'admin.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    monkeypatch.setattr(_base, "_iniciado", False)
    monkeypatch.setenv("QUANTUM_ADMIN_ROOT", str(tmp_path))
    pasta = tmp_path / "quantum_admin" / "settings"
    pasta.mkdir(parents=True)
    estrangeiro = Fernet(Fernet.generate_key()).encrypt(b"outra-chave").decode()
    (pasta / "projects.yaml").write_text(yaml.safe_dump(PROJETOS), encoding="utf-8")
    (pasta / "connectors.yaml").write_text(yaml.safe_dump(connectors(estrangeiro)), encoding="utf-8")
    yield tmp_path
    engine.dispose()


def _hash(pasta):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(pasta.glob("*.yaml"))}


def test_pendente_lista_o_que_falta():
    projects.create_project("blog")          # ja existe no banco (outra caixa nao importa)
    assert yaml_import.pending() == {"projects": ["quantum-rag"], "connectors": ["cache", "pg do blog", "fila"]}


def test_importa_preservando_campos_e_dono(isolado):
    r = yaml_import.run()
    assert r["projects"] == ["blog", "quantum-rag"]
    assert r["connectors"] == ["cache", "pg do blog", "fila"]
    with _base.sessao() as db:
        blog = db.query(models.Project).filter_by(name="blog").one()
        rag = db.query(models.Project).filter_by(name="quantum-rag").one()
        assert (blog.description, blog.created_at.isoformat(), rag.status, rag.source_path) == \
            ("o blog", "2026-01-02T03:04:05", "archived", "projects/quantum-rag")
        pg = db.query(models.Connector).filter_by(id="c-pg").one()
        assert pg.owner_project_id == blog.id and pg.visibility == "private"
        assert db.query(models.Connector).filter_by(id="c-redis").one().options_json == '{"db": 0}'


def test_senha_em_texto_puro_e_cifrada_e_nunca_devolvida(isolado):
    r = yaml_import.run()
    assert "segredo-em-texto-puro" not in str(r)
    with _base.sessao() as db:
        cifrada = db.query(models.Connector).filter_by(id="c-pg").one().password_encrypted
    assert cifrada != "segredo-em-texto-puro"
    assert SecretManager().decrypt(cifrada) == "segredo-em-texto-puro"


def test_senha_cifrada_com_outra_chave_e_mantida_e_avisada():
    r = yaml_import.run()
    assert any("fila" in n and "cannot open" in n for n in r["notes"])


def test_backup_antes_e_yaml_intacto(isolado):
    projects.create_project("existente")     # o banco ja tem dado: o backup precisa conte-lo
    antes = _hash(isolado / "quantum_admin" / "settings")
    r = yaml_import.run()
    assert r["backup"] and (isolado / "quantum_admin" / "backups").is_dir()
    copia = create_engine(f"sqlite:///{r['backup']}")
    with copia.connect() as conexao:
        nomes = [linha[0] for linha in conexao.exec_driver_sql("select name from projects")]
    copia.dispose()
    assert nomes == ["existente"]
    assert _hash(isolado / "quantum_admin" / "settings") == antes


def test_idempotente():
    yaml_import.run()
    segunda = yaml_import.run()
    assert segunda == {"backup": None, "projects": [], "connectors": [], "notes": []}
    assert len(projects.list_projects()) == 2
