"""`q:param` tinha duas implementacoes, e elas discordavam.

`ComponentRuntime._coerce_param` e `ActionHandler._validate_type` faziam a
mesma coisa de dois jeitos. O action so conhecia `integer`, `decimal` e
`float`; todo o resto caia num `return str(value)` final. Duas consequencias
reproduzidas aqui:

  * `type="number"` — 32 usos no repositorio — nao era convertido nem
    checado contra min/max dentro de um q:action, enquanto dentro de um
    componente era. `min="18"` aceitava 7.

  * `type="file"` — 5 usos, incluindo components/upload_demo.q — passava o
    objeto de upload pelo `str()`, e o que chegava ao contexto era a repr:
    `"<FileStorage: 'foto.png' ('image/png')>"`. O
    `<q:file action="upload" file="{avatar}">` recebia essa string no lugar
    do arquivo, entao upload por formulario nao funcionava de ponta a ponta,
    mesmo depois de request.files passar a ser lido.

Os dois lados usam agora quantum/runtime/param_validation.py.
"""

import contextlib
import io
import pathlib

import pytest

pytest.importorskip("flask")

from flask import Flask                                       # noqa: E402

from quantum.core.parser import QuantumParser                 # noqa: E402
from quantum.runtime.action_handler import (                  # noqa: E402
    ActionHandler, ValidationError,
)
from quantum.runtime.component import ComponentRuntime        # noqa: E402


@pytest.fixture
def app():
    a = Flask(__name__)
    a.secret_key = "t"
    return a


def _action_from(src):
    ast = QuantumParser().parse(src)
    return next(s for s in ast.statements if type(s).__name__ == "ActionNode")


class _Param:
    """Um q:param minimo, com os atributos que a validacao le."""

    def __init__(self, name, type='string', **kw):
        self.name = name
        self.type = type
        self.required = kw.get('required', False)
        self.default = kw.get('default')
        for attr in ('min', 'max', 'minlength', 'maxlength', 'pattern',
                     'enum'):
            setattr(self, attr, kw.get(attr))


