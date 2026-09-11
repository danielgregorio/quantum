"""Generate quantum_admin/INVENTORY.md by MEASURING the admin, never by hand.

    python scripts/admin-inventory.py

Passo A1 do plano de oficialização do admin: antes de mover qualquer coisa
para serviços declarados e telas .q, saber o que existe, o que cada rota usa e
o que de fato responde. Mede:

  - Rotas FastAPI (quantum_admin/backend/main.py), pela AST: verbo, caminho,
    área (tags), handler, linhas, módulos de serviço que o corpo usa.
  - Rotas sombreadas: pergunta ao PRÓPRIO roteador do Starlette qual rota
    atende a URL de cada uma. Se é outra, esta nunca é alcançada.
  - Status real de cada GET sem parâmetro, autenticado, contra um banco
    TEMPORÁRIO (QUANTUM_ADMIN_DATABASE_URL) — nunca o banco real do admin.
    Rotas de escrita não são executadas.
  - Módulos de serviço do backend: linhas, rotas que usam, testes que citam.
  - Telas .q (components/admin): rota, require_auth, q:action, blocos
    q:python e o que tocam, status — servidas de uma CÓPIA temporária do
    layout do repositório, só com GET.
"""

import ast
import collections
import logging
import os
import pathlib
import re
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
BACKEND = REPO / "quantum_admin" / "backend"
MAIN = BACKEND / "main.py"
TELAS = REPO / "components" / "admin"
SAIDA = REPO / "quantum_admin" / "INVENTORY.md"
VERBOS = {"get", "post", "put", "delete", "patch", "websocket"}
FORA_DO_SERVICO = {"main", "schemas", "models", "database", "__init__"}


# --------------------------------------------------------------------------- rotas (AST)

def _mapa_de_imports(tree):
    """nome local -> módulo do backend de onde veio (topo e dentro de funções)."""
    modulos = {p.stem for p in BACKEND.glob("*.py")}
    mapa = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            base = node.module.split(".")[-1]
            if base in modulos:
                for alias in node.names:
                    mapa[alias.asname or alias.name] = base
        elif isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[-1]
                if base in modulos:
                    mapa[alias.asname or base] = base
    return mapa


def rotas_da_ast():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    imports = _mapa_de_imports(tree)
    rotas = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nomes = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        usa = sorted({imports[n] for n in nomes if n in imports} - FORA_DO_SERVICO)
        efeitos = sorted(n for n in ("subprocess", "shutil", "open") if n in nomes)
        for dec in node.decorator_list:
            if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name) and dec.func.value.id == "app"
                    and dec.func.attr in VERBOS and dec.args
                    and isinstance(dec.args[0], ast.Constant)):
                continue
            tags = next((kw.value for kw in dec.keywords if kw.arg == "tags"), None)
            area = tags.elts[0].value if isinstance(tags, ast.List) and tags.elts else "—"
            html = any(kw.arg == "response_class" and getattr(kw.value, "id", "") == "HTMLResponse"
                       for kw in dec.keywords)
            rotas.append({
                "verbo": dec.func.attr.upper(), "caminho": dec.args[0].value, "area": area,
                "handler": node.name, "linha": node.lineno,
                "linhas": (node.end_lineno or node.lineno) - node.lineno + 1,
                "tipo": "websocket" if dec.func.attr == "websocket" else ("página" if html else "api"),
                "usa": usa, "efeitos": efeitos,
            })
    return rotas


# --------------------------------------------------------------------------- chamadas da UI

_FETCH = re.compile(r"fetch\(\s*(?P<url>`[^`]*`|'[^']*'(?:\s*\+[^,)]*)?|\"[^\"]*\"(?:\s*\+[^,)]*)?|[A-Za-z_]\w*)"
                    r"(?P<resto>[^;]{0,300})")
_HX = re.compile(r"hx-(?P<verbo>get|post|put|delete|patch)=\"(?P<url>[^\"]+)\"")
_HREF = re.compile(r"href=\"(?P<url>\{URL_PREFIX\}/[^\"#]*)\"")


