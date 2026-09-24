"""
`quantum stop` said "Server stopped" and exited 0 with the server still up.

With `reload: true` — quantum.config.yaml's default — Werkzeug serves from a
CHILD process, and `.quantum.pid` only had the parent's PID. On Windows,
`taskkill /F` brought the parent down and left the child orphaned, answering
HTTP 200 on the same port. The stop never checked anything.

A second defect came with it: on each hot reload the child exits with code 3
to be restarted, and its cleanup DELETED `.quantum.pid`. After the first file
edit, `quantum stop` answered "No running server found" with the server up.

Reproduced on 2026-09-10 before the fix: the parent's PID dead, the child
alive, `curl` returning 200 after "Server stopped".

A third one (RUN-3): the file held bare PIDs, and the operating system reuses
a PID for the next process that starts. A stale `.quantum.pid` made `quantum
stop` kill whatever process had the number — once, the pytest run itself. The
file now records each process's start time, and stop kills only a PID whose
process still has it.
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from quantum.cli.server_process import pid_alive, read_pid_entries, read_pids, stop_server
from quantum.runtime.process_identity import process_start_time

REPO = Path(__file__).resolve().parents[2]


class FakeProcesses:
    """A process table the test controls."""

    def __init__(self, alive, ignores_sigterm=(), immortal=()):
        self.alive_pids = set(alive)
        self.ignores_sigterm = set(ignores_sigterm)
        self.immortal = set(immortal)
        self.signals = []

    def alive(self, pid):
        return pid in self.alive_pids

    @staticmethod
    def started(pid):
        """The start time the fake process table reports: `t<pid>`."""
        return f't{pid}'

    def terminate(self, pid, force):
        self.signals.append((pid, force))
        if pid in self.immortal:
            return
        if force or pid not in self.ignores_sigterm:
            self.alive_pids.discard(pid)


def pid_file_with(tmp_path, content):
    path = tmp_path / '.quantum.pid'
    path.write_text(content, encoding='utf-8')
    return path


class TestReadingTheFile:
    def test_the_old_one_line_format(self, tmp_path):
        assert read_pids(pid_file_with(tmp_path, '123')) == [123]

    def test_the_reloader_s_parent_and_child(self, tmp_path):
        assert read_pids(pid_file_with(tmp_path, '10\n20\n')) == [10, 20]

    def test_an_empty_file_is_invalid(self, tmp_path):
        with pytest.raises(ValueError):
            read_pids(pid_file_with(tmp_path, '\n'))

    def test_each_line_carries_the_start_time(self, tmp_path):
        # RUN-3
        assert read_pid_entries(pid_file_with(tmp_path, '10 111\n20 222\n')) == [(10, '111'), (20, '222')]

    def test_a_bare_pid_has_no_start_time(self, tmp_path):
        # RUN-3: a file written before the start time was recorded
        assert read_pid_entries(pid_file_with(tmp_path, '10\n')) == [(10, None)]


class TestOnlyTheServerThatWroteTheFile:
    """RUN-3: a PID reused by another process is never killed."""

    def test_a_reused_pid_is_not_killed(self, tmp_path, capsys):
        # RUN-3: the number is alive, but it started at another time.
        pid_file = pid_file_with(tmp_path, '10 t9\n')
        procs = FakeProcesses({10})
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate, started=procs.started) == 1
        assert procs.signals == []
        output = capsys.readouterr().out
        assert 'Not stopping PID 10' in output and 'Server stopped' not in output
        assert not pid_file.exists()

    def test_one_foreign_pid_stops_nothing(self, tmp_path):
        # RUN-3: the reloader's parent is gone and its number reused; nothing
        # in the file is trusted enough to kill.
        pid_file = pid_file_with(tmp_path, '10 t10\n20 old\n')
        procs = FakeProcesses({10, 20})
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate, started=procs.started) == 1
        assert procs.signals == []

    @staticmethod
    def _unrelated_process():
        return subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])

    @pytest.mark.parametrize('line', ['{pid}', '{pid} 12345'], ids=['bare pid', 'other start time'])
    def test_an_unrelated_live_process_survives(self, tmp_path, capsys, line):
        # RUN-3, with a real process and the real kill: the old stop killed it.
        proc = self._unrelated_process()
        try:
            pid_file = pid_file_with(tmp_path, line.format(pid=proc.pid) + '\n')
            assert stop_server(pid_file, grace=0.5) == 1
            time.sleep(0.3)
            assert proc.poll() is None, 'quantum stop killed a process it did not start'
            assert not pid_file.exists()
            assert 'Not stopping PID' in capsys.readouterr().out
        finally:
            proc.kill()
            proc.wait()

    def test_the_process_that_wrote_the_file_is_stopped(self, tmp_path):
        # RUN-3: the same start time — it is the server, and it goes.
        proc = self._unrelated_process()
        try:
            started = process_start_time(proc.pid)
            assert started
            pid_file = pid_file_with(tmp_path, f'{proc.pid} {started}\n')
            assert stop_server(pid_file, grace=5.0) == 0
            proc.wait(timeout=10)
            assert not pid_file.exists()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


class TestOnlyClaimsSuccessIfItStopped:
    def test_brings_down_parent_and_child(self, tmp_path, capsys):
        pid_file = pid_file_with(tmp_path, '10 t10\n20 t20\n')
        procs = FakeProcesses({10, 20})
        assert stop_server(pid_file, grace=0.5, alive=procs.alive,
                           terminate=procs.terminate, started=procs.started) == 0
        assert not procs.alive_pids
        assert not pid_file.exists()
        assert 'Server stopped' in capsys.readouterr().out

    def test_a_process_that_survives_is_an_error_that_names_the_pid(self, tmp_path, capsys):
        pid_file = pid_file_with(tmp_path, '10 t10\n20 t20\n')
        procs = FakeProcesses({10, 20}, immortal={20})
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate, started=procs.started) == 1
        output = capsys.readouterr().out
        assert 'Server stopped' not in output
        assert '20' in output
        # The file stays: the server is still up and the next stop needs it.
        assert pid_file.exists()

    def test_an_ignored_sigterm_escalates_to_forced(self, tmp_path):
        pid_file = pid_file_with(tmp_path, '10 t10')
        procs = FakeProcesses({10}, ignores_sigterm={10})
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate, started=procs.started) == 0
        assert procs.signals == [(10, False), (10, True)]

    def test_a_stale_pid_does_not_pretend_it_stopped_anything(self, tmp_path, capsys):
        pid_file = pid_file_with(tmp_path, '10')
        procs = FakeProcesses(set())
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate, started=procs.started) == 1
        assert procs.signals == []
        assert 'Server stopped' not in capsys.readouterr().out
        assert not pid_file.exists()

    def test_without_a_file(self, tmp_path):
        assert stop_server(tmp_path / '.quantum.pid') == 1

    def test_a_corrupted_file(self, tmp_path):
        pid_file = pid_file_with(tmp_path, 'garbage')
        assert stop_server(pid_file) == 1
        assert not pid_file.exists()


class TestPidAlive:
    def test_this_process_is_alive(self):
        assert pid_alive(os.getpid())

    def test_checking_does_not_kill_the_process(self):
        # On Windows, os.kill(pid, 0) is TerminateProcess. The "is it alive?"
        # check must not be what brings the process down.
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            assert pid_alive(proc.pid)
            assert pid_alive(proc.pid)
            assert proc.poll() is None
        finally:
            proc.kill()
            proc.wait()
        assert not pid_alive(proc.pid)

    @pytest.mark.skipif(not os.path.isdir('/proc'), reason='needs /proc (Linux)')
    def test_a_zombie_does_not_count_as_alive(self):
        # Dead but not yet reaped by its parent (no wait()). os.kill(pid, 0)
        # says it exists; for the stop, it is not running.
        proc = subprocess.Popen([sys.executable, '-c', 'pass'])
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                with open(f'/proc/{proc.pid}/stat', 'rb') as f:
                    if f.read().rsplit(b')', 1)[1].split()[0] == b'Z':
                        break
                time.sleep(0.05)
            else:
                pytest.fail('the process did not become a zombie')
            assert not pid_alive(proc.pid)
        finally:
            proc.wait()


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def answers(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            return True
    except OSError:
        return False


def kill_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                       capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait(timeout=10)


class TestARealServer:
    """The bug's exact scenario: `quantum start` with reload on, then stop."""

    def test_stop_brings_down_the_server_with_the_reloader(self, tmp_path):
        shutil.copy(REPO / 'quantum.config.yaml', tmp_path / 'quantum.config.yaml')
        (tmp_path / 'components').mkdir()
        port = free_port()
        env = dict(os.environ, PYTHONPATH=str(REPO))

        server = subprocess.Popen(
            [sys.executable, '-m', 'quantum.cli.runner', 'start', '--port', str(port)],
            cwd=tmp_path, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=(os.name != 'nt'),
        )
        pid_file = tmp_path / '.quantum.pid'
        pids = []
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                try:
                    ready = answers(port) and len(read_pids(pid_file)) == 2
                except (OSError, ValueError):
                    ready = False  # not there yet, or caught halfway through writing
                if ready:
                    break
                time.sleep(0.3)
            else:
                pytest.fail('the server did not start with the reloader in 60s')

            pids = read_pids(pid_file)

            stop = subprocess.run(
                [sys.executable, '-m', 'quantum.cli.runner', 'stop'],
                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
            )
            assert stop.returncode == 0, stop.stdout + stop.stderr

            deadline = time.monotonic() + 10
            while answers(port) and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not answers(port), 'stop exited with 0 and the port is still open'
            assert not [p for p in pids if pid_alive(p)]
            assert not pid_file.exists()
        finally:
            kill_tree(server)
            # If the stop fails the old way, the parent is already dead and the
            # reloader's child is no longer in its tree: kill it by the recorded PID.
            for pid in pids:
                if pid_alive(pid):
                    try:
                        os.kill(pid, signal.SIGKILL if os.name != 'nt' else signal.SIGTERM)
                    except OSError:
                        pass
