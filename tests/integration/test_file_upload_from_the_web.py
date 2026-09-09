"""
q:file action="upload" could not be reached from a browser.

The executor reads the file from a context variable:

    <q:file action="upload" file="{avatar}" destination="..." />

and _extract_form_data returned request.form only. request.files never
entered the context, so `avatar` was never defined and every upload raised
"File variable 'avatar' not found" — for the one tag whose entire purpose is
handling a browser upload.

These go through a real multipart POST, so a pass means a file actually
arrived and was written.
"""

import io
import pathlib

import pytest

pytest.importorskip("flask")

from quantum.runtime.action_handler import ActionHandler  # noqa: E402


@pytest.fixture
def app():
    from flask import Flask
    application = Flask(__name__)
    application.config["SECRET_KEY"] = "test"
    return application


class TestTheFilesReachTheContext:
    def test_an_uploaded_file_is_in_the_extracted_data(self, app):
        handler = ActionHandler.__new__(ActionHandler)
        with app.test_request_context(
            "/", method="POST",
            data={"nome": "maria",
                  "avatar": (io.BytesIO(b"conteudo"), "foto.png")},
            content_type="multipart/form-data",
        ):
            data = handler._extract_form_data()

            assert data["nome"] == "maria"
            assert data["avatar"].filename == "foto.png"
            assert data["avatar"].read() == b"conteudo"

    def test_files_are_also_grouped(self, app):
        handler = ActionHandler.__new__(ActionHandler)
        with app.test_request_context(
            "/", method="POST",
            data={"avatar": (io.BytesIO(b"x"), "foto.png")},
            content_type="multipart/form-data",
        ):
            data = handler._extract_form_data()

        assert "avatar" in data["files"]

    def test_an_empty_file_input_is_not_a_file(self, app):
        # A form submitted with nothing chosen still posts the part.
        handler = ActionHandler.__new__(ActionHandler)
        with app.test_request_context(
            "/", method="POST",
            data={"nome": "maria", "avatar": (io.BytesIO(b""), "")},
            content_type="multipart/form-data",
        ):
            data = handler._extract_form_data()

        assert "avatar" not in data
        assert data["nome"] == "maria"

    def test_a_plain_form_post_is_unchanged(self, app):
        handler = ActionHandler.__new__(ActionHandler)
        with app.test_request_context(
            "/", method="POST", data={"nome": "maria", "idade": "41"}
        ):
            assert handler._extract_form_data() == {"nome": "maria",
                                                    "idade": "41"}

    def test_a_json_post_is_unchanged(self, app):
        handler = ActionHandler.__new__(ActionHandler)
        with app.test_request_context("/", method="POST", json={"a": 1}):
            assert handler._extract_form_data() == {"a": 1}


class TestTheFileActuallyLands:
    def test_the_upload_service_writes_what_was_posted(self, app, tmp_path):
        """The whole chain: multipart POST -> context -> file on disk."""
        from quantum.runtime.file_upload_service import FileUploadService

        service = FileUploadService(root=str(tmp_path))
        handler = ActionHandler.__new__(ActionHandler)

        with app.test_request_context(
            "/", method="POST",
            data={"avatar": (io.BytesIO(b"bytes reais"), "foto.png")},
            content_type="multipart/form-data",
        ):
            data = handler._extract_form_data()
            result = service.upload_file(
                file=data["avatar"], destination="avatares")

        assert result.get("success"), result
        written = list(pathlib.Path(tmp_path).rglob("*.png"))
        assert written, "nothing was written to disk"
        assert written[0].read_bytes() == b"bytes reais"
