"""Conformance: SPEC.md section 7a (Declared services)."""

import sys
import textwrap

import pytest

from quantum import services


@pytest.fixture
def module(tmp_path, monkeypatch):
    """A Python module of the project with declared services."""
    services._reset()
    (tmp_path / 'my_services.py').write_text(textwrap.dedent('''
        from quantum.services import service

        @service("projects.list")
        def list_projects(status="active", limit=10):
            items = [{"name": "a", "status": "active"}, {"name": "b", "status": "stopped"}]
            return [i for i in items if i["status"] == status][:limit]

        @service("math.double")
        def double(n):
            return n * 2

        @service("failure")
        def failure():
            raise RuntimeError("disk full")
    '''), encoding='utf-8')
    # No syspath_prepend: the module must be found from the project directory,
    # as with `quantum start` (the script does not put the cwd on sys.path).
    monkeypatch.chdir(tmp_path)
    path_before = list(sys.path)
    yield 'services:\n  - my_services\n'
    sys.path[:] = path_before
    sys.modules.pop('my_services', None)
    services._reset()


def page(name, body):
    return f'<q:component name="{name}" xmlns:q="https://quantum.lang/ns">{body}</q:component>'


class TestServices:
    def test_a_page_calls_a_declared_service(self, serve_pages, module):
        # SVC-1 / SVC-3
        client = serve_pages(datasources_yaml=module, p=page('p',
            '<q:invoke name="ps" service="projects.list"><q:param name="status" value="active"/></q:invoke>'
            '<q:loop items="{ps}" var="x"><p>PROJECT {x.name}</p></q:loop>'))
        html = client.get('/p').get_data(as_text=True)
        assert 'PROJECT a' in html and 'PROJECT b' not in html

    def test_a_param_is_converted_by_its_type(self, serve_pages, module):
        # SVC-3
        client = serve_pages(datasources_yaml=module, p=page('p',
            '<q:invoke name="d" service="math.double"><q:param name="n" value="21" type="integer"/></q:invoke>'
            '<p>R={d}</p>'))
        assert 'R=42' in client.get('/p').get_data(as_text=True)

    def test_a_missing_service_lists_the_registered_ones(self, run_body, module, monkeypatch):
        # SVC-3
        import yaml
        from quantum.runtime import service_container
        monkeypatch.setattr(service_container.ServiceContainer, 'config',
                            property(lambda self: yaml.safe_load(module)))
        with pytest.raises(Exception, match="no service named 'projects.lst'.*projects.list"):
            run_body('<q:invoke name="x" service="projects.lst"/>')

    def test_a_service_failure_follows_inv2(self, run_body, module, monkeypatch):
        # SVC-3 / INV-2
        import yaml
        from quantum.runtime import service_container
        monkeypatch.setattr(service_container.ServiceContainer, 'config',
                            property(lambda self: yaml.safe_load(module)))
        with pytest.raises(Exception, match="service 'failure' failed: disk full"):
            run_body('<q:invoke name="x" service="failure"/>')
        r = run_body('<q:invoke name="x" service="failure" onerror="continue"/><q:return value="{x_result}"/>')
        assert r['success'] is False and 'disk full' in r['error']['message']

    def test_a_module_loads_only_if_listed(self, run_body, module):
        # SVC-2: without services: in the config, nothing is imported
        with pytest.raises(Exception, match="no service named 'math.double'"):
            run_body('<q:invoke name="x" service="math.double"><q:param name="n" value="1"/></q:invoke>')

    def test_a_listed_module_that_does_not_exist_is_an_error(self, run_body, monkeypatch):
        # SVC-2
        services._reset()
        from quantum.runtime import service_container
        monkeypatch.setattr(service_container.ServiceContainer, 'config',
                            property(lambda self: {'services': ['no_such_module']}))
        with pytest.raises(Exception, match="service module 'no_such_module'"):
            run_body('<q:invoke name="x" service="a.b"/>')

    def test_a_duplicate_name_of_another_function_is_an_error(self):
        # SVC-1
        services._reset()

        @services.service('dup.x')
        def one():
            return 1

        with pytest.raises(services.ServiceError, match="already registered"):
            @services.service('dup.x')
            def two():
                return 2
        services._reset()

    def test_endpoint_on_invoke_is_a_parse_error(self):
        # SVC-3
        from quantum.core.parser import QuantumParser, QuantumParseError
        with pytest.raises(QuantumParseError, match='endpoint= is not supported'):
            QuantumParser().parse(page('p', '<q:invoke name="x" endpoint="/graphql"/>'))
