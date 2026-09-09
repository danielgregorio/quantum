"""Um `on-click` escrito com parenteses nao chegava a lugar nenhum.

Tres alvos, tres formas do mesmo defeito — o texto CRU do handler era usado
como se fosse um nome:

  * **terminal (Textual)** — `py_id("salvar()")` devolvia `salvar()` e o
    gerador escrevia `def action_salvar()(self):`. O arquivo Python gerado
    nao COMPILAVA: um unico botao com parenteses derrubava o aplicativo
    inteiro no import. E a comparacao com os nomes das q:function nunca
    casava, entao nem a funcao certa era chamada.

  * **desktop (pywebview)** — saia `__quantumCall('salvar()')`, e do outro
    lado esta `window.pywebview.api[fn]`, cujas chaves sao os nomes das
    q:function. `api["salvar()"]` e undefined, entao o clique caia num
    `console.warn` dentro de uma janela nativa onde ninguem ve console: o
    botao nao fazia nada.

  * **desktop, corpo da funcao** — `_generate_statement` so entendia
    `SetNode`; todo o resto virava `pass  # Unsupported statement type`.
    Uma q:function com `<q:script>` (que o parser entrega como HTMLNode)
    virava um no-op completo, sem erro em lugar nenhum.

E, no alvo web, o corpo de uma q:function nunca vai para o navegador — mas
o `onclick="minhaFuncao()"` ia, sem nenhuma definicao junto:
`ReferenceError` no console e silencio em todo o resto.
"""

import ast as pyast

import pytest

from quantum.core.parser import QuantumParser


def _app(src):
    return QuantumParser(use_cache=False).parse(src)


def _gera_terminal(src):
    from quantum.runtime.terminal_builder import TerminalBuilder
    return TerminalBuilder().build(_app(src))


SRC_TERMINAL = '''<q:application id="t" type="terminal">
  <q:function name="salvar"><q:set name="x" value="1" /></q:function>
  <qt:screen name="main">
    <qt:button id="b1" label="Com parenteses" on-click="salvar()" />
    <qt:button id="b2" label="Sem parenteses" on-click="salvar" />
  </qt:screen>
</q:application>'''


class TestTerminal:
    def test_o_arquivo_gerado_compila(self):
        codigo = _gera_terminal(SRC_TERMINAL)
        pyast.parse(codigo)          # antes: SyntaxError

    def test_nao_existe_um_metodo_com_parenteses_no_nome(self):
        codigo = _gera_terminal(SRC_TERMINAL)
        assert 'def action_salvar()' not in codigo, codigo

    def test_as_duas_formas_chamam_a_mesma_acao(self):
        codigo = _gera_terminal(SRC_TERMINAL)
        assert codigo.count('self.action_salvar()') >= 2, codigo
        # E um so metodo, nao dois.
        assert codigo.count('def action_salvar(self):') == 1

    def test_a_acao_chama_a_q_function_do_usuario(self):
        codigo = _gera_terminal(SRC_TERMINAL)
        corpo = codigo.split('def action_salvar(self):')[1]
        assert 'self.salvar()' in corpo.split('def ')[0], corpo[:300]

    def test_um_handler_com_lixo_ainda_gera_codigo_valido(self):
        codigo = _gera_terminal('''<q:application id="t" type="terminal">
  <qt:screen name="main">
    <qt:button id="b" label="x" on-click="nao existe!" />
  </qt:screen>
</q:application>''')
        pyast.parse(codigo)

    @pytest.mark.parametrize("entrada,esperado", [
        ('salvar()', ('salvar', '')),
        ('salvar', ('salvar', None)),
        ('salvar(1, 2)', ('salvar', '1, 2')),
        ('  salvar( a )  ', ('salvar', 'a')),
        ('', ('', None)),
    ])
    def test_split_call(self, entrada, esperado):
        from quantum.runtime.terminal_templates import split_call
        assert split_call(entrada) == esperado

    @pytest.mark.parametrize("entrada", [
        'salvar()', 'nao existe!', 'a.b(c)', '9inicio', '', 'com-traco',
    ])
    def test_py_id_sempre_produz_um_identificador(self, entrada):
        from quantum.runtime.terminal_templates import py_id
        assert py_id(entrada).isidentifier(), (entrada, py_id(entrada))


