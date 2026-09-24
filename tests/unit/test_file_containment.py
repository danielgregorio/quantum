"""
q:file could delete and write anywhere on disk.

FileUploadService.delete_file did `Path(filepath).unlink()` with no
containment, and q:file's path is databound — it can carry a form value. So

    <q:file action="delete" file="{nomeArquivo}" />

with nomeArquivo = "uploads/../banco-importante.db" deleted a file outside the
upload directory and reported
{'success': True, 'message': 'File deleted successfully'}. Reproduced before
fixing. upload_file had the same hole on `destination`, which it passed
straight to Path(...).mkdir(parents=True).

Every path the service touches is now confined to a root (paths.uploads,
./uploads by default). Every destination= in this repo already points under
./uploads/, so this breaks no real usage.
"""

import pytest

from quantum.runtime.file_upload_service import FileUploadService, FileUploadError


@pytest.fixture
def svc(tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    (root / "foto.png").write_text("img", encoding="utf-8")
    (tmp_path / "banco-importante.db").write_text("dados", encoding="utf-8")
    return FileUploadService(root=str(root)), tmp_path, root


class TestDeleteIsConfined:
    def test_traversal_is_refused(self, svc):
        s, tmp, _ = svc
        out = s.delete_file("uploads/../banco-importante.db")
        assert out["success"] is False
        assert "escapes" in out["error"]
        assert (tmp / "banco-importante.db").exists(), "the victim was deleted"

    def test_an_absolute_path_outside_is_refused(self, svc):
        s, tmp, _ = svc
        out = s.delete_file(str(tmp / "banco-importante.db"))
        assert out["success"] is False
        assert (tmp / "banco-importante.db").exists()

    def test_backslash_traversal_is_refused(self, svc):
        s, tmp, _ = svc
        out = s.delete_file("uploads\\..\\banco-importante.db")
        assert out["success"] is False
        assert (tmp / "banco-importante.db").exists()

    def test_a_legitimate_delete_still_works(self, svc):
        s, _, root = svc
        out = s.delete_file("foto.png")
        assert out["success"] is True
        assert not (root / "foto.png").exists()

    def test_a_missing_file_inside_the_root_reports_not_found(self, svc):
        s, _, _ = svc
        out = s.delete_file("naoexiste.png")
        assert out["success"] is False
        assert "not found" in out["error"].lower()


class TestResolveWithinRoot:
    @pytest.mark.parametrize("bad", [
        "../x", "a/../../x", "..\\x", "", None,
    ])
    def test_refuses(self, svc, bad):
        s, _, _ = svc
        with pytest.raises(FileUploadError):
            s.resolve_within_root(bad)

    @pytest.mark.parametrize("good", ["a.txt", "sub/a.txt", "sub/deep/a.txt"])
    def test_allows(self, svc, good):
        s, _, root = svc
        assert root in s.resolve_within_root(good).parents or \
            s.resolve_within_root(good).parent == root


class TestConfiguredRoot:
    def test_the_container_passes_paths_uploads(self, tmp_path):
        from quantum.runtime.service_container import ServiceContainer
        sc = ServiceContainer({"paths": {"uploads": str(tmp_path / "custom")}})
        assert sc.file_upload.root == (tmp_path / "custom").resolve()

    def test_it_defaults_to_uploads(self):
        from quantum.runtime.service_container import ServiceContainer
        assert ServiceContainer({}).file_upload.root.name == "uploads"
