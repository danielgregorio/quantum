"""
`ComponentRuntime()` sem config nao lia quantum.config.yaml.

Isso fazia todo `q:query` cair na API opcional do admin em localhost:8000 e
falhar citando um datasource que esta declarado no proprio arquivo do
projeto. Treze das 29 falhas antigas da suite eram isso.

A correcao trouxe um custo: cada runtime relia e reparseava o arquivo — 200
runtimes, 200 leituras de disco, e a suite constroi milhares. Daí o cache por
mtime. O que os testes aqui seguram sao as duas propriedades que brigam entre
si: nao reler a toa, e enxergar quando o arquivo muda.
"""

import os
import time

import pytest

from quantum.runtime import service_container as sc
from quantum.runtime.component import ComponentRuntime


@pytest.fixture(autouse=True)
def clean_cache():
    sc._config_cache.clear()
    yield
    sc._config_cache.clear()


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "quantum.config.yaml"
    path.write_text(
        "datasources:\n"
        "  principal:\n"
        "    driver: sqlite\n"
        "    database: ./dados.db\n",
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return path


class TestItReadsTheProjectConfig:
    def test_a_runtime_without_config_sees_the_datasources(self, config_file):
        runtime = ComponentRuntime()
        assert "principal" in runtime.services.database.local_datasources

    def test_an_explicit_empty_config_still_means_empty(self, config_file):
        runtime = ComponentRuntime(config={})
        assert runtime.services.database.local_datasources == {}

    def test_an_explicit_config_wins_over_the_file(self, config_file):
        runtime = ComponentRuntime(config={
            "datasources": {"outro": {"driver": "sqlite", "database": ":memory:"}}})
        sources = runtime.services.database.local_datasources
        assert "outro" in sources and "principal" not in sources

    def test_no_file_is_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert sc.load_project_config() == {}

    def test_broken_yaml_warns_instead_of_exploding(self, tmp_path, monkeypatch, caplog):
        import logging
        (tmp_path / "quantum.config.yaml").write_text(
            "datasources: [nao\n  fecha", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        with caplog.at_level(logging.WARNING):
            assert sc.load_project_config() == {}
        assert "quantum.config.yaml" in caplog.text

    def test_a_yaml_that_is_not_a_mapping_is_ignored(self, tmp_path, monkeypatch):
        (tmp_path / "quantum.config.yaml").write_text("- um\n- dois\n",
                                                      encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert sc.load_project_config() == {}


class TestTheCache:
    def test_the_file_is_read_once_for_many_runtimes(self, config_file, monkeypatch):
        reads = {"n": 0}
        real_open = open

        def counting_open(path, *args, **kwargs):
            if str(path).endswith("quantum.config.yaml"):
                reads["n"] += 1
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", counting_open)
        for _ in range(20):
            ComponentRuntime()
        assert reads["n"] == 1, f"leu o arquivo {reads['n']} vezes"

    def test_editing_the_file_is_picked_up(self, config_file):
        assert "principal" in sc.load_project_config()["datasources"]

        # mtime tem granularidade; garantir que muda de verdade.
        time.sleep(0.01)
        config_file.write_text(
            "datasources:\n  novo:\n    driver: sqlite\n    database: ./x.db\n",
            encoding="utf-8")
        os.utime(config_file, None)

        loaded = sc.load_project_config()
        assert "novo" in loaded["datasources"]
        assert "principal" not in loaded["datasources"]

    def test_each_caller_gets_its_own_copy(self, config_file):
        # Servicos mexem na propria config; entregar o mesmo objeto deixaria
        # a mudanca de um runtime vazar para o proximo.
        first = sc.load_project_config()
        first["datasources"]["principal"]["database"] = "./mexido.db"

        second = sc.load_project_config()
        assert second["datasources"]["principal"]["database"] == "./dados.db"