class TestUmArquivoNuncaViraTexto:
    SRC = (
        '<q:component name="U">'
        '<q:action name="enviar" method="POST">'
        '<q:param name="avatar" type="file" required="true" />'
        '<q:set name="nome_do_arquivo" value="{avatar}" />'
        '</q:action></q:component>'
    )

    def _executa(self, app, form):
        handler = ActionHandler(ComponentRuntime())
        action = _action_from(self.SRC)
        capturado = {}

        # Espia o contexto: e ali que o valor errado aparecia.
        original = handler._execute_action_body

        def espiao(acao, contexto):
            valor = contexto.get_variable('avatar')
            capturado['avatar'] = valor
            capturado['tipo'] = type(valor).__name__
            # Ler AQUI: o arquivo temporario fecha quando o contexto de
            # requisicao sai.
            if not isinstance(valor, str) and hasattr(valor, 'read'):
                capturado['nome'] = valor.filename
                capturado['bytes'] = valor.read()
            return original(acao, contexto)

        handler._execute_action_body = espiao
        with app.test_request_context(
            "/x", method="POST", data=form,
            content_type="multipart/form-data",
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                handler.handle_action(action)
        return capturado

    def test_o_contexto_recebe_o_objeto_de_upload(self, app):
        visto = self._executa(
            app, {"avatar": (io.BytesIO(b"bytes reais"), "foto.png")})

        assert not isinstance(visto['avatar'], str), (
            f"o upload virou texto: {visto['avatar']!r}")
        assert visto['nome'] == "foto.png"
        assert visto['bytes'] == b"bytes reais"

    def test_a_repr_do_filestorage_nunca_chega_ao_contexto(self, app):
        visto = self._executa(
            app, {"avatar": (io.BytesIO(b"x"), "foto.png")})
        assert visto['tipo'] == 'FileStorage', visto['tipo']
        assert not isinstance(visto['avatar'], str)

    def test_declarar_o_arquivo_como_string_e_erro_e_nao_conversao(self, app):
        """Antes isso passava calado, com a repr no lugar do arquivo."""
        handler = ActionHandler(ComponentRuntime())
        src = (
            '<q:component name="U">'
            '<q:action name="enviar" method="POST">'
            '<q:param name="avatar" type="string" required="true" />'
            '</q:action></q:component>'
        )
        action = _action_from(src)
        with app.test_request_context(
            "/x", method="POST",
            data={"avatar": (io.BytesIO(b"x"), "foto.png")},
            content_type="multipart/form-data",
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                destino, status = handler.handle_action(action)
        # ValidationError vira redirect 302 com flash — nao um upload
        # silenciosamente corrompido.
        assert status == 302


class TestUploadSemQParamDeclarado:
    """`<q:file file="{avatar}">` sem um `<q:param name="avatar">` acima.

    So os parametros VALIDADOS entravam no contexto, entao um upload nao
    declarado nunca chegava — "File variable 'avatar' not found" — apesar de
    `_extract_form_data` ja o ter coletado e de a documentacao prometer
    `q.files`.
    """

    def test_o_arquivo_chega_ao_contexto(self, app, tmp_path):
        from quantum.runtime.file_upload_service import FileUploadService

        handler = ActionHandler(ComponentRuntime())
        src = (
            '<q:component name="U">'
            '<q:action name="enviar" method="POST">'
            '<q:set name="x" value="1" />'
            '</q:action></q:component>'
        )
        action = _action_from(src)
        visto = {}
        original = handler._execute_action_body

        servico = FileUploadService(root=str(tmp_path))

        def espiao(acao, contexto):
            avatar = contexto.get_variable('avatar')
            visto['avatar'] = avatar
            visto['files'] = contexto.get_variable('files')
            if avatar is not None and not isinstance(avatar, str):
                visto['nome'] = avatar.filename
                # E ele serve mesmo para o upload — feito aqui dentro, o
                # arquivo temporario fecha quando a requisicao termina.
                visto['resultado'] = servico.upload_file(
                    file=avatar, destination="avatares")
            return original(acao, contexto)

        handler._execute_action_body = espiao
        with app.test_request_context(
            "/x", method="POST",
            data={"avatar": (io.BytesIO(b"conteudo"), "foto.png")},
            content_type="multipart/form-data",
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                handler.handle_action(action)

        assert visto['avatar'] is not None, "o upload nao chegou ao contexto"
        assert visto['nome'] == "foto.png"
        assert 'avatar' in (visto['files'] or {})
        assert visto['resultado'].get("success"), visto['resultado']
        escritos = list(pathlib.Path(tmp_path).rglob("*.png"))
        assert escritos and escritos[0].read_bytes() == b"conteudo"


class TestOsDoisLadosConcordam:
    """O mesmo q:param, o mesmo resultado, no componente e no action."""

    CASOS = [
        (_Param('n', 'number', min=18), '7', 'rejeita'),
        (_Param('n', 'number', min=18), '30', 30.0),
        (_Param('n', 'numeric'), '2.5', 2.5),
        (_Param('n', 'int'), '42', 42),
        (_Param('n', 'long'), '42', 42),
        (_Param('n', 'double'), '1.5', 1.5),
        (_Param('n', 'integer'), 'abc', 'rejeita'),
        (_Param('n', 'boolean'), 'on', True),
        (_Param('n', 'email'), 'nao-e-email', 'rejeita'),
        (_Param('n', 'string', maxlength=3), 'abcd', 'rejeita'),
        (_Param('n', 'string', enum='a,b'), 'c', 'rejeita'),
        (_Param('n', 'string', pattern=r'^\\d+$'), 'xyz', 'rejeita'),
    ]

    @pytest.mark.parametrize("param,entrada,esperado", CASOS)
    def test_componente_e_action_dao_o_mesmo_veredito(
            self, param, entrada, esperado):
        runtime = ComponentRuntime()
        handler = ActionHandler(runtime)

        # Lado componente
        valor_c, erro_c = runtime._coerce_param(param, entrada)
        if not erro_c:
            erro_c = '; '.join(runtime._check_param_rules(param, valor_c))

        # Lado action
        erro_a = None
        valor_a = None
        try:
            valor_a = handler._validate_type(param, entrada)
            handler._validate_rules(param, valor_a)
        except ValidationError as exc:
            erro_a = str(exc)

        assert bool(erro_c) == bool(erro_a), (
            f"componente={erro_c!r} action={erro_a!r}")
        if esperado == 'rejeita':
            assert erro_c, "os dois aceitaram um valor invalido"
        else:
            assert not erro_c, erro_c
            assert valor_c == esperado and valor_a == esperado
            assert type(valor_c) is type(valor_a)


class TestNumberDentroDeUmAction:
    """O caso concreto: `type="number" min="18"` num q:action."""

    SRC = (
        '<q:component name="C">'
        '<q:action name="salvar" method="POST">'
        '<q:param name="idade" type="number" min="18" />'
        '<q:redirect url="/ok" />'
        '</q:action></q:component>'
    )

    def _status(self, app, valor):
        handler = ActionHandler(ComponentRuntime())
        with app.test_request_context("/x", method="POST",
                                      data={"idade": valor}):
            with contextlib.redirect_stdout(io.StringIO()):
                destino, status = handler.handle_action(_action_from(self.SRC))
        return destino, status

    def test_abaixo_do_minimo_e_recusado(self, app):
        destino, status = self._status(app, "7")
        assert status == 302 and destino != "/ok", (destino, status)

    def test_acima_do_minimo_passa_e_vira_numero(self, app):
        handler = ActionHandler(ComponentRuntime())
        visto = {}
        original = handler._execute_action_body

        def espiao(acao, contexto):
            visto['idade'] = contexto.get_variable('idade')
            return original(acao, contexto)

        handler._execute_action_body = espiao
        with app.test_request_context("/x", method="POST",
                                      data={"idade": "30"}):
            with contextlib.redirect_stdout(io.StringIO()):
                destino, status = handler.handle_action(_action_from(self.SRC))

        assert (destino, status) == ("/ok", 302)
        assert visto['idade'] == 30.0
        assert not isinstance(visto['idade'], str)
