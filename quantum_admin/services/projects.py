"""Serviços da área Projetos (admin.projects.*).

Portados de components/admin/applications.q, que fazia tudo em q:python sobre
quantum_admin/settings/projects.yaml. Os comportamentos preservados:

  - criar exige nome único (sem diferenciar maiúsculas) e cria a pasta do
    projeto com components/, static/ e um quantum.config.yaml padrão, sem
    sobrescrever um que já exista;
  - sincronizar registra cada pasta de projects/ que ainda não é projeto,
    ignorando as que começam com "." ou "_";
  - remover apaga só o registro, nunca os arquivos;
  - a listagem mostra estado do processo, porta, se há config, quantos
    componentes .q e quantos connectors o projeto tem.

O que mudou de propósito:
  - os dados vão para o banco do admin (o mesmo do FastAPI), não para o YAML;
  - nome inválido ou repetido é erro — a tela antiga ignorava em silêncio e
    redirecionava como se tivesse criado;
  - o caminho do projeto não pode sair da raiz (a tela aceitava qualquer um);
  - o config padrão escuta em 127.0.0.1 sem debug (era 0.0.0.0 com debug).
"""

import datetime
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import connectors, raiz, sessao, status_do_processo

CONFIG_PADRAO = {
    "server": {"port": 8080, "host": "127.0.0.1", "debug": False},
    "paths": {"components": "./components", "static": "./static"},
}


class ProjectError(ValueError):
    """Pedido inválido para a área Projetos (a mensagem é para quem usa a tela)."""


def _crud():
    from quantum_admin.backend import crud, models
    return crud, models


def _pasta(source_path: str) -> Path:
    base = raiz()
    pasta = (base / (source_path or "")).resolve()
    if pasta != base and base not in pasta.parents:
        raise ProjectError(f"the project path must be inside {base}: {source_path!r}")
    return pasta


def _config_do_disco(pasta: Path) -> dict:
    arquivo = pasta / "quantum.config.yaml"
    if not arquivo.is_file():
        return {}
    try:
        return yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _iso(valor):
    return valor.isoformat(timespec="seconds") if isinstance(valor, datetime.datetime) else valor


def _registro(projeto, models, db) -> dict:
    pasta = _pasta(projeto.source_path) if projeto.source_path else None
    servidor = (_config_do_disco(pasta).get("server") or {}) if pasta else {}
    componentes = sum(1 for _ in (pasta / "components").rglob("*.q")) \
        if pasta and (pasta / "components").is_dir() else 0
    processo = status_do_processo(projeto.name)
    try:
        modificado = datetime.datetime.fromtimestamp(pasta.stat().st_mtime).strftime("%Y-%m-%d %H:%M") \
            if pasta and pasta.is_dir() else None
    except OSError:
        modificado = None
    # Connectors vivem em settings/connectors.yaml (connector_service); a
    # tabela `connectors` do banco não é usada por nada no backend.
    do_projeto = len(connectors().list_connectors(application_id=projeto.id, include_public=False))
    return {
        "id": projeto.id,
        "name": projeto.name,
        "description": projeto.description or "",
        "status": projeto.status or "active",
        "source_path": projeto.source_path or "",
        "created_at": _iso(projeto.created_at),
        "updated_at": _iso(projeto.updated_at),
        "running": processo["running"],
        "pid": processo["pid"],
        "port": servidor.get("port"),
        "debug": servidor.get("debug"),
        "has_config": bool(pasta and (pasta / "quantum.config.yaml").is_file()),
        "component_count": componentes,
        "connector_count": do_projeto,
        "last_modified": modificado,
        "initial": (projeto.name or "?")[0].upper(),
    }


@service("admin.projects.list")
def list_projects(search: str = ""):
    """Projetos em ordem de nome; `search` filtra por nome ou descrição."""
    crud, models = _crud()
    termo = (search or "").strip().lower()
    with sessao() as db:
        projetos = db.query(models.Project).order_by(models.Project.name).all()
        return [_registro(p, models, db) for p in projetos
                if not termo or termo in (p.name or "").lower() or termo in (p.description or "").lower()]


@service("admin.projects.summary")
def summary():
    """Totais do cabeçalho da tela de aplicações."""
    projetos = list_projects()
    return {
        "total": len(projetos),
        "active": sum(1 for p in projetos if p["status"] == "active"),
        "running": sum(1 for p in projetos if p["running"]),
        "with_config": sum(1 for p in projetos if p["has_config"]),
        "connectors": len(connectors().list_connectors()),
    }


@service("admin.projects.get")
def get_project(project_id: int):
    crud, models = _crud()
    with sessao() as db:
        projeto = crud.get_project(db, int(project_id))
        if projeto is None:
            raise ProjectError(f"no project with id {project_id}")
        return _registro(projeto, models, db)


@service("admin.projects.create")
def create_project(name: str, description: str = "", source_path: str = ""):
    """Registra o projeto e cria a pasta dele (sem sobrescrever o que existe)."""
    crud, models = _crud()
    nome = (name or "").strip()
    if len(nome) < 2:
        raise ProjectError("the project name needs at least 2 characters")
    caminho = (source_path or "").strip() or f"projects/{nome}"
    pasta = _pasta(caminho)
    with sessao() as db:
        repetido = db.query(models.Project).filter(models.Project.name.ilike(nome)).first()
        if repetido is not None:
            raise ProjectError(f"a project named {repetido.name!r} already exists")
        (pasta / "components").mkdir(parents=True, exist_ok=True)
        (pasta / "static").mkdir(parents=True, exist_ok=True)
        config = pasta / "quantum.config.yaml"
        if not config.is_file():
            config.write_text(yaml.safe_dump(CONFIG_PADRAO, sort_keys=False), encoding="utf-8")
        projeto = models.Project(name=nome, description=(description or "").strip(),
                                 status="active", source_path=caminho.replace("\\", "/"))
        db.add(projeto)
        db.flush()
        return _registro(projeto, models, db)


@service("admin.projects.delete")
def delete_project(project_id: int):
    """Remove o registro (e o que pertence a ele no banco). Os arquivos ficam."""
    crud, _ = _crud()
    with sessao() as db:
        if not crud.delete_project(db, int(project_id)):
            raise ProjectError(f"no project with id {project_id}")
    return {"deleted": int(project_id)}


@service("admin.projects.sync")
def sync_projects():
    """Registra as pastas de <raiz>/projects que ainda não são projetos."""
    _, models = _crud()
    pasta_projetos = raiz() / "projects"
    criados = []
    with sessao() as db:
        caminhos = {p.source_path for p in db.query(models.Project).all()}
        nomes = {(p.name or "").lower() for p in db.query(models.Project).all()}
        if pasta_projetos.is_dir():
            for pasta in sorted(pasta_projetos.iterdir()):
                if not pasta.is_dir() or pasta.name.startswith((".", "_")):
                    continue
                caminho = f"projects/{pasta.name}"
                if caminho in caminhos or pasta.name.lower() in nomes:
                    continue
                db.add(models.Project(name=pasta.name, description="", status="active", source_path=caminho))
                criados.append(pasta.name)
    return {"created": criados, "total": len(list_projects())}
