"""
Root conftest.py - Registers Quantum pytest plugins globally.

This file ensures that .q regression tests and dataset-driven tests
are all discovered by pytest.
"""

import logging
import os
import sys
from pathlib import Path

import pytest

# Ensure src is importable from any test location

# Ensure project root is importable (for test_database.py etc.)

# Register custom plugins
pytest_plugins = [
    "tests.plugins.quantum_q_plugin",
]

# The .q examples' `test-sqlite` datasource is a fresh database per test, in a
# temporary folder (tests/plugins/quantum_q_plugin.py). It used to be rebuilt
# once per session at <repo>/test_data/quantum_test.db — a test run writing
# into the repository.


def pytest_configure(config):
    """No test writes into the repository: a log folder or an undeclared
    static folder that would fall inside the checkout (./logs, ./static,
    relative to the folder the tests run in) points at a temporary folder of
    this process instead. A hook, not a fixture: the .q items request no
    fixtures."""
    import tempfile
    from quantum.runtime import logging_setup, web_config
    folder = Path(tempfile.mkdtemp(prefix='quantum-tests-paths-'))
    web_config.DEFAULT_PATHS['logs'] = str(folder / 'logs')

    # A server started with the repository's own quantum.config.yaml (paths.logs:
    # ./logs, logging.file: true) wrote its log into the checkout. Everything else
    # of that config stays; only a log folder inside the repository moves.
    repo = Path(__file__).resolve().parent
    setup_logging = logging_setup.setup_logging

    def outside_the_repo(config):
        logs = Path((config.get('paths') or {}).get('logs') or web_config.DEFAULT_PATHS['logs']).resolve()
        if logs == repo or repo in logs.parents:
            config = {**config, 'paths': {**(config.get('paths') or {}), 'logs': str(folder / 'logs')}}
        return setup_logging(config)

    logging_setup.setup_logging = outside_the_repo

    # The page bundles (styles-<hash>.css, scripts-<hash>.js) go to paths.static.
    # A config that does not declare it gets ./static, and a server started from
    # the checkout with such a config wrote the bundles into the repository. A
    # project without a config (served from its own folder) keeps its ./static.
    load_config = web_config.ConfigLoading._load_config

    def load_outside_the_repo(self, config_path):
        config = load_config(self, config_path)
        try:
            import yaml
            declared = (yaml.safe_load(Path(config_path).read_text(encoding='utf-8')) or {}).get('paths') or {}
        except Exception:
            declared = {}
        static = Path(config['paths']['static']).resolve()
        if 'static' not in declared and (static == repo or repo in static.parents):
            config['paths']['static'] = str(folder / 'static')
        return config

    web_config.ConfigLoading._load_config = load_outside_the_repo


# ------------------------------------------------------------------ no test writes into the repository
#
# The suite used to leave test_data/quantum_test.db, quantum_jobs.db,
# logs/quantum.log, .quantum/knowledge and bundles in static/ in the checkout.
# The controller records every file git reports (untracked and ignored
# included, with size and time) before the run and compares after it; anything
# new or changed fails the run, naming the files. Caches do not count.

REPO = Path(__file__).resolve().parent
# coverage.xml and htmlcov/ are the reports `pytest --cov-report=...` writes
# (CI does), not something a test wrote.
_CACHES = ('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.hypothesis', '.coverage',
           'coverage.xml', 'htmlcov')


def _repository_files():
    import subprocess
    try:
        out = subprocess.run(['git', 'status', '--porcelain', '--ignored', '--untracked-files=all', '-z'],
                             cwd=REPO, capture_output=True, text=True, timeout=120, check=True).stdout
    except Exception:
        return None                              # not a git checkout: no guard
    files = {}
    for entry in filter(None, out.split('\0')):
        path = entry[3:]
        if any(part in _CACHES for part in Path(path).parts) or '.pyc' in path:
            continue
        try:
            stat = (REPO / path).stat()
            files[path] = (entry[:2], stat.st_size, stat.st_mtime_ns)
        except OSError:
            files[path] = (entry[:2], None, None)
    return files


def pytest_sessionstart(session):
    if not os.environ.get("PYTEST_XDIST_WORKER"):
        session.config._repository_files = _repository_files()


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, '_repository_files', None)
    if before is None or os.environ.get("PYTEST_XDIST_WORKER"):
        return
    after = _repository_files() or {}
    written = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    if written:
        reporter = session.config.pluginmanager.get_plugin('terminalreporter')
        if reporter is not None:
            reporter.write_sep('=', 'the tests wrote into the repository', red=True)
            for path in written:
                reporter.write_line(f'  {path}')
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


# Laboratory (SUPPORT_TIERS.md): the game engine, the Godot codegen and the
# React Native target. Their tests stay in the suite (decision D1) but run in a
# CI job of their own, so a red build says at once whether the Core or the
# Laboratory broke. Marked here, by file, so a new test cannot forget it.
LABORATORY = ("test_game_", "test_godot_", "test_mobile_target", "game_engine_2d", "test-mobile.q")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if any(marca in item.nodeid for marca in LABORATORY):
            item.add_marker(pytest.mark.laboratory)




@pytest.fixture(autouse=True)
def _logging_intacto():
    """Every test starts with the logging state the previous one found.

    The web server applies the project's `logging:` config to the `quantum`
    loggers (level, propagate, handlers) and some tests call
    logging.disable(). Left behind, that silenced the next test that reads
    the log — which passed or failed depending on test order, and a parallel
    run (pytest -n) changes the order.
    """
    manager = logging.Logger.manager
    antes_disable = manager.disable
    estados = {nome: (lg.level, lg.propagate, list(lg.handlers), lg.disabled)
               for nome, lg in list(manager.loggerDict.items())
               if isinstance(lg, logging.Logger) and nome.split('.')[0] == 'quantum'}
    raiz = (logging.root.level, list(logging.root.handlers))
    yield
    logging.disable(antes_disable)

    def _close_added(current, kept):
        # A handler the test added (a FileHandler from the web server's
        # logging config) is dropped here; close it, or its file stays open
        # until garbage collection and warns in some later test.
        for handler in current:
            if handler not in kept:
                handler.close()

    for nome, lg in list(manager.loggerDict.items()):
        if not isinstance(lg, logging.Logger) or nome.split('.')[0] != 'quantum':
            continue
        if nome in estados:
            lg.level, lg.propagate, handlers, lg.disabled = estados[nome]
            _close_added(lg.handlers, handlers)
            lg.handlers[:] = handlers
        else:
            lg.setLevel(logging.NOTSET)
            lg.propagate = True
            _close_added(lg.handlers, [])
            lg.handlers.clear()
            lg.disabled = False
    logging.root.setLevel(raiz[0])
    _close_added(logging.root.handlers, raiz[1])
    logging.root.handlers[:] = raiz[1]
