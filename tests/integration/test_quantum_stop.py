"""
`quantum stop` dizia "Server stopped" e saia 0 com o servidor ainda no ar.

Com `reload: true` — o padrao do quantum.config.yaml — o Werkzeug serve a
partir de um processo FILHO, e o `.quantum.pid` so tinha o PID do pai. No
Windows, `taskkill /F` derrubava o pai e deixava o filho orfao respondendo
HTTP 200 na mesma porta. O stop nunca conferia nada.

Havia um segundo defeito junto: a cada hot reload o filho sai com codigo 3
para ser reiniciado, e o cleanup dele APAGAVA o `.quantum.pid`. Depois da
primeira edicao de arquivo, `quantum stop` respondia "No running server
found" com o servidor de pe.

Reproduzido em 2026-09-10 antes da correcao: PID do pai morto, filho vivo,
`curl` devolvendo 200 depois do "Server stopped".
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

from quantum.cli.server_process import pid_alive, read_pids, stop_server

REPO = Path(__file__).resolve().parents[2]


class ProcessosFalsos:
    """Tabela de processos controlada pelo teste."""

    def __init__(self, vivos, ignora_sigterm=(), imortais=()):
        self.vivos = set(vivos)
        self.ignora_sigterm = set(ignora_sigterm)
        self.imortais = set(imortais)
        self.sinais = []

    def alive(self, pid):
        return pid in self.vivos

    def terminate(self, pid, force):
        self.sinais.append((pid, force))
        if pid in self.imortais:
            return
        if force or pid not in self.ignora_sigterm:
            self.vivos.discard(pid)


def arquivo_pid(tmp_path, conteudo):
    caminho = tmp_path / '.quantum.pid'
    caminho.write_text(conteudo, encoding='utf-8')
    return caminho


class TestLeituraDoArquivo:
    def test_formato_antigo_uma_linha(self, tmp_path):
        assert read_pids(arquivo_pid(tmp_path, '123')) == [123]

    def test_pai_e_filho_do_reloader(self, tmp_path):
        assert read_pids(arquivo_pid(tmp_path, '10\n20\n')) == [10, 20]

    def test_arquivo_vazio_e_invalido(self, tmp_path):
        with pytest.raises(ValueError):
            read_pids(arquivo_pid(tmp_path, '\n'))


class TestSoDeclaraSucessoSeParou:
    def test_derruba_pai_e_filho(self, tmp_path, capsys):
        pid_file = arquivo_pid(tmp_path, '10\n20\n')
        procs = ProcessosFalsos({10, 20})
        assert stop_server(pid_file, grace=0.5, alive=procs.alive,
                           terminate=procs.terminate) == 0
        assert not procs.vivos
        assert not pid_file.exists()
        assert 'Server stopped' in capsys.readouterr().out

    def test_processo_que_sobrevive_da_erro_e_nomeia_o_pid(self, tmp_path, capsys):
        pid_file = arquivo_pid(tmp_path, '10\n20\n')
        procs = ProcessosFalsos({10, 20}, imortais={20})
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate) == 1
        saida = capsys.readouterr().out
        assert 'Server stopped' not in saida
        assert '20' in saida
        # O arquivo fica: o servidor continua no ar e o proximo stop precisa dele.
        assert pid_file.exists()

    def test_sigterm_ignorado_escala_para_forcado(self, tmp_path):
        pid_file = arquivo_pid(tmp_path, '10')
        procs = ProcessosFalsos({10}, ignora_sigterm={10})
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate) == 0
        assert procs.sinais == [(10, False), (10, True)]

    def test_pid_velho_nao_finge_que_parou_algo(self, tmp_path, capsys):
        pid_file = arquivo_pid(tmp_path, '10')
        procs = ProcessosFalsos(set())
        assert stop_server(pid_file, grace=0.3, alive=procs.alive,
                           terminate=procs.terminate) == 1
        assert procs.sinais == []
        assert 'Server stopped' not in capsys.readouterr().out
        assert not pid_file.exists()

    def test_sem_arquivo(self, tmp_path):
        assert stop_server(tmp_path / '.quantum.pid') == 1

    def test_arquivo_corrompido(self, tmp_path):
        pid_file = arquivo_pid(tmp_path, 'lixo')
        assert stop_server(pid_file) == 1
        assert not pid_file.exists()


class TestPidAlive:
    def test_o_proprio_processo_esta_vivo(self):
        assert pid_alive(os.getpid())

    def test_checar_nao_mata_o_processo(self):
        # No Windows, os.kill(pid, 0) e TerminateProcess. A checagem de
        # "esta vivo?" nao pode ser o que derruba o processo.
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            assert pid_alive(proc.pid)
            assert pid_alive(proc.pid)
            assert proc.poll() is None
        finally:
            proc.kill()
            proc.wait()
        assert not pid_alive(proc.pid)

    @pytest.mark.skipif(not os.path.isdir('/proc'), reason='precisa de /proc (Linux)')
    def test_zumbi_nao_conta_como_vivo(self):
        # Morto mas ainda nao recolhido pelo pai (sem wait()). os.kill(pid, 0)
        # responde que existe; para o stop, nao esta rodando.
        proc = subprocess.Popen([sys.executable, '-c', 'pass'])
        try:
            limite = time.monotonic() + 10
            while time.monotonic() < limite:
                with open(f'/proc/{proc.pid}/stat', 'rb') as f:
                    if f.read().rsplit(b')', 1)[1].split()[0] == b'Z':
                        break
                time.sleep(0.05)
            else:
                pytest.fail('o processo nao virou zumbi')
            assert not pid_alive(proc.pid)
        finally:
            proc.wait()


def porta_livre():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def responde(porta):
    try:
        with socket.create_connection(('127.0.0.1', porta), timeout=1):
            return True
    except OSError:
        return False


def derrubar_arvore(proc):
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


class TestServidorDeVerdade:
    """O cenario exato do bug: `quantum start` com reload ligado, depois stop."""

    def test_stop_derruba_o_servidor_com_reloader(self, tmp_path):
        shutil.copy(REPO / 'quantum.config.yaml', tmp_path / 'quantum.config.yaml')
        (tmp_path / 'components').mkdir()
        porta = porta_livre()
        env = dict(os.environ, PYTHONPATH=str(REPO))

        servidor = subprocess.Popen(
            [sys.executable, '-m', 'quantum.cli.runner', 'start', '--port', str(porta)],
            cwd=tmp_path, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=(os.name != 'nt'),
        )
        pid_file = tmp_path / '.quantum.pid'
        pids = []
        try:
            limite = time.monotonic() + 60
            while time.monotonic() < limite:
                try:
                    pronto = responde(porta) and len(read_pids(pid_file)) == 2
                except (OSError, ValueError):
                    pronto = False  # ainda nao existe, ou pego no meio da escrita
                if pronto:
                    break
                time.sleep(0.3)
            else:
                pytest.fail('o servidor nao subiu com o reloader em 60s')

            pids = read_pids(pid_file)

            parar = subprocess.run(
                [sys.executable, '-m', 'quantum.cli.runner', 'stop'],
                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
            )
            assert parar.returncode == 0, parar.stdout + parar.stderr

            limite = time.monotonic() + 10
            while responde(porta) and time.monotonic() < limite:
                time.sleep(0.2)
            assert not responde(porta), 'stop saiu com 0 e a porta segue aberta'
            assert not [p for p in pids if pid_alive(p)]
            assert not pid_file.exists()
        finally:
            derrubar_arvore(servidor)
            # Se o stop falhar do jeito antigo, o pai ja morreu e o filho do
            # reloader nao esta mais na arvore dele: mata pelo PID anotado.
            for pid in pids:
                if pid_alive(pid):
                    try:
                        os.kill(pid, signal.SIGKILL if os.name != 'nt' else signal.SIGTERM)
                    except OSError:
                        pass
