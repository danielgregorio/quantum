---
source: guide/services.md
source_hash: 3aa1d341057a
---
# Serviços declarados

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/services). O código é o mesmo do original.
:::

Alguma lógica pertence ao Python: ler o sistema de arquivos, iniciar um
processo, chamar uma biblioteca. Escreva-a como uma função Python comum, dê a
ela um nome com `@service`, e chame-a de uma página com `q:invoke service=`.

A página nomeia o que chama; o Python é escrito, revisado e testado como
Python. Nada é importado a menos que o `quantum.config.yaml` o liste.

Os arquivos desta página formam uma pequena aplicação que o CI serve e
confere (`tests/docs/test_guide_services.py`).

## 1. Escreva o serviço {#_1-write-the-service}

Salve como `myapp/services.py`:

```python
from pathlib import Path
from quantum.services import service


@service("reports.list")
def list_reports(folder: str = "reports", limit: int = 20):
    if not Path(folder).is_dir():
        raise FileNotFoundError(f"no folder named {folder}")
    files = sorted(Path(folder).glob("*.pdf"), key=lambda p: p.name)
    return [{"name": f.name, "size": f.stat().st_size} for f in files[:limit]]
```

Um serviço devolve dados simples — listas, dicts, texto, números. Ele fica
disponível para as expressões como qualquer outro valor.

## 2. Liste o módulo {#_2-list-the-module}

Salve como `quantum.config.yaml`:

```yaml
services:
  - myapp.services
```

Um módulo só é importado quando está listado (SVC-2). Ele precisa poder ser
importado a partir de onde o `quantum start` roda (a pasta do projeto está no
path), e um módulo listado que falha ao ser importado para a página com o
erro de import dele.

## 3. Chame-o {#_3-call-it}

Salve como `components/reports.q`:

```xml
<q:component name="reports" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="reports" service="reports.list">
    <q:param name="limit" value="10" type="integer" />
  </q:invoke>

  <ul>
    <q:loop items="{reports}" var="r">
      <li>{r.name} — {r.size} bytes</li>
    </q:loop>
  </ul>
</q:component>
```

Cada `q:param` é um argumento nomeado, convertido pelo seu `type` como
qualquer [`q:param`](/pt/guide/functions#parameters) (SVC-3). Com
`annual.pdf` (1200 bytes) e `q1.pdf` (300 bytes) em `reports/`, `/reports`
mostra:

```text
annual.pdf — 1200 bytes
q1.pdf — 300 bytes
```

## Quando ele falha {#when-it-fails}

Uma exceção lançada pelo serviço é uma falha de invocação (INV-2): sem uma
pasta `reports/`, `/reports` para. O visitante recebe uma página de erro, e o
log do servidor diz
`q:invoke 'reports' failed: service 'reports.list' failed: no folder named reports`.
Para tratar isso na página, acrescente `onerror="continue"` e leia
`reports_result`. Salve como `components/safe-reports.q`:

```xml
<q:component name="safe-reports" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="reports" service="reports.list" onerror="continue" />
  <q:if condition="reports_result.success">
    <p>{len(reports)} reports</p>
    <q:else><p>Could not list reports: {reports_result.error.message}</p></q:else>
  </q:if>
</q:component>
```

Com a pasta, `/safe-reports` mostra `2 reports`; sem ela,
`Could not list reports: service 'reports.list' failed: no folder named reports`.

Um nome que não está registrado é um erro que lista os nomes registrados.
`onerror` aceita `fail` (o padrão) ou `continue`; qualquer outra coisa não
passa pelo parser:

```xml
<q:invoke name="reports" service="reports.list" onerror="ignore" />
```

**Erro:** `onerror must be "fail" or "continue", not "ignore"`

## Serviços ou `q:python`? {#services-or-q-python}

Prefira um serviço. O `q:python` coloca Python dentro da página, onde ele não
pode ser testado sozinho e cresce fácil até virar a lógica inteira da página.
As regras são [SVC-1 a SVC-3](../../reference/spec#SVC-1).
