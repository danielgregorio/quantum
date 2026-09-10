"""Conformidade: SPEC.md seções 3 (Ações), 4 (Autenticação) e 5 (Dados)."""

import re
import sqlite3

import pytest

from quantum.core.expression_stdlib import hash_password, verify_password


def texto_de(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


def texto(resposta):
    return texto_de(resposta.get_data(as_text=True))


DUAS_ACOES = ('<q:component name="acoes" xmlns:q="https://quantum.lang/ns">'
              '<q:action name="criar" method="POST"><q:redirect url="/criado"/></q:action>'
              '<q:action name="excluir" method="POST"><q:redirect url="/excluido"/></q:action>'
              '<p>x</p></q:component>')

FORM = ('<q:component name="form" xmlns:q="https://quantum.lang/ns">'
        '<q:action name="salvar" method="POST">'
        '<q:param name="nome" required="true" minlength="2"/>'
        '<q:param name="idade" type="integer" min="18"/>'
        '<q:set name="session.visto" value="{nome}|{idade}"/>'
        '<q:redirect url="/form" flash="Salvo {nome}"/></q:action>'
        '<html><body><q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>'
        '<p>VISTO={session.visto}</p></body></html></q:component>')


class TestAcoes:
    def test_campo_action_escolhe(self, servidor):
        # ACT-1
        cliente = servidor(acoes=DUAS_ACOES)
        assert cliente.post('/acoes', data={'action': 'excluir'}).headers['Location'].endswith('/excluido')
        assert cliente.post('/acoes', data={'action': 'criar'}).headers['Location'].endswith('/criado')

    def test_param_convertido_e_validado(self, servidor):
        # ACT-2
        cliente = servidor(form=FORM)
        cliente.post('/form', data={'nome': 'Ana', 'idade': '30'})
        assert 'VISTO=Ana|30' in texto(cliente.get('/form'))

    def test_validacao_falha_nao_executa_e_volta_com_motivo(self, servidor):
        # ACT-2
        cliente = servidor(form=FORM)
        r = cliente.post('/form', data={'nome': 'A', 'idade': '30'},
                         headers={'Referer': 'http://localhost/form'})
        assert r.status_code == 302
        html = cliente.get('/form').get_data(as_text=True)   # uma vez: o flash some depois (ACT-3)
        assert 'at least 2 characters' in html
        assert 'class="error"' in html
        assert 'VISTO=A|' not in texto_de(html)

    def test_flash_aparece_uma_vez(self, servidor):
        # ACT-3
        cliente = servidor(form=FORM)
        cliente.post('/form', data={'nome': 'Bia', 'idade': '20'})
        assert 'Salvo Bia' in texto(cliente.get('/form'))
        assert 'Salvo Bia' not in texto(cliente.get('/form'))

    def test_flash_e_redirect_aceitam_expressoes(self, servidor):
        # ACT-3 (antes: so nome simples; {r.msg} dava 500 "not found in any scope")
        cliente = servidor(ex=('<q:component name="ex" xmlns:q="https://quantum.lang/ns">'
                               '<q:action name="a" method="POST">'
                               '<q:set name="r" type="object" value=\'{"msg": "ok", "n": 3}\'/>'
                               '<q:set name="itens" type="array" value="[1, 2]"/>'
                               '<q:flash type="error" message="{r.msg}: {len(itens)} itens"/>'
                               '<q:redirect url="/ex?n={r.n + 1}"/></q:action>'
                               '<p>[{flash}]</p></q:component>'))
        r = cliente.post('/ex', data={})
        assert r.status_code == 302 and r.headers['Location'].endswith('/ex?n=4')
        assert '[ok: 2 itens]' in texto(cliente.get('/ex'))

    def test_flash_existe_vazio_sem_mensagem(self, servidor):
        # ACT-3: sempre definido, '' sem mensagem
        cliente = servidor(v=('<q:component name="v" xmlns:q="https://quantum.lang/ns">'
                              '<p>[{flash}|{flashType}]</p><q:if condition="flash"><p>TEM</p></q:if></q:component>'))
        corpo = texto(cliente.get('/v'))
        assert '[|]' in corpo and 'TEM' not in corpo

    def test_action_inexistente_e_400_e_nao_executa_outra(self, servidor):
        # ACT-5 (era G6: caia em silencio na primeira action)
        cliente = servidor(acoes=DUAS_ACOES)
        r = cliente.post('/acoes', data={'action': 'exclir'})
        assert r.status_code == 400
        corpo = r.get_data(as_text=True)
        assert 'exclir' in corpo and 'criar' in corpo and 'excluir' in corpo

    def test_campo_action_ausente_com_varias_actions_e_400(self, servidor):
        # ACT-5
        assert servidor(acoes=DUAS_ACOES).post('/acoes', data={}).status_code == 400

    def test_uma_action_so_nao_exige_o_campo(self, servidor):
        # ACT-5
        cliente = servidor(form=FORM)
        assert cliente.post('/form', data={'nome': 'Caio', 'idade': '40'}).status_code == 302

    def test_form_dentro_da_action(self, servidor):
        # ACT-6 (era G7: {form.campo} saia vazio dentro da action)
        cliente = servidor(eco=('<q:component name="eco" xmlns:q="https://quantum.lang/ns">'
                                '<q:action name="salvar" method="POST">'
                                '<q:set name="session.visto" value="{form.nome}"/>'
                                '<q:redirect url="/eco"/></q:action>'
                                '<p>VISTO={session.visto}</p></q:component>'))
        cliente.post('/eco', data={'nome': 'ana'})
        assert 'VISTO=ana' in texto(cliente.get('/eco'))

    def test_query_em_action_usa_datasource_da_config(self, servidor, tmp_path):
        # ACT-4
        banco = tmp_path / 'app.db'
        sqlite3.connect(banco).execute('create table t (v text)').connection.commit()
        cliente = servidor(
            datasources_yaml=f"datasources:\n  db:\n    driver: sqlite\n    database: {banco.as_posix()}\n",
            grava=('<q:component name="grava" xmlns:q="https://quantum.lang/ns">'
                   '<q:action name="g" method="POST"><q:param name="v" required="true"/>'
                   '<q:query name="ins" datasource="db">INSERT INTO t (v) VALUES (:v)'
                   '<q:param name="v" value="{v}" type="string"/></q:query>'
                   '<q:redirect url="/grava"/></q:action><p>ok</p></q:component>'))
        assert cliente.post('/grava', data={'v': 'gravado'}).status_code == 302
        assert sqlite3.connect(banco).execute('select v from t').fetchall() == [('gravado',)]


PAGINA = ('<q:component name="{nome}" require_auth="true" {extra} '
          'xmlns:q="https://quantum.lang/ns"><p>DENTRO</p></q:component>')

ENTRAR = ('<q:component name="entrar" xmlns:q="https://quantum.lang/ns">'
          '<q:action name="e" method="POST"><q:param name="papel" required="true"/>'
          '<q:param name="horas" type="integer" required="true"/>'
          '<q:set name="session.authenticated" value="true" type="boolean"/>'
          '<q:set name="session.userRole" value="{papel}"/>'
          '<q:set name="session.sessionExpiry" value="{dateAdd(\'h\', horas)}"/>'
          '<q:redirect url="/entrar"/></q:action><p>x</p></q:component>')


class TestAutenticacao:
    def paginas(self, servidor):
        return servidor(
            entrar=ENTRAR,
            aberta=PAGINA.format(nome='aberta', extra=''),
            admin=PAGINA.format(nome='admin', extra='require_role="admin"'),
            equipe=PAGINA.format(nome='equipe', extra='require_role="admin,editor"'))

    def test_sem_sessao_redireciona(self, servidor):
        # AUTH-1
        r = self.paginas(servidor).get('/aberta')
        assert r.status_code == 302 and r.headers['Location'].endswith('/login')

    def test_sessao_valida_entra(self, servidor):
        # AUTH-1
        cliente = self.paginas(servidor)
        cliente.post('/entrar', data={'papel': 'user', 'horas': '1'})
        assert 'DENTRO' in texto(cliente.get('/aberta'))

    def test_sessao_expirada_redireciona_com_expired(self, servidor):
        # AUTH-1
        cliente = self.paginas(servidor)
        cliente.post('/entrar', data={'papel': 'user', 'horas': '-1'})
        r = cliente.get('/aberta')
        assert r.status_code == 302 and 'expired=true' in r.headers['Location']

    def test_papel_errado_e_403_e_lista_aceita(self, servidor):
        # AUTH-2
        cliente = self.paginas(servidor)
        cliente.post('/entrar', data={'papel': 'editor', 'horas': '1'})
        assert cliente.get('/admin').status_code == 403
        assert 'DENTRO' in texto(cliente.get('/equipe'))

    def test_cookie_de_sessao_httponly_e_samesite_lax(self, servidor):
        # AUTH-5: sem SameSite, outro site poderia enviar um formulario (q:action) com a sessao
        cliente = self.paginas(servidor)
        r = cliente.post('/entrar', data={'papel': 'user', 'horas': '1'})
        cookie = r.headers.get('Set-Cookie', '')
        assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie

    def test_login_url_configuravel(self, servidor):
        # AUTH-4
        c = servidor(datasources_yaml="security:\n  login_url: /admin/login\n",
                     aberta=PAGINA.format(nome='aberta', extra=''))
        r = c.get('/aberta')
        assert r.status_code == 302 and r.headers['Location'].endswith('/admin/login')

    def test_login_url_por_componente(self, servidor):
        # AUTH-4: o componente pode apontar outro login sem mudar a config
        c = servidor(admin=('<q:component name="admin" require_auth="true" login_url="/admin/login" '
                            'xmlns:q="https://quantum.lang/ns"><p>x</p></q:component>'),
                     aberta=PAGINA.format(nome='aberta', extra=''))
        assert c.get('/admin').headers['Location'].endswith('/admin/login')
        assert c.get('/aberta').headers['Location'].endswith('/login')

    def test_login_url_de_componente_externo_e_erro_de_parse(self):
        # AUTH-4
        from quantum.core.parser import QuantumParser, QuantumParseError
        with pytest.raises(QuantumParseError, match='login_url'):
            QuantumParser().parse('<q:component name="x" require_auth="true" login_url="https://mal.example" '
                                  'xmlns:q="https://quantum.lang/ns"/>')

    @pytest.mark.parametrize('url', ['https://mal.example/login', '//mal.example/login', 'login'])
    def test_login_url_so_aceita_caminho_local(self, servidor, url):
        # AUTH-4: uma URL completa faria de toda pagina protegida um redirecionamento aberto
        from quantum.runtime.web_server import ConfigError
        with pytest.raises(ConfigError, match='login_url'):
            servidor(datasources_yaml=f"security:\n  login_url: '{url}'\n",
                     aberta=PAGINA.format(nome='aberta', extra=''))

    @pytest.mark.parametrize('senha,hash_', [('', 'x'), ('s', None), ('s', 'lixo')])
    def test_verificacao_de_senha_e_fail_closed(self, senha, hash_):
        # AUTH-3
        assert verify_password(senha, hash_) is False

    def test_hash_tem_sal_proprio(self):
        # AUTH-3
        a, b = hash_password('mesma'), hash_password('mesma')
        assert a != b and verify_password('mesma', a) and verify_password('mesma', b)


class TestDados:
    @pytest.fixture(autouse=True)
    def arquivos(self, tmp_path, monkeypatch):
        (tmp_path / 'c.csv').write_text('id,nome,extra\n1,Ana,x\n2,Bia,y\n', encoding='utf-8')
        (tmp_path / 'l.xml').write_text(
            '<ls><l id="1"><t>A</t><e s="X"/></l><l id="2"><t>B</t><e s="Y"/></l></ls>',
            encoding='utf-8')
        (tmp_path / 'p.json').write_text('[{"n": "a", "v": 3}, {"n": "b", "v": 1}, {"n": "c", "v": 2}]',
                                         encoding='utf-8')
        monkeypatch.chdir(tmp_path)

    def test_csv_colunas_declaradas_tipadas_e_demais_texto(self, executar):
        # DATA-1
        r = executar('<q:data name="c" source="c.csv" type="csv">'
                     '<q:column name="id" type="integer"/></q:data><q:return value="{c}"/>')
        assert r == [{'id': 1, 'nome': 'Ana', 'extra': 'x'}, {'id': 2, 'nome': 'Bia', 'extra': 'y'}]

    def test_xml_caminhos_e_tipos(self, executar):
        # DATA-2
        r = executar('<q:data name="l" source="l.xml" type="xml" xpath=".//l">'
                     '<q:field name="id" xpath="@id" type="integer"/>'
                     '<q:field name="t" xpath="t/text()"/><q:field name="s" xpath="e/@s"/>'
                     '<q:field name="t2" xpath="t"/></q:data><q:return value="{l}"/>')
        assert r == [{'id': 1, 't': 'A', 's': 'X', 't2': 'A'}, {'id': 2, 't': 'B', 's': 'Y', 't2': 'B'}]

    def test_arquivo_inexistente_e_erro_que_nomeia_a_fonte(self, executar):
        # DATA-4 (era G16: devolvia None em silencio)
        with pytest.raises(Exception, match="q:data 'x' could not read 'naoexiste.csv'.*onerror"):
            executar('<q:data name="x" source="naoexiste.csv" type="csv"/><q:return value="nao chega"/>')

    def test_com_continue_a_falha_fica_no_resultado(self, executar):
        # DATA-4
        r = executar('<q:data name="x" source="naoexiste.csv" type="csv" onerror="continue"/>'
                     '<q:return value="{x_result}"/>')
        assert r['success'] is False and 'naoexiste.csv' in r['error']['message']

    def test_transformacoes_em_ordem(self, executar):
        # DATA-3
        r = executar('<q:data name="p" source="p.json" type="json"><q:transform>'
                     '<q:compute field="d" expression="{v} * 10" type="integer"/>'
                     '<q:filter condition="v > 1"/><q:sort by="v" order="asc"/>'
                     '<q:limit value="1"/></q:transform></q:data><q:return value="{p}"/>')
        assert r == [{'n': 'c', 'v': 2, 'd': 20}]
