"""The Ajustes app (os/apps/ajustes): the machine's settings, read, on every renderer.

The services (leitura.py) read the machine through two doors, `run` and
`read`, replaced here with a machine made of canned outputs; the page is
then served and read in the browser, in the console and on the Hive's
screen with the parity test's drivers (UI-7, UI-15), where it shows what
this host really is.
"""

import asyncio
import importlib
import logging
import os
import shutil
import socket
import sys
import threading
from pathlib import Path

import pytest

from tests.apps.test_ui_parity_script import OS_DIR, Browser, Console, Pixel, Screen, run_script

AJUSTES = Path(__file__).resolve().parents[2] / 'os' / 'apps' / 'ajustes'

IP_ADDR = '''[{"ifindex":1,"ifname":"lo","link_type":"loopback","operstate":"UNKNOWN",
  "addr_info":[{"family":"inet","local":"127.0.0.1","prefixlen":8,"scope":"host"}]},
 {"ifindex":2,"ifname":"enp0s3","link_type":"ether","operstate":"UP",
  "addr_info":[{"family":"inet","local":"10.0.2.15","prefixlen":24,"scope":"global","dynamic":true},
               {"family":"inet6","local":"fe80::1","prefixlen":64,"scope":"link"}]},
 {"ifindex":3,"ifname":"enp0s8","link_type":"ether","operstate":"DOWN","addr_info":[]}]'''
IP_ROUTE = '[{"dst":"default","gateway":"10.0.2.2","dev":"enp0s3","protocol":"dhcp"},{"dst":"10.0.2.0/24","dev":"enp0s3"}]'
RESOLVECTL = 'Global\n  Protocols: -LLMNR\nLink 2 (enp0s3)\n  Current DNS Server: 10.0.2.3\n  DNS Servers: 10.0.2.3 1.1.1.1\n'
KEYBOARD = '# KEYBOARD CONFIGURATION FILE\nXKBMODEL="abnt2"\nXKBLAYOUT="br"\nXKBVARIANT=""\nXKBOPTIONS=""\n'
WHITELIST = '''[run_command]
allowed = [ { command = "df", args = ["-h"] }, { command = "ip", args = ["addr"] }, { command = "ip", args = ["route"] } ]
[service]
allowed = ["nginx", "docker"]
[file_ops]
allowed_paths = ["/home/*", "/tmp/*"]
'''


@pytest.fixture
def leitura(monkeypatch):
    """The services module, read against a machine made of canned outputs."""
    monkeypatch.syspath_prepend(str(AJUSTES))
    module = importlib.import_module('leitura')
    files = {
        '/proc/sys/kernel/hostname': 'forja\n',
        '/etc/os-release': 'NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 24.04 LTS"\n',
        '/proc/uptime': '93784.12 300000.00\n',
        '/proc/meminfo': 'MemTotal:        8000000 kB\nMemFree:          500000 kB\nMemAvailable:    6000000 kB\n',
        '/etc/default/keyboard': KEYBOARD,
        '/etc/hive/whitelist.toml': WHITELIST,
        '/etc/resolv.conf': 'nameserver 9.9.9.9\n',
    }
    outputs = {
        ('ip', '-j', 'addr'): IP_ADDR,
        ('ip', '-j', 'route'): IP_ROUTE,
        ('resolvectl', 'status'): RESOLVECTL,
    }
    monkeypatch.setattr(module, 'read', lambda path: files.get(path))
    monkeypatch.setattr(module, 'run', lambda cmd, timeout=5.0: outputs.get(tuple(cmd)))

    def run_any(cmd, timeout=5.0):
        if cmd[:2] != ['systemctl', 'is-active']:
            return None
        states = {'hive-cortex': 'active', 'hive-synapse': 'active', 'hive-actuator': 'inactive',
                  'hive-screen': 'active'}
        # systemctl prints one state a unit, and stops at the units it knows
        return ''.join(states[u] + '\n' for u in cmd[2:] if u in states and u != 'hive-nerve-process'
                       and cmd[2:].index(u) < 3 or (len(cmd) == 3 and u in states))

    monkeypatch.setattr(module, 'run_any', run_any)
    asked = []

    def ask(args):
        asked.append(list(args))
        return (0, 'asked the Hive: ' + ' '.join(args)) if args[0] != 'set-keyboard' or args[1] != 'us' \
            else (1, 'the Hive is not listening')

    monkeypatch.setattr(module, 'ask', ask)
    module.asked = asked
    return module


def rows(result):
    return {r['campo']: r['valor'] for r in result['linhas']}


def test_the_machine_is_read_in_its_own_words(leitura):
    m = leitura.maquina()
    assert m['nome'] == 'forja'
    r = rows(m)
    assert r['sistema'] == 'Ubuntu 24.04 LTS'
    assert r['ligada há'] == '1 d 2 h 3 min'
    assert r['memória'] == '1,9 GB em uso de 7,6 GB'
    assert r['núcleos'] == str(os.cpu_count() or 1)
    assert r['disco /'].endswith('%)')


