"""os/config/screen/screen.toml and font.png are written from os/config/screen/screen.q, and committed as written.

scripts/generate-screen-config.py compiles screen.q (the Hive's screen, in
Quantum) to the scene hive-screen loads and the font sheet it draws text
with; the sprite sheets beside them are scripts/art/hive_screen.py's. A
file edited by hand, or a screen.q changed without regenerating, fails
here: run `python scripts/generate-screen-config.py`.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        'generate_screen_config', REPO / 'scripts' / 'generate-screen-config.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_screen_config_is_current():
    gen = generator()
    for name, data in gen.build().items():
        assert (gen.OUT / name).read_bytes() == data, (
            f'os/config/screen/{name} is stale: run python scripts/generate-screen-config.py')


def test_the_os_screen_names_a_cell_for_every_service_the_rules_allow():
    """A crash of a service the whitelist names has a cell to smoke in."""
    from quantum.core.parser import QuantumParser
    from quantum.runtime.hive import read_hive
    from quantum.runtime.screen import read_screen
    hive = read_hive(QuantumParser(use_cache=False).parse_file(str(REPO / 'os' / 'config' / 'hive' / 'hive.q')))
    screen = read_screen(QuantumParser(use_cache=False).parse_file(str(REPO / 'os' / 'config' / 'screen' / 'screen.q')))
    cells = {n.attrs['name'] for n in screen.nodes if n.kind == 'sprite' and n.attrs['sheet'] == 'cell'}
    assert cells <= set(hive.services), cells - set(hive.services)
    assert len(cells) >= 8
