"""What the Settings app reads of the machine, as the user who opened it, and how it asks the Hive for a change.

Five services, one a tab: the machine, the network, the keyboard, the
screen, the Hive. Each answers plain data for the page (rows of `field` and
`value`, tables), never raises, and says "?" or "not read" for what it could
not read: the page is the same on a machine with no `ip`, no systemd and no
screen. Everything is read from files anyone may read and commands anyone
may run (`ip -j addr`, `systemctl is-active`); nothing here changes the
system, and nothing needs root. A sixth service, `settings.ask`, asks the
Hive for a change (`hive request`) and changes nothing itself.

`run`, `run_any`, `read` and `ask` are the doors to the machine, so a test
replaces them.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from quantum.services import service

# The Hive's daemons, in the order the Hive tab lists them.
DAEMONS = ['hive-cortex', 'hive-synapse', 'hive-actuator', 'hive-nerve-process', 'hive-nerve-journal',
           'hive-nerve-network', 'hive-nerve-fs', 'hive-screen']

NOT_READ = 'not read'
# the keyboards the screen reads, and the model each asks for
KEYBOARDS = {'us': 'pc105', 'br': 'abnt2'}


def run(cmd: List[str], timeout: float = 5.0) -> Optional[str]:
    """The command's output, or None when it is not on the machine, fails or hangs."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def run_any(cmd: List[str], timeout: float = 5.0) -> Optional[str]:
    """The command's output whatever its exit code (systemctl is-active exits 3 for an inactive unit)."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def read(path: str) -> Optional[str]:
    """A file's text, or None when it is not there or not ours to read."""
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def ask(args: List[str]) -> Tuple[Optional[int], str]:
    """`hive request ...`: the one door that changes anything, and only by asking.
    The exit code (None when `hive` is not on the machine) and what it said."""
    if shutil.which('hive') is None:
        return None, 'the hive command is not on this machine'
    try:
        done = subprocess.run(['hive', 'request', *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return done.returncode, (done.stdout + done.stderr).strip()


def _doors() -> Dict[str, Callable]:
    """The doors as they are now (a test replaces the module's functions)."""
    return {'run': run, 'run_any': run_any, 'read': read, 'ask': ask}


# ---------------------------------------------------------------- the machine

def _size(kib: float) -> str:
    """Kibibytes as people say them: 15.6 GB, 512 MB."""
    b = kib * 1024
    for unit, size in (('TB', 1024 ** 4), ('GB', 1024 ** 3), ('MB', 1024 ** 2)):
        if b >= size:
            return f'{b / size:.1f} {unit}'
    return f'{int(kib)} kB'


def _uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f'{days} d')
    if days or hours:
        parts.append(f'{hours} h')
    parts.append(f'{minutes} min')
    return ' '.join(parts)


def _meminfo(text: Optional[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for line in (text or '').splitlines():
        m = re.match(r'^(\w+):\s+(\d+)', line)
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


@service('settings.machine')
def machine() -> dict:
    """The machine: its name, system, kernel, uptime, cores, memory and disk."""
    d = _doors()
    name = (d['read']('/proc/sys/kernel/hostname') or '').strip() or socket.gethostname()
    system = NOT_READ
    for line in (d['read']('/etc/os-release') or '').splitlines():
        if line.startswith('PRETTY_NAME='):
            system = line.split('=', 1)[1].strip().strip('"')
    uptime = d['read']('/proc/uptime')
    up = _uptime(float(uptime.split()[0])) if uptime else NOT_READ
    mem = _meminfo(d['read']('/proc/meminfo'))
    if 'MemTotal' in mem:
        free = mem.get('MemAvailable', mem.get('MemFree', 0.0))
        memory = f'{_size(mem["MemTotal"] - free)} used of {_size(mem["MemTotal"])}'
    else:
        memory = NOT_READ
    try:
        usage = shutil.disk_usage('/')
        disk = f'{_size(usage.used / 1024)} used of {_size(usage.total / 1024)} ' \
               f'({usage.used * 100 // max(usage.total, 1)}%)'
    except OSError:
        disk = NOT_READ
    cores = os.cpu_count() or 1
    rows = [
        {'field': 'name', 'value': name},
        {'field': 'system', 'value': system},
        {'field': 'kernel', 'value': os.uname().release},
        {'field': 'up for', 'value': up},
        {'field': 'cores', 'value': str(cores)},
        {'field': 'memory', 'value': memory},
        {'field': 'disk /', 'value': disk},
    ]
    return {'name': name, 'cores': cores, 'rows': rows}


# ---------------------------------------------------------------- the network

def _json(text: Optional[str]) -> list:
    try:
        value = json.loads(text or '')
    except ValueError:
        return []
    return value if isinstance(value, list) else []


def _dns(d: Dict[str, Callable]) -> List[str]:
    """The DNS servers: resolvectl's, else resolv.conf's."""
    servers: List[str] = []
    status = d['run'](['resolvectl', 'status'])
    for line in (status or '').splitlines():
        m = re.match(r'\s*DNS Servers:\s*(.+)$', line)
        if m:
            servers.extend(s for s in m.group(1).split() if s not in servers)
    if not servers:
        for line in (d['read']('/etc/resolv.conf') or '').splitlines():
            m = re.match(r'^nameserver\s+(\S+)', line)
            if m and m.group(1) not in servers:
                servers.append(m.group(1))
    return servers


@service('settings.network')
def network() -> dict:
    """The network: each interface with its addresses, state and where the
    address came from; the gateway; the DNS servers; and what the form to
    ask for a change starts from (the first interface as it is now)."""
    d = _doors()
    interfaces = []
    addrs = _json(d['run'](['ip', '-j', 'addr']))
    if addrs:
        for iface in addrs:
            if iface.get('link_type') == 'loopback':
                continue
            addresses, dynamic = [], 0
            for a in iface.get('addr_info', []):
                if a.get('family') == 'inet' or a.get('scope') == 'global':
                    addresses.append(f'{a.get("local")}/{a.get("prefixlen")}')
                    if a.get('dynamic'):
                        dynamic += 1
            state = str(iface.get('operstate', '?')).lower()
            interfaces.append({
                'name': iface.get('ifname', '?'),
                'state': {'up': 'up', 'down': 'down', 'unknown': 'up'}.get(state, state),
                'address': ', '.join(addresses) or 'no address',
                'source': 'DHCP' if dynamic else ('static' if addresses else '-'),
            })
    else:
        # no ip: the kernel still names them
        for name in sorted(p.name for p in Path('/sys/class/net').glob('*')) if Path('/sys/class/net').is_dir() else []:
            if name == 'lo':
                continue
            state = (d['read'](f'/sys/class/net/{name}/operstate') or '?').strip()
            interfaces.append({'name': name, 'state': state, 'address': NOT_READ, 'source': '?'})
    gateway = 'none'
    for route in _json(d['run'](['ip', '-j', 'route'])):
        if route.get('dst') == 'default':
            gateway = f'{route.get("gateway", "?")} on {route.get("dev", "?")}'
            if route.get('protocol') == 'dhcp':
                gateway += ' (DHCP)'
            break
    dns = _dns(d)
    # the form's choices: the interfaces by name, the first one chosen; what it has now, as the fields' start
    names = [i['name'] for i in interfaces if INTERFACE.match(str(i['name']))]
    first = interfaces[0] if interfaces else {}
    address = str(first.get('address', '')).split(',')[0].strip()
    return {
        'interfaces': interfaces,
        'gateway': gateway,
        'dns': ', '.join(dns) if dns else 'none',
        'names': ','.join(names),
        'chosen': names[0] if names else '',
        'mode': 'static' if first.get('source') == 'static' else 'dhcp',
        'address': address if CIDR.match(address) else '',
        'via': gateway.split()[0] if gateway != 'none' else '',
        'servers': ','.join(dns),
        'rows': [{'field': 'gateway', 'value': gateway},
                 {'field': 'DNS', 'value': ', '.join(dns) if dns else 'none'}],
    }


# ---------------------------------------------------------------- the keyboard

def _keyboard_file(text: Optional[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (text or '').splitlines():
        m = re.match(r'^\s*(XKB\w+)\s*=\s*"?([^"]*)"?\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


@service('settings.keyboard')
def keyboard() -> dict:
    """The keyboard: the system's layout (/etc/default/keyboard), the one the
    Hive set (which the screen reads first), and the one the screen reads,
    when the page is on the screen."""
    d = _doors()
    keys = _keyboard_file(d['read']('/etc/default/keyboard'))
    layout = keys.get('XKBLAYOUT') or NOT_READ
    model = keys.get('XKBMODEL') or '-'
    # the keyboard the Hive applied (set-keyboard), which the screen reads first
    hive_setting = (d['read']('/var/lib/hive/settings/keyboard') or '').split()
    setting = ' '.join(hive_setting) if hive_setting else "none (the screen reads the system's)"
    status = _screen_status()
    on_screen = status.get('keyboard') if status else 'this page is not on the screen'
    choice = hive_setting[0] if hive_setting and hive_setting[0] in KEYBOARDS \
        else (layout if layout in KEYBOARDS else 'us')
    return {
        'layout': layout,
        'choice': choice,
        'rows': [
            {'field': 'system layout', 'value': f'{layout} ({model}), from /etc/default/keyboard'},
            {'field': "the Hive's setting", 'value': setting},
            {'field': 'the screen reads', 'value': on_screen},
        ],
    }


# ---------------------------------------------------------------- the screen

def _screen_status() -> Optional[dict]:
    """What hive-screen said of itself to this page's runtime (ui_pixel), or
    None when the page is not on the screen."""
    try:
        from quantum.runtime.ui_pixel import screen_status
    except ImportError:
        return None
    return screen_status()


@service('settings.screen')
def screen() -> dict:
    """The screen: its presentation level, pinned or chosen, what a frame
    costs, whether pages move; and whether the daemon runs."""
    d = _doors()
    unit = (d['run_any'](['systemctl', 'is-active', 'hive-screen']) or NOT_READ).strip()
    s = _screen_status()
    if s is None:
        rows = [{'field': 'this page', 'value': 'not on the screen (open it with hive settings)'},
                {'field': 'hive-screen', 'value': unit}]
        return {'on_screen': False, 'unit': unit, 'choice': 'auto', 'rows': rows}
    level = f'{s.get("level_name", "?")} ({s.get("level", "?")})'
    how = "pinned (HIVE_SCREEN_LEVEL or the Hive's setting)" if s.get('pinned') \
        else 'chosen by measuring the frame'
    frame = s.get('frame_ms')
    rows = [
        {'field': 'level', 'value': level},
        {'field': 'how', 'value': how},
        {'field': 'cores for the screen', 'value': str(s.get('cores', '?'))},
        {'field': 'a frame costs', 'value': f'{frame:.1f} ms' if isinstance(frame, (int, float)) else '?'},
        {'field': 'motion', 'value': 'on' if s.get('motion') else 'off (HIVE_SCREEN_MOTION=off)'},
        {'field': 'scene', 'value': 'x'.join(str(n) for n in s.get('scene', [])) or '?'},
        {'field': 'hive-screen', 'value': unit},
    ]
    choice = str(s.get('level_name') or 'auto') if s.get('pinned') else 'auto'
    return {'on_screen': True, 'unit': unit, 'level': s.get('level_name'), 'choice': choice, 'rows': rows}


# ---------------------------------------------------------------- the Hive

def _whitelist(text: Optional[str]) -> dict:
    if not text:
        return {}
    try:
        import tomllib
    except ImportError:
        return {}
    try:
        return tomllib.loads(text)
    except (tomllib.TOMLDecodeError, ValueError):
        return {}


@service('settings.hive')
def hive() -> dict:
    """The Hive: each daemon and its state, and what the whitelist allows."""
    d = _doors()
    states = (d['run_any'](['systemctl', 'is-active', *DAEMONS]) or '').split()
    daemons = [{'name': name, 'state': states[i] if i < len(states) else NOT_READ}
               for i, name in enumerate(DAEMONS)]
    wl = _whitelist(d['read']('/etc/hive/whitelist.toml'))
    commands = [c.get('command', '?') for c in wl.get('run_command', {}).get('allowed', [])]
    services = wl.get('service', {}).get('allowed', [])
    paths = wl.get('file_ops', {}).get('allowed_paths', [])
    rows = [
        {'field': 'commands', 'value': ', '.join(dict.fromkeys(commands)) if commands else NOT_READ},
        {'field': 'services', 'value': ', '.join(services) if services else NOT_READ},
        {'field': 'paths', 'value': ', '.join(paths) if paths else NOT_READ},
        {'field': 'from', 'value': '/etc/hive/whitelist.toml' if wl else 'no readable whitelist'},
    ]
    return {'daemons': daemons, 'active': sum(1 for x in daemons if x['state'] == 'active'), 'rows': rows}


# ---------------------------------------------------------------- asking the Hive

HOSTNAME = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$')
LEVELS = ('auto', 'plain', 'effects', 'fine')
INTERFACE = re.compile(r'^[a-z][a-z0-9._-]{0,14}$')
IPV4 = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
CIDR = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$')


def _ipv4(text: str) -> bool:
    m = IPV4.match(text)
    return bool(m) and all(0 <= int(g) <= 255 for g in m.groups())


def _cidr(text: str) -> bool:
    m = CIDR.match(text)
    return bool(m) and _ipv4(text.split('/')[0]) and 1 <= int(m.group(5)) <= 32


def _network_args(interface: str, mode: str, address: str, gateway: str, dns: str) -> Tuple[Optional[List[str]], str]:
    """The words of `hive request set-network`, or what is wrong with the fields."""
    if not INTERFACE.match(interface):
        return None, f'"{interface}" is not an interface'
    if mode == 'dhcp':
        return ['set-network', interface, 'dhcp'], f'network {interface} by DHCP'
    if mode != 'static':
        return None, f'"{mode}" is not a source: dhcp or static'
    if not _cidr(address):
        return None, f'"{address}" is not an address with its prefix (10.0.2.20/24)'
    if gateway and not _ipv4(gateway):
        return None, f'"{gateway}" is not an IPv4 gateway'
    servers = [s for s in re.split(r'[,\s]+', dns) if s]
    if len(servers) > 4 or not all(_ipv4(s) for s in servers):
        return None, f'"{dns}" is not up to four IPv4 DNS servers'
    args = ['set-network', interface, address]
    what = f'network {interface} static at {address}'
    if gateway:
        args += ['via', gateway]
        what += f' via {gateway}'
    if servers:
        args += ['dns', ','.join(servers)]
        what += f', DNS {", ".join(servers)}'
    return args, what


@service('settings.ask')
def ask_hive(action: str, value: str = '', mode: str = 'dhcp', address: str = '', gateway: str = '',
             dns: str = '') -> dict:
    """Asks the Hive for a setting (`hive request`): the name of the machine
    (set-hostname), the keyboard (set-keyboard: us or br, with its model), the
    screen's level (set-screen-level: auto, plain, effects, fine), the network
    (set-network: `value` is the interface; by DHCP, or static at `address`
    with its prefix, `gateway` and `dns`). Nothing changes here: the Hive
    offers it, and someone approves it on the screen (F1, Enter; twice for the
    network, which is dangerous) or the dashboard. Answers whether it was
    asked, and what to say."""
    value = (value or '').strip()
    dangerous = False
    if action == 'set-network':
        args, what = _network_args(value, (mode or 'dhcp').strip(), (address or '').strip(),
                                   (gateway or '').strip(), (dns or '').strip())
        if args is None:
            return {'ok': False, 'message': what}
        dangerous = True
    elif action == 'set-hostname':
        if not HOSTNAME.match(value):
            return {'ok': False, 'message': f'"{value}" is not a name: lowercase letters, digits and hyphens, up to 63'}
        args = ['set-hostname', value]
        what = f'name the machine {value}'
    elif action == 'set-keyboard':
        if value not in KEYBOARDS:
            return {'ok': False, 'message': f'"{value}" is not a keyboard the screen reads: us or br'}
        args = ['set-keyboard', value, KEYBOARDS[value]]
        what = f'keyboard {value} ({KEYBOARDS[value]})'
    elif action == 'set-screen-level':
        if value not in LEVELS:
            return {'ok': False, 'message': f'"{value}" is not a level: auto, plain, effects or fine'}
        args = ['set-screen-level', value]
        what = 'screen level chosen by the measure' if value == 'auto' else f'screen level {value}'
    else:
        return {'ok': False, 'message': f'{action}: not a setting one can ask for'}
    code, said = _doors()['ask'](args)
    if code == 0:
        how = 'It is dangerous: approve it on the screen with Enter twice (F1)' if dangerous \
            else 'Approve it on the screen (F1, Enter)'
        return {'ok': True, 'message': f'Asked the Hive: {what}. {how} or on the dashboard; F5 reads again.'}
    return {'ok': False, 'message': f'The Hive did not get the request ({what}): {said or "no answer"}'}
