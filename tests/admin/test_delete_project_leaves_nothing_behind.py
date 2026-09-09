"""Apagar um projeto quebrava, ou deixava lixo apontando para ele.

`Project` declarava `cascade="all, delete-orphan"` para TRES relacoes —
datasources, components, endpoints — e dezenove tabelas tem uma FK para
`projects.id`. As dezesseis restantes nao tinham relacao nenhuma, entao
`db.delete(project)` nao as tocava:

  * as oito com `project_id` NOT NULL violavam a chave estrangeira. Com o
    SQLite enforcando FKs isso e IntegrityError, ou seja HTTP 500 ao apagar
    qualquer projeto que ja tenha sido usado; sem enforcar (o padrao do
    SQLite) as linhas ficavam apontando para um projeto inexistente.
  * as oito NULL-aveis ficavam orfas, e `secrets`/`port_allocations`
    seguravam recursos de um projeto que ninguem mais consegue ver.

Estes testes rodam com `PRAGMA foreign_keys=ON`, que e onde o defeito e um
erro em vez de uma corrupcao silenciosa.
"""

import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, event                    # noqa: E402
from sqlalchemy.orm import sessionmaker                        # noqa: E402

from backend import crud, models                               # noqa: E402


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin.db'}")

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    models.Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()


def _com_filhos(db):
    """Um projeto com uma linha em cada tabela filha que a politica conhece."""
    projeto = models.Project(name="app", description="x")
    db.add(projeto)
    db.commit()

    criadas = {}
    for modelo, coluna, _acao in crud._project_child_tables():
        linha = modelo()
        setattr(linha, coluna, projeto.id)
        # Preenche as colunas NOT NULL que nao tem default, para a linha
        # existir de verdade.
        for col in modelo.__table__.columns:
            if col.name == coluna:
                continue
            tipo = col.type.python_type if hasattr(col.type, 'python_type') \
                else str
            if col.primary_key:
                # PK inteira e autoincremento; PK de texto (Connector.id)
                # precisa de valor.
                if tipo is not int and col.default is None:
                    setattr(linha, col.name, f"{modelo.__name__}-1")
                continue
            if col.nullable or col.default is not None or col.server_default:
                continue
            if tipo is int:
                valor = 1
            elif tipo is float:
                valor = 1.0
            elif tipo is bool:
                valor = False
            else:
                valor = "x"
            setattr(linha, col.name, valor)
        db.add(linha)
        criadas[modelo.__name__] = (modelo, coluna, _acao)
    db.commit()
    return projeto, criadas


class TestTodaTabelaFilhaTemPolitica:
    def test_a_introspeccao_cobre_todas_as_fks_para_projects(self):
        """Nenhuma tabela com project_id fica de fora sem alguem decidir."""
        cobertas = {m.__name__ for m, _c, _a in crud._project_child_tables()}
        # 19 tabelas apontam para projects.id.
        assert len(cobertas) == 19, sorted(cobertas)

    def test_uma_tabela_sem_politica_e_erro_e_nao_silencio(self, monkeypatch):
        politica = dict(crud._PROJECT_CHILD_POLICY)
        politica.pop('TestRun')
        monkeypatch.setattr(crud, '_PROJECT_CHILD_POLICY', politica)
        with pytest.raises(RuntimeError, match="TestRun"):
            crud._project_child_tables()


class TestApagarUmProjetoUsado:
    def test_nao_levanta_com_as_fks_enforcadas(self, db):
        projeto, _ = _com_filhos(db)
        assert crud.delete_project(db, projeto.id) is True
        assert crud.get_project(db, projeto.id) is None

    def test_as_filhas_not_null_somem(self, db):
        projeto, criadas = _com_filhos(db)
        pid = projeto.id
        crud.delete_project(db, pid)

        for nome, (modelo, coluna, acao) in criadas.items():
            if acao != 'delete':
                continue
            restantes = db.query(modelo).filter(
                getattr(modelo, coluna) == pid).count()
            assert restantes == 0, f"{nome} ficou com {restantes} orfas"

    def test_o_historico_fica_sem_dono_e_nao_apagado(self, db):
        projeto, criadas = _com_filhos(db)
        pid = projeto.id
        crud.delete_project(db, pid)

        for nome, (modelo, coluna, acao) in criadas.items():
            if acao != 'null':
                continue
            assert db.query(modelo).filter(
                getattr(modelo, coluna) == pid).count() == 0, nome
            # A linha continua existindo — so perdeu o dono.
            assert db.query(modelo).count() >= 1, f"{nome} foi apagada"

    def test_o_log_de_auditoria_sobrevive(self, db):
        """Apagar o audit_log ao apagar o projeto apagaria o registro de que
        o projeto foi apagado."""
        projeto, _ = _com_filhos(db)
        pid = projeto.id
        antes = db.query(models.AuditLog).count()
        crud.delete_project(db, pid)
        assert db.query(models.AuditLog).count() == antes

    def test_um_secret_nao_vira_global(self, db):
        """project_id=NULL num secret o tornaria visivel a outros projetos."""
        projeto, _ = _com_filhos(db)
        pid = projeto.id
        crud.delete_project(db, pid)
        assert db.query(models.Secret).filter(
            models.Secret.project_id.is_(None)).count() == 0

    def test_a_porta_alocada_e_liberada(self, db):
        projeto, _ = _com_filhos(db)
        crud.delete_project(db, projeto.id)
        assert db.query(models.PortAllocation).count() == 0

    def test_um_projeto_inexistente_continua_devolvendo_false(self, db):
        assert crud.delete_project(db, 99999) is False

    def test_outro_projeto_nao_e_afetado(self, db):
        projeto, criadas = _com_filhos(db)
        outro = models.Project(name="outro")
        db.add(outro)
        db.commit()
        modelo, coluna, _a = criadas['Datasource']
        preservada = modelo(name="d", type="sqlite", connection_type="local")
        setattr(preservada, coluna, outro.id)
        db.add(preservada)
        db.commit()

        crud.delete_project(db, projeto.id)

        assert crud.get_project(db, outro.id) is not None
        assert db.query(models.Datasource).filter(
            models.Datasource.project_id == outro.id).count() == 1
