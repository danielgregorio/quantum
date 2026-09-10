"""Conformidade: SPEC.md seção 8a (Configuração)."""

import sqlite3

import pytest

from quantum.cli.runner import load_config
from quantum.core.config_env import ConfigEnvError, expand_env


def escrever(tmp_path, texto):
    caminho = tmp_path / 'quantum.config.yaml'
    caminho.write_text(texto, encoding='utf-8')
    return str(caminho)


class TestVariaveisDeAmbiente:
    def test_substitui_no_cli(self, tmp_path, monkeypatch):
        # CFG-1 (era G4: lido literalmente)
        monkeypatch.setenv('QUANTUM_T_DB', './data/app.db')
        config = load_config(escrever(tmp_path, 'datasources:\n  db:\n    database: ${QUANTUM_T_DB}\n'))
        assert config['datasources']['db']['database'] == './data/app.db'

    def test_padrao_literal_e_listas(self, monkeypatch):
        # CFG-1
        monkeypatch.delenv('QUANTUM_T_AUSENTE', raising=False)
        monkeypatch.setenv('QUANTUM_T_HOST', 'db.local')
        assert expand_env({'a': ['${QUANTUM_T_HOST}:5432', '${QUANTUM_T_AUSENTE:-5}'],
                           'b': 'custa $$10', 'c': 7}) == \
            {'a': ['db.local:5432', '5'], 'b': 'custa $10', 'c': 7}

    def test_ausente_sem_padrao_e_erro_que_nomeia(self, tmp_path, monkeypatch):
        # CFG-1
        monkeypatch.delenv('QUANTUM_T_SENHA', raising=False)
        with pytest.raises(ConfigEnvError, match=r'datasources\.db\.password uses \$\{QUANTUM_T_SENHA\}'):
            load_config(escrever(tmp_path, 'datasources:\n  db:\n    password: ${QUANTUM_T_SENHA}\n'))

    def test_servidor_usa_o_datasource_da_variavel(self, servidor, tmp_path, monkeypatch):
        # CFG-1: o valor substituido chega ate a query de uma pagina servida.
        # chdir: sem a substituicao, o sqlite criaria um arquivo chamado
        # '${QUANTUM_T_BANCO}' no diretorio atual (aconteceu, no repo).
        monkeypatch.chdir(tmp_path)
        banco = tmp_path / 'env.db'
        conexao = sqlite3.connect(banco)
        conexao.execute('create table t (v text)')
        conexao.execute("insert into t values ('veio do env')")
        conexao.commit()
        conexao.close()
        monkeypatch.setenv('QUANTUM_T_BANCO', banco.as_posix())
        cliente = servidor(
            datasources_yaml='datasources:\n  db:\n    driver: sqlite\n    database: ${QUANTUM_T_BANCO}\n',
            ler=('<q:component name="ler" xmlns:q="https://quantum.lang/ns">'
                 '<q:query name="linhas" datasource="db">SELECT v FROM t</q:query>'
                 '<p>{linhas[0].v}</p></q:component>'))
        assert 'veio do env' in cliente.get('/ler').get_data(as_text=True)
