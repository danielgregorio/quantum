"""admin.settings.* and the YAML editor that keeps comments."""

import shutil

import pytest
import yaml

from quantum_admin.services import _yaml_editor as editor
from quantum_admin.services import settings as svc

REPO_CONFIG = __import__("pathlib").Path(__file__).resolve().parents[2] / "quantum.config.yaml"

CONFIG = """# Server configuration
server:
  # Port
  port: 8080   # default
  host: 127.0.0.1

  debug: false

paths:
  components: ./components
"""


@pytest.fixture(autouse=True)
def isolated(isolated_admin):
    return isolated_admin


class TestEditor:
    def test_it_changes_only_the_value_and_keeps_comments(self):
        new = editor.edit_text(CONFIG, {("server", "port"): 9090, ("server", "debug"): True})
        assert "  port: 9090   # default" in new
        assert "# Port" in new and "# Server configuration" in new
        assert "  debug: true" in new
        assert new.count("\n") == CONFIG.count("\n")

    def test_it_inserts_a_missing_key_and_section(self):
        new = editor.edit_text(CONFIG, {("server", "reload"): False, ("logging", "level"): "INFO"})
        data = yaml.safe_load(new)
        assert data["server"]["reload"] is False and data["logging"] == {"level": "INFO"}
        assert data["paths"] == {"components": "./components"}

    def test_text_that_looks_like_another_type_is_quoted(self, tmp_path):
        path = tmp_path / "c.yaml"
        path.write_text(CONFIG, encoding="utf-8")
        editor.write_values(path, {("server", "host"): "true", ("server", "port"): 8081})
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["server"]["host"] == "true" and data["server"]["port"] == 8081

    def test_it_refuses_when_the_result_would_not_be_what_was_asked(self, tmp_path):
        # a duplicated key: editing the first does not change the effective value (YAML uses the last)
        path = tmp_path / "c.yaml"
        original = "server:\n  port: 1\n  port: 2\n"
        path.write_text(original, encoding="utf-8")
        with pytest.raises(editor.YamlEditError):
            editor.write_values(path, {("server", "port"): 3})
        assert path.read_text(encoding="utf-8") == original

    def test_on_the_repository_s_real_config_only_the_lines_asked_for_change(self, tmp_path):
        copy = tmp_path / "quantum.config.yaml"
        shutil.copy2(REPO_CONFIG, copy)
        before = copy.read_text(encoding="utf-8").splitlines()
        editor.write_values(copy, {("server", "port"): 8181, ("server", "debug"): False})
        after = copy.read_text(encoding="utf-8").splitlines()
        assert len(before) == len(after)
        different = [(a, d) for a, d in zip(before, after) if a != d]
        assert len(different) == 1 and "8181" in different[0][1]
        assert sum(1 for l in after if l.lstrip().startswith("#")) == sum(1 for l in before if l.lstrip().startswith("#"))


class TestServerConfig:
    def test_it_reads_the_file(self, isolated):
        (isolated / "quantum.config.yaml").write_text(CONFIG, encoding="utf-8")
        c = svc.server_config()
        assert c["found"] and c["server"] == {"port": 8080, "host": "127.0.0.1", "debug": False, "reload": False}

    def test_without_a_file(self):
        assert svc.server_config()["found"] is False

    def test_saving_keeps_comments(self, isolated):
        (isolated / "quantum.config.yaml").write_text(CONFIG, encoding="utf-8")
        svc.save_server_config(port=9000, host="127.0.0.1", debug=True, log_level="warning")
        text = (isolated / "quantum.config.yaml").read_text(encoding="utf-8")
        assert "# Port" in text and "port: 9000   # default" in text
        assert yaml.safe_load(text)["logging"]["level"] == "WARNING"

    @pytest.mark.parametrize("fields,reason", [
        ({"port": 70000, "host": "127.0.0.1"}, "between 1 and 65535"),
        ({"port": "abc", "host": "127.0.0.1"}, "must be a number"),
        ({"port": 8080, "host": ""}, "host is required"),
        ({"port": 8080, "host": "0.0.0.0", "debug": True}, "debug cannot be on"),
        ({"port": 8080, "host": "127.0.0.1", "log_level": "verbose"}, "log_level"),
    ])
    def test_invalid_values_are_errors_and_nothing_is_written(self, isolated, fields, reason):
        (isolated / "quantum.config.yaml").write_text(CONFIG, encoding="utf-8")
        with pytest.raises(svc.SettingsError, match=reason):
            svc.save_server_config(**fields)
        assert (isolated / "quantum.config.yaml").read_text(encoding="utf-8") == CONFIG


def test_the_global_settings_mask_secrets(isolated):
    (isolated / "quantum_admin" / "settings" / "global.yaml").write_text(
        "email:\n  smtp_password: the-real-password\n  smtp_user: me\nsecurity:\n  jwt_secret: ${JWT_SECRET}\n",
        encoding="utf-8")
    g = svc.global_get()
    assert "the-real-password" not in str(g)
    assert g["email"]["smtp_password"] == "****" and g["email"]["smtp_user"] == "me"
    assert g["security"]["jwt_secret"] == "${JWT_SECRET}"


def test_the_system_info_counts_real_registrations():
    info = svc.system_info()
    assert info["parser_tags"] > 20 and info["executors"] > 20       # the old screen showed 0
