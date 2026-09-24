"""The /_dev panel (M12, DEV-1): what the last requests did, while developing.

With `server.debug: true`, the server records each request — the component,
the action it ran, the queries (SQL, parameters, time, rows), the variables of
each scope, the redirect and the flash — and `/_dev` shows the last ones. With
`debug: false` nothing is recorded and `/_dev` does not exist.

Recording goes through a context variable, so a query executed deep in the
runtime finds the request it belongs to without anything being passed down,
and two requests in two threads never mix.
"""

import contextvars
import html
import threading
import time
from collections import deque
from typing import Any, Dict, Optional

_CURRENT: contextvars.ContextVar = contextvars.ContextVar('quantum_dev_request', default=None)

# A value longer than this is cut in the panel (a query of 10k rows, a blob).
_MAX_TEXT = 300


def _short(value: Any) -> str:
    text = repr(value) if not isinstance(value, str) else value
    return text if len(text) <= _MAX_TEXT else text[:_MAX_TEXT] + f'… ({len(text)} chars)'


def _scope(variables: Dict[str, Any]) -> Dict[str, str]:
    return {name: _short(value) for name, value in sorted((variables or {}).items())
            if not str(name).startswith('_')}


# -- what the runtime reports ------------------------------------------------

def note(**facts) -> None:
    """Add facts to the request being recorded (no-op when nothing records)."""
    record = _CURRENT.get()
    if record is not None:
        record.update(facts)


def note_query(datasource: str, sql: str, params: Optional[Dict[str, Any]], ms: float,
               rows: Optional[int], error: Optional[str] = None) -> None:
    record = _CURRENT.get()
    if record is not None:
        record['queries'].append({
            'datasource': datasource, 'sql': ' '.join(sql.split()),
            'params': {k: _short(v) for k, v in (params or {}).items()},
            'ms': round(ms, 2), 'rows': rows, 'error': error,
        })


def note_scopes(execution_context, label: str = 'page') -> None:
    """The variables the page — or the action (`label='action'`) — ended with,
    and the session and application scopes as they were then."""
    record = _CURRENT.get()
    if record is None or execution_context is None:
        return
    own = dict(getattr(execution_context, 'component_vars', {}) or {})
    own.update(getattr(execution_context, 'local_vars', {}) or {})
    scopes = record['scopes'] or {}
    scopes[label] = _scope({k: v for k, v in own.items() if '.' not in str(k)})
    scopes['session'] = _scope(getattr(execution_context, 'session_vars', {}))
    scopes['application'] = _scope(getattr(execution_context, 'application_vars', {}))
    # action, then page, then the scopes that outlive them
    order = ['action', 'page', 'session', 'application']
    record['scopes'] = {k: scopes[k] for k in order if k in scopes}


# -- the recorder ------------------------------------------------------------

class DevPanel:
    """The last requests of this server process, newest first."""

    def __init__(self, keep: int = 30):
        self.requests: deque = deque(maxlen=keep)
        self._counter = 0
        self._lock = threading.Lock()

    def start(self, method: str, path: str):
        with self._lock:
            self._counter += 1
            number = self._counter
        record = {'n': number, 'method': method, 'path': path, 'component': None,
                  'action': None, 'queries': [], 'scopes': None, 'status': None,
                  'redirect': None, 'flash': None, 'error': None, 't0': time.perf_counter()}
        return _CURRENT.set(record)

    def finish(self, token, status: int, location: Optional[str], flash: Optional[dict]) -> None:
        record = _CURRENT.get()
        _CURRENT.reset(token)
        if record is None:
            return
        record['status'] = status
        record['redirect'] = location
        record['flash'] = flash
        record['ms'] = round((time.perf_counter() - record.pop('t0')) * 1000, 1)
        with self._lock:
            self.requests.appendleft(record)

    def get(self, number: int) -> Optional[dict]:
        return next((r for r in list(self.requests) if r['n'] == number), None)

    # -- the page ------------------------------------------------------------

    def render(self, number: Optional[int] = None) -> str:
        recent = list(self.requests)
        chosen = self.get(number) if number is not None else (recent[0] if recent else None)
        e = html.escape
        rows = []
        for r in recent:
            current = chosen is not None and r['n'] == chosen['n']
            rows.append(
                f'<tr class="{"current" if current else ""}"><td><a href="/_dev/{r["n"]}">#{r["n"]}</a></td>'
                f'<td>{e(r["method"])}</td><td>{e(r["path"])}</td><td>{r["status"]}</td>'
                f'<td>{e(r["action"] or "")}</td><td>{len(r["queries"])}</td><td>{r["ms"]} ms</td></tr>')
        detail = self._detail(chosen) if chosen else '<p>No requests yet. Open a page of the app.</p>'
        return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Quantum /_dev</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font: 14px/1.45 system-ui, sans-serif; margin: 0; padding: 16px; color: #1f2328; background: #f6f8fa; }}
