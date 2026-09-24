"""
`ComponentRuntime()` without a config did not read quantum.config.yaml.

That made every `q:query` fall through to the admin's optional API on
localhost:8000 and fail naming a datasource declared in the project's own
file. Thirteen of the suite's 29 old failures were this.

The fix brought a cost: each runtime re-read and re-parsed the file — 200
runtimes, 200 disk reads, and the suite builds thousands. Hence the cache by
mtime. What the tests here hold are the two properties that fight each other:
do not re-read for nothing, and see when the file changes.
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
        "  main:\n"
        "    driver: sqlite\n"
        "    database: ./data.db\n",
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return path


class TestItReadsTheProjectConfig:
    def test_a_runtime_without_config_sees_the_datasources(self, config_file):
        runtime = ComponentRuntime()
        assert "main" in runtime.services.database.local_datasources

    def test_an_explicit_empty_config_still_means_empty(self, config_file):
        runtime = ComponentRuntime(config={})
        assert runtime.services.database.local_datasources == {}

    def test_an_explicit_config_wins_over_the_file(self, config_file):
        runtime = ComponentRuntime(config={
            "datasources": {"other": {"driver": "sqlite", "database": ":memory:"}}})
        sources = runtime.services.database.local_datasources
        assert "other" in sources and "main" not in sources

    def test_no_file_is_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert sc.load_project_config() == {}

    def test_broken_yaml_warns_instead_of_exploding(self, tmp_path, monkeypatch, caplog):
        import logging
        (tmp_path / "quantum.config.yaml").write_text(
            "datasources: [does not\n  close", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        with caplog.at_level(logging.WARNING):
            assert sc.load_project_config() == {}
        assert "quantum.config.yaml" in caplog.text

    def test_a_yaml_that_is_not_a_mapping_is_ignored(self, tmp_path, monkeypatch):
        (tmp_path / "quantum.config.yaml").write_text("- one\n- two\n",
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
        assert reads["n"] == 1, f"read the file {reads['n']} times"

    def test_editing_the_file_is_picked_up(self, config_file):
        assert "main" in sc.load_project_config()["datasources"]

        # mtime has a granularity; make sure it really changes.
        time.sleep(0.01)
        config_file.write_text(
            "datasources:\n  new:\n    driver: sqlite\n    database: ./x.db\n",
            encoding="utf-8")
        os.utime(config_file, None)

        loaded = sc.load_project_config()
        assert "new" in loaded["datasources"]
        assert "main" not in loaded["datasources"]

    def test_each_caller_gets_its_own_copy(self, config_file):
        # Services change their own config; handing out the same object would
        # let one runtime's change leak into the next.
        first = sc.load_project_config()
        first["datasources"]["main"]["database"] = "./changed.db"

        second = sc.load_project_config()
        assert second["datasources"]["main"]["database"] == "./data.db"