class TestFuncoesNoTopoDoApplication:
    """Um `<q:function>` filho direto do `<q:application>` era descartado.

    Os parsers por engine (qt:, qg:, ui:) so olham os filhos do PROPRIO
    namespace, e nao havia onde guardar um filho `q:`. O gerador do terminal
    entao so encontrava funcoes declaradas dentro de um `<qt:screen>`, e o
    on-click que apontava para a funcao global caia no ramo "acao
    desconhecida": `self.notify("Action: salvar")` — o botao ANUNCIAVA a
    acao em vez de executa-la.
    """

    SRC = '''<q:application id="t" type="terminal">
  <q:set name="contador" type="integer" value="0" />
  <q:function name="salvar"><q:set name="x" value="1" /></q:function>
  <qt:screen name="main"><qt:button id="b" label="x" on-click="salvar()" /></qt:screen>
</q:application>'''

    def test_a_funcao_e_guardada_no_no_da_aplicacao(self):
        app = _app(self.SRC)
        assert [f.name for f in app.functions] == ['salvar']

    def test_o_q_set_do_topo_tambem(self):
        app = _app(self.SRC)
        assert [s.name for s in app.state_vars] == ['contador']

    def test_o_botao_executa_a_funcao_em_vez_de_anuncia_la(self):
        codigo = _gera_terminal(self.SRC)
        assert 'self.notify("Action: salvar")' not in codigo, codigo
        assert 'def salvar(self):' in codigo
        corpo = codigo.split('def action_salvar(self):')[1].split('def ')[0]
        assert 'self.salvar()' in corpo, corpo

    def test_a_variavel_do_topo_vira_estado_reativo(self):
        codigo = _gera_terminal(self.SRC)
        assert 'contador = reactive(' in codigo, codigo


class TestDesktop:
    def _html(self, fonte):
        from quantum.runtime.ui_html_adapter import UIHtmlAdapter
        app = _app(fonte)
        return UIHtmlAdapter(desktop_mode=True).generate(
            app.ui_windows, app.ui_children, 'T')

    SRC = ('<q:application id="a" type="ui">'
           '<ui:window><ui:button on-click="salvar()">Ok</ui:button>'
           '</ui:window></q:application>')

    def test_a_ponte_recebe_o_nome_e_nao_o_texto_com_parenteses(self):
        html = self._html(self.SRC)
        assert "__quantumCall('salvar')" in html, html
        assert "'salvar()'" not in html, html

    def test_os_argumentos_viajam_junto(self):
        html = self._html(
            '<q:application id="a" type="ui">'
            '<ui:window><ui:button on-click="somar(1, 2)">Ok</ui:button>'
            '</ui:window></q:application>')
        assert "__quantumCall('salvar'" not in html
        assert "'somar'" in html and '1, 2' in html, html

    def test_sem_parenteses_continua_igual(self):
        html = self._html(
            '<q:application id="a" type="ui">'
            '<ui:window><ui:button on-click="salvar">Ok</ui:button>'
            '</ui:window></q:application>')
        assert "__quantumCall('salvar')" in html

    def test_uma_aspa_no_handler_nao_escapa_da_string_js(self):
        from quantum.runtime.ui_html_adapter import UIHtmlAdapter
        adaptador = UIHtmlAdapter(desktop_mode=True)
        saida = adaptador._transform_onclick("salvar');alert('x")
        assert "');alert('" not in saida.replace("\\'", ''), saida


