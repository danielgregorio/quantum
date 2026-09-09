"""
A CLI e a porta de entrada e quase nao tinha teste.

Medido: `quantum/cli/runner.py` 9,4% de cobertura, `deploy.py` 0%, `mq.py`
9,5%, `jobs.py` 0%, `pkg.py` 0%. Todo usuario toca a CLI antes de qualquer
outra coisa, e foi so rodando o instalador que se descobriu, por acaso, que
`quantum apps` apontava para um host privado.

O que estes testes travam e o CONTRATO, nao o formato da saida:

1. Falhar devolve codigo != 0. Um comando que falha e sai com 0 quebra
   qualquer script e qualquer CI que dependa dele.
2. Nenhum traceback cru na cara do usuario. Traceback e para quem escreveu o
   framework; quem usa merece uma frase.
3. A mensagem diz o que fazer, nao so o que aconteceu.

Sao subprocessos de proposito: `main()` chamado em processo pode passar por
caminhos que o entry point real nao passa, e o codigo de saida so existe de
verdade num processo.
"""

import pathlib
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TRACEBACK = "Traceback (most recent call last)"


def cli(*args, timeout=180):
    return subprocess.run(
        [sys.executable, "-m", "quantum.cli.runner", *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
    )


def saida(resultado):
    return (resultado.stdout or "") + (resultado.stderr or "")


@pytest.fixture
def arquivo_invalido():
    caminho = pathlib.Path(tempfile.mkdtemp()) / "quebrado.q"
    caminho.write_text('<q:component name="X"><q:if></q:component>',
                       encoding="utf-8")
    return caminho


@pytest.fixture
def arquivo_valido():
    caminho = pathlib.Path(tempfile.mkdtemp()) / "ok.q"
    caminho.write_text(
        '<q:component name="Ok"><q:set name="n" value="2" type="number" />'
        '<q:return value="{n}" /></q:component>', encoding="utf-8")
    return caminho


class TestFalharDevolveCodigoDeErro:
    """Sair com 0 depois de falhar quebra todo script que confia na CLI."""

    def test_subcomando_desconhecido(self):
        assert cli("faz-cafe").returncode != 0

    def test_arquivo_inexistente(self):
        resultado = cli("run", "/nao/existe/em/lugar/nenhum.q")
        assert resultado.returncode != 0

    def test_arquivo_que_nao_parseia(self, arquivo_invalido):
        resultado = cli("run", str(arquivo_invalido))
        assert resultado.returncode != 0

    def test_run_sem_argumento(self):
        assert cli("run").returncode != 0

    def test_um_arquivo_valido_sai_com_zero(self, arquivo_valido):
        resultado = cli("run", str(arquivo_valido))
        assert resultado.returncode == 0, saida(resultado)[-400:]


class TestNaoJogaTracebackNaCaraDoUsuario:
    """Traceback e para quem escreveu o framework."""

    def test_arquivo_inexistente(self):
        assert TRACEBACK not in saida(cli("run", "/nao/existe.q"))

    def test_arquivo_que_nao_parseia(self, arquivo_invalido):
        assert TRACEBACK not in saida(cli("run", str(arquivo_invalido)))

    def test_subcomando_desconhecido(self):
        assert TRACEBACK not in saida(cli("faz-cafe"))

    def test_status_sem_servidor(self):
        assert TRACEBACK not in saida(cli("status"))

    def test_stop_sem_servidor(self):
        assert TRACEBACK not in saida(cli("stop"))


class TestAsMensagensDizemOQueFazer:
    def test_arquivo_inexistente_diz_o_caminho(self):
        texto = saida(cli("run", "/nao/existe/arquivo.q"))
        assert "arquivo.q" in texto

    def test_erro_de_parse_aponta_a_linha(self, arquivo_invalido):
        texto = saida(cli("run", str(arquivo_invalido)))
        assert "line" in texto.lower() or "linha" in texto.lower()

    def test_ajuda_lista_os_subcomandos(self):
        texto = saida(cli("--help"))
        for comando in ("run", "start", "migrate"):
            assert comando in texto

    def test_deploy_sem_servidor_explica_de_onde_vem_o_host(self):
        # O alvo default e um host privado de quem escreveu o framework; o
        # erro precisa dizer isso em vez de so mostrar falha de DNS.
        texto = saida(cli("apps"))
        assert "QUANTUM_FORGE_URL" in texto or "forge" in texto.lower()


class TestSemArgumentoImprimeAjuda:
    """Nao e falha: pedir ajuda implicitamente e uso legitimo."""

    def test_sai_com_zero(self):
        assert cli().returncode == 0

    def test_mostra_os_subcomandos(self):
        texto = saida(cli())
        assert "run" in texto and "start" in texto


class TestOsSubcomandosRespondem:
    """Um subcomando que nem chega a rodar e pior que um que falha."""

    # A lista real do runner. Uma versao anterior deste teste incluia
    # "status", que na verdade e subcomando de `migrate` — o teste falhava
    # por engano meu, nao por defeito da CLI.
    TOPO = ["run", "start", "stop", "deploy", "apps", "pkg", "jobs", "mq",
            "migrate"]

    @pytest.mark.parametrize("comando", TOPO)
    def test_o_help_do_subcomando_funciona(self, comando):
        resultado = cli(comando, "--help")
        assert resultado.returncode == 0, saida(resultado)[-300:]
        assert TRACEBACK not in saida(resultado)

    def test_a_lista_daqui_bate_com_a_do_runner(self):
        # Se alguem adicionar um subcomando, este teste avisa que ele nao
        # esta coberto — em vez de a cobertura cair em silencio.
        import re
        fonte = (REPO / "quantum" / "cli" / "runner.py").read_text(
            encoding="utf-8")
        bloco = fonte.split("subparsers = ")[1]
        declarados = set(re.findall(r"subparsers\.add_parser\(\s*'([a-z-]+)'",
                                    bloco))
        faltando = declarados - set(self.TOPO)
        assert faltando == set(), f"subcomandos sem teste: {faltando}"

    def test_migrate_status_e_subcomando_de_migrate(self):
        resultado = cli("migrate", "status", "--help")
        assert resultado.returncode == 0
        assert TRACEBACK not in saida(resultado)
