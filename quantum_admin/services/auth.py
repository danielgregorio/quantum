"""Login of the admin .q screens (admin.auth.*).

Uses the backend's auth_service — the same credentials as the FastAPI
(ADMIN_PASSWORD, or the password generated and printed at startup). The .q
login screen calls admin.auth.login and, if `ok`, stores in the session what
AUTH-1 requires (session.authenticated, session.sessionExpiry, session.userRole).

Adds what the library lacked: after MAX_FAILURES wrong attempts for the same
user within WINDOW seconds, the login is locked for WINDOW seconds — without
this, nothing limited trying passwords in sequence. The failure message is the
same for a nonexistent user and a wrong password.
"""

import threading
import time

from quantum.services import service

MAX_FAILURES = 5
WINDOW = 300

_failures = {}
_lock = threading.Lock()


def _auth():
    from quantum_admin.core.auth_service import get_auth_service
    return get_auth_service()


def _locked_until(user, now):
    with _lock:
        recent = [t for t in _failures.get(user, []) if now - t < WINDOW]
        _failures[user] = recent
        return recent[0] + WINDOW if len(recent) >= MAX_FAILURES else None


@service("admin.auth.login")
def login(username: str, password: str):
    user = (username or "").strip()
    now = time.time()
    until = _locked_until(user, now)
    if until is not None:
        return {"ok": False, "locked": True,
                "error": f"too many failed attempts; try again in {int(until - now) + 1} seconds"}
    result = _auth().authenticate(user, password or "") if user and password else None
    if not result:
        with _lock:
            _failures.setdefault(user, []).append(now)
        return {"ok": False, "locked": False, "error": "invalid username or password"}
    with _lock:
        _failures.pop(user, None)
    hours = max(1, int(result.get("expires_in", 3600) // 3600))
    return {"ok": True, "username": result["user"]["username"], "role": result["user"]["role"],
            "expires_in_hours": hours}


def _reset():
    """Tests."""
    with _lock:
        _failures.clear()
