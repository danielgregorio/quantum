"""Answers that arrive as they are written (M5, IA-7).

`<q:llm stream="true">` in a web request does not wait for the model: it
registers the request here and the page renders at once. `<ui:stream
for="answer">` then reads `/_stream/<token>`, which runs the model and sends
the answer in pieces as the provider produces them.

A token is random, used once, expires after ten minutes, and belongs to the
session that created it (its id is kept in that session's scope), so another
visitor cannot read the answer. A failure while streaming ends the text with
ERROR_MARK and the message — the renderers show it as an error, never as part
of the answer.
"""

import secrets
import threading
import time
from typing import Dict, Iterator, Optional

TTL_SECONDS = 600
ERROR_MARK = '\x00ERROR:'
SESSION_KEY = '_streams'

_JOBS: Dict[str, dict] = {}
_LOCK = threading.Lock()


def register(job: dict, session_vars: dict) -> str:
    """Keep a model request for /_stream/<token>; returns the token."""
    token = secrets.token_urlsafe(24)
    now = time.monotonic()
    with _LOCK:
        for old in [t for t, j in _JOBS.items() if now - j['created'] > TTL_SECONDS]:
            del _JOBS[old]
        _JOBS[token] = {**job, 'created': now}
    tokens = list(session_vars.get(SESSION_KEY) or [])[-20:]
    session_vars[SESSION_KEY] = tokens + [token]
    return token


def take(token: str, session_vars: Optional[dict]) -> Optional[dict]:
    """The request for a token of this session, once; None otherwise."""
    if token not in ((session_vars or {}).get(SESSION_KEY) or []):
        return None
    with _LOCK:
        job = _JOBS.pop(token, None)
    if job is None or time.monotonic() - job['created'] > TTL_SECONDS:
        return None
    return job


def run(job: dict, llm_service) -> Iterator[str]:
    """The answer's pieces; a failure ends it with ERROR_MARK and the message."""
    try:
        yield from llm_service.stream_chat(
            messages=job['messages'], model=job.get('model'), provider=job.get('provider'),
            endpoint=job.get('endpoint'), api_key=job.get('api_key'),
            temperature=job.get('temperature'), max_tokens=job.get('max_tokens'),
            timeout=job.get('timeout'))
    except Exception as exc:          # the text already sent stays; the error follows it
        yield f'{ERROR_MARK}{exc}'


STREAM_JS = """
(function () {
  function read(box) {
    if (box.dataset.qStarted) return;
    box.dataset.qStarted = '1';
    var out = box.querySelector('.q-stream-text');
    fetch(box.dataset.qStream, {credentials: 'same-origin'}).then(function (response) {
      if (!response.ok) { box.classList.add('q-stream-error'); out.textContent = 'This answer is no longer available.'; return; }
      var reader = response.body.getReader(), decoder = new TextDecoder(), text = '';
      function pump() {
        return reader.read().then(function (part) {
          if (part.done) { box.classList.add('q-stream-done'); return; }
          text += decoder.decode(part.value, {stream: true});
          var mark = text.indexOf('\\u0000ERROR:');
          if (mark >= 0) {
            out.textContent = text.slice(0, mark);
            var err = document.createElement('div');
            err.className = 'q-field-error';
            err.textContent = text.slice(mark + 7);
            box.appendChild(err);
            box.classList.add('q-stream-error');
            return;
          }
          out.textContent = text;
          return pump();
        });
      }
      return pump();
    });
  }
  function start() { document.querySelectorAll('[data-q-stream]').forEach(read); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
"""

STREAM_CSS = """
/* IA-7: an answer arriving as it is written */
.q-stream { white-space: pre-wrap; min-height: 1.5em; }
.q-stream:not(.q-stream-done):not(.q-stream-error) .q-stream-text::after { content: '▍'; opacity: .6; }
"""
