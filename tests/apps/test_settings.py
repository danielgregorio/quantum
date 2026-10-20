"""The Settings app (os/apps/settings): the machine's settings, read, and asked of the Hive, on every renderer.

The services (machine.py) read the machine through its doors, `run`,
`run_any` and `read`, and ask through `ask`, all replaced here with a
machine made of canned outputs; the page is then served and read in the
browser, in the console and on the Hive's screen with the parity test's
drivers (UI-7, UI-15), where it shows what this host really is.
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

SETTINGS = Path(__file__).resolve().parents[2] / 'os' / 'apps' / 'settings'

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
def machine(monkeypatch):
    """The services module, read against a machine made of canned outputs."""
    monkeypatch.syspath_prepend(str(SETTINGS))
    module = importlib.import_module('machine')
    files = {
        '/proc/sys/kernel/hostname': 'forge\n',
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
    return {r['field']: r['value'] for r in result['rows']}


def test_the_machine_is_read_in_its_own_words(machine):
    m = machine.machine()
    assert m['name'] == 'forge'
    r = rows(m)
    assert r['system'] == 'Ubuntu 24.04 LTS'
    assert r['up for'] == '1 d 2 h 3 min'
    assert r['memory'] == '1.9 GB used of 7.6 GB'
    assert r['cores'] == str(os.cpu_count() or 1)
    assert r['disk /'].endswith('%)')


def test_the_network_names_each_interface_the_gateway_and_the_dns(machine):
    n = machine.network()
    assert [i['name'] for i in n['interfaces']] == ['enp0s3', 'enp0s8'], 'the loopback is not listed'
    assert n['interfaces'][0] == {'name': 'enp0s3', 'state': 'up', 'address': '10.0.2.15/24', 'source': 'DHCP'}
    assert n['interfaces'][1] == {'name': 'enp0s8', 'state': 'down', 'address': 'no address', 'source': '-'}
    assert n['gateway'] == '10.0.2.2 on enp0s3 (DHCP)'
    assert n['dns'] == '10.0.2.3, 1.1.1.1', 'resolvectl first'
    # the form starts from what the first interface has
    assert (n['names'], n['chosen'], n['mode']) == ('enp0s3,enp0s8', 'enp0s3', 'dhcp')
    assert (n['address'], n['via'], n['servers']) == ('10.0.2.15/24', '10.0.2.2', '10.0.2.3,1.1.1.1')


def test_the_dns_falls_back_to_resolv_conf(machine, monkeypatch):
    monkeypatch.setattr(machine, 'run', lambda cmd, timeout=5.0: None)
    n = machine.network()
    assert n['dns'] == '9.9.9.9'
    assert n['gateway'] == 'none'


def test_the_keyboard_is_the_systems_layout_unless_the_hive_set_one(machine, monkeypatch):
    k = machine.keyboard()
    assert k['layout'] == 'br'
    assert k['choice'] == 'br'
    r = rows(k)
    assert r['system layout'] == 'br (abnt2), from /etc/default/keyboard'
    assert r["the Hive's setting"] == "none (the screen reads the system's)"
    assert r['the screen reads'] == 'this page is not on the screen'
    read = machine.read
    monkeypatch.setattr(machine, 'read', lambda path: 'us pc105\n' if path == '/var/lib/hive/settings/keyboard'
                        else read(path))
    k = machine.keyboard()
    assert k['choice'] == 'us', "the Hive's setting is what the screen reads"
    assert rows(k)["the Hive's setting"] == 'us pc105'


def test_the_screen_tab_says_what_the_screen_said(machine, monkeypatch):
    import quantum.runtime.ui_pixel as ui_pixel
    monkeypatch.setattr(ui_pixel, '_SCREEN_STATUS', None)
    off = machine.screen()
    assert off['on_screen'] is False
    assert rows(off)['hive-screen'] == 'active'
    monkeypatch.setattr(ui_pixel, '_SCREEN_STATUS', {
        'level': 2, 'level_name': 'fine', 'pinned': False, 'cores': 4, 'motion': True,
        'keyboard': 'br (ABNT2)', 'frame_ms': 3.25, 'scene': [320, 180]})
    on = machine.screen()
    assert on['on_screen'] is True
    r = rows(on)
    assert r['level'] == 'fine (2)'
    assert r['how'] == 'chosen by measuring the frame'
    assert r['a frame costs'] == '3.2 ms'
    assert r['scene'] == '320x180'
    assert rows(machine.keyboard())['the screen reads'] == 'br (ABNT2)'


def test_the_hive_tab_lists_the_daemons_and_the_whitelist(machine):
    h = machine.hive()
    assert h['daemons'][:3] == [{'name': 'hive-cortex', 'state': 'active'},
                                {'name': 'hive-synapse', 'state': 'active'},
                                {'name': 'hive-actuator', 'state': 'inactive'}]
    assert h['daemons'][3]['state'] == 'not read'
    assert h['active'] == 2
    r = rows(h)
    assert r['commands'] == 'df, ip'
    assert r['services'] == 'nginx, docker'
    assert r['paths'] == '/home/*, /tmp/*'


def test_a_change_is_asked_of_the_hive_never_made(machine):
    ok = machine.ask_hive('set-hostname', 'forge')
    assert ok['ok'] and ok['message'].startswith('Asked the Hive: name the machine forge')
    assert machine.asked == [['set-hostname', 'forge']]
    bad = machine.ask_hive('set-hostname', 'Forge New')
    assert not bad['ok'] and 'is not a name' in bad['message']
    kb = machine.ask_hive('set-keyboard', 'br')
    assert kb['ok'] and machine.asked[-1] == ['set-keyboard', 'br', 'abnt2']
    level = machine.ask_hive('set-screen-level', 'fine')
    assert level['ok'] and machine.asked[-1] == ['set-screen-level', 'fine']
    auto = machine.ask_hive('set-screen-level', 'auto')
    assert 'chosen by the measure' in auto['message']
    assert not machine.ask_hive('set-screen-level', '9')['ok']
    assert not machine.ask_hive('restart-service', 'nginx')['ok']
    refused = machine.ask_hive('set-keyboard', 'us')
    assert not refused['ok'] and 'did not get the request' in refused['message']
    assert 'not listening' in refused['message']


def test_the_network_is_asked_by_dhcp_or_static_and_checked_first(machine):
    dhcp = machine.ask_hive('set-network', 'enp0s3', mode='dhcp', address='ignored', gateway='', dns='')
    assert dhcp['ok'] and machine.asked[-1] == ['set-network', 'enp0s3', 'dhcp']
    assert dhcp['message'].startswith('Asked the Hive: network enp0s3 by DHCP. '
                                      'It is dangerous: approve it on the screen with Enter twice')
    static = machine.ask_hive('set-network', 'enp0s3', mode='static', address='10.0.2.20/24', gateway='10.0.2.2',
                              dns='10.0.2.3, 1.1.1.1')
    assert static['ok'] and machine.asked[-1] == ['set-network', 'enp0s3', '10.0.2.20/24', 'via', '10.0.2.2',
                                                  'dns', '10.0.2.3,1.1.1.1']
    assert 'network enp0s3 static at 10.0.2.20/24 via 10.0.2.2, DNS 10.0.2.3, 1.1.1.1' in static['message']
    bare = machine.ask_hive('set-network', 'enp0s3', mode='static', address='10.0.2.20/24')
    assert bare['ok'] and machine.asked[-1] == ['set-network', 'enp0s3', '10.0.2.20/24']
    asked = len(machine.asked)
    # what is wrong is said before anything is asked
    assert 'is not an interface' in machine.ask_hive('set-network', 'eth0;rm', mode='dhcp')['message']
    assert 'is not a source' in machine.ask_hive('set-network', 'enp0s3', mode='fixed')['message']
    assert 'is not an address with its prefix' in machine.ask_hive('set-network', 'enp0s3', mode='static',
                                                                    address='10.0.2.20')['message']
    assert 'is not an IPv4 gateway' in machine.ask_hive('set-network', 'enp0s3', mode='static',
                                                         address='10.0.2.20/24', gateway='router')['message']
    assert 'DNS servers' in machine.ask_hive('set-network', 'enp0s3', mode='static', address='10.0.2.20/24',
                                             dns='1.1.1.1,2.2.2.2,3.3.3.3,4.4.4.4,5.5.5.5')['message']
    assert len(machine.asked) == asked


def test_without_the_hive_command_asking_says_so(machine, monkeypatch):
    monkeypatch.setattr(machine, 'ask', lambda args: (None, 'the hive command is not on this machine'))
    answer = machine.ask_hive('set-hostname', 'forge')
    assert not answer['ok'] and 'not on this machine' in answer['message']


def test_a_bare_machine_is_read_without_an_error(machine, monkeypatch):
    monkeypatch.setattr(machine, 'read', lambda path: None)
    monkeypatch.setattr(machine, 'run', lambda cmd, timeout=5.0: None)
    monkeypatch.setattr(machine, 'run_any', lambda cmd, timeout=5.0: None)
    for svc in (machine.machine, machine.network, machine.keyboard, machine.screen, machine.hive):
        assert svc()['rows']
    assert rows(machine.hive())['from'] == 'no readable whitelist'


# -- the page, on every renderer, reading this host -------------------------

@pytest.fixture
def url(tmp_path, monkeypatch):
    project = tmp_path / 'settings'
    shutil.copytree(SETTINGS, project, ignore=shutil.ignore_patterns('__pycache__', 'logs'))
    monkeypatch.chdir(project)
    monkeypatch.syspath_prepend(str(project))
    sys.modules.pop('machine', None)
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
        ('sees', ['Machine', 'Network', 'Keyboard', 'Screen', 'Hive', f'name: {host}', 'up for:',
                  f'cores: {os.cpu_count() or 1}', 'memory:', 'disk /:']),
        ('does_not_see', ['gateway:']),      # the Network tab is closed
    ] + ([] if on_screen else [('does_not_see', ['level:'])])


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
        assert pixel.window()['title'] == 'Settings'
        run_script(pixel, script(on_screen=True))
        # a change is asked of the Hive: the page's service runs `hive request`, replaced here
        asked = []
        from quantum.services import _registry
        # the app's own module, as the server imported it: its `ask` door is replaced
        _registry['settings.ask'].__globals__['ask'] = \
            lambda args: (asked.append(list(args)), (0, 'asked the Hive'))[1]
        run_script(pixel, [('fill', 'hostname', 'forge'), ('click', 'Ask the Hive'),
                           ('sees', ['Asked the Hive: name the machine forge'])])
        assert asked == [['set-hostname', 'forge']]
        # the Network tab: a static address asked for, the fields checked by the page before the Hive hears of it
        pixel._focus(lambda i: i['kind'] == 'tabpanel')
        screen.request({'op': 'act', 'tap': ['right']})
        run_script(pixel, [('sees', ['gateway:', 'Interface', 'Source']),
                           ('choose', 'mode', 'static'), ('fill', 'address', '10.0.2.20/24'),
                           ('fill', 'gateway', '10.0.2.2'), ('fill', 'dns', '10.0.2.3'), ('click', 'Ask the Hive'),
                           ('sees', ['Enter twice'])])
        assert asked[-1][:3] == ['set-network', asked[-1][1], '10.0.2.20/24'] and asked[-1][3:] == \
            ['via', '10.0.2.2', 'dns', '10.0.2.3']
        # UI-17: the page came back on the tab the request was made from
        tabs = pixel._focus(lambda i: i['kind'] == 'tabpanel')
        assert tabs['tabs'][tabs['tab']] == 'Network'
        # the arrows go through the tabs: the Screen tab says what the screen told the page's runtime
        screen.request({'op': 'act', 'tap': ['right', 'right']})
        text = pixel.text()
        assert 'level: effects (1)' in text, text
        assert 'how: chosen by measuring the frame' in text
        assert 'motion: on' in text
        assert 'scene: 320x180' in text
        screen.request({'op': 'act', 'tap': ['escape']})
        runtime.join(10)
        assert not runtime.is_alive()
    finally:
        screen.end()