def test_the_network_names_each_interface_the_gateway_and_the_dns(leitura):
    n = leitura.rede()
    assert [i['nome'] for i in n['interfaces']] == ['enp0s3', 'enp0s8'], 'the loopback is not listed'
    assert n['interfaces'][0] == {'nome': 'enp0s3', 'estado': 'ligada', 'endereco': '10.0.2.15/24', 'origem': 'DHCP'}
    assert n['interfaces'][1] == {'nome': 'enp0s8', 'estado': 'desligada', 'endereco': 'sem endereço', 'origem': '-'}
    assert n['gateway'] == '10.0.2.2 por enp0s3 (DHCP)'
    assert n['dns'] == '10.0.2.3, 1.1.1.1', 'resolvectl first'


def test_the_dns_falls_back_to_resolv_conf(leitura, monkeypatch):
    monkeypatch.setattr(leitura, 'run', lambda cmd, timeout=5.0: None)
    n = leitura.rede()
    assert n['dns'] == '9.9.9.9'
    assert n['gateway'] == 'nenhum'


def test_the_keyboard_is_the_systems_layout_unless_the_hive_set_one(leitura, monkeypatch):
    t = leitura.teclado()
    assert t['layout'] == 'br'
    assert t['escolha'] == 'br'
    r = rows(t)
    assert r['layout do sistema'] == 'br (abnt2), de /etc/default/keyboard'
    assert r['ajuste da Hive'] == 'nenhum (a tela lê o do sistema)'
    assert r['a tela lê'] == 'a página não está na tela'
    read = leitura.read
    monkeypatch.setattr(leitura, 'read', lambda path: 'us pc105\n' if path == '/var/lib/hive/settings/keyboard'
                        else read(path))
    t = leitura.teclado()
    assert t['escolha'] == 'us', 'the Hive\'s setting is what the screen reads'
    assert rows(t)['ajuste da Hive'] == 'us pc105'


def test_the_screen_tab_says_what_the_screen_said(leitura, monkeypatch):
    import quantum.runtime.ui_pixel as ui_pixel
    monkeypatch.setattr(ui_pixel, '_SCREEN_STATUS', None)
    off = leitura.tela()
    assert off['na_tela'] is False
    assert rows(off)['hive-screen'] == 'active'
    monkeypatch.setattr(ui_pixel, '_SCREEN_STATUS', {
        'level': 2, 'level_name': 'fine', 'pinned': False, 'cores': 4, 'motion': True,
        'keyboard': 'br (ABNT2)', 'frame_ms': 3.25, 'scene': [320, 180]})
    on = leitura.tela()
    assert on['na_tela'] is True
    r = rows(on)
    assert r['nível'] == 'fine (2)'
    assert r['escolha'] == 'escolhido pela medida do quadro'
    assert r['um quadro custa'] == '3,2 ms'
    assert r['cena'] == '320x180'
    assert rows(leitura.teclado())['a tela lê'] == 'br (ABNT2)'


def test_the_hive_tab_lists_the_daemons_and_the_whitelist(leitura):
    h = leitura.hive()
    assert h['daemons'][:3] == [{'nome': 'hive-cortex', 'estado': 'active'},
                                {'nome': 'hive-synapse', 'estado': 'active'},
                                {'nome': 'hive-actuator', 'estado': 'inactive'}]
    assert h['daemons'][3]['estado'] == 'não lido'
    assert h['ativos'] == 2
    r = rows(h)
    assert r['comandos'] == 'df, ip'
    assert r['serviços'] == 'nginx, docker'
    assert r['caminhos'] == '/home/*, /tmp/*'


def test_a_change_is_asked_of_the_hive_never_made(leitura):
    ok = leitura.pedir('set-hostname', 'forja')
    assert ok['ok'] and ok['mensagem'].startswith('Pedido à Hive: mudar o nome da máquina para forja')
    assert leitura.asked == [['set-hostname', 'forja']]
    bad = leitura.pedir('set-hostname', 'Forja Nova')
    assert not bad['ok'] and 'não serve de nome' in bad['mensagem']
    kb = leitura.pedir('set-keyboard', 'br')
    assert kb['ok'] and leitura.asked[-1] == ['set-keyboard', 'br', 'abnt2']
    level = leitura.pedir('set-screen-level', 'fine')
    assert level['ok'] and leitura.asked[-1] == ['set-screen-level', 'fine']
    auto = leitura.pedir('set-screen-level', 'auto')
    assert 'escolhido pela medida' in auto['mensagem']
    assert not leitura.pedir('set-screen-level', '9')['ok']
    assert not leitura.pedir('restart-service', 'nginx')['ok']
    refused = leitura.pedir('set-keyboard', 'us')
    assert not refused['ok'] and 'não recebeu o pedido' in refused['mensagem']
    assert 'not listening' in refused['mensagem']


