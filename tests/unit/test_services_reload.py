"""services.load() after services._reset() must not re-execute a module.

It used to importlib.reload() an already imported services module whose
registrations had been cleared. The module ran again in place: its classes
became new objects while every module that had imported them kept the old
ones. The admin's apps.py raised the old ProjectError, the tests caught the
new one, and tests/admin/test_admin_services_apps.py failed in some orders.
"""

import sys
import textwrap

import pytest

from quantum import services


@pytest.fixture
def module(tmp_path, monkeypatch):
    services._reset()
    (tmp_path / 'reload_probe_services.py').write_text(textwrap.dedent('''
        from quantum.services import service

        class ProbeError(Exception):
            pass

        @service("probe.fail")
        def fail():
            raise ProbeError("no")
    '''), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    path_before = list(sys.path)
    yield 'reload_probe_services'
    sys.path[:] = path_before
    sys.modules.pop('reload_probe_services', None)
    services._reset()


def test_loading_again_after_a_reset_keeps_the_module_s_classes(module):
    services.load([module])
    first = sys.modules[module].ProbeError

    services._reset()
    services.load([module])

    assert sys.modules[module].ProbeError is first
    with pytest.raises(first):
        services.get("probe.fail")()


def test_the_services_are_registered_again(module):
    services.load([module])
    services._reset()
    with pytest.raises(services.ServiceError):
        services.get("probe.fail")
    services.load([module])
    assert services.get("probe.fail").__module__ == module
