"""Infraestrutura comum dos serviços do admin: sessão do banco, raiz, processos."""

import contextlib
import os
from pathlib import Path

_iniciado = False


def _database():
    from quantum_admin.backend import database
    return database


@contextlib.contextmanager
def sessao():
    """Sessão do banco do admin (o mesmo do FastAPI), com as tabelas criadas.

    commit no fim do bloco, rollback se ele levantar.
    """
    global _iniciado
    database = _database()
    if not _iniciado:
        database.Base.metadata.create_all(bind=database.engine)
        _iniciado = True
    db = database.SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def raiz() -> Path:
    """Pasta a partir da qual os caminhos dos projetos são relativos.

    As telas antigas usavam os.getcwd() — `quantum start` na raiz do
    repositório. QUANTUM_ADMIN_ROOT permite apontar outra.
    """
    return Path(os.environ.get("QUANTUM_ADMIN_ROOT") or os.getcwd()).resolve()


def pasta_de_configuracao() -> Path:
    """quantum_admin/settings, onde ficam PIDs, logs e os YAML antigos."""
    return raiz() / "quantum_admin" / "settings"


def status_do_processo(nome_projeto: str) -> dict:
    """{'running': bool, 'pid': int|None} a partir de settings/pids/<nome>.pid.

    Usa quantum.cli.server_process.pid_alive. A versão das telas (_lib.py)
    chamava OpenProcess no Windows e tomava um handle aberto como processo
    vivo — um processo que já terminou continuava "Running".
    """
    from quantum.cli.server_process import pid_alive
    arquivo = pasta_de_configuracao() / "pids" / f"{nome_projeto}.pid"
    try:
        pid = int(arquivo.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return {"running": False, "pid": None}
    if pid_alive(pid):
        return {"running": True, "pid": pid}
    with contextlib.suppress(OSError):
        arquivo.unlink()
    return {"running": False, "pid": None}
