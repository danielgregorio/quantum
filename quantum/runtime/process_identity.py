"""
Which process is behind a PID: its start time (RUN-3).

A PID alone does not name a process. When the server that wrote
`.quantum.pid` is gone, the operating system hands its PID to the next process
that starts — and `quantum stop` killed whatever that was: a stale file with a
reused PID brought down the pytest run that happened to get it. The PID file
therefore records each process's start time next to its PID, and `quantum
stop` kills a PID only when the process behind it still has that start time.

Standard library only (psutil is not a dependency of the framework):
GetProcessTimes on Windows, /proc/<pid>/stat on Linux, `ps -o lstart=`
elsewhere on POSIX. The value is an opaque token without spaces; only
equality matters.
"""

import os
import subprocess
from typing import Optional


def process_start_time(pid: int) -> Optional[str]:
    """The start time of process `pid` as an opaque token, or None if unknown."""
    if pid <= 0:
        return None
    try:
        if os.name == 'nt':
            return _start_time_windows(pid)
        if os.path.isdir('/proc'):
            return _start_time_proc(pid)
        return _start_time_ps(pid)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def _start_time_windows(pid: int) -> Optional[str]:
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                        ctypes.byref(kernel), ctypes.byref(user)):
            return None
        return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
    finally:
        kernel32.CloseHandle(handle)


def _start_time_proc(pid: int) -> Optional[str]:
    # Field 22 of /proc/<pid>/stat is the start time in clock ticks since
    # boot. The command name (field 2) may hold spaces and parentheses, so
    # the fields are counted after its closing ')': the state (field 3) is
    # index 0 there, the start time index 19.
    with open(f'/proc/{pid}/stat', 'rb') as f:
        fields = f.read().rsplit(b')', 1)[1].split()
    return fields[19].decode()


def _start_time_ps(pid: int) -> Optional[str]:
    result = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)],
                            capture_output=True, text=True, timeout=5)
    started = '_'.join(result.stdout.split())
    return started or None


def pid_file_line(pid: int) -> str:
    """One line of `.quantum.pid`: the PID and, when known, its start time."""
    started = process_start_time(pid)
    return f'{pid} {started}' if started else str(pid)