class TestCorpoDaFuncaoNoDesktop:
    def _api(self, fonte):
        from quantum.runtime.ui_desktop_adapter import UIDesktopAdapter
        app = _app(fonte)
        funcoes = {f.name: f for f in (getattr(app, 'functions', None) or [])}
        adaptador = UIDesktopAdapter()
        return adaptador._generate_api_methods(funcoes) \
            if hasattr(adaptador, '_generate_api_methods') else None

    def test_um_corpo_intraduzivel_levanta_em_vez_de_virar_pass(self):
        from quantum.runtime.ui_desktop_adapter import UIDesktopAdapter
        from quantum.core.ast_nodes import HTMLNode

        app = _app('<q:component name="C">'
                   '<q:function name="mostrar">'
                   '<q:script>alert(1)</q:script>'
                   '</q:function></q:component>')
        funcao = (getattr(app, 'functions', None) or [])[0]
        codigo = UIDesktopAdapter()._generate_function_method('mostrar', funcao)

        assert 'raise NotImplementedError' in codigo, codigo
        assert 'pass  # Unsupported' not in codigo, codigo
        assert 'mostrar' in codigo
        pyast.parse('class X:\n' + codigo)

    def test_a_mensagem_diz_o_que_falta(self):
        from quantum.runtime.ui_desktop_adapter import UIDesktopAdapter

        app = _app('<q:component name="C">'
                   '<q:function name="mostrar">'
                   '<q:script>alert(1)</q:script>'
                   '</q:function></q:component>')
        funcao = (getattr(app, 'functions', None) or [])[0]
        codigo = UIDesktopAdapter()._generate_function_method('mostrar', funcao)
        assert 'q:set' in codigo and 'desktop' in codigo

    def test_um_corpo_com_q_set_continua_sendo_traduzido(self):
        from quantum.runtime.ui_desktop_adapter import UIDesktopAdapter

        app = _app('<q:component name="C">'
                   '<q:function name="somar">'
                   '<q:set name="n" value="1" />'
                   '</q:function></q:component>')
        funcao = (getattr(app, 'functions', None) or [])[0]
        codigo = UIDesktopAdapter()._generate_function_method('somar', funcao)
        assert "self.state.set('n'" in codigo
        assert 'NotImplementedError' not in codigo


class TestQFunctionNoAlvoWeb:
    def _render(self, fonte):
        from quantum.runtime.component import ComponentRuntime
        from quantum.runtime.renderer import HTMLRenderer
        ast = _app(fonte)
        contexto = ComponentRuntime().execute_component(ast, {})
        return HTMLRenderer(contexto if isinstance(contexto, dict) else {}
                            ).render(ast)

    SRC = ('<q:component name="C">'
           '<q:function name="incrementar"><q:set name="n" value="1" />'
           '</q:function>'
           '<button onclick="incrementar()">+1</button>'
           '</q:component>')

    def test_o_nome_chamado_passa_a_existir_no_cliente(self):
        html = self._render(self.SRC)
        assert 'incrementar' in html.split('<script>')[-1], html

    def test_o_erro_diz_o_que_usar_no_lugar(self):
        html = self._render(self.SRC)
        assert 'q:action' in html

    def test_o_aviso_sai_no_log_do_servidor(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger='quantum.renderer'):
            self._render(self.SRC)
        assert any('incrementar' in r.getMessage() for r in caplog.records), \
            [r.getMessage() for r in caplog.records]

    def test_o_script_entra_no_documento_e_nao_depois_do_html(self):
        """Depois de `</html>` o navegador reposiciona sozinho, mas a saida
        deixa de ser HTML valido."""
        html = self._render(
            '<q:component name="C">'
            '<q:function name="f"><q:set name="n" value="1" /></q:function>'
            '<html><body><button onclick="f()">x</button></body></html>'
            '</q:component>')
        assert html.rstrip().endswith('</html>'), html
        assert html.index('<script>') < html.index('</body>'), html

    def test_um_handler_que_nao_e_q_function_nao_vira_script(self):
        """JavaScript comum na pagina nao pode ser sequestrado."""
        html = self._render(
            '<q:component name="C">'
            '<button onclick="alert(1)">x</button>'
            '</q:component>')
        assert '<script>' not in html, html

    def test_sem_handler_nenhum_nao_ha_script(self):
        html = self._render(
            '<q:component name="C">'
            '<q:function name="f"><q:set name="n" value="1" /></q:function>'
            '<p>oi</p></q:component>')
        assert '<script>' not in html, html
