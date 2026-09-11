"""Serviços das telas de leitura do repositório.

admin.dashboard.stats    dashboard.q
admin.features.list      features.q
admin.agents.list        agents.q
admin.source.read        source.q
admin.databases.list     database.q
admin.jobs.list          jobs.q

Tudo só lê. O que as telas tinham de errado e mudou:
  - dashboard.q e features.q procuravam src/core/features, src/core/parsers
    e src/runtime/executors — pastas que não existem desde a troca de src/
    para quantum/. O dashboard mostrava 0 features, 0 parsers e 0 executores,
    e a tela de features vinha vazia. Agora lêem quantum/core/features e os
    registros reais;
  - source.q mostrava qualquer arquivo da raiz — .env, chaves, os YAML de
    settings com as credenciais dos connectors. Agora esses são recusados, e
    a checagem de caminho não aceita mais a pasta vizinha com o mesmo prefixo;
  - database.q abria cada .db com sqlite3.connect normal (modo escrita, com
    journal e trava, inclusive em bancos de aplicações rodando). Agora abre em
    modo somente leitura.
"""

import datetime
import re
import sqlite3
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import raiz

PULAR = {".git", "__pycache__", "node_modules", ".venv", "venv", ".claude", "build", "dist"}
TIPOS = {".q": "Quantum", ".py": "Python", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".html": "HTML",
         ".css": "CSS", ".js": "JavaScript", ".md": "Markdown", ".txt": "Text"}
ESTADOS_DE_JOB = ("pending", "running", "completed", "failed")
SENSIVEIS_NOMES = re.compile(r"(^\.env(\..*)?$|\.pem$|\.key$|^id_(rsa|ed25519|ecdsa)|\.db$|\.sqlite3?$)", re.I)


class RepositoryError(ValueError):
    """Pedido inválido para as telas de leitura."""


def _arquivos(pasta: Path, padrao: str):
    if not pasta.is_dir():
        return []
    return [p for p in sorted(pasta.rglob(padrao)) if not PULAR.intersection(p.relative_to(pasta).parts)]


def _tamanho(n: int) -> str:
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    return f"{n / 1024:.1f} KB" if n >= 1024 else f"{n} B"


def _registros():
    from quantum.core.parser import QuantumParser
    from quantum.runtime.component import ComponentRuntime
    parser = QuantumParser()
    registro = parser._parser_registry
    tags = sum(1 for tag in registro.registered_tags
               if type(registro.get_parser(tag)).__name__ != "HTMLParser")
    return tags, ComponentRuntime(config={})._executor_registry.executor_count


