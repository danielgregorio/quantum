---
source: guide/services.md
source_hash: 3aa1d341057a
---

# Servicios declarados

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/services).
:::

Parte de la lógica corresponde a Python: leer el sistema de archivos, iniciar un
proceso, llamar a una biblioteca. Escríbela como una función de Python común,
dale un nombre con `@service`, y llámala desde una página con `q:invoke service=`.

La página nombra lo que llama; el Python se escribe, se revisa y se prueba como
Python. No se importa nada que `quantum.config.yaml` no liste.

Los archivos de esta página forman una pequeña aplicación que CI sirve y verifica
(`tests/docs/test_guide_services.py`).

## 1. Escribe el servicio {#_1-write-the-service}

Guárdalo como `myapp/services.py`:

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

Un servicio devuelve datos simples — listas, diccionarios, textos, números. Está
disponible para las expresiones como cualquier otro valor.

## 2. Lista el módulo {#_2-list-the-module}

Guárdalo como `quantum.config.yaml`:

```yaml
services:
  - myapp.services
```

Un módulo se importa solo cuando está listado (SVC-2). Tiene que poder importarse
desde donde se ejecuta `quantum start` (la carpeta del proyecto está en el path),
y un módulo listado que no se puede importar detiene la página con su error de
importación.

## 3. Llámalo {#_3-call-it}

Guárdalo como `components/reports.q`:

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

Cada `q:param` es un argumento con nombre, convertido por su `type` como
cualquier [`q:param`](/es/guide/functions#parameters) (SVC-3). Con `annual.pdf` (1200
bytes) y `q1.pdf` (300 bytes) en `reports/`, `/reports` muestra:

```text
annual.pdf — 1200 bytes
q1.pdf — 300 bytes
```

## Cuando falla {#when-it-fails}

Una excepción que lanza el servicio es un fallo de invocación (INV-2): sin una
carpeta `reports/`, `/reports` se detiene. El visitante recibe una página de
error, y el log del servidor dice
`q:invoke 'reports' failed: service 'reports.list' failed: no folder named reports`.
Para manejarlo en la página, agrega `onerror="continue"` y lee
`reports_result`. Guárdalo como
`components/safe-reports.q`:

```xml
<q:component name="safe-reports" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="reports" service="reports.list" onerror="continue" />
  <q:if condition="reports_result.success">
    <p>{len(reports)} reports</p>
    <q:else><p>Could not list reports: {reports_result.error.message}</p></q:else>
  </q:if>
</q:component>
```

Con la carpeta, `/safe-reports` muestra `2 reports`; sin ella,
`Could not list reports: service 'reports.list' failed: no folder named reports`.

Un nombre que no está registrado es un error que lista los nombres registrados.
`onerror` acepta `fail` (por defecto) o `continue`; cualquier otra cosa no pasa
el análisis:

```xml
<q:invoke name="reports" service="reports.list" onerror="ignore" />
```

**Error:** `onerror must be "fail" or "continue", not "ignore"`

## ¿Servicios o `q:python`? {#services-or-q-python}

Prefiere un servicio. `q:python` pone Python dentro de la página, donde no se
puede probar por separado y es fácil que crezca hasta ser toda la lógica de la
página. Las reglas son [SVC-1 a SVC-3](/reference/spec#SVC-1).
