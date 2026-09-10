"""Serviços das áreas Componentes e Testes (admin.components.*, admin.tests.*).

Portados de components/admin/components.q, tests.q e component/[...path].q.

Preservado: a listagem de componentes (grupo, linhas, tamanho, tags usadas),
a de testes (funções por pasta), rodar o pytest de um arquivo e guardar o
último resultado em settings/last_test_result.json, e gerar um teste a partir
da estrutura do componente (_component_test_generator, cópia do gerador das
telas).

Corrigido:
  - rodar testes aceitava QUALQUER arquivo: a tela só barrava "..", e um
    caminho absoluto passava (os.path.join descarta a base) — pytest, isto é,
    código arbitrário, sobre qualquer .py da máquina, num POST sem login.
    Agora só test_*.py dentro de <raiz>/tests;
  - gerar teste sobrescrevia tests/test_<componente>.py sem avisar, perdendo
    edições feitas à mão. Agora recusa, a menos que overwrite=True;
  - a checagem de caminho da tela de detalhe usava startswith, que aceita uma
    pasta vizinha com o mesmo prefixo (quantum2/). Agora compara caminhos.
"""

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

from quantum.services import service
from quantum_admin.services._base import pasta_de_configuracao, raiz

TIPOS = {".q": "Quantum", ".py": "Python", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
         ".html": "HTML", ".css": "CSS", ".js": "JavaScript"}


class ComponentError(ValueError):
    """Pedido inválido para Componentes/Testes."""


def _dentro(relativo: str, pasta: str = "") -> Path:
    """Caminho relativo à raiz (ou a <raiz>/<pasta>) que não sai de lá."""
    base = (raiz() / pasta).resolve() if pasta else raiz()
    alvo = (raiz() / (relativo or "")).resolve()
    if alvo != base and base not in alvo.parents:
        raise ComponentError(f"{relativo!r} is outside {base}")
    return alvo


def _tamanho(n: int) -> str:
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    return f"{n / 1024:.1f} KB" if n >= 1024 else f"{n} B"


def _tags(conteudo: str):
    return sorted(set(re.findall(r"<q:(\w+)", conteudo)) - {"component", "param"})


def _arquivo_de_teste(comp_path: str) -> str:
    return f"tests/test_{comp_path.replace('/', '_').replace('.q', '')}.py"


@service("admin.components.list")
def list_components():
    pasta = raiz() / "components"
    itens, grupos = [], set()
    for arquivo in sorted(pasta.rglob("*.q")) if pasta.is_dir() else []:
        rel = arquivo.relative_to(pasta).as_posix()
        grupo = arquivo.parent.relative_to(pasta).as_posix()
        grupo = "root" if grupo == "." else grupo
        grupos.add(grupo)
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
        itens.append({"path": rel, "group": grupo, "lines": conteudo.count("\n") + 1,
                      "size": _tamanho(arquivo.stat().st_size), "feature_tags": _tags(conteudo)})
    exemplos = raiz() / "examples"
    return {"components": itens, "directories": len(grupos),
            "examples": sum(1 for _ in exemplos.rglob("*.q")) if exemplos.is_dir() else 0}