def _normalizar(url):
    """URL de uma chamada no HTML/JS gerado por main.py -> caminho de exemplo, ou None."""
    url = url.strip()
    if url[:1] not in "`'\"":
        return None                 # fetch(url) com variável: não resolvível
    # '/docker/containers/' + id + '/start': cada literal fica, cada expressão
    # entre eles vira um valor de exemplo.
    partes = []
    for pedaco in re.findall(r"`[^`]*`|'[^']*'|\"[^\"]*\"|[^+]+", url):
        pedaco = pedaco.strip()
        if not pedaco:
            continue
        partes.append(pedaco[1:-1] if pedaco[:1] in "`'\"" else "1")
    url = "".join(partes)
    url = url.replace("{URL_PREFIX}", "")
    url = re.sub(r"\$\{\{?[^}]*\}?\}", "1", url)       # ${x} e ${{x}} (dentro de f-string)
    url = re.sub(r"\{\{?[^}]*\}?\}", "1", url)          # {project_id} de f-string
    url = url.split("?")[0]
    return url if url.startswith("/") else None


def chamadas_da_ui():
    fonte = MAIN.read_text(encoding="utf-8")
    chamadas, dinamicas = [], 0
    for m in _FETCH.finditer(fonte):
        caminho = _normalizar(m.group("url"))
        if caminho is None:
            dinamicas += 1
            continue
        verbo = re.search(r"method\s*:\s*['\"`](\w+)", m.group("resto"))
        chamadas.append((verbo.group(1).upper() if verbo else "GET", caminho,
                         fonte[:m.start()].count("\n") + 1))
    for m in _HX.finditer(fonte):
        caminho = _normalizar('"' + m.group("url") + '"')
        if caminho:
            chamadas.append((m.group("verbo").upper(), caminho, fonte[:m.start()].count("\n") + 1))
    for m in _HREF.finditer(fonte):
        caminho = _normalizar('"' + m.group("url") + '"')
        if caminho and not caminho.startswith("/static"):
            chamadas.append(("GET", caminho, fonte[:m.start()].count("\n") + 1))
    return chamadas, dinamicas


# --------------------------------------------------------------------------- app real

def _url_de_exemplo(caminho):
    return re.sub(r"\{[^}]+\}", "1", caminho)


def _handler_que_atende(candidatas, verbo, caminho):
    from starlette.routing import Match
    escopo = {"type": "http", "path": caminho, "method": verbo, "root_path": "",
              "query_string": b"", "headers": []}
    parcial = None
    for candidata in candidatas:
        match, _ = candidata.matches(escopo)
        if match == Match.FULL:
            return getattr(getattr(candidata, "endpoint", None), "__name__", "?"), candidata.path
        if match == Match.PARTIAL and parcial is None:
            parcial = candidata.path
    return None, parcial


