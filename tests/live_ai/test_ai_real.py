"""
IA contra um modelo REAL (decisão D6: os testes de IA devem ser reais).

Estes testes não rodam no CI comum — o runner do GitHub não alcança o servidor
de modelos. Rodam no runner self-hosted (Forge), antes de cada release e toda
noite, e em qualquer máquina com acesso ao Ollama:

    QUANTUM_LIVE_AI=1 QUANTUM_LLM_BASE_URL=http://<host>:11434 pytest tests/live_ai

Modelos: QUANTUM_LIVE_AI_MODEL (padrão phi3) e QUANTUM_LIVE_AI_EMBED (padrão
nomic-embed-text).

Asserções estruturais, nunca o texto exato: modelo real não é determinístico.
Verifica-se QUE a tool foi chamada e com quais argumentos, QUE o trecho certo
foi recuperado, QUE o número aparece na resposta. Sem retry automático — uma
oscilação aparece como falha e é investigada.

Cada bug de IA achado em 2026-09-10 ao rodar contra o Mac mini tem um teste
aqui:
- IA-1: q:llm e q:agent usavam servidores DIFERENTES no mesmo programa.
- IA-2: q:knowledge reaproveitava a base persistida pelo nome e ignorava
        fontes novas (respondia com texto de uma execução antiga).
- IA-3: falha do RAG voltava como RESPOSTA ("Error generating answer...").
"""

import contextlib
import io
import os
import pathlib
import socket
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(os.environ.get('QUANTUM_LIVE_AI') != '1',
                       reason='IA real: defina QUANTUM_LIVE_AI=1 e QUANTUM_LLM_BASE_URL'),
]

MODELO = os.environ.get('QUANTUM_LIVE_AI_MODEL', 'phi3')
EMBED = os.environ.get('QUANTUM_LIVE_AI_EMBED', 'nomic-embed-text')


def executar(corpo, config=None):
    """Executa um componente e devolve as variáveis do contexto."""
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    caminho.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
        encoding='utf-8')
    runtime = ComponentRuntime(config=config if config is not None else {})
    with contextlib.redirect_stdout(io.StringIO()):
        runtime.execute_component(QuantumParser().parse_file(str(caminho)), {})
    return runtime.execution_context.get_all_variables()


def porta_fechada():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestLlm:
    def test_completa_texto_com_databinding(self):
        v = executar(
            f'<q:set name="produto" value="Quantum"/>'
            f'<q:llm name="slogan" model="{MODELO}" temperature="0" maxTokens="60">'
            f'<q:prompt>Write a one-sentence slogan for {{produto}}, a web framework.</q:prompt>'
            f'</q:llm>')
        assert isinstance(v['slogan'], str) and v['slogan'].strip()

    def test_resposta_json_vira_objeto(self):
        v = executar(
            f'<q:llm name="dados" model="{MODELO}" responseFormat="json" temperature="0">'
            f'<q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".'
            f'</q:prompt></q:llm>')
        dados = v['dados']
        assert isinstance(dados, dict), dados
        assert str(dados.get('age')) == '34'


    def test_modo_chat_com_mensagens(self):
        v = executar(
            f'<q:llm name="r" model="{MODELO}" temperature="0" maxTokens="60">'
            '<q:message role="system">Answer with a single word.</q:message>'
            '<q:message role="user">What color is the clear daytime sky?</q:message>'
            '</q:llm>')
        assert 'blue' in str(v['r']).lower()


def renderizar(corpo):
    """Executa e renderiza — o que a página realmente mostra."""
    from quantum.runtime.renderer import HTMLRenderer
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'p.q'
    caminho.write_text(
        f'<q:component name="P" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
        encoding='utf-8')
    runtime = ComponentRuntime(config={})
    node = QuantumParser().parse_file(str(caminho))
    with contextlib.redirect_stdout(io.StringIO()):
        runtime.execute_component(node, {})
        return HTMLRenderer(runtime.execution_context).render(node)


class TestO_que_a_pagina_mostra:
    def test_campos_do_json_na_pagina(self):
        html = renderizar(
            f'<q:llm name="dados" model="{MODELO}" responseFormat="json" temperature="0">'
            f'<q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".'
            f'</q:prompt></q:llm><p>IDADE={{dados.age}}</p>')
        assert 'IDADE=34' in html

    def test_resposta_do_rag_na_pagina_em_memoria(self):
        html = renderizar(
            f'<q:knowledge name="manual" model="{MODELO}" embedModel="{EMBED}" persist="false">'
            '<q:source type="text">Quantum pages are served on port 8080 by default.</q:source>'
            '</q:knowledge>'
            f'<q:query name="resposta" datasource="knowledge:manual" mode="rag" model="{MODELO}">'
            'SELECT answer FROM knowledge WHERE question = :p'
            '<q:param name="p" value="What is the default port?" type="string"/></q:query>'
            '<p>RESPOSTA={resposta[0].answer}</p>')
        assert 'RESPOSTA=' in html and '8080' in html.split('RESPOSTA=', 1)[1]