@service("admin.components.get")
def get_component(path: str):
    """Detalhe de um arquivo da raiz: tipo, tamanho, actions, queries, tags, teste e último resultado."""
    relativo = (path or "").strip()
    if relativo and not Path(relativo).suffix:
        relativo += ".q"
    arquivo = _dentro(relativo)
    if not arquivo.is_file():
        raise ComponentError(f"file not found: {relativo}")
    conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
    nome = re.search(r'<q:component\s+name="([^"]+)"', conteudo)
    teste = _arquivo_de_teste(relativo)
    arquivo_teste = raiz() / teste
    funcoes = re.findall(r"^\s*def (test_\w+)", arquivo_teste.read_text(encoding="utf-8", errors="ignore"),
                         re.M) if arquivo_teste.is_file() else []
    return {
        "path": relativo,
        "name": nome.group(1) if nome else arquivo.stem,
        "type": TIPOS.get(arquivo.suffix.lower(), "Unknown"),
        "size": _tamanho(arquivo.stat().st_size),
        "lines": conteudo.count("\n") + 1,
        "modified": datetime.datetime.fromtimestamp(arquivo.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        "actions": re.findall(r'<q:action\s+name="([^"]+)"', conteudo),
        "queries": re.findall(r'<q:query\s+name="([^"]+)"', conteudo),
        "feature_tags": _tags(conteudo),
        "test_file": teste if arquivo_teste.is_file() else None,
        "test_functions": funcoes,
        "last_run": _ultimo_resultado(teste),
    }


@service("admin.tests.list")
def list_tests():
    pasta = raiz() / "tests"
    arquivos, grupos = [], {}
    for arquivo in sorted(pasta.rglob("test_*.py")) if pasta.is_dir() else []:
        grupo = arquivo.parent.relative_to(pasta).as_posix()
        grupo = "root" if grupo == "." else grupo
        funcoes = len(re.findall(r"^\s*def test_", arquivo.read_text(encoding="utf-8", errors="ignore"), re.M))
        arquivos.append({"path": arquivo.relative_to(pasta).as_posix(), "directory": grupo, "functions": funcoes})
        g = grupos.setdefault(grupo, {"name": grupo, "files": 0, "functions": 0})
        g["files"] += 1
        g["functions"] += funcoes
    return {"files": arquivos, "directories": [grupos[k] for k in sorted(grupos)],
            "total_functions": sum(a["functions"] for a in arquivos)}


def _ultimo_resultado(test_file: str = None):
    arquivo = pasta_de_configuracao() / "last_test_result.json"
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dados if not test_file or dados.get("test_file") == test_file else None


@service("admin.tests.run")
def run_tests(test_file: str, timeout: int = 120):
    """pytest num test_*.py de <raiz>/tests; guarda e devolve o resultado."""
    relativo = (test_file or "").strip().replace("\\", "/")
    arquivo = _dentro(relativo, "tests")
    if not (arquivo.is_file() and arquivo.name.startswith("test_") and arquivo.suffix == ".py"):
        raise ComponentError(f"not a test file under tests/: {relativo!r}")
    # O processo filho usa o mesmo `quantum` que o admin está usando, rodando
    # de um clone ou instalado — sem isso, um projeto fora do repositório não
    # conseguia importar o pacote nos testes.
    import os
    import quantum
    ambiente = dict(os.environ)
    pacote = str(Path(quantum.__file__).resolve().parents[1])
    ambiente["PYTHONPATH"] = os.pathsep.join(p for p in (pacote, ambiente.get("PYTHONPATH")) if p)
    try:
        processo = subprocess.run([sys.executable, "-m", "pytest", str(arquivo), "-v", "--tb=short", "--no-header"],
                                  capture_output=True, text=True, timeout=int(timeout), cwd=str(raiz()),
                                  env=ambiente)
    except subprocess.TimeoutExpired:
        raise ComponentError(f"tests did not finish in {timeout}s: {relativo}")
    saida = processo.stdout + processo.stderr
    testes = [{"id": m.group(1), "name": m.group(2), "status": m.group(3)}
              for m in re.finditer(r"^(.+?::(\S+))\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b",
                                   processo.stdout, re.M)]
    resumo = {chave: int(m.group(1)) for chave, padrao in (("passed", r"(\d+) passed"), ("failed", r"(\d+) failed"),
                                                           ("errors", r"(\d+) errors?"), ("skipped", r"(\d+) skipped"))
              if (m := re.search(padrao, saida))}
    duracao = re.search(r"in ([\d.]+)s", saida)
    resultado = {"test_file": relativo, "passed": processo.returncode == 0, "returncode": processo.returncode,
                 "tests": testes, "summary": {**resumo, "duration": duracao.group(1) if duracao else None},
                 "output": saida, "ran_at": datetime.datetime.now().isoformat(timespec="seconds")}
    destino = pasta_de_configuracao()
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "last_test_result.json").write_text(json.dumps(resultado), encoding="utf-8")
    return resultado


@service("admin.tests.generate")
def generate_tests(comp_path: str, overwrite: bool = False):
    """Gera tests/test_<componente>.py a partir da estrutura do .q."""
    from quantum_admin.services._component_test_generator import ComponentTestGenerator
    relativo = (comp_path or "").strip().replace("\\", "/")
    arquivo = _dentro(relativo, "components")
    if not (arquivo.is_file() and arquivo.suffix == ".q"):
        raise ComponentError(f"not a .q component under components/: {relativo!r}")
    destino = raiz() / _arquivo_de_teste(relativo)
    if destino.exists() and not overwrite:
        raise ComponentError(f"{destino.relative_to(raiz()).as_posix()} already exists; "
                             f"pass overwrite=true to replace it")
    gerador = ComponentTestGenerator(arquivo.relative_to(raiz() / "components").as_posix(), str(raiz()))
    gerador.analyze()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(gerador.generate(), encoding="utf-8")
    return {"test_file": destino.relative_to(raiz()).as_posix(), "overwritten": bool(overwrite)}