h1 {{ font-size: 18px; margin: 0 0 4px; }} h2 {{ font-size: 15px; margin: 20px 0 6px; }}
.note {{ color: #57606a; margin: 0 0 12px; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; }}
td, th {{ border: 1px solid #d0d7de; padding: 4px 8px; text-align: left; vertical-align: top; }}
tr.current td {{ background: #ddf4ff; }}
code, pre {{ font: 12px/1.4 ui-monospace, monospace; white-space: pre-wrap; word-break: break-word; margin: 0; }}
th code {{ white-space: nowrap; word-break: normal; }}
.error {{ color: #cf222e; }}
.box {{ overflow-x: auto; }}
</style></head><body>
<h1>Quantum /_dev</h1>
<p class="note">The last {len(recent)} requests of this server process. Shown because
<code>server.debug</code> is true; with <code>debug: false</code> this page does not exist.</p>
<div class="box"><table><tr><th>#</th><th>Method</th><th>Path</th><th>Status</th><th>Action</th>
<th>Queries</th><th>Time</th></tr>{"".join(rows)}</table></div>
{detail}
</body></html>'''

    def _detail(self, r: dict) -> str:
        e = html.escape
        parts = [f'<h2>#{r["n"]} {e(r["method"])} {e(r["path"])} → {r["status"]} ({r["ms"]} ms)</h2>',
                 '<div class="box"><table>',
                 f'<tr><th>Component</th><td><code>{e(r["component"] or "—")}</code></td></tr>',
                 f'<tr><th>Action</th><td>{e(r["action"] or "—")}</td></tr>',
                 f'<tr><th>Redirect</th><td>{e(r["redirect"] or "—")}</td></tr>']
        flash = r.get('flash')
        parts.append('<tr><th>Flash</th><td>' + (
            f'{e(str(flash.get("message", "")))} <em>({e(str(flash.get("type", "")))})</em>' if flash else '—')
            + '</td></tr>')
        if r.get('error'):
            parts.append(f'<tr><th>Error</th><td class="error"><pre>{e(r["error"])}</pre></td></tr>')
        parts.append('</table></div>')
        parts.append(f'<h2>Queries ({len(r["queries"])})</h2>')
        if r['queries']:
            parts.append('<div class="box"><table><tr><th>Datasource</th><th>SQL</th><th>Params</th>'
                         '<th>Rows</th><th>Time</th></tr>')
            for q in r['queries']:
                params = ', '.join(f'{e(k)}={e(v)}' for k, v in q['params'].items())
                result = f'<span class="error">{e(q["error"])}</span>' if q['error'] else (q['rows'] if q['rows'] is not None else '—')
                parts.append(f'<tr><td>{e(q["datasource"])}</td><td><pre>{e(q["sql"])}</pre></td>'
                             f'<td><code>{params}</code></td><td>{result}</td><td>{q["ms"]} ms</td></tr>')
            parts.append('</table></div>')
        else:
            parts.append('<p>None.</p>')
        for scope, variables in (r.get('scopes') or {}).items():
            parts.append(f'<h2>{e(scope)} ({len(variables)})</h2>')
            if variables:
                parts.append('<div class="box"><table>' + ''.join(
                    f'<tr><th><code>{e(k)}</code></th><td><code>{e(v)}</code></td></tr>'
                    for k, v in variables.items()) + '</table></div>')
            else:
                parts.append('<p>None.</p>')
        return '\n'.join(parts)
