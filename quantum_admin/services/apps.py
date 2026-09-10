"""Serviços da tela de uma aplicação (components/admin/app/[name].q).

admin.projects.update / config / save_config
admin.environments.list / create / update / delete / create_defaults
admin.servers.status / start / stop / log

O que a tela fazia e estava quebrado, e mudou:
  - "iniciar servidor" rodava src/cli/runner.py, que não existe desde a troca
    de src/ para quantum/: o processo morria na hora, o PID era gravado e o
    botão não fazia nada. Agora roda `python -m quantum.cli.runner start` na
    pasta do projeto;
  - "parar" no Windows usava taskkill /F sem /T: o filho do reloader
    sobrevivia e seguia servindo. Agora usa quantum.cli.server_process.stop_server
    com o .quantum.pid que o próprio servidor grava (pai e filho);
  - salvar a config gravava qualquer caminho e engolia erro de escrita.
    Agora o caminho fica dentro da raiz, o YAML precisa ser um mapeamento e a
    gravação é atômica;
  - ambientes ficavam embutidos no projects.yaml; agora são os do
    environment_service do backend (banco), com variáveis, porta e branch.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import connectors, pasta_de_configuracao, raiz, sessao, status_do_processo
from quantum_admin.services.projects import ProjectError, _pasta, get_project

STATUS_VALIDOS = ("active", "archived", "error")


def _projeto(db, project_id):
    from quantum_admin.backend import crud
    projeto = crud.get_project(db, int(project_id))
    if projeto is None:
        raise ProjectError(f"no project with id {project_id}")
    return projeto


# --------------------------------------------------------------------------- projeto

@service("admin.projects.update")
def update_project(project_id: int, name: str = "", description: str = None, status: str = ""):
    from quantum_admin.backend import models
    with sessao() as db:
        projeto = _projeto(db, project_id)
        nome = (name or "").strip()
        if nome and nome.lower() != (projeto.name or "").lower():
            if len(nome) < 2:
                raise ProjectError("the project name needs at least 2 characters")
            if db.query(models.Project).filter(models.Project.name.ilike(nome)).first():
                raise ProjectError(f"a project named {nome!r} already exists")
        if nome:
            projeto.name = nome
        if description is not None:
            projeto.description = description.strip()
        if status:
            if status not in STATUS_VALIDOS:
                raise ProjectError(f"status must be one of {', '.join(STATUS_VALIDOS)}")
            projeto.status = status
    return get_project(project_id)


@service("admin.projects.config")
def project_config(project_id: int):
    """O quantum.config.yaml do projeto, em texto (para o editor) e interpretado."""
    with sessao() as db:
        caminho = _projeto(db, project_id).source_path
    arquivo = _pasta(caminho) / "quantum.config.yaml"
    texto = arquivo.read_text(encoding="utf-8") if arquivo.is_file() else ""
    try:
        interpretado = yaml.safe_load(texto) or {}
        erro = None
    except yaml.YAMLError as exc:
        interpretado, erro = {}, str(exc)
    return {"path": str(arquivo), "exists": arquivo.is_file(), "text": texto,
            "server": (interpretado.get("server") or {}) if isinstance(interpretado, dict) else {},
            "error": erro}


@service("admin.projects.save_config")
def save_project_config(project_id: int, config_yaml: str):
    try:
        interpretado = yaml.safe_load(config_yaml or "")
    except yaml.YAMLError as exc:
        raise ProjectError(f"invalid YAML: {exc}")
    if interpretado is not None and not isinstance(interpretado, dict):
        raise ProjectError("the configuration must be a YAML mapping (key: value)")
    with sessao() as db:
        caminho = _projeto(db, project_id).source_path
    pasta = _pasta(caminho)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "quantum.config.yaml"
    temporario = arquivo.with_name(arquivo.name + ".tmp")
    temporario.write_text(config_yaml or "", encoding="utf-8")
    os.replace(temporario, arquivo)
    return project_config(project_id)


# --------------------------------------------------------------------------- ambientes

def _ambiente_publico(env) -> dict:
    return {"id": env.id, "project_id": env.project_id, "name": env.name, "display_name": env.display_name,
            "order": env.order, "port": env.port, "branch": env.branch, "health_url": env.health_url,
            "requires_approval": bool(env.requires_approval), "is_active": bool(env.is_active),
            "variables": json.loads(env.env_vars_json) if env.env_vars_json else {}}


def _variaveis(texto_ou_dict):
    """'CHAVE=valor' por linha (como o formulário da tela) ou um dict."""
    if isinstance(texto_ou_dict, dict):
        return {str(k): str(v) for k, v in texto_ou_dict.items()}
    variaveis = {}
    for linha in (texto_ou_dict or "").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "=" not in linha:
            raise ProjectError(f"variable line must be NAME=value: {linha!r}")
        chave, valor = linha.split("=", 1)
        variaveis[chave.strip()] = valor.strip()
    return variaveis


def _servico_de_ambientes(db):
    from quantum_admin.backend.environment_service import EnvironmentService
    return EnvironmentService(db=db)


@service("admin.environments.list")
def list_environments(project_id: int):
    with sessao() as db:
        _projeto(db, project_id)
        return [_ambiente_publico(e) for e in _servico_de_ambientes(db).list_environments(int(project_id),
                                                                                         active_only=False)]


@service("admin.environments.create")
def create_environment(project_id: int, name: str, display_name: str = "", port: int = None,
                       branch: str = "main", variables="", health_url: str = ""):
    nome = (name or "").strip().lower()
    if not nome:
        raise ProjectError("environment name is required")
    with sessao() as db:
        _projeto(db, project_id)
        servico = _servico_de_ambientes(db)
        if servico.get_environment_by_name(int(project_id), nome):
            raise ProjectError(f"environment {nome!r} already exists in this project")
        env = servico.create_environment(int(project_id), {
            "name": nome, "display_name": display_name or None, "port": int(port) if port else None,
            "branch": branch or "main", "env_vars": _variaveis(variables), "health_url": health_url or None})
        return _ambiente_publico(env)


@service("admin.environments.update")
def update_environment(environment_id: int, display_name: str = None, port: int = None, branch: str = None,
                       variables=None, health_url: str = None):
    dados = {k: v for k, v in {"display_name": display_name, "branch": branch, "health_url": health_url}.items()
             if v is not None}
    if port not in (None, ""):
        dados["port"] = int(port)
    with sessao() as db:
        servico = _servico_de_ambientes(db)
        env = servico.update_environment(int(environment_id), dados) if dados else servico.get_environment(
            int(environment_id))
        if env is None:
            raise ProjectError(f"no environment with id {environment_id}")
        if variables is not None:
            servico.set_env_vars(int(environment_id), _variaveis(variables))
            env = servico.get_environment(int(environment_id))
        return _ambiente_publico(env)


@service("admin.environments.delete")
def delete_environment(environment_id: int):
    with sessao() as db:
        if not _servico_de_ambientes(db).delete_environment(int(environment_id)):
            raise ProjectError(f"no environment with id {environment_id}")
    return {"deleted": int(environment_id)}


@service("admin.environments.create_defaults")
def create_default_environments(project_id: int):
    with sessao() as db:
        _projeto(db, project_id)
        return [_ambiente_publico(e) for e in _servico_de_ambientes(db).create_default_environments(int(project_id))]


# --------------------------------------------------------------------------- servidor do projeto

def _pasta_do_projeto(project_id):
    with sessao() as db:
        projeto = _projeto(db, project_id)
        nome, caminho = projeto.name, projeto.source_path
    pasta = _pasta(caminho)
    if not (pasta / "quantum.config.yaml").is_file():
        raise ProjectError(f"{caminho}/quantum.config.yaml not found; save a configuration first")
    return nome, pasta


def _log(nome):
    pasta = pasta_de_configuracao() / "logs"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{nome}.log"


@service("admin.servers.status")
def server_status(project_id: int):
    nome, pasta = _pasta_do_projeto(project_id)
    from quantum.cli.server_process import pid_alive, read_pids
    arquivo = pasta / ".quantum.pid"
    try:
        vivos = [p for p in read_pids(arquivo) if pid_alive(p)]
    except (OSError, ValueError):
        vivos = []
    processo = status_do_processo(nome)
    return {"running": bool(vivos) or processo["running"], "pids": vivos or ([processo["pid"]] if processo["pid"] else [])}


@service("admin.servers.start")
def start_server(project_id: int, port: int = None, wait: float = 15.0):
    """Sobe `quantum start` na pasta do projeto e espera o arquivo de PID aparecer."""
    nome, pasta = _pasta_do_projeto(project_id)
    if server_status(project_id)["running"]:
        raise ProjectError(f"{nome} is already running")
    comando = [sys.executable, "-m", "quantum.cli.runner", "start", "--config", "quantum.config.yaml"]
    if port:
        comando += ["--port", str(int(port))]
    import quantum
    ambiente = dict(os.environ)
    pacote = str(Path(quantum.__file__).resolve().parents[1])
    ambiente["PYTHONPATH"] = os.pathsep.join(p for p in (pacote, ambiente.get("PYTHONPATH")) if p)
    log = open(_log(nome), "a", encoding="utf-8")
    opcoes = {"stdout": log, "stderr": subprocess.STDOUT, "cwd": str(pasta), "env": ambiente}
    if os.name == "nt":
        opcoes["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    processo = subprocess.Popen(comando, **opcoes)
    log.close()
    pids = pasta_de_configuracao() / "pids"
    pids.mkdir(parents=True, exist_ok=True)
    (pids / f"{nome}.pid").write_text(str(processo.pid), encoding="utf-8")

    limite = time.time() + float(wait)
    while time.time() < limite:
        if processo.poll() is not None:
            raise ProjectError(f"{nome} exited with code {processo.returncode}; see the log: "
                               f"{server_log(project_id, 20)['text']}")
        if (pasta / ".quantum.pid").is_file():
            return server_status(project_id)
        time.sleep(0.2)
    return server_status(project_id)


@service("admin.servers.stop")
def stop_server(project_id: int):
    nome, pasta = _pasta_do_projeto(project_id)
    from quantum.cli import server_process
    arquivo = pasta / ".quantum.pid"
    if arquivo.is_file():
        server_process.stop_server(arquivo)
    else:
        processo = status_do_processo(nome)
        if processo["running"]:
            server_process._terminate(processo["pid"], True)
    (pasta_de_configuracao() / "pids" / f"{nome}.pid").unlink(missing_ok=True)
    return server_status(project_id)


@service("admin.servers.log")
def server_log(project_id: int, lines: int = 50):
    with sessao() as db:
        nome = _projeto(db, project_id).name
    arquivo = _log(nome)
    texto = arquivo.read_text(encoding="utf-8", errors="replace") if arquivo.is_file() else ""
    return {"text": "".join(texto.splitlines(keepends=True)[-int(lines):])}
