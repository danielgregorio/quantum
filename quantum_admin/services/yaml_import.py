"""Importa os YAML antigos das telas .q para o banco do admin (admin.import.*).

As telas .q gravavam projetos e connectors em quantum_admin/settings/*.yaml;
o FastAPI, no banco. Medido em 2026-09-10: nenhum projeto em comum — os reais
estavam no YAML, e o banco só tinha os três projetos de demonstração do
seed_db. Os serviços do admin usam o banco; esta importação traz o YAML para lá.

Garantias (os dados são do dono, não são recriáveis):
  - antes de gravar, copia o arquivo do banco para quantum_admin/backups/;
  - nunca altera nem apaga os YAML;
  - idempotente: projeto já existente (mesmo nome, sem diferenciar
    maiúsculas) e connector já existente (mesmo id) são pulados;
  - senha em texto puro é cifrada com o secret_manager; senha já cifrada é
    mantida como está, e o relatório diz se a chave atual consegue abri-la;
  - nenhum valor de senha aparece no retorno.
"""

import datetime
import json
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
    """O que os YAML têm e o banco ainda não (nomes e ids, sem segredos)."""
    models = _models()
    projetos, connectors = _ler_yaml("projects.yaml"), _ler_yaml("connectors.yaml")
    with sessao() as db:
        nomes = {(p.name or "").lower() for p in db.query(models.Project).all()}
        ids = {c.id for c in db.query(models.Connector).all()}
    return {
        "projects": [p.get("name") for p in projetos if p.get("name") and p["name"].lower() not in nomes],
        "connectors": [c.get("name") for c in connectors if c.get("id") and str(c["id"]) not in ids],
    }


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


def _senha(valor):
    """(senha_para_o_banco, observação) — sem nunca devolver o valor."""
    from quantum_admin.backend.secret_manager import SecretManager, encrypt_value
    texto = str(valor or "")
    if not texto:
        return "", None
    if texto.startswith("gAAAA"):
        try:
            SecretManager().decrypt(texto)
            return texto, None
        except ValueError:
            return texto, "password kept encrypted, but the current QUANTUM_ENCRYPTION_KEY cannot open it"
    return encrypt_value(texto), "plain-text password was encrypted"


@service("admin.import.run")
def run():
    """Importa o que falta; devolve o relatório. Não mexe nos YAML."""
    models = _models()
    projetos, connectors = _ler_yaml("projects.yaml"), _ler_yaml("connectors.yaml")
    faltando = pending()
    relatorio = {"backup": None, "projects": [], "connectors": [], "notes": []}
    if not faltando["projects"] and not faltando["connectors"]:
        return relatorio
    relatorio["backup"] = _backup()

    with sessao() as db:
        nomes = {(p.name or "").lower(): p for p in db.query(models.Project).all()}
        id_novo = {}                         # id do projeto no YAML -> id no banco
        for item in projetos:
            nome = (item.get("name") or "").strip()
            if not nome:
                continue
            existente = nomes.get(nome.lower())
            if existente is None:
                existente = models.Project(
                    name=nome, description=item.get("description") or "",
                    status=item.get("status") or "active",
                    source_path=(item.get("source_path") or "").replace("\\", "/"))
                criado, alterado = _data(item.get("created_at")), _data(item.get("updated_at"))
                if criado:
                    existente.created_at = criado
                if alterado:
                    existente.updated_at = alterado
                db.add(existente)
                db.flush()
                nomes[nome.lower()] = existente
                relatorio["projects"].append(nome)
            if item.get("id"):
                id_novo[str(item["id"])] = existente.id

        ids = {c.id for c in db.query(models.Connector).all()}
        for item in connectors:
            cid = str(item.get("id") or "")
            if not cid or cid in ids:
                continue
            senha, nota = _senha(item.get("password"))
            if nota:
                relatorio["notes"].append(f"{item.get('name')}: {nota}")
            dono = id_novo.get(str(item.get("application_id") or "")) if item.get("application_id") else None
            conector = models.Connector(
                id=cid, name=item.get("name") or cid, type=item.get("type") or "",
                provider=item.get("provider") or "", host=item.get("host") or "localhost",
                port=int(item.get("port") or 0), username=item.get("username") or "",
                password_encrypted=senha, database=item.get("database") or "",
                options_json=json.dumps(item.get("options") or {}),
                is_default=bool(item.get("is_default")), docker_auto=bool(item.get("docker_auto")),
                docker_image=item.get("docker_image") or "",
                docker_container_id=item.get("docker_container_id") or "",
                status=item.get("status") or "unknown", last_tested=_data(item.get("last_tested")),
                visibility="private" if item.get("scope") == "application" else "public",
                owner_project_id=dono)
            criado = _data(item.get("created_at"))
            if criado:
                conector.created_at = criado
            db.add(conector)
            relatorio["connectors"].append(item.get("name") or cid)
    return relatorio