def medir_app(rotas):
    """Sombreamento pelo roteador real e status dos GETs sem parâmetro."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    os.environ["QUANTUM_ADMIN_DATABASE_URL"] = f"sqlite:///{(tmp / 'admin.db').as_posix()}"
    # Os GETs medidos criam settings/global.yaml quando ele não existe: numa
    # pasta temporária, não na do dono.
    (tmp / "settings").mkdir()
    os.environ["QUANTUM_ADMIN_SETTINGS_DIR"] = str(tmp / "settings")
    os.environ["ADMIN_PASSWORD"] = "inventario-senha-suficientemente-longa"
    os.environ["JWT_SECRET_KEY"] = "i" * 64
    for p in (str(REPO), str(REPO / "quantum_admin"), str(BACKEND)):
        if p not in sys.path:
            sys.path.insert(0, p)
    logging.disable(logging.CRITICAL)
    from starlette.routing import Match
    from starlette.testclient import TestClient
    from backend import main

    candidatas = [r for r in main.app.routes if hasattr(r, "matches")]
    for rota in rotas:
        escopo = {"type": "websocket" if rota["verbo"] == "WEBSOCKET" else "http",
                  "path": _url_de_exemplo(rota["caminho"]), "method": rota["verbo"],
                  "root_path": "", "query_string": b"", "headers": []}
        for candidata in candidatas:
            match, _ = candidata.matches(escopo)
            if match == Match.FULL:
                alvo = getattr(candidata, "endpoint", None)
                nome = getattr(alvo, "__name__", "?")
                if nome != rota["handler"]:
                    rota["sombreada_por"] = f"{nome} ({candidata.path})"
                break

    # Quem a interface chama: cada chamada resolvida pelo mesmo roteador.
    chamadas, dinamicas = chamadas_da_ui()
    chamados = collections.Counter()
    quebradas = []
    for verbo, caminho, linha in chamadas:
        handler, rota_path = _handler_que_atende(candidatas, verbo, caminho)
        if handler:
            chamados[handler] += 1
        else:
            sem_admin, _ = (_handler_que_atende(candidatas, verbo, caminho[len("/admin"):])
                            if caminho.startswith("/admin/") else (None, None))
            if sem_admin:
                motivo = f"existe sem o prefixo `/admin` (`{caminho[len('/admin'):]}` → `{sem_admin}`)"
            elif rota_path:
                motivo = f"a rota `{rota_path}` existe, mas não aceita {verbo}"
            else:
                motivo = "nenhuma rota"
            quebradas.append((verbo, caminho, linha, motivo))
    for rota in rotas:
        rota["chamada_pela_ui"] = chamados.get(rota["handler"], 0)
    medicao = {"chamadas": len(chamadas), "dinamicas": dinamicas, "quebradas": quebradas}

    with TestClient(main.app, raise_server_exceptions=False) as cliente:
        login = cliente.post("/auth/login", params={"username": "admin",
                                                    "password": os.environ["ADMIN_PASSWORD"]})
        cabecalho = {"Authorization": f"Bearer {login.json()['access_token']}"}
        for rota in rotas:
            if rota["verbo"] != "GET" or "{" in rota["caminho"] or rota.get("sombreada_por"):
                continue
            try:
                resposta = cliente.get(rota["caminho"], headers=cabecalho, follow_redirects=False)
                rota["status"] = resposta.status_code
                if resposta.status_code >= 400:
                    rota["detalhe"] = re.sub(r"\s+", " ", resposta.text)[:90]
            except Exception as exc:  # noqa: BLE001
                rota["status"] = f"exceção: {type(exc).__name__}"
    shutil.rmtree(tmp, ignore_errors=True)
    return medicao


# --------------------------------------------------------------------------- serviços

def modulos_de_servico(rotas):
    testes = {p: p.read_text(encoding="utf-8", errors="replace")
              for p in (REPO / "tests").rglob("*.py")}
    telas = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in TELAS.rglob("*.q"))
    uso = collections.Counter(m for r in rotas for m in r["usa"])
    linhas = []
    for arquivo in sorted(BACKEND.glob("*.py")):
        nome = arquivo.stem
        if nome in FORA_DO_SERVICO:
            continue
        fonte = arquivo.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(fonte)
        publicas = [n.name for n in tree.body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_")]
        citado = [str(p.relative_to(REPO)).replace("\\", "/") for p, t in testes.items()
                  if re.search(rf"\b{nome}\b", t)]
        linhas.append({"modulo": nome, "linhas": len(fonte.splitlines()), "publicas": len(publicas),
                       "rotas": uso.get(nome, 0), "testes": citado,
                       "telas_q": bool(re.search(rf"\b{nome}\b", telas))})
    return linhas


# --------------------------------------------------------------------------- telas .q

EFEITOS_PY = {
    "processos": r"\bsubprocess\b|\bPopen\b|os\.kill",
    "escreve arquivo": r"open\([^)]*['\"][wa]['\"]|save_yaml|write_text|shutil\.(copy|move)",
    "apaga": r"os\.remove|shutil\.rmtree|unlink\(",
    "lê arquivos": r"open\(|load_yaml|os\.walk|glob\(|read_text",
    "rede": r"\brequests\.|urllib|socket\.",
}


def telas_q():
    telas = []
    for arquivo in sorted(TELAS.rglob("*.q")):
        fonte = arquivo.read_text(encoding="utf-8", errors="replace")
        rel = arquivo.relative_to(REPO / "components").with_suffix("").as_posix()
        url = "/" + (rel[:-len("/index")] if rel.endswith("/index") else rel)
        blocos = re.findall(r"<q:python\b[^>]*>(.*?)</q:python>", fonte, re.S)
        codigo = "\n".join(blocos)
        telas.append({
            "arquivo": str(arquivo.relative_to(REPO)).replace("\\", "/"), "url": url,
            "auth": bool(re.search(r"<q:component[^>]*require_auth=\"true\"", fonte)),
            "acoes": re.findall(r"<q:action\s+name=\"([^\"]+)\"", fonte),
            "python": len(blocos), "linhas_python": sum(len(b.strip().splitlines()) for b in blocos),
            "efeitos": [nome for nome, padrao in EFEITOS_PY.items() if re.search(padrao, codigo)],
            "datasource": sorted(set(re.findall(r"datasource=\"([^\"]+)\"", fonte))),
            "yaml": sorted(set(re.findall(r"(?:load_yaml|save_yaml)\(\s*['\"]([^'\"]+)['\"]", codigo))),
            "servicos": sorted(set(re.findall(r"service=\"([^\"]+)\"", fonte))),
        })
    return telas


def medir_telas(telas):
    """GET em cada tela, numa cópia temporária do layout (a tela escreve em quantum_admin/settings)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(REPO / "components", tmp / "components", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp / "quantum_admin").mkdir()
    if (REPO / "quantum_admin" / "settings").exists():
        shutil.copytree(REPO / "quantum_admin" / "settings", tmp / "quantum_admin" / "settings")
    if (REPO / "quantum_admin" / "quantum_admin.db").exists():
        shutil.copy2(REPO / "quantum_admin" / "quantum_admin.db", tmp / "quantum_admin" / "quantum_admin.db")
    shutil.copy2(REPO / "quantum.config.yaml", tmp / "quantum.config.yaml")
    anterior = os.getcwd()
    os.chdir(tmp)
    try:
        from quantum.runtime.web_server import QuantumWebServer
        cliente = QuantumWebServer("quantum.config.yaml").app.test_client()
        for tela in telas:
            url = tela["url"].replace("[name]", "blog").replace("[...path]", "components/admin/dashboard.q")
            tela["status"] = cliente.get(url).status_code
    finally:
        os.chdir(anterior)
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- markdown

