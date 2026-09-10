"""Conformidade: SPEC.md seções 6a (Tipos em q:set) e 9 (quantum run)."""

import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


class TestConversaoDeTipos:
    @pytest.mark.parametrize('valor,tipo,esperado', [
        ('{5 / 2}', 'number', 2.5),        # era 2: int() truncava
        ('{6 / 2}', 'integer', 3),
        ('42', 'integer', 42),
        ('2.5', 'decimal', 2.5),
        ('yes', 'boolean', True),
        ('0', 'boolean', False),
        ('', 'boolean', False),
        ('[1, 2]', 'array', [1, 2]),
        ('{"a": 1}', 'object', {'a': 1}),
    ])
    def test_valores_que_convertem(self, executar, valor, tipo, esperado):
        # ERR-1
        r = executar(f"<q:set name=\"x\" value='{valor}' type=\"{tipo}\"/><q:return value=\"{{x}}\"/>")
        assert r == esperado and type(r) is type(esperado)

    def test_inteiro_com_fracao_e_erro(self, executar):
        # ERR-1 (era 3, em silencio)
        with pytest.raises(Exception, match='3.5 is not a whole number.*round'):
            executar('<q:set name="x" value="{7 / 2}" type="integer"/>')

    def test_texto_com_expressoes_ensina_a_juntar(self, executar):
        # ERR-1 (era G3: "could not convert string to float: '10 + 20'")
        with pytest.raises(Exception) as erro:
            executar('<q:set name="a" value="10"/><q:set name="b" value="20"/>'
                     '<q:set name="r" value="{a} + {b}" type="number"/>')
        assert 'value="{a + b}"' in str(erro.value)
        assert 'float' not in str(erro.value)

    def test_json_com_aspas_simples_diz_para_usar_duplas(self, executar):
        # ERR-1 (era G13: "Expecting property name enclosed in double quotes")
        with pytest.raises(Exception) as erro:
            executar('''<q:set name="a" type="array" value="[{'x': 1}]"/>''')
        assert 'double quotes' in str(erro.value)
        assert 'Expecting property name' not in str(erro.value)

    def test_booleano_desconhecido_e_erro(self, executar):
        # ERR-1 (era False, em silencio)
        with pytest.raises(Exception, match="'flase' is not a boolean"):
            executar('<q:set name="b" value="flase" type="boolean"/>')


def rodar(tmp_path, fonte):
    arquivo = tmp_path / 'app.q'
    arquivo.write_text(fonte, encoding='utf-8')
    return subprocess.run(
        [sys.executable, '-m', 'quantum.cli.runner', 'run', str(arquivo)],
        capture_output=True, text=True, cwd=tmp_path, timeout=120,
        env=dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8'))


class TestQuantumRun:
    def test_falha_tratada_nao_mostra_traceback(self, tmp_path):
        # RUN-2 (era G5)
        saida = rodar(tmp_path,
                      '<q:component name="I" xmlns:q="https://quantum.lang/ns">'
                      '<q:function name="soma"><q:param name="a" type="number" required="true"/>'
                      '<q:set name="r" value="{a} + 1" type="number"/><q:return value="{r}"/>'
                      '</q:function>'
                      '<q:invoke name="x" function="soma"><q:param name="a" default="1"/></q:invoke>'
                      '<q:return value="{x_result.error.message}"/></q:component>')
        texto = saida.stdout + saida.stderr
        assert 'Traceback (most recent call last)' not in texto
        assert 'value="{a + 1}"' in texto
        assert '[DEBUG]' not in texto          # RUN-1: sem log interno na saida

    def test_nao_cria_arquivos_que_o_programa_nao_usa(self, tmp_path):
        # RUN-1 (antes: ./logs/ e ./quantum_jobs.db a cada execucao)
        saida = rodar(tmp_path, '<q:component name="Oi" xmlns:q="https://quantum.lang/ns">'
                                '<q:return value="oi"/></q:component>')
        assert saida.returncode == 0 and 'oi' in saida.stdout
        assert sorted(p.name for p in tmp_path.iterdir()) == ['app.q']


class TestUmaInstanciaPorServico:
    def test_runtime_e_container_compartilham(self):
        # RUN-1: q:job (runtime.job_executor) e q:schedule (services.job_executor)
        # rodavam em JobExecutors diferentes
        from quantum.runtime.component import ComponentRuntime
        rt = ComponentRuntime(config={})
        assert rt.job_executor is rt.services.job_executor
        assert rt.llm_service is rt.services.llm
        assert rt.database_service is rt.services.database
