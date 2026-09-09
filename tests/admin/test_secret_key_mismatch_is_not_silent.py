"""Um segredo que a chave atual nao abre e um erro, nao um valor.

`decrypt_or_legacy` tinha um `except Exception: return stored` que valia para
os dois motivos de falha:

  1. o valor nunca foi cifrado (linhas antigas, gravadas quando a coluna
     `credentials_encrypted` guardava JSON puro) — devolver o guardado esta
     certo;
  2. o valor E um token Fernet e a QUANTUM_ENCRYPTION_KEY atual nao o abre
     (chave trocada, perdida, ou ausente num deploy novo, quando o modulo cai
     na chave padrao) — devolver o guardado entrega o TEXTO CIFRADO como se
     fosse a senha.

O caso 2 vazava de duas formas: a conexao tentava autenticar com o base64 do
token e o erro apontava para "senha invalida"; e o proximo save re-cifrava
esse token com a chave nova, destruindo para sempre a senha que so a chave
antiga abria — sem nada no caminho avisando.
"""

import base64
import importlib
import os
import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

pytest.importorskip("cryptography", reason="the admin needs cryptography")


def _modulo_com_chave(chave):
    """Recarrega o secret_manager com uma QUANTUM_ENCRYPTION_KEY dada.

    O cipher e montado uma vez num singleton de modulo, entao trocar a chave
    exige reimportar — que e exatamente o que acontece quando o processo
    sobe com outra variavel de ambiente.
    """
    anterior = os.environ.get('QUANTUM_ENCRYPTION_KEY')
    if chave is None:
        os.environ.pop('QUANTUM_ENCRYPTION_KEY', None)
    else:
        os.environ['QUANTUM_ENCRYPTION_KEY'] = chave

    import secret_manager as sm
    sm.SecretManager._instance = None
    modulo = importlib.reload(sm)

    if anterior is None:
        os.environ.pop('QUANTUM_ENCRYPTION_KEY', None)
    else:
        os.environ['QUANTUM_ENCRYPTION_KEY'] = anterior
    return modulo


@pytest.fixture(autouse=True)
def _restaura_singleton():
    yield
    import secret_manager as sm
    sm.SecretManager._instance = None
    importlib.reload(sm)


class TestChaveTrocada:
    def test_nao_devolve_o_texto_cifrado_como_senha(self):
        from cryptography.fernet import Fernet

        chave_a = Fernet.generate_key().decode()
        chave_b = Fernet.generate_key().decode()

        sm_a = _modulo_com_chave(chave_a)
        cifrado = sm_a.encrypt_value("a-senha-de-verdade")

        sm_b = _modulo_com_chave(chave_b)
        with pytest.raises(ValueError) as erro:
            sm_b.decrypt_or_legacy(cifrado)

        # Antes: devolvia `cifrado` — o proprio token — como se fosse a senha.
        assert cifrado not in str(erro.value)
        assert 'QUANTUM_ENCRYPTION_KEY' in str(erro.value)

    def test_a_mensagem_avisa_que_salvar_por_cima_destroi_o_segredo(self):
        from cryptography.fernet import Fernet

        sm_a = _modulo_com_chave(Fernet.generate_key().decode())
        cifrado = sm_a.encrypt_value("segredo")

        sm_b = _modulo_com_chave(Fernet.generate_key().decode())
        with pytest.raises(ValueError) as erro:
            sm_b.decrypt_or_legacy(cifrado)
        assert 'overwrite' in str(erro.value).lower()


class TestTextoNuncaCifradoContinuaPassando:
    """O caminho legado tem de continuar funcionando — e a razao de existir."""

    def test_json_puro_e_devolvido(self):
        from cryptography.fernet import Fernet
        sm = _modulo_com_chave(Fernet.generate_key().decode())
        guardado = '{"api_key": "abc123", "region": "us-east-1"}'
        assert sm.decrypt_or_legacy(guardado) == guardado

    def test_texto_que_por_acaso_e_base64_valido_e_devolvido(self):
        """`user:pass` decodifica como base64? Nao importa: nao comeca com
        0x80 nem tem 57 bytes, entao nao e token Fernet."""
        from cryptography.fernet import Fernet
        sm = _modulo_com_chave(Fernet.generate_key().decode())
        for guardado in ('abcd', 'senha1234', base64.urlsafe_b64encode(
                b'x' * 60).decode()):
            assert sm.decrypt_or_legacy(guardado) == guardado

    def test_vazio_passa_direto(self):
        from cryptography.fernet import Fernet
        sm = _modulo_com_chave(Fernet.generate_key().decode())
        assert sm.decrypt_or_legacy('') == ''
        assert sm.decrypt_or_legacy(None) is None

    def test_a_chave_certa_abre_normalmente(self):
        from cryptography.fernet import Fernet
        chave = Fernet.generate_key().decode()
        sm = _modulo_com_chave(chave)
        cifrado = sm.encrypt_value("ok")
        assert _modulo_com_chave(chave).decrypt_or_legacy(cifrado) == "ok"


class TestDeteccaoDeToken:
    def test_reconhece_um_token_fernet(self):
        from cryptography.fernet import Fernet
        sm = _modulo_com_chave(Fernet.generate_key().decode())
        assert sm._looks_like_fernet_token(sm.encrypt_value("x")) is True

    def test_nao_confunde_texto_comum_com_token(self):
        from cryptography.fernet import Fernet
        sm = _modulo_com_chave(Fernet.generate_key().decode())
        for texto in ('senha', '{"a": 1}', 'nao-e-base64!!!', 'x' * 100):
            assert sm._looks_like_fernet_token(texto) is False, texto


class TestFailClosedEmProducao:
    """Sem QUANTUM_ENCRYPTION_KEY em producao, o admin nao pode subir.

    A chave padrao e derivada de literais no fonte (senha fixa + salt fixo,
    PBKDF2), entao qualquer um com o codigo a reconstroi e decifra tudo. O
    admin grava valores cifrados em quantum_admin/settings/*.yaml (ja
    versionado antes), entao o default RE-ARMA o vazamento a cada save. Em
    producao isso tem de ser recusa, nao um aviso que ninguem le.
    """

    def _sobe(self, env, tem_chave):
        import os, sys, subprocess
        e = dict(os.environ)
        e.pop('QUANTUM_ENCRYPTION_KEY', None); e.pop('QUANTUM_ADMIN_ENV', None)
        if env:
            e['QUANTUM_ADMIN_ENV'] = env
        if tem_chave:
            from cryptography.fernet import Fernet
            e['QUANTUM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
        raiz = str(pathlib.Path(__file__).resolve().parents[2])
        code = ("import sys; sys.path[:0]=[r'%s/quantum_admin', r'%s/quantum_admin/backend'];"
                "import secret_manager; secret_manager.SecretManager(); print('SUBIU')" % (raiz, raiz))
        return subprocess.run([sys.executable, '-c', code], env=e,
                              capture_output=True, text=True)

    def test_producao_sem_chave_recusa(self):
        r = self._sobe('production', tem_chave=False)
        assert 'SUBIU' not in r.stdout
        assert 'requires QUANTUM_ENCRYPTION_KEY' in r.stderr, r.stderr[-200:]

    def test_producao_com_chave_sobe(self):
        r = self._sobe('production', tem_chave=True)
        assert 'SUBIU' in r.stdout, r.stderr[-200:]

    def test_dev_sem_chave_sobe_com_aviso(self):
        r = self._sobe('development', tem_chave=False)
        assert 'SUBIU' in r.stdout, r.stderr[-200:]
