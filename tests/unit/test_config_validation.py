"""
Config was never validated, so a bad one failed later and confusingly.

The worst case: a broken quantum.config.yaml logged one WARNING and fell back
to DEFAULTS. Every datasource, the host binding and the security settings the
operator wrote were silently discarded and the server ran on defaults —
the opposite of what was configured, with a single warning line as the sign.

`port: oitenta` was accepted too, and blew up much later inside app.run(); a
datasource with no driver failed only when a query ran. The boot is where an
operator is watching, so that is where it should break.
"""

import pathlib
import pytest

from quantum.runtime.web_server import QuantumWebServer, ConfigError


def _cfg(tmp_path, text):
    f = tmp_path / "q.yaml"
    f.write_text(text, encoding="utf-8")
    return str(f)


class TestBrokenYamlDoesNotSilentlyBecomeDefaults:
    def test_it_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="could not read"):
            QuantumWebServer(_cfg(tmp_path, "server:\n  port: [8080\n"))

    def test_the_message_says_what_to_do(self, tmp_path):
        with pytest.raises(ConfigError) as e:
            QuantumWebServer(_cfg(tmp_path, "server:\n  port: [8080\n"))
        assert "move it aside" in str(e.value)


class TestTypeErrorsAreCaughtAtBoot:
    @pytest.mark.parametrize("text,needle", [
        ("server:\n  port: oitenta\n", "server.port"),
        ("server:\n  host: 8080\n", "server.host"),
        ("security:\n  python_scripting: talvez\n", "security.python_scripting"),
        ("llm:\n  timeout: sempre\n", "llm.timeout"),
    ])
    def test_rejected(self, tmp_path, text, needle):
        with pytest.raises(ConfigError, match=needle):
            QuantumWebServer(_cfg(tmp_path, text))

    def test_a_boolean_is_not_a_port(self, tmp_path):
        """bool is a subclass of int; True must not pass as a port number."""
        with pytest.raises(ConfigError, match="server.port"):
            QuantumWebServer(_cfg(tmp_path, "server:\n  port: true\n"))


class TestDatasourcesMustBeComplete:
    def test_missing_driver(self, tmp_path):
        with pytest.raises(ConfigError, match="missing 'driver'"):
            QuantumWebServer(_cfg(tmp_path, "datasources:\n  d:\n    database: x.db\n"))

    def test_missing_database(self, tmp_path):
        with pytest.raises(ConfigError, match="missing 'database'"):
            QuantumWebServer(_cfg(tmp_path, "datasources:\n  d:\n    driver: sqlite\n"))

    def test_a_complete_one_is_accepted(self, tmp_path):
        s = QuantumWebServer(_cfg(
            tmp_path,
            "datasources:\n  d:\n    driver: sqlite\n    database: x.db\n"))
        assert s.config["datasources"]["d"]["driver"] == "sqlite"


class TestUnknownSectionsWarnButDoNotBlock:
    def test_it_still_boots(self, tmp_path, caplog):
        """A newer config read by an older engine is a real situation;
        refusing to boot over it would be worse than saying so."""
        s = QuantumWebServer(_cfg(tmp_path, "servr:\n  port: 8080\n"))
        assert s.config["server"]["port"] == 8080  # default, section ignored

    def test_it_names_the_section(self, tmp_path, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="quantum"):
            QuantumWebServer(_cfg(tmp_path, "servr:\n  port: 8080\n"))
        assert "servr" in caplog.text


class TestAValidConfigStillWorks:
    def test_values_are_applied(self, tmp_path):
        s = QuantumWebServer(_cfg(
            tmp_path, "server:\n  port: 9090\n  host: 127.0.0.1\n"))
        assert s.config["server"]["port"] == 9090
        assert s.config["server"]["host"] == "127.0.0.1"

    def test_the_repo_config_is_valid(self):
        """The config shipped in this repo must pass its own validator."""
        root = pathlib.Path(__file__).resolve().parents[2]
        QuantumWebServer(str(root / "quantum.config.yaml"))