def escrever(rotas, modulos, telas, ui):
    por_area = collections.defaultdict(list)
    for r in rotas:
        por_area[r["area"]].append(r)
    total_get = [r for r in rotas if "status" in r]
    ok = sum(1 for r in total_get if isinstance(r["status"], int) and r["status"] < 400)
    sombreadas = [r for r in rotas if r.get("sombreada_por")]
    sem_auth = [t for t in telas if not t["auth"]]
    L = []
    w = L.append
    w("# Inventário do Quantum Admin")
    w("")
    w("> **Gerado** por `python scripts/admin-inventory.py` — não editar à mão. Medido, não "
      "declarado: rotas lidas da AST de `quantum_admin/backend/main.py`, sombreamento perguntado "
      "ao roteador real, status de cada GET autenticado contra um banco temporário, telas `.q` "
      "servidas de uma cópia temporária. Rotas de escrita não são executadas.")
    w("")
    w(f"**{len(rotas)} rotas FastAPI** em {len(por_area)} áreas · "
      f"{sum(1 for r in rotas if r['tipo'] == 'página')} páginas HTML · "
      f"{len(sombreadas)} sombreadas (nunca alcançadas) · "
      f"GET sem parâmetro medidos: {ok}/{len(total_get)} respondem sem erro · "
      f"**{len(modulos)} módulos de serviço** · **{len(telas)} telas `.q`**, "
      f"{len(sem_auth)} sem `require_auth`, {sum(t['python'] for t in telas)} blocos `q:python`.")
    w("")
    nao_chamadas = [r for r in rotas if r["tipo"] == "api" and not r["chamada_pela_ui"]
                     and not r.get("sombreada_por")]
    w(f"A interface do admin (HTML e JS gerados dentro de `main.py`) faz **{ui['chamadas']} chamadas** "
      f"com URL legível ({ui['dinamicas']} usam uma variável e não entram na conta). "
      f"**{len(ui['quebradas'])} não chegam a rota nenhuma**. "
      f"**{len(nao_chamadas)} rotas de API não são chamadas pela interface** — candidatas a "
      f"sair se também não servirem a nada fora dela (A2).")
    w("")
    w("## Áreas")
    w("")
    w("| Área | Rotas | Páginas | Escrita | Chamadas pela UI | Serviços usados | GET medidos ok |")
    w("|---|---:|---:|---:|---:|---|---|")
    for area, rs in sorted(por_area.items(), key=lambda kv: -len(kv[1])):
        medidos = [r for r in rs if "status" in r]
        bons = sum(1 for r in medidos if isinstance(r["status"], int) and r["status"] < 400)
        servicos = sorted({m for r in rs for m in r["usa"]})
        w(f"| {area} | {len(rs)} | {sum(1 for r in rs if r['tipo'] == 'página')} | "
          f"{sum(1 for r in rs if r['verbo'] in ('POST', 'PUT', 'DELETE', 'PATCH'))} | "
          f"{sum(1 for r in rs if r['chamada_pela_ui'])} | "
          f"{', '.join(servicos) or '—'} | {f'{bons}/{len(medidos)}' if medidos else '—'} |")
    w("")
    if sombreadas:
        w("## Rotas sombreadas")
        w("")
        w("Declaradas, mas o roteador entrega a URL a outra rota registrada antes. O código "
          "delas não roda.")
        w("")
        w("| Verbo | Caminho | Handler (linha) | Atendida por |")
        w("|---|---|---|---|")
        for r in sombreadas:
            w(f"| {r['verbo']} | `{r['caminho']}` | `{r['handler']}` ({r['linha']}) | {r['sombreada_por']} |")
        w("")
    if ui["quebradas"]:
        w("## Chamadas da interface que não chegam a uma rota")
        w("")
        w("Botões e telas que chamam uma URL que o roteador não atende: falham sempre.")
        w("")
        w("| Verbo | URL chamada | Linha em main.py | Por quê |")
        w("|---|---|---:|---|")
        for verbo, caminho, linha, motivo in sorted(set(ui["quebradas"]), key=lambda q: q[2]):
            w(f"| {verbo} | `{caminho}` | {linha} | {motivo} |")
        w("")
    falhas = [r for r in total_get if not (isinstance(r["status"], int) and r["status"] < 400)]
    if falhas:
        w("## GETs que respondem com erro")
        w("")
        w("| Caminho | Status | Resposta |")
        w("|---|---|---|")
        for r in falhas:
            w(f"| `{r['caminho']}` | {r['status']} | {r.get('detalhe', '').replace('|', '/')} |")
        w("")
    w("## Módulos de serviço")
    w("")
    w("O que o plano (A1) preserva como biblioteca. **Rotas** = rotas cujo handler usa o módulo; "
      "**testes** = arquivos de teste que o citam.")
    w("")
    w("| Módulo | Linhas | Públicos | Rotas | Telas .q | Testes |")
    w("|---|---:|---:|---:|---|---|")
    for m in sorted(modulos, key=lambda m: -m["linhas"]):
        testes = ", ".join(f"`{t.split('/')[-1]}`" for t in m["testes"][:3])
        if len(m["testes"]) > 3:
            testes += f" +{len(m['testes']) - 3}"
        w(f"| `{m['modulo']}` | {m['linhas']} | {m['publicas']} | {m['rotas']} | "
          f"{'sim' if m['telas_q'] else '—'} | {testes or '**nenhum**'} |")
    w("")
    w("## Telas `.q` (components/admin)")
    w("")
    w("Cada tela chama os serviços declarados (`q:invoke service=`, `quantum_admin/services/`); "
      "**Status** é a resposta a um GET sem sessão — 302 para `/admin/login` numa tela protegida.")
    w("")
    w("| Tela | Rota | Auth | Status | Actions | Serviços | q:python (linhas) | Efeitos do Python | Fonte de dados |")
    w("|---|---|---|---|---|---:|---|---|---|")
    for t in telas:
        w(f"| `{t['arquivo'].split('components/admin/')[-1]}` | `{t['url']}` | "
          f"{'sim' if t['auth'] else '**não**'} | {t.get('status', '—')} | "
          f"{', '.join(t['acoes']) or '—'} | {len(t['servicos'])} | {t['python']} ({t['linhas_python']}) | "
          f"{', '.join(t['efeitos']) or '—'} | "
          f"{', '.join([f'banco ({d})' for d in t['datasource']] + [f'yaml ({y})' for y in t['yaml']]) or '—'} |")
    w("")
    w("## Rotas")
    w("")
    for area, rs in sorted(por_area.items()):
        w(f"### {area}")
        w("")
        w("| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |")
        w("|---|---|---|---|---|---|---|")
        for r in sorted(rs, key=lambda r: (r["caminho"], r["verbo"])):
            status = r.get("status", "sombreada" if r.get("sombreada_por") else "—")
            usa = ", ".join(r["usa"] + [f"*{e}*" for e in r["efeitos"]]) or "—"
            w(f"| {r['verbo']} | `{r['caminho']}` | {r['tipo']} | `{r['handler']}` "
              f"({r['linha']}, {r['linhas']}) | {usa} | {'sim' if r['chamada_pela_ui'] else '—'} | {status} |")
        w("")
    SAIDA.write_text("\n".join(L), encoding="utf-8")
    return len(rotas), len(sombreadas), ok, len(total_get), len(telas), len(sem_auth)


def main():
    rotas = rotas_da_ast()
    ui = medir_app(rotas)
    modulos = modulos_de_servico(rotas)
    telas = telas_q()
    medir_telas(telas)
    total, sombreadas, ok, medidos, n_telas, sem_auth = escrever(rotas, modulos, telas, ui)
    print(f"{total} rotas, {sombreadas} sombreadas, GET ok {ok}/{medidos}, "
          f"{n_telas} telas .q ({sem_auth} sem auth) -> {SAIDA.relative_to(REPO)}")


if __name__ == "__main__":
    main()
