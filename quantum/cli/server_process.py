"""
Stop the server started by `quantum start` and CHECK that it stopped.

The old `quantum stop` killed the PID in `.quantum.pid`, printed "Server
stopped" and exited with 0 — without looking at whether anything had stopped.
With `reload: true` (the quantum.config.yaml default) Werkzeug serves from a
CHILD process; the file held only the parent's PID. On Windows,
`taskkill /F` without `/T` brings down only the parent, and the child lived
on, orphaned, answering HTTP 200 on the same port.

Now:
- `.quantum.pid` holds the parent and, when there is a reloader, the child
  (one line each — the old format, a single line, is still valid);
- stop brings down the tree of each PID, waits, and declares success only if
  none of them is still alive. If one is left, it says which and exits with 1.

And it kills only the server that wrote the file (RUN-3). The file used to
hold bare PIDs, and a PID is reused by the next process that starts: a stale
`.quantum.pid` made `quantum stop` kill whatever had the number — once, the
pytest run. Each line now carries the process's start time too
(`quantum.runtime.process_identity`), and a PID whose process started at
another time, or a line with no start time to compare, is not touched: the
stale file is removed, the command says so and exits with 1.
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from quantum.runtime.process_identity import process_start_time

PID_FILE = '.quantum.pid'


def read_pid_entries(pid_file: Path) -> List[Tuple[int, Optional[str]]]:
    """(PID, start time) per line, in order, without repeated PIDs.

    A line is `<pid> <start time>`, or a bare `<pid>` (files written before
    RUN-3, whose start time is None). Raises ValueError if the file holds no
    valid line.
    """
    entries: List[Tuple[int, Optional[str]]] = []
    for line in pid_file.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if not parts:
            continue
        pid = int(parts[0])
        if pid not in [p for p, _ in entries]:
            entries.append((pid, parts[1] if len(parts) > 1 else None))
    if not entries:
        raise ValueError(f"{pid_file} is empty")
    return entries


def read_pids(pid_file: Path) -> List[int]:
    """PIDs listed in the file, in order, without repeats.

    Raises ValueError if the file holds no valid line.
    """
    return [pid for pid, _ in read_pid_entries(pid_file)]


def pid_alive(pid: int) -> bool:
    """Does the process exist and has it not finished yet?"""
    if pid <= 0:
        return False
    if os.name == 'nt':
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass  # it exists, it just is not ours
    return not _exited_unreaped(pid)


def _exited_unreaped(pid: int) -> bool:
    """Is the PID still in the table, but the process already finished?"""
    # A process that finished and was not yet reaped by its parent (a zombie)
    # answers os.kill(pid, 0) as if it were alive. It is not: it does not run,
    # it holds no port. Without this, stopping a server whose parent is slow to
    # call wait() — a supervisor, or pytest itself — gave "still running".
    try:
        with open(f'/proc/{pid}/stat', 'rb') as f:
            state = f.read().rsplit(b')', 1)[1].split()[0]
    except FileNotFoundError:
        return os.path.isdir('/proc')  # /proc exists and the pid does not: already gone
    except (OSError, IndexError):
        return False  # no /proc (macOS): keep the os.kill result
    return state in (b'Z', b'X')


def _pid_alive_windows(pid: int) -> bool:
    # os.kill(pid, 0) does NOT work on Windows: any signal other than
    # CTRL_C/CTRL_BREAK becomes TerminateProcess — the check would kill the process.
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
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _terminate(pid: int, force: bool) -> None:
    if os.name == 'nt':
        # /T brings down the whole tree: the reloader's child along with the parent.
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                       capture_output=True)
        return
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def _wait_until_dead(pids: List[int], timeout: float,
                     alive: Callable[[int], bool]) -> List[int]:
    deadline = time.monotonic() + timeout
    running = [p for p in pids if alive(p)]
    while running and time.monotonic() < deadline:
        time.sleep(0.2)
        running = [p for p in running if alive(p)]
    return running


def stop_server(pid_file: Path = Path(PID_FILE), grace: float = 5.0,
                alive: Callable[[int], bool] = pid_alive,
                terminate: Callable[[int, bool], None] = _terminate,
                started: Callable[[int], Optional[str]] = process_start_time) -> int:
    """Stop the server in `pid_file`. Returns the command's exit code."""
    if not pid_file.exists():
        print(f"No running server found ({pid_file.name} not found)")
        return 1

    try:
        entries = read_pid_entries(pid_file)
    except (ValueError, OSError) as e:
        print(f"Invalid PID file: {e}")
        pid_file.unlink(missing_ok=True)
        return 1

    pids = [pid for pid, _ in entries]
    live = [(pid, recorded) for pid, recorded in entries if alive(pid)]
    if not live:
        print(f"No running server found (PID {', '.join(map(str, pids))} "
              f"is not running; removed stale {pid_file.name})")
        pid_file.unlink(missing_ok=True)
        return 1

    # RUN-3: only the processes that wrote the file. A live PID with another
    # start time is a different process that got the number; one with no
    # recorded start time cannot be told apart from one.
    foreign = [pid for pid, recorded in live
               if recorded is None or started(pid) != recorded]
    if foreign:
        print(f"Not stopping PID {', '.join(map(str, foreign))}: it is not the Quantum "
              f"server that wrote {pid_file.name} (the PID now belongs to another "
              f"process, or the file does not say when the server started). Removed "
              f"the stale {pid_file.name}; if a Quantum server is still running, "
              f"stop it by hand.")
        pid_file.unlink(missing_ok=True)
        return 1

    running = [pid for pid, _ in live]

    for pid in running:
        terminate(pid, False)
    remaining = _wait_until_dead(running, grace, alive)

    if remaining:
        # SIGTERM ignored (POSIX). On Windows taskkill /F is already forced.
        for pid in remaining:
            terminate(pid, True)
        remaining = _wait_until_dead(remaining, 2.0, alive)

    if remaining:
        print(f"Could not stop the server: PID {', '.join(map(str, remaining))} "
              f"is still running. Stop it manually.")
        return 1

    print(f"Server stopped (PID {', '.join(map(str, running))})")
    pid_file.unlink(missing_ok=True)
    return 0
