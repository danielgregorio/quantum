"""Conformance: SPEC.md section 8a (Configuration)."""

import sqlite3

import pytest

from quantum.cli.runner import load_config
from quantum.core.config_env import ConfigEnvError, expand_env


def write(tmp_path, text):
    path = tmp_path / 'quantum.config.yaml'
    path.write_text(text, encoding='utf-8')
    return str(path)


class TestEnvironmentVariables:
    def test_replaced_in_the_cli(self, tmp_path, monkeypatch):
        # CFG-1 (was G4: read literally)
        monkeypatch.setenv('QUANTUM_T_DB', './data/app.db')
        config = load_config(write(tmp_path, 'datasources:\n  db:\n    database: ${QUANTUM_T_DB}\n'))
        assert config['datasources']['db']['database'] == './data/app.db'

    def test_default_literal_and_lists(self, monkeypatch):
        # CFG-1
        monkeypatch.delenv('QUANTUM_T_MISSING', raising=False)
        monkeypatch.setenv('QUANTUM_T_HOST', 'db.local')
        assert expand_env({'a': ['${QUANTUM_T_HOST}:5432', '${QUANTUM_T_MISSING:-5}'],
                           'b': 'costs $$10', 'c': 7}) == \
            {'a': ['db.local:5432', '5'], 'b': 'costs $10', 'c': 7}

    def test_missing_without_a_default_is_an_error_that_names_it(self, tmp_path, monkeypatch):
        # CFG-1
        monkeypatch.delenv('QUANTUM_T_PASSWORD', raising=False)
        with pytest.raises(ConfigEnvError, match=r'datasources\.db\.password uses \$\{QUANTUM_T_PASSWORD\}'):
            load_config(write(tmp_path, 'datasources:\n  db:\n    password: ${QUANTUM_T_PASSWORD}\n'))

    def test_the_server_uses_the_datasource_from_the_variable(self, serve_pages, tmp_path, monkeypatch):
        # CFG-1: the replaced value reaches the query of a served page.
        # chdir: without the replacement, sqlite would create a file named
        # '${QUANTUM_T_DB}' in the current directory (it happened, in the repo).
        monkeypatch.chdir(tmp_path)
        db = tmp_path / 'env.db'
        connection = sqlite3.connect(db)
        connection.execute('create table t (v text)')
        connection.execute("insert into t values ('from the env')")
        connection.commit()
        connection.close()
        monkeypatch.setenv('QUANTUM_T_DB', db.as_posix())
        client = serve_pages(
            datasources_yaml='datasources:\n  db:\n    driver: sqlite\n    database: ${QUANTUM_T_DB}\n',
            read=('<q:component name="read" xmlns:q="https://quantum.lang/ns">'
                  '<q:query name="rows" datasource="db">SELECT v FROM t</q:query>'
                  '<p>{rows[0].v}</p></q:component>'))
        assert 'from the env' in client.get('/read').get_data(as_text=True)


class TestSecurityKeys:
    def test_a_body_over_the_limit_is_refused(self, serve_pages):
        # CFG-2 (before: max_content_length never reached Flask; uploads had no limit)
        c = serve_pages(datasources_yaml="security:\n  max_content_length: 1000\n",
                        p='<q:component name="p" xmlns:q="https://quantum.lang/ns"><p>ok</p></q:component>')
        assert c.post('/p', data={'x': 'a' * 5000}).status_code == 413
        assert c.get('/p').status_code == 200

    def test_the_default_limit_is_16_mb(self, serve_pages):
        # CFG-2
        c = serve_pages(p='<q:component name="p" xmlns:q="https://quantum.lang/ns"><p>ok</p></q:component>')
        assert c.application.config['MAX_CONTENT_LENGTH'] == 16 * 1024 * 1024

    def test_a_key_nothing_reads_is_warned_about(self, serve_pages):
        # CFG-2: csrf_protection: true protected nothing, and nothing said so
        import logging
        records = []
        collector = logging.Handler(logging.WARNING)
        collector.emit = records.append
        logger = logging.getLogger('quantum')   # propagate and level come from another test's config
        level = logger.level
        logger.setLevel(logging.WARNING)
        logger.addHandler(collector)
        try:
            serve_pages(datasources_yaml="security:\n  csrf_protection: true\n  rate_limiting: {enabled: true}\n",
                        p='<q:component name="p" xmlns:q="https://quantum.lang/ns"><p>ok</p></q:component>')
        finally:
            logger.removeHandler(collector)
            logger.setLevel(level)
        warnings = ' '.join(r.getMessage() for r in records)
        assert 'security.csrf_protection, rate_limiting are not implemented' in warnings

    @pytest.mark.parametrize('attribute', ['require_auth="true"', 'csrf="false"', 'rate_limit="10/minute"'])
    def test_an_action_attribute_that_never_applied_is_an_error(self, attribute):
        # AUTH-7 (before: require_auth on an action was read and ignored — the action ran for anyone)
        from quantum.core.parser import QuantumParser, QuantumParseError
        with pytest.raises(QuantumParseError, match='never enforced'):
            QuantumParser().parse('<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                                  f'<q:action name="a" {attribute}><q:set name="x" value="1"/></q:action></q:component>')


class TestKeysThatWork:
    def test_the_log_format(self, tmp_path):
        # CFG-3 (before: logging.format was documented and ignored)
        import logging
        from quantum.runtime.logging_setup import setup_logging
        setup_logging({'logging': {'level': 'INFO', 'console': False, 'file': True, 'filename': 'x.log',
                                   'format': 'FMT|%(levelname)s|%(message)s'},
                       'paths': {'logs': str(tmp_path)}})
        logging.getLogger('quantum.test').warning('hello')
        for h in logging.getLogger('quantum').handlers:
            h.flush()
        assert 'FMT|WARNING|hello' in (tmp_path / 'x.log').read_text(encoding='utf-8')

    def test_the_migrations_folder_from_the_config(self, tmp_path):
        # CFG-3 (before: paths.migrations was ignored; always ./migrations)
        from quantum.cli.migrations import MigrationRunner
        (tmp_path / 'quantum.config.yaml').write_text(
            'paths:\n  migrations: ./db/versions\ndatasources:\n  db:\n    driver: sqlite\n    database: app.db\n',
            encoding='utf-8')
        (tmp_path / 'db' / 'versions').mkdir(parents=True)
        (tmp_path / 'db' / 'versions' / 'V001_t.sql').write_text('CREATE TABLE t (x INT);', encoding='utf-8')
        assert [r['status'] for r in MigrationRunner(project_path=tmp_path).up()] == ['applied']

    def test_an_unknown_key_in_server_paths_logging_is_warned_about(self):
        # CFG-3
        import logging
        from quantum.runtime.web_server import _validate_config
        records = []
        collector = logging.Handler(logging.WARNING)
        collector.emit = records.append
        logger = logging.getLogger('quantum')
        logger.setLevel(logging.WARNING)
        logger.addHandler(collector)
        try:
            _validate_config({'server': {'port': 1, 'workers': 4}, 'paths': {'templates': 'x'},
                              'logging': {'rotate': True}}, 'cfg')
        finally:
            logger.removeHandler(collector)
        warnings = ' '.join(r.getMessage() for r in records)
        assert 'server.workers' in warnings and 'paths.templates' in warnings and 'logging.rotate' in warnings
