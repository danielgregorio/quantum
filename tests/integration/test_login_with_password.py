"""
Login de verdade em .q: buscar o usuário, verificar a senha, abrir a sessão.

Autenticação entrou no Core (decisão D4), e dois defeitos impediam um login
honesto escrito na linguagem:

1. Não havia como verificar uma senha contra um hash sem q:python.
   Todo exemplo de login gravava session.authenticated=true para quem
   enviasse o formulário. Agora `hashPassword()` e `verifyPassword()` fazem
   parte da biblioteca padrão de expressões (regra AUTH-3 do SPEC.md).

2. Todo q:query dentro de q:action falhava. O ActionHandler criava o seu
   ComponentRuntime SEM a config do servidor, então os datasources de
   quantum.config.yaml não existiam para ele: "Datasource 'db' is not declared
   locally". Um formulário que grava no banco não funcionava — e nenhum teste
   rodava q:query dentro de action contra o servidor.

Achados escrevendo docs/guide/authentication.md e rodando o exemplo.
"""

import re
import sqlite3

import pytest

from quantum.core.expression_stdlib import hash_password, verify_password
from quantum.runtime.web_server import QuantumWebServer

LOGIN = '''<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <q:action name="entrar" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="senha" required="true" />
    <q:query name="usuario" datasource="db">
      SELECT id, nome, papel, senha_hash FROM usuarios WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:if condition="usuario.length == 1 and verifyPassword(senha, usuario[0].senha_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userName" value="{usuario[0].nome}" />
      <q:set name="session.userRole" value="{usuario[0].papel}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/painel" />
    </q:if>
    <q:flash type="error" message="E-mail ou senha inválidos" />
    <q:redirect url="/login" />
  </q:action>
  <html><body><q:if condition="flash"><p>{flash}</p></q:if></body></html>
</q:component>'''

PAINEL = ('<q:component name="painel" require_auth="true" require_role="admin" '
          'xmlns:q="https://quantum.lang/ns"><html><body><p>Olá, {session.userName}</p>'
          '</body></html></q:component>')


@pytest.fixture
def servidor(tmp_path):
    banco = tmp_path / 'app.db'
    con = sqlite3.connect(banco)
    con.execute('create table usuarios (id integer primary key, email text unique, '
                'nome text, papel text, senha_hash text)')
    con.execute('insert into usuarios (email, nome, papel, senha_hash) values (?,?,?,?)',
                ('ana@exemplo.com', 'Ana', 'admin', hash_password('senha-da-ana')))
    con.commit()
    con.close()

    componentes = tmp_path / 'components'
    componentes.mkdir()
    (componentes / 'login.q').write_text(LOGIN, encoding='utf-8')
    (componentes / 'painel.q').write_text(PAINEL, encoding='utf-8')
    config = tmp_path / 'config.yaml'
    config.write_text(
        f"server:\n  debug: false\npaths:\n  components: {componentes.as_posix()}\n"
        "  static: ./static\n  logs: ./logs\n"
        "logging:\n  level: ERROR\n  console: false\n  file: false\n"
        f"datasources:\n  db:\n    driver: sqlite\n    database: {banco.as_posix()}\n",
        encoding='utf-8')
    server = QuantumWebServer(str(config))
    server.app.config['TESTING'] = True
    return server.app


def texto(resposta):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', resposta.get_data(as_text=True)))


class TestLogin:
    def test_senha_certa_abre_o_painel(self, servidor):
        cliente = servidor.test_client()
        r = cliente.post('/login', data={'email': 'ana@exemplo.com', 'senha': 'senha-da-ana'})
        assert r.headers['Location'].endswith('/painel'), texto(cliente.get('/login'))
        painel = cliente.get('/painel')
        assert painel.status_code == 200
        assert 'Olá, Ana' in texto(painel)

    def test_senha_errada_nao_abre(self, servidor):
        cliente = servidor.test_client()
        r = cliente.post('/login', data={'email': 'ana@exemplo.com', 'senha': 'chute'})
        assert r.headers['Location'].endswith('/login')
        assert cliente.get('/painel').status_code == 302
        assert 'E-mail ou senha inválidos' in texto(cliente.get('/login'))

    def test_usuario_inexistente_nao_abre(self, servidor):
        cliente = servidor.test_client()
        cliente.post('/login', data={'email': 'ninguem@exemplo.com', 'senha': 'senha-da-ana'})
        assert cliente.get('/painel').status_code == 302


class TestQueryDentroDeAction:
    def test_a_action_enxerga_o_datasource_da_config(self, servidor):
        # O sintoma do defeito 2: a mensagem de datasource não declarado.
        cliente = servidor.test_client()
        cliente.post('/login', data={'email': 'ana@exemplo.com', 'senha': 'chute'})
        assert 'is not declared locally' not in texto(cliente.get('/login'))


class TestFuncoesDeSenha:
    def test_hash_e_verificacao(self):
        h = hash_password('segredo')
        assert h != 'segredo'
        assert verify_password('segredo', h)
        assert not verify_password('outro', h)

    @pytest.mark.parametrize('senha,hash_', [
        ('', '$2b$12$abc'), ('segredo', ''), ('segredo', None),
        ('segredo', 'isto-nao-e-um-hash'), (None, None),
    ])
    def test_dado_ruim_e_falso_nunca_erro(self, senha, hash_):
        assert verify_password(senha, hash_) is False

    def test_hash_de_senha_vazia_e_recusado(self):
        with pytest.raises(ValueError):
            hash_password('')
