"""
Parar o servidor iniciado por `quantum start` e CONFERIR que ele parou.

O `quantum stop` antigo matava o PID do `.quantum.pid`, imprimia "Server
stopped" e saia com 0 — sem olhar se alguma coisa tinha parado. Com
`reload: true` (o padrao do quantum.config.yaml) o Werkzeug serve a partir de
um processo FILHO; o arquivo tinha so o PID do pai. No Windows,
`taskkill /F` sem `/T` derruba so o pai, e o filho seguia vivo, orfao,
respondendo HTTP 200 na mesma porta.

Agora:
- o `.quantum.pid` guarda o pai e, quando ha reloader, o filho (uma linha
  cada — o formato antigo, uma linha so, continua valido);
- o stop derruba a arvore de cada PID, espera, e so declara sucesso se
  nenhum deles continuar vivo. Se sobrar algum, diz qual e sai com 1.
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable, List

PID_FILE = '.quantum.pid'


def read_pids(pid_file: Path) -> List[int]:
    """PIDs listados no arquivo, na ordem, sem repetir.

    Levanta ValueError se o arquivo nao tiver nenhum inteiro valido.
    """
    pids: List[int] = []
    for linha in pid_file.read_text(encoding='utf-8').split():
        pid = int(linha)
        if pid not in pids:
            pids.append(pid)
    if not pids:
        raise ValueError(f"{pid_file} is empty")
    return pids


def pid_alive(pid: int) -> bool:
    """O processo existe e ainda nao terminou?"""
    if pid <= 0:
        return False
    if os.name == 'nt':
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass  # existe, so nao e nosso
    return not _exited_unreaped(pid)


def _exited_unreaped(pid: int) -> bool:
    """O PID ainda existe na tabela, mas o processo ja terminou?"""
    # Um processo que terminou e ainda nao foi recolhido pelo pai (zumbi)
    # responde a os.kill(pid, 0) como se estivesse vivo. Nao esta: nao roda,
    # nao segura porta. Sem isso, parar um servidor cujo pai demora a chamar
    # wait() — um supervisor, ou o proprio pytest — dava "still running".
    try:
        with open(f'/proc/{pid}/stat', 'rb') as f:
            estado = f.read().rsplit(b')', 1)[1].split()[0]
    except FileNotFoundError:
        return os.path.isdir('/proc')  # /proc existe e o pid nao: ja foi embora
    except (OSError, IndexError):
        return False  # sem /proc (macOS): fica com o resultado do os.kill
    return estado in (b'Z', b'X')


def _pid_alive_windows(pid: int) -> bool:
    # os.kill(pid, 0) NAO serve no Windows: qualquer sinal que nao seja
    # CTRL_C/CTRL_BREAK vira TerminateProcess — a checagem mataria o processo.
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    ERROR_ACCESS_DENIED = 5

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        codigo = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(codigo)):
            return False
        return codigo.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _terminate(pid: int, force: bool) -> None:
    if os.name == 'nt':
        # /T derruba a arvore inteira: o filho do reloader junto com o pai.
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                       capture_output=True)
        return
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def _wait_until_dead(pids: List[int], timeout: float,
                     alive: Callable[[int], bool]) -> List[int]:
    limite = time.monotonic() + timeout
    vivos = [p for p in pids if alive(p)]
    while vivos and time.monotonic() < limite:
        time.sleep(0.2)
        vivos = [p for p in vivos if alive(p)]
    return vivos


def stop_server(pid_file: Path = Path(PID_FILE), grace: float = 5.0,
                alive: Callable[[int], bool] = pid_alive,
                terminate: Callable[[int, bool], None] = _terminate) -> int:
    """Para o servidor do `pid_file`. Devolve o codigo de saida do comando."""
    if not pid_file.exists():
        print(f"No running server found ({pid_file.name} not found)")
        return 1

    try:
        pids = read_pids(pid_file)
    except (ValueError, OSError) as e:
        print(f"Invalid PID file: {e}")
        pid_file.unlink(missing_ok=True)
        return 1

    vivos = [p for p in pids if alive(p)]
    if not vivos:
        print(f"No running server found (PID {', '.join(map(str, pids))} "
              f"is not running; removed stale {pid_file.name})")
        pid_file.unlink(missing_ok=True)
        return 1

    for pid in vivos:
        terminate(pid, False)
    restantes = _wait_until_dead(vivos, grace, alive)

    if restantes:
        # SIGTERM ignorado (POSIX). No Windows o taskkill /F ja e forcado.
        for pid in restantes:
            terminate(pid, True)
        restantes = _wait_until_dead(restantes, 2.0, alive)

    if restantes:
        print(f"Could not stop the server: PID {', '.join(map(str, restantes))} "
              f"is still running. Stop it manually.")
        return 1

    print(f"Server stopped (PID {', '.join(map(str, vivos))})")
    pid_file.unlink(missing_ok=True)
    return 0
