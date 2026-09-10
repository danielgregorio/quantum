"""Edita valores de um YAML de configuração preservando comentários e ordem.

components/admin/settings.q regravava quantum.config.yaml com yaml.dump: todo
comentário do arquivo sumia — inclusive os avisos de segurança sobre host e
debug —, e um erro de escrita era engolido. Sem ruamel.yaml no projeto, este
editor cobre o caso do admin: chaves de primeiro nível dentro de uma seção
(`server.port`), valores escalares.

Nunca grava algo diferente do pedido: depois de editar o texto, relê o
resultado com yaml.safe_load e confere que (1) cada chave pedida tem o valor
pedido e (2) todo o resto continua igual. Se não, levanta e o arquivo fica como
estava. A gravação é atômica.
"""

import copy
import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


class YamlEditError(RuntimeError):
    """A edição não produziria exatamente o arquivo pedido; nada foi gravado."""


def _formatar(valor: Any) -> str:
    texto = yaml.safe_dump(valor, default_flow_style=True, allow_unicode=True).strip()
    if texto.endswith("..."):
        texto = texto[:-3].strip()
    return texto


def editar_texto(texto: str, valores: Dict[Tuple[str, str], Any]) -> str:
    linhas = texto.splitlines()
    for (secao, chave), valor in valores.items():
        inicio = next((i for i, l in enumerate(linhas) if re.match(rf"^{re.escape(secao)}\s*:\s*(#.*)?$", l)), None)
        if inicio is None:
            if linhas and linhas[-1].strip():
                linhas.append("")
            linhas.extend([f"{secao}:", f"  {chave}: {_formatar(valor)}"])
            continue
        fim = next((i for i in range(inicio + 1, len(linhas))
                    if linhas[i] and not linhas[i].startswith((" ", "\t", "#"))), len(linhas))
        filhos = [i for i in range(inicio + 1, fim) if re.match(r"^(\s+)[^\s#]", linhas[i])]
        recuo = re.match(r"^(\s+)", linhas[filhos[0]]).group(1) if filhos else "  "
        alvo = next((i for i in filhos if re.match(rf"^{re.escape(recuo)}{re.escape(chave)}\s*:", linhas[i])), None)
        if alvo is None:
            linhas.insert(inicio + 1, f"{recuo}{chave}: {_formatar(valor)}")
            continue
        m = re.match(rf"^({re.escape(recuo)}{re.escape(chave)}\s*:\s*)(.*?)(\s+#.*)?$", linhas[alvo])
        linhas[alvo] = f"{m.group(1)}{_formatar(valor)}{m.group(3) or ''}"
    return "\n".join(linhas) + ("\n" if texto.endswith("\n") or not texto else "")


def gravar_valores(arquivo: Path, valores: Dict[Tuple[str, str], Any]) -> Dict:
    """Aplica `valores` ao arquivo (criando se não existir) e devolve o YAML resultante."""
    arquivo = Path(arquivo)
    original = arquivo.read_text(encoding="utf-8") if arquivo.is_file() else ""
    antes = yaml.safe_load(original) or {}
    if not isinstance(antes, dict):
        raise YamlEditError(f"{arquivo} does not contain a mapping")

    novo_texto = editar_texto(original, valores)
    try:
        depois = yaml.safe_load(novo_texto) or {}
    except yaml.YAMLError as exc:
        raise YamlEditError(f"editing {arquivo} would produce invalid YAML: {exc}") from exc

    esperado = copy.deepcopy(antes)
    for (secao, chave), valor in valores.items():
        if not isinstance(esperado.get(secao), dict):
            esperado[secao] = {}
        esperado[secao][chave] = valor
    if depois != esperado:
        raise YamlEditError(f"editing {arquivo} would change more than was asked; nothing was written")

    temporario = arquivo.with_name(arquivo.name + ".tmp")
    temporario.write_text(novo_texto, encoding="utf-8")
    os.replace(temporario, arquivo)
    return depois
