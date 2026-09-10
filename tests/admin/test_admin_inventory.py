"""O inventario do admin (scripts/admin-inventory.py) mede o que diz medir.

Achados que ele sustenta — rotas sombreadas, chamadas da interface que nao
chegam a rota nenhuma — foram conferidos com requisicoes reais. Estes testes
guardam as duas partes que produziram falso positivo durante a escrita.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("admin_inventory", REPO / "scripts" / "admin-inventory.py")
inventario = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventario)


def test_concatenacao_mantem_os_pedacos_depois_da_variavel():
    # '/docker/containers/' + id + '/start' virava /docker/containers/1 e
    # aparecia como chamada quebrada.
    assert inventario._normalizar("'{URL_PREFIX}/docker/containers/' + id + '/start'") == \
        "/docker/containers/1/start"


def test_template_string_e_fstring():
    assert inventario._normalizar("`/admin/projects/${{PROJECT_ID}}/environments/${{envId}}`") == \
        "/admin/projects/1/environments/1"
    assert inventario._normalizar("`{URL_PREFIX}/api/projects/{project_id}/logs/stats?hours=${{hours}}`") == \
        "/api/projects/1/logs/stats"


def test_variavel_nao_e_resolvida():
    assert inventario._normalizar("url") is None


def test_todas_as_rotas_do_main_sao_lidas():
    rotas = inventario.rotas_da_ast()
    assert len(rotas) >= 260
    assert any(r["caminho"] == "/settings/export" and r["handler"] == "export_settings" for r in rotas)
