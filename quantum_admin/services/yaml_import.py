"""Importa os projetos do YAML antigo das telas .q para o banco (admin.import.*).

As telas .q gravavam projetos em quantum_admin/settings/projects.yaml; o
FastAPI (crud), no banco. Medido em 2026-09-10: nenhum projeto em comum — os
14 reais estavam no YAML, e o banco só tinha os três de demonstração do
seed_db. O serviço admin.projects usa o banco; esta importação traz os
projetos para lá.

Connectors NÃO são importados: a biblioteca do backend (connector_service)
os mantém em settings/connectors.yaml, o mesmo arquivo das telas — não há
divisão. A tabela `connectors` do banco não é usada por nada. O que a
importação faz com connectors é só apontar os que estão presos a um projeto
pelo id antigo do YAML (um uuid), que connector_service não reconhece.

Garantias (os dados são do dono, não são recriáveis):
  - antes de gravar, copia o arquivo do banco para quantum_admin/backups/;
  - nunca altera nem apaga os YAML;
  - idempotente: projeto já existente (mesmo nome, sem diferenciar
    maiúsculas) é pulado.
"""

import datetime
import shutil
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import pasta_de_configuracao, raiz, sessao


def _ler_yaml(nome):
    arquivo = pasta_de_configuracao() / nome
    if not arquivo.is_file():
        return []
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or []
    return dados if isinstance(dados, list) else []


def _data(valor):
    if isinstance(valor, datetime.datetime):
        return valor
    try:
        return datetime.datetime.fromisoformat(str(valor).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _models():
    from quantum_admin.backend import models
    return models


@service("admin.import.pending")
def pending():
    """Projetos do YAML que o banco ainda não tem, e connectors presos a ids antigos."""
    models = _models()
    projetos = _ler_yaml("projects.yaml")
    with sessao() as db:
        nomes = {(p.name or "").lower() for p in db.query(models.Project).all()}
    return {
        "projects": [p.get("name") for p in projetos if p.get("name") and p["name"].lower() not in nomes],
        "connectors_to_review": _connectors_com_id_antigo(projetos),
    }


def _connectors_com_id_antigo(projetos):
    ids_yaml = {str(p.get("id")): p.get("name") for p in projetos if p.get("id")}
    revisar = []
    for c in _ler_yaml("connectors.yaml"):
        dono = c.get("application_id")
        if dono is not None and str(dono) in ids_yaml:
            revisar.append(f"{c.get('name')} (project {ids_yaml[str(dono)]})")
    return revisar


def _backup():
    from quantum_admin.backend import database
    arquivo = database.engine.url.database
    if database.engine.url.get_backend_name() != "sqlite" or not arquivo or not Path(arquivo).is_file():
        return None
    destino = raiz() / "quantum_admin" / "backups"
    destino.mkdir(parents=True, exist_ok=True)
    copia = destino / f"quantum_admin-{datetime.datetime.now():%Y%m%d-%H%M%S}.db"
    database.engine.dispose()               # nada pendente em conexões abertas
    shutil.copy2(arquivo, copia)
    return str(copia)


@service("admin.import.run")
def run():
    """Importa os projetos que faltam; devolve o relatório. Não mexe nos YAML."""
    models = _models()
    projetos = _ler_yaml("projects.yaml")
    faltando = pending()
    relatorio = {"backup": None, "projects": [], "connectors_to_review": faltando["connectors_to_review"]}
    if not faltando["projects"]:
        return relatorio
    relatorio["backup"] = _backup()
    with sessao() as db:
        nomes = {(p.name or "").lower() for p in db.query(models.Project).all()}
        for item in projetos:
            nome = (item.get("name") or "").strip()
            if not nome or nome.lower() in nomes:
                continue
            projeto = models.Project(
                name=nome, description=item.get("description") or "",
                status=item.get("status") or "active",
                source_path=(item.get("source_path") or "").replace("\\", "/"))
            criado, alterado = _data(item.get("created_at")), _data(item.get("updated_at"))
            if criado:
                projeto.created_at = criado
            if alterado:
                projeto.updated_at = alterado
            db.add(projeto)
            nomes.add(nome.lower())
            relatorio["projects"].append(nome)
    return relatorio
