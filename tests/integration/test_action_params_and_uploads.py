"""`q:param` had two implementations, and they disagreed.

`ComponentRuntime._coerce_param` and `ActionHandler._validate_type` did the
same thing two ways. The action only knew `integer`, `decimal` and `float`;
everything else fell into a final `return str(value)`. Two consequences,
reproduced here:

  * `type="number"` — 32 uses in the repository — was not converted nor
    checked against min/max inside a q:action, while inside a component it
    was. `min="18"` accepted 7.

  * `type="file"` — 5 uses, including components/upload_demo.q — passed the
    upload object through `str()`, and what reached the context was its repr:
    `"<FileStorage: 'photo.png' ('image/png')>"`. The
    `<q:file action="upload" file="{avatar}">` got that string instead of the
    file, so uploading through a form did not work end to end, even after
    request.files started being read.

Both sides now use quantum/runtime/param_validation.py.
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
    """A minimal q:param, with the attributes validation reads."""

    def __init__(self, name, type='string', **kw):
        self.name = name
        self.type = type
        self.required = kw.get('required', False)
        self.default = kw.get('default')
        for attr in ('min', 'max', 'minlength', 'maxlength', 'pattern',
                     'enum'):
            setattr(self, attr, kw.get(attr))


class TestAFileNeverBecomesText:
    SRC = (
        '<q:component name="U">'
        '<q:action name="send" method="POST">'
        '<q:param name="avatar" type="file" required="true" />'
        '<q:set name="file_name" value="{avatar}" />'
        '</q:action></q:component>'
    )

    def _run(self, app, form):
        handler = ActionHandler(ComponentRuntime())
        action = _action_from(self.SRC)
        captured = {}

        # Spy on the context: that is where the wrong value showed.
        original = handler._execute_action_body

        def spy(act, context):
            value = context.get_variable('avatar')
            captured['avatar'] = value
            captured['type'] = type(value).__name__
            # Read HERE: the temporary file closes when the request context ends.
            if not isinstance(value, str) and hasattr(value, 'read'):
                captured['name'] = value.filename
                captured['bytes'] = value.read()
            return original(act, context)

        handler._execute_action_body = spy
        with app.test_request_context(
            "/x", method="POST", data=form,
            content_type="multipart/form-data",
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                handler.handle_action(action)
        return captured

    def test_the_context_gets_the_upload_object(self, app):
        seen = self._run(
            app, {"avatar": (io.BytesIO(b"real bytes"), "photo.png")})

        assert not isinstance(seen['avatar'], str), (
            f"the upload became text: {seen['avatar']!r}")
        assert seen['name'] == "photo.png"
        assert seen['bytes'] == b"real bytes"

    def test_the_filestorage_repr_never_reaches_the_context(self, app):
        seen = self._run(
            app, {"avatar": (io.BytesIO(b"x"), "photo.png")})
        assert seen['type'] == 'FileStorage', seen['type']
        assert not isinstance(seen['avatar'], str)

    def test_declaring_the_file_as_a_string_is_an_error_not_a_conversion(self, app):
        """Before, this passed silently, with the repr instead of the file."""
        handler = ActionHandler(ComponentRuntime())
        src = (
            '<q:component name="U">'
            '<q:action name="send" method="POST">'
            '<q:param name="avatar" type="string" required="true" />'
            '</q:action></q:component>'
        )
        action = _action_from(src)
        with app.test_request_context(
            "/x", method="POST",
            data={"avatar": (io.BytesIO(b"x"), "photo.png")},
            content_type="multipart/form-data",
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                target, status = handler.handle_action(action)
        # A ValidationError becomes a 302 redirect with a flash — not a
        # silently corrupted upload.
        assert status == 302


class TestUploadWithoutADeclaredQParam:
    """`<q:file file="{avatar}">` without a `<q:param name="avatar">` above.

    Only the VALIDATED params entered the context, so an undeclared upload
    never arrived — "File variable 'avatar' not found" — although
    `_extract_form_data` had already collected it and the documentation
    promised `q.files`.
    """

    def test_the_file_reaches_the_context(self, app, tmp_path):
        from quantum.runtime.file_upload_service import FileUploadService

        handler = ActionHandler(ComponentRuntime())
        src = (
            '<q:component name="U">'
            '<q:action name="send" method="POST">'
            '<q:set name="x" value="1" />'
            '</q:action></q:component>'
        )
        action = _action_from(src)
        seen = {}
        original = handler._execute_action_body

        service = FileUploadService(root=str(tmp_path))

        def spy(act, context):
            avatar = context.get_variable('avatar')
            seen['avatar'] = avatar
            seen['files'] = context.get_variable('files')
            if avatar is not None and not isinstance(avatar, str):
                seen['name'] = avatar.filename
                # And it really works for the upload — done in here, as the
                # temporary file closes when the request ends.
                seen['result'] = service.upload_file(
                    file=avatar, destination="avatars")
            return original(act, context)

        handler._execute_action_body = spy
        with app.test_request_context(
            "/x", method="POST",
            data={"avatar": (io.BytesIO(b"content"), "photo.png")},
            content_type="multipart/form-data",
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                handler.handle_action(action)

        assert seen['avatar'] is not None, "the upload did not reach the context"
        assert seen['name'] == "photo.png"
        assert 'avatar' in (seen['files'] or {})
        assert seen['result'].get("success"), seen['result']
        written = list(pathlib.Path(tmp_path).rglob("*.png"))
        assert written and written[0].read_bytes() == b"content"


class TestBothSidesAgree:
    """The same q:param, the same result, in the component and in the action."""

    CASES = [
        (_Param('n', 'number', min=18), '7', 'refuses'),
        (_Param('n', 'number', min=18), '30', 30.0),
        (_Param('n', 'numeric'), '2.5', 2.5),
        (_Param('n', 'int'), '42', 42),
        (_Param('n', 'long'), '42', 42),
        (_Param('n', 'double'), '1.5', 1.5),
        (_Param('n', 'integer'), 'abc', 'refuses'),
        (_Param('n', 'boolean'), 'on', True),
        (_Param('n', 'email'), 'not-an-email', 'refuses'),
        (_Param('n', 'string', maxlength=3), 'abcd', 'refuses'),
        (_Param('n', 'string', enum='a,b'), 'c', 'refuses'),
        (_Param('n', 'string', pattern=r'^\\d+$'), 'xyz', 'refuses'),
    ]

    @pytest.mark.parametrize("param,given,expected", CASES)
    def test_component_and_action_give_the_same_verdict(
            self, param, given, expected):
        runtime = ComponentRuntime()
        handler = ActionHandler(runtime)

        # Component side
        value_c, error_c = runtime._coerce_param(param, given)
        if not error_c:
            error_c = '; '.join(runtime._check_param_rules(param, value_c))

        # Action side
        error_a = None
        value_a = None
        try:
            value_a = handler._validate_type(param, given)
            handler._validate_rules(param, value_a)
        except ValidationError as exc:
            error_a = str(exc)

        assert bool(error_c) == bool(error_a), (
            f"component={error_c!r} action={error_a!r}")
        if expected == 'refuses':
            assert error_c, "both accepted an invalid value"
        else:
            assert not error_c, error_c
            assert value_c == expected and value_a == expected
            assert type(value_c) is type(value_a)


class TestNumberInsideAnAction:
    """The concrete case: `type="number" min="18"` in a q:action."""

    SRC = (
        '<q:component name="C">'
        '<q:action name="save" method="POST">'
        '<q:param name="age" type="number" min="18" />'
        '<q:redirect url="/ok" />'
        '</q:action></q:component>'
    )

    def _status(self, app, value):
        handler = ActionHandler(ComponentRuntime())
        with app.test_request_context("/x", method="POST",
                                      data={"age": value}):
            with contextlib.redirect_stdout(io.StringIO()):
                target, status = handler.handle_action(_action_from(self.SRC))
        return target, status

    def test_below_the_minimum_is_refused(self, app):
        target, status = self._status(app, "7")
        assert status == 302 and target != "/ok", (target, status)

    def test_above_the_minimum_passes_and_becomes_a_number(self, app):
        handler = ActionHandler(ComponentRuntime())
        seen = {}
        original = handler._execute_action_body

        def spy(act, context):
            seen['age'] = context.get_variable('age')
            return original(act, context)

        handler._execute_action_body = spy
        with app.test_request_context("/x", method="POST",
                                      data={"age": "30"}):
            with contextlib.redirect_stdout(io.StringIO()):
                target, status = handler.handle_action(_action_from(self.SRC))

        assert (target, status) == ("/ok", 302)
        assert seen['age'] == 30.0
        assert not isinstance(seen['age'], str)