class TestServidorUnico:
    """IA-1: toda tag de IA usa o mesmo servidor — o da variável de ambiente."""

    def test_config_diferente_nao_desvia_o_q_llm(self):
        # A config aponta para uma porta fechada; o ambiente, para o servidor
        # real. q:llm lia a config e falhava enquanto q:agent usava o ambiente.
        config = {'llm': {'base_url': f'http://127.0.0.1:{porta_fechada()}'}}
        v = executar(f'<q:llm name="ok" model="{MODELO}" temperature="0" maxTokens="10">'
                     f'<q:prompt>Say ok.</q:prompt></q:llm>', config=config)
        assert v['ok']


class TestConhecimento:
    FONTES = ('<q:source type="text">Quantum pages are served on port 8080 by default. '
              'The quantum stop command stops the server.</q:source>'
              '<q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>')

    def base(self, pasta, fontes, nome='base-teste'):
        return (f'<q:knowledge name="{nome}" model="{MODELO}" embedModel="{EMBED}" '
                f'chunkSize="200" chunkOverlap="20" persistPath="{pasta.as_posix()}">'
                f'{fontes}</q:knowledge>')

    def test_busca_recupera_o_trecho_certo(self, tmp_path):
        v = executar(self.base(tmp_path, self.FONTES) +
                     '<q:query name="t" datasource="knowledge:base-teste">'
                     'SELECT content, relevance FROM chunks WHERE content SIMILAR TO :p LIMIT 1'
                     '<q:param name="p" value="Which port does the server use?" type="string"/>'
                     '</q:query>')
        assert '8080' in v['t'][0]['content']

    def test_rag_responde_com_base_no_trecho(self, tmp_path):
        v = executar(self.base(tmp_path, self.FONTES) +
                     f'<q:query name="r" datasource="knowledge:base-teste" mode="rag" model="{MODELO}">'
                     'SELECT answer, sources FROM knowledge WHERE question = :p'
                     '<q:param name="p" value="What is the default port?" type="string"/>'
                     '</q:query>')
        assert '8080' in v['r'][0]['answer']

    def test_fontes_novas_reindexam_a_base_persistida(self, tmp_path):
        # IA-2: mesma base, mesmo caminho, fonte trocada.
        velha = '<q:source type="text">The secret code is BANANA.</q:source>'
        nova = '<q:source type="text">The secret code is PITANGA.</q:source>'
        consulta = ('<q:query name="t" datasource="knowledge:base-teste">'
                    'SELECT content FROM chunks WHERE content SIMILAR TO :p LIMIT 1'
                    '<q:param name="p" value="secret code" type="string"/></q:query>')
        executar(self.base(tmp_path, velha) + consulta)
        v = executar(self.base(tmp_path, nova) + consulta)
        assert 'PITANGA' in v['t'][0]['content']

    def test_nome_curto_funciona(self, tmp_path):
        # O ChromaDB exige 3+ caracteres no nome da coleção; name="kb" quebrava
        # com a mensagem de validação dele.
        v = executar(self.base(tmp_path, self.FONTES, nome='kb') +
                     '<q:query name="t" datasource="knowledge:kb">'
                     'SELECT content FROM chunks WHERE content SIMILAR TO :p LIMIT 1'
                     '<q:param name="p" value="port" type="string"/></q:query>')
        assert v['t']

    def test_falha_do_rag_e_erro_nao_resposta(self, tmp_path):
        # IA-3: a busca funciona (embedding real) e a GERAÇÃO falha, porque o
        # modelo não existe no servidor. Antes, o erro voltava como a resposta:
        # "Error generating answer: ...", com confiança 0. Uma porta fechada
        # não serve para provocar isto — quem quebraria primeiro é a busca.
        with pytest.raises(Exception) as erro:
            executar(self.base(tmp_path, self.FONTES) +
                     '<q:query name="r" datasource="knowledge:base-teste" mode="rag" '
                     'model="modelo-que-nao-existe">'
                     'SELECT answer FROM knowledge WHERE question = :p'
                     '<q:param name="p" value="What is the default port?" type="string"/>'
                     '</q:query>')
        assert 'Error generating answer' not in str(erro.value)


class TestAgente:
    def test_chama_a_tool_e_usa_o_resultado(self):
        v = executar(
            f'<q:agent name="calc" model="{MODELO}" max_iterations="4">'
            '<q:instruction>Use the add tool, then answer with the number.</q:instruction>'
            '<q:tool name="add" description="Add two numbers">'
            '<q:param name="a" type="number" required="true"/>'
            '<q:param name="b" type="number" required="true"/>'
            '<q:function name="doAdd"><q:set name="s" value="{a + b}" type="number"/>'
            '<q:return value="{s}"/></q:function></q:tool>'
            '<q:execute task="What is 17 plus 25?"/></q:agent>')
        resultado = v['calc_result']
        assert resultado['success'], resultado.get('error')
        chamadas = [a for a in resultado['actions'] if a['tool'] == 'add']
        assert chamadas and chamadas[0]['result'] == 42
        assert '42' in str(v['calc'])


class TestServidorForaDoAr:
    def test_q_llm_falha_com_erro_que_nomeia_o_servidor(self, monkeypatch):
        porta = porta_fechada()
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', f'http://127.0.0.1:{porta}')
        with pytest.raises(Exception) as erro:
            executar(f'<q:llm name="x" model="{MODELO}"><q:prompt>oi</q:prompt></q:llm>')
        assert str(porta) in str(erro.value) or 'connect' in str(erro.value).lower()
