# Declared Services

Some logic belongs in Python: reading the file system, starting a process,
calling a library. Write it as an ordinary Python function, give it a name with
`@service`, and call it from a page with `q:invoke service=`.

The page names what it calls; the Python is written, reviewed and tested as
Python. Nothing is imported unless `quantum.config.yaml` lists it.

The files on this page make a small app that CI serves and checks
(`tests/docs/test_guide_services.py`).

## 1. Write the service

Save as `myapp/services.py`:

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

A service returns plain data — lists, dicts, text, numbers. It is available to
expressions like any other value.

## 2. List the module

Save as `quantum.config.yaml`:

```yaml
services:
  - myapp.services
```

A module is imported only when it is listed (SVC-2). It must be importable
from where `quantum start` runs (the project folder is on the path), and a
listed module that fails to import stops the page with its import error.

## 3. Call it

Save as `components/reports.q`:

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

Each `q:param` is a keyword argument, converted by its `type` like any
[`q:param`](/guide/functions#parameters) (SVC-3). With `annual.pdf` (1200
bytes) and `q1.pdf` (300 bytes) in `reports/`, `/reports` shows:

```text
annual.pdf — 1200 bytes
q1.pdf — 300 bytes
```

## When it fails

An exception raised by the service is an invocation failure (INV-2): without
a `reports/` folder, `/reports` stops. The visitor gets an error page, and the
server's log says
`q:invoke 'reports' failed: service 'reports.list' failed: no folder named reports`.
To handle it in the page instead, add `onerror="continue"` and read
`reports_result`. Save as
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

With the folder, `/safe-reports` shows `2 reports`; without it,
`Could not list reports: service 'reports.list' failed: no folder named reports`.

A name that is not registered is an error that lists the registered names.
`onerror` takes `fail` (the default) or `continue`; anything else does not parse:

```xml
<q:invoke name="reports" service="reports.list" onerror="ignore" />
```

**Error:** `onerror must be "fail" or "continue", not "ignore"`

## Services or `q:python`?

Prefer a service. `q:python` puts Python inside the page, where it cannot be
tested on its own and is easy to grow into the page's whole logic. The rules are
[SVC-1 to SVC-3](../reference/spec#SVC-1).
