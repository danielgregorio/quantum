"""Login das telas .q do admin (admin.auth.*).

Usa o auth_service do backend — as mesmas credenciais do FastAPI
(ADMIN_PASSWORD, ou a senha gerada e impressa na subida). A tela de login .q
chama admin.auth.login e, se `ok`, grava na sessão o que AUTH-1 exige
(session.authenticated, session.sessionExpiry, session.userRole).

Acrescenta o que a biblioteca não tinha: depois de MAX_FALHAS tentativas
erradas para o mesmo usuário em JANELA segundos, o login fica bloqueado por
JANELA segundos — sem isso, nada limitava tentar senhas em sequência. A
mensagem de falha é a mesma para usuário inexistente e senha errada.
"""

import threading
import time

from quantum.services import service

MAX_FALHAS = 5
JANELA = 300

_falhas = {}
_trava = threading.Lock()


def _auth():
    from quantum_admin.backend.auth_service import get_auth_service
    return get_auth_service()


def _bloqueado_ate(usuario, agora):
    with _trava:
        recentes = [t for t in _falhas.get(usuario, []) if agora - t < JANELA]
        _falhas[usuario] = recentes
        return recentes[0] + JANELA if len(recentes) >= MAX_FALHAS else None


@service("admin.auth.login")
def login(username: str, password: str):
    usuario = (username or "").strip()
    agora = time.time()
    ate = _bloqueado_ate(usuario, agora)
    if ate is not None:
        return {"ok": False, "locked": True,
                "error": f"too many failed attempts; try again in {int(ate - agora) + 1} seconds"}
    resultado = _auth().authenticate(usuario, password or "") if usuario and password else None
    if not resultado:
        with _trava:
            _falhas.setdefault(usuario, []).append(agora)
        return {"ok": False, "locked": False, "error": "invalid username or password"}
    with _trava:
        _falhas.pop(usuario, None)
    horas = max(1, int(resultado.get("expires_in", 3600) // 3600))
    return {"ok": True, "username": resultado["user"]["username"], "role": resultado["user"]["role"],
            "expires_in_hours": horas}


def _reset():
    """Testes."""
    with _trava:
        _falhas.clear()