def test_without_the_hive_command_asking_says_so(leitura, monkeypatch):
    monkeypatch.setattr(leitura, 'ask', lambda args: (None, 'o comando hive não está nesta máquina'))
    answer = leitura.pedir('set-hostname', 'forja')
    assert not answer['ok'] and 'não está nesta máquina' in answer['mensagem']


def test_a_bare_machine_is_read_without_an_error(leitura, monkeypatch):
    monkeypatch.setattr(leitura, 'read', lambda path: None)
    monkeypatch.setattr(leitura, 'run', lambda cmd, timeout=5.0: None)
    monkeypatch.setattr(leitura, 'run_any', lambda cmd, timeout=5.0: None)
    for svc in (leitura.maquina, leitura.rede, leitura.teclado, leitura.tela, leitura.hive):
        assert svc()['linhas']
    assert rows(leitura.hive())['de'] == 'sem whitelist legível'


# -- the page, on every renderer, reading this host -------------------------

@pytest.fixture
def url(tmp_path, monkeypatch):
    project = tmp_path / 'ajustes'
    shutil.copytree(AJUSTES, project, ignore=shutil.ignore_patterns('__pycache__', 'logs'))
    monkeypatch.chdir(project)
    monkeypatch.syspath_prepend(str(project))
    sys.modules.pop('leitura', None)
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / 'quantum.config.yaml')).app
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_port}/'
    server.shutdown()
    logging.disable(logging.NOTSET)


def script(on_screen):
    host = Path('/proc/sys/kernel/hostname').read_text().strip() if Path('/proc/sys/kernel/hostname').is_file() \
        else socket.gethostname()
    return [
        ('sees', ['Máquina', 'Rede', 'Teclado', 'Tela', 'Hive', f'nome: {host}', 'ligada há:',
                  f'núcleos: {os.cpu_count() or 1}', 'memória:', 'disco /:']),
        ('does_not_see', ['gateway:']),      # the Rede tab is closed
    ] + ([] if on_screen else [('does_not_see', ['nível:'])])


def test_the_app_in_the_browser(url):
    playwright = pytest.importorskip('playwright.sync_api', reason='Playwright is not installed')
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        try:
            page = chromium.new_page(viewport={'width': 1280, 'height': 900})
            page.goto(url)
            run_script(Browser(page), script(on_screen=False))
        finally:
            chromium.close()


def test_the_app_in_the_console(url):
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded

    async def main():
        app = ConsoleUI(url)
        async with app.run_test(size=(160, 120)) as pilot:
            await page_loaded(app, pilot)
            run_script(Console(app, pilot), script(on_screen=False))

    asyncio.run(main())


def test_the_app_on_the_pixel_screen_says_what_the_screen_is(url, tmp_path):
    binary = os.environ.get('HIVE_SCREEN') or str(OS_DIR / 'target/debug/hive-screen')
    if not Path(binary).is_file():
        pytest.skip('hive-screen is not built (cd os && cargo build -p hive-screen, or HIVE_SCREEN=...)')
    from quantum.runtime.ui_pixel import PixelClient

    socket_path = str(tmp_path / 'pixel.sock')
    screen = Screen(binary, socket_path)
    try:
        client = PixelClient(url, '/', socket_path)
        runtime = threading.Thread(target=client.run, daemon=True)
        runtime.start()
        first = screen.request({'op': 'until', 'shown': 1, 'max_ticks': 600})
        assert first['stopped'] == 'condition', 'quantum pixel did not bring the page'
        pixel = Pixel(screen)
        assert pixel.window()['title'] == 'Ajustes'
        run_script(pixel, script(on_screen=True))
        # a change is asked of the Hive: the page's service runs `hive request`, replaced here
        asked = []
        from quantum.services import _registry
        # the app's own module, as the server imported it: its `ask` door is replaced
        _registry['ajustes.pedir'].__globals__['ask'] = \
            lambda args: (asked.append(list(args)), (0, 'asked the Hive'))[1]
        run_script(pixel, [('fill', 'nome', 'forja'), ('click', 'Pedir à Hive'),
                           ('sees', ['Pedido à Hive: mudar o nome da máquina para forja'])])
        assert asked == [['set-hostname', 'forja']]
        # the arrows go through the tabs: the Tela tab says what the screen told the page's runtime
        pixel._focus(lambda i: i['kind'] == 'tabpanel')
        screen.request({'op': 'act', 'tap': ['right', 'right', 'right']})
        text = pixel.text()
        assert 'nível: effects (1)' in text, text
        assert 'escolha: escolhido pela medida do quadro' in text
        assert 'movimento: ligado' in text
        assert 'cena: 320x180' in text
        screen.request({'op': 'act', 'tap': ['escape']})
        runtime.join(10)
        assert not runtime.is_alive()
    finally:
        screen.end()
