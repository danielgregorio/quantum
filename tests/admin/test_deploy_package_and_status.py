"""Dois defeitos no caminho de deploy.

**O tarball levava os segredos.** `QuantumDeployer` tem uma lista de padroes
de exclusao, casada por um matcher escrito a mao que so entendia `*x*`,
`*.ext`, `prefixo*` e igualdade exata. Um `*` no MEIO caia na igualdade
exata, e tres padroes da lista tem um:

    .env.*.local   ->  `.env.production.local` ia empacotado e ENVIADO
    test_*.py      ->  testes iam junto
    *_test.py      ->  idem

Alem disso o filtro subia por `item.parents`, que vai ate a raiz do disco:
um app em `.../venv/meuapp` ou `~/projetos/tests/app` casava com um padrao
num diretorio de FORA e o tarball saia vazio.

**Um deploy que falhou ficava "rodando" para sempre.** `_run_deployment`
fazia `return` quando um passo devolvia False, sem mexer no status. A rota
que a interface le responde `completed = status in (completed, failed, ...)`
e `failed = status == failed`, entao um build quebrado aparecia como
`completed=false, failed=false`: um spinner eterno, sem erro na tela.
"""

import pathlib
import sys
import tarfile

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

from quantum.cli.deploy import QuantumDeployer                 # noqa: E402


def _app(raiz, arquivos):
    for caminho, conteudo in arquivos.items():
        destino = raiz / caminho
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding='utf-8')
    return raiz


def _empacota(raiz):
    deployer = QuantumDeployer.__new__(QuantumDeployer)
    deployer.config = {'deploy': {'include_runtime': False}}
    tarball = deployer._create_tarball(raiz, 'app')
    try:
        with tarfile.open(tarball) as tar:
            nomes = {m.name.replace('\\', '/') for m in tar.getmembers()}
        # `src/.cache_bust` e sempre acrescentado, para invalidar o cache do
        # Docker; nao vem do diretorio do app.
        return nomes - {'src/.cache_bust'}
    finally:
        tarball.unlink(missing_ok=True)


class TestOsSegredosNaoVaoNoPacote:
    def test_env_de_ambiente_local_e_excluido(self, tmp_path):
        raiz = _app(tmp_path / "app", {
            'app.q': '<q:component name="A" />',
            '.env.production.local': 'SENHA=super-secreta',
            '.env.staging.local': 'SENHA=outra',
        })
        dentro = _empacota(raiz)

        assert 'app.q' in dentro
        assert '.env.production.local' not in dentro, dentro
        assert '.env.staging.local' not in dentro, dentro

    def test_env_por_ambiente_tambem(self, tmp_path):
        """`.env` sozinho so casava com esse nome exato."""
        raiz = _app(tmp_path / "app", {
            'app.q': '<q:component name="A" />',
            '.env': 'A=1',
            '.env.production': 'SENHA=x',
            '.env.prod': 'SENHA=y',
        })
        dentro = _empacota(raiz)

        assert dentro == {'app.q'}, dentro

    def test_o_env_example_CONTINUA_indo(self, tmp_path):
        """`.env.example` e documentacao, nao segredo — e o arquivo que diz
        ao operador quais variaveis definir. Trocar um vazamento por uma
        omissao silenciosa nao seria conserto."""
        raiz = _app(tmp_path / "app", {
            'app.q': '<q:component name="A" />',
            '.env.example': 'SENHA=troque-me',
            '.env.sample': 'A=1',
            '.env.production.example': 'A=1',
            '.env.production': 'SENHA=de-verdade',
        })
        dentro = _empacota(raiz)

        assert '.env.example' in dentro, dentro
        assert '.env.sample' in dentro
        assert '.env.production.example' in dentro
        assert '.env.production' not in dentro

    def test_os_padroes_de_teste_funcionam(self, tmp_path):
        raiz = _app(tmp_path / "app", {
            'app.q': '<q:component name="A" />',
            'test_coisa.py': '',
            'coisa_test.py': '',
        })
        dentro = _empacota(raiz)

        assert dentro == {'app.q'}, dentro

    def test_o_que_deve_ir_continua_indo(self, tmp_path):
        raiz = _app(tmp_path / "app", {
            'app.q': '<q:component name="A" />',
            'components/lista.q': '<q:component name="L" />',
            'static/estilo.css': 'body{}',
            'requirements.txt': 'flask',
        })
        dentro = _empacota(raiz)

        assert dentro == {'app.q', 'components/lista.q',
                          'static/estilo.css', 'requirements.txt'}, dentro


