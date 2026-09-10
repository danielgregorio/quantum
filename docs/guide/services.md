# Declared Services

Some logic belongs in Python: reading the file system, starting a process,
calling a library. Write it as an ordinary Python function, give it a name with
`@service`, and call it from a page with `q:invoke service=`.

The page names what it calls; the Python is written, reviewed and tested as
Python. Nothing is imported unless `quantum.config.yaml` lists it.

## 1. Write the service

```python
# myapp/services.py
from pathlib import Path
from quantum.services import service

@service("reports.list")
def list_reports(folder: str = "reports", limit: int = 20):
    files = sorted(Path(folder).glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": f.name, "size": f.stat().st_size} for f in files[:limit]]
```

A service returns plain data — lists, dicts, text, numbers. It is available to
expressions like any other value.

## 2. List the module

```yaml
# quantum.config.yaml
services:
  - myapp.services
```

The module must be importable from where `quantum start` runs (the project
folder is on the path). A listed module that fails to import stops the page
with its import error.

## 3. Call it

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
[`q:param`](/guide/functions#parameters).

## When it fails

An exception raised by the service stops the page with
`service 'reports.list' failed: <message>`. To handle it in the page instead,
add `onerror="continue"` and read `reports_result`:

```xml
<q:invoke name="reports" service="reports.list" onerror="continue" />
<q:if condition="reports_result.success">
  <p>{len(reports)} reports</p>
  <q:else><p>Could not list reports: {reports_result.error.message}</p></q:else>
</q:if>
```

A name that is not registered is an error that lists the registered names.

## Services or `q:python`?

Prefer a service. `q:python` puts Python inside the page, where it cannot be
tested on its own and is easy to grow into the page's whole logic. The rules are
`SVC-1` to `SVC-3` in `SPEC.md`.