def _config_da_raiz() -> dict:
    """quantum.config.yaml da raiz, ou {} se não houver ou não abrir."""
    try:
        return yaml.safe_load((raiz() / "quantum.config.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _pasta_de_features():
    import quantum
    return Path(quantum.__file__).resolve().parent / "core" / "features"


@service("admin.dashboard.stats")
def dashboard_stats():
    base = raiz()
    componentes = [p.relative_to(base / "components").as_posix() for p in _arquivos(base / "components", "*.q")]
    tags, executores = _registros()
    return {
        "components": len(componentes), "component_list": componentes,
        "features": len(list_features()["features"]),
        "tests": len(_arquivos(base / "tests", "test_*.py")),
        "parser_tags": tags, "executors": executores,
        "examples": len(_arquivos(base / "examples", "*.q")),
    }


@service("admin.features.list")
def list_features():
    """Features de quantum/core/features, pelo manifest.yaml de cada uma."""
    features = []
    base = raiz()
    for manifesto in sorted(_pasta_de_features().glob("*/manifest.yaml")):
        pasta = manifesto.parent.name
        # Só dá para abrir no leitor de código quando o pacote está dentro da raiz.
        fonte = manifesto.relative_to(base).as_posix() if base in manifesto.parents else None
        try:
            dados = yaml.safe_load(manifesto.read_text(encoding="utf-8")) or {}
            feature = dados.get("feature") or {}
            descricao = dados.get("description")
            curta = descricao.get("short") if isinstance(descricao, dict) else (descricao or "").strip().split("\n")[0]
            features.append({"name": feature.get("name", pasta), "display_name": feature.get("display_name", pasta),
                             "version": feature.get("version"), "status": feature.get("status", "unknown"),
                             "category": feature.get("category"), "short_desc": curta or "", "source": fonte})
        except (OSError, yaml.YAMLError, AttributeError) as exc:
            features.append({"name": pasta, "display_name": pasta, "version": None, "status": "error",
                             "category": None, "short_desc": f"manifest could not be read: {exc}", "source": fonte})
    contagem = {}
    for f in features:
        contagem[f["status"]] = contagem.get(f["status"], 0) + 1
    ativas, planejadas = contagem.get("active", 0), contagem.get("planned", 0)
    return {"features": features, "by_status": contagem,
            "summary": {"active": ativas, "planned": planejadas, "other": len(features) - ativas - planejadas}}


@service("admin.agents.list")
def list_agents():
    """q:agent e q:team declarados em components/, examples/ e projects/."""
    base = raiz()
    atributos = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
    agentes, times = [], []
    for pasta in ("components", "examples", "projects"):
        for arquivo in _arquivos(base / pasta, "*.q"):
            texto = arquivo.read_text(encoding="utf-8", errors="ignore")
            origem = arquivo.relative_to(base).as_posix()
            for m in re.finditer(r"<q:agent\s+([^>]*?)/?>", texto, re.S):
                a = dict(atributos.findall(m.group(1)))
                agentes.append({"name": a.get("name"), "model": a.get("model"),
                                "provider": a.get("provider"), "source": origem})
            for m in re.finditer(r"<q:team\s+([^>]*?)/?>", texto, re.S):
                a = dict(atributos.findall(m.group(1)))
                times.append({"name": a.get("name"), "supervisor": a.get("supervisor"), "source": origem})
    llm = _config_da_raiz().get("llm")
    return {"agents": agentes, "teams": times,
            "sources": sorted({a["source"] for a in agentes} | {t["source"] for t in times}),
            "providers": sorted({a["provider"] for a in agentes if a["provider"]}),
            # Só estes três campos: a seção llm pode ter api_key.
            "llm": {"base_url": llm.get("base_url"), "default_model": llm.get("default_model"),
                    "timeout": llm.get("timeout", 60)} if isinstance(llm, dict) else None}


@service("admin.source.read")
def read_source(path: str):
    relativo = (path or "").strip().replace("\\", "/")
    if not relativo:
        raise RepositoryError("a file path is required")
    base = raiz()
    arquivo = (base / relativo).resolve()
    if base not in arquivo.parents:
        raise RepositoryError(f"{relativo!r} is outside the project root")
    partes = arquivo.relative_to(base).parts
    if SENSIVEIS_NOMES.search(arquivo.name) or partes[:2] == ("quantum_admin", "settings"):
        raise RepositoryError(f"{relativo} may contain credentials and is not shown here")
    if not arquivo.is_file():
        raise RepositoryError(f"file not found: {relativo}")
    conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
    estado = arquivo.stat()
    return {"path": arquivo.relative_to(base).as_posix(), "type": TIPOS.get(arquivo.suffix.lower(), "Unknown"),
            "size": _tamanho(estado.st_size), "lines": conteudo.count("\n") + 1, "content": conteudo,
            "modified": datetime.datetime.fromtimestamp(estado.st_mtime).strftime("%Y-%m-%d %H:%M")}


@service("admin.databases.list")
def list_databases():
    """Arquivos .db da raiz, abertos SOMENTE LEITURA, com tabelas e linhas."""
    base = raiz()
    bancos = []
    for arquivo in _arquivos(base, "*.db"):
        tabelas, erro = [], None
        try:
            conexao = sqlite3.connect(f"{arquivo.resolve().as_uri()}?mode=ro", uri=True, timeout=2)
            try:
                for (nome,) in conexao.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
                    try:
                        linhas = conexao.execute(f'SELECT COUNT(*) FROM "{nome}"').fetchone()[0]
                    except sqlite3.DatabaseError:
                        linhas = None
                    tabelas.append({"name": nome, "rows": linhas})
            finally:
                conexao.close()
        except sqlite3.DatabaseError as exc:
            erro = str(exc)
        estado = arquivo.stat()
        bancos.append({"path": arquivo.relative_to(base).as_posix(), "size": _tamanho(estado.st_size),
                       "modified": datetime.datetime.fromtimestamp(estado.st_mtime).strftime("%Y-%m-%d %H:%M"),
                       "tables": tabelas, "error": erro})
    fontes = _config_da_raiz().get("datasources") or {}
    # Nome, driver e banco — host, usuário e senha ficam de fora.
    declaradas = [{"name": nome, "driver": (cfg or {}).get("driver") or (cfg or {}).get("type"),
                   "database": (cfg or {}).get("database")} for nome, cfg in sorted(fontes.items())
                  if isinstance(cfg, dict)] if isinstance(fontes, dict) else []
    return {"databases": bancos, "total_tables": sum(len(b["tables"]) for b in bancos), "datasources": declaradas}


@service("admin.jobs.list")
def list_jobs(limit: int = 50):
    """Fila de q:job (quantum_jobs.db na raiz), somente leitura."""
    arquivo = raiz() / "quantum_jobs.db"
    # Os quatro estados da fila sempre presentes, para a tela não testar chave.
    vazio = {"found": False, "counts": dict.fromkeys(ESTADOS_DE_JOB, 0), "total": 0, "jobs": []}
    if not arquivo.is_file():
        return vazio
    try:
        conexao = sqlite3.connect(f"{arquivo.resolve().as_uri()}?mode=ro", uri=True, timeout=2)
        conexao.row_factory = sqlite3.Row
        try:
            contagem = dict.fromkeys(ESTADOS_DE_JOB, 0)
            contagem.update({r["status"]: r["cnt"] for r in
                        conexao.execute("SELECT status, COUNT(*) AS cnt FROM quantum_jobs GROUP BY status")})
            jobs = [dict(r) for r in conexao.execute(
                "SELECT id, name, queue, status, attempts, max_attempts, created_at, error "
                "FROM quantum_jobs ORDER BY id DESC LIMIT ?", (int(limit),))]
        finally:
            conexao.close()
    except sqlite3.DatabaseError as exc:
        return {**vazio, "found": True, "error": str(exc)}
    return {"found": True, "counts": contagem, "total": sum(contagem.values()), "jobs": jobs}