class TestUmDiretorioPaiNaoEsvaziaOPacote:
    def test_um_app_dentro_de_uma_pasta_chamada_venv(self, tmp_path):
        """`item.parents` sobe ate a raiz do disco."""
        raiz = _app(tmp_path / "venv" / "meuapp", {
            'app.q': '<q:component name="A" />',
            'components/x.q': '<q:component name="X" />',
        })
        dentro = _empacota(raiz)

        assert dentro == {'app.q', 'components/x.q'}, dentro

    def test_um_app_dentro_de_uma_pasta_chamada_tests(self, tmp_path):
        raiz = _app(tmp_path / "tests" / "meuapp", {
            'app.q': '<q:component name="A" />',
        })
        assert _empacota(raiz) == {'app.q'}

    def test_um_diretorio_excluido_DENTRO_do_app_continua_excluido(
            self, tmp_path):
        raiz = _app(tmp_path / "app", {
            'app.q': '<q:component name="A" />',
            'tests/test_x.py': '',
            'node_modules/lib/index.js': '',
        })
        assert _empacota(raiz) == {'app.q'}


class TestOMatcher:
    @pytest.mark.parametrize("nome,excluido", [
        ('.env.production.local', True),
        ('.env.local', True),
        ('.env', True),
        ('.env.production', True),
        ('.env.example', False),
        ('.env.sample', False),
        ('.env.production.example', False),
        ('test_a.py', True),
        ('a_test.py', True),
        ('__pycache__', True),
        ('x.pyc', True),
        ('app.log', True),
        ('dados.db', True),
        ('node_modules', True),
        ('app.q', False),
        ('environment.q', False),
        ('testes.q', False),
        ('meu_test_helper.q', False),
        ('README.md', False),
    ])
    def test_padroes(self, nome, excluido):
        assert QuantumDeployer._is_excluded(nome) is excluido


class TestUmDeployQueFalhaDizQueFalhou:
    @pytest.fixture
    def svc(self):
        from backend.deploy_service import DeployService
        return DeployService()

    def _deployment(self, svc):
        from backend.deploy_service import DeployStatus
        d = svc.create_deployment(
            project_id=1, project_name="app-que-nao-existe",
            environment="local", branch="main", strategy="direct")
        d.status = DeployStatus.RUNNING
        return d

    def test_um_passo_que_falha_marca_o_deploy_como_falho(self, svc,
                                                          monkeypatch):
        from backend.deploy_service import DeployStatus

        d = self._deployment(svc)
        monkeypatch.setattr(svc, '_step_build', lambda dep: False)
        svc._run_deployment(d)

        assert d.status == DeployStatus.FAILED, d.status
        assert d.completed_at is not None
        assert d.error_message

    def test_a_rota_passa_a_reportar_completed_e_failed(self, svc,
                                                        monkeypatch):
        """As duas expressoes que a interface le, em main.py."""
        d = self._deployment(svc)
        monkeypatch.setattr(svc, '_step_build', lambda dep: False)
        svc._run_deployment(d)

        completed = d.status.value in ("completed", "failed", "cancelled",
                                       "rolled_back")
        failed = d.status.value == "failed"
        # Antes: (False, False) — spinner eterno.
        assert (completed, failed) == (True, True)

    @pytest.mark.parametrize("passo", ['_step_prepare', '_step_build',
                                       '_step_deploy', '_step_health'])
    def test_vale_para_todos_os_passos(self, svc, monkeypatch, passo):
        from backend.deploy_service import DeployStatus

        d = self._deployment(svc)
        for nome in ('_step_prepare', '_step_build', '_step_deploy',
                     '_step_health'):
            monkeypatch.setattr(svc, nome, lambda dep, ok=(nome != passo): ok)
        svc._run_deployment(d)

        assert d.status == DeployStatus.FAILED, (passo, d.status)
        assert passo.replace('_step_', '') in (d.error_message or '') or \
            d.error_message, (passo, d.error_message)

    def test_um_deploy_que_da_certo_continua_completo(self, svc, monkeypatch):
        from backend.deploy_service import DeployStatus

        d = self._deployment(svc)
        for nome in ('_step_prepare', '_step_build', '_step_deploy',
                     '_step_health'):
            monkeypatch.setattr(svc, nome, lambda dep: True)
        svc._run_deployment(d)

        assert d.status == DeployStatus.COMPLETED
