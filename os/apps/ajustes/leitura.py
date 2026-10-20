"""What the Ajustes app reads of the machine, as the user who opened it.

Five services, one a tab: the machine, the network, the keyboard, the
screen, the Hive. Each answers plain data for the page (rows of `campo` and
`valor`, tables), never raises, and says "?" or "não lido" for what it could
not read: the page is the same on a machine with no `ip`, no systemd and no
screen. Everything is read from files anyone may read and commands anyone
may run (`ip -j addr`, `systemctl is-active`); nothing here changes the
system, and nothing needs root.

`run` and `read` are the two doors to the machine, so a test replaces them.
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

NAO_LIDO = 'não lido'
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
    """`hive request ...`: the third door, the only one that changes anything, and only by asking.
    The exit code (None when `hive` is not on the machine) and what it said."""
    if shutil.which('hive') is None:
        return None, 'o comando hive não está nesta máquina'
    try:
        done = subprocess.run(['hive', 'request', *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return done.returncode, (done.stdout + done.stderr).strip()


def _doors() -> Dict[str, Callable]:
    """The doors as they are now (a test replaces the module's functions)."""
    return {'run': run, 'run_any': run_any, 'read': read, 'ask': ask}


# ---------------------------------------------------------------- the machine

def _tamanho(kib: float) -> str:
    """Kibibytes as the shelf says them: 15,6 GB, 512 MB."""
    b = kib * 1024
    for unit, size in (('TB', 1024 ** 4), ('GB', 1024 ** 3), ('MB', 1024 ** 2)):
        if b >= size:
            return f'{b / size:.1f} {unit}'.replace('.', ',')
    return f'{int(kib)} kB'


def _ligada(seconds: float) -> str:
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


@service('ajustes.maquina')
def maquina() -> dict:
    """The machine: its name, system, kernel, uptime, cores, memory and disk."""
    d = _doors()
    nome = (d['read']('/proc/sys/kernel/hostname') or '').strip() or socket.gethostname()
    sistema = NAO_LIDO
    for line in (d['read']('/etc/os-release') or '').splitlines():
        if line.startswith('PRETTY_NAME='):
            sistema = line.split('=', 1)[1].strip().strip('"')
    uptime = d['read']('/proc/uptime')
    ligada = _ligada(float(uptime.split()[0])) if uptime else NAO_LIDO
    mem = _meminfo(d['read']('/proc/meminfo'))
    if 'MemTotal' in mem:
        livre = mem.get('MemAvailable', mem.get('MemFree', 0.0))
        memoria = f'{_tamanho(mem["MemTotal"] - livre)} em uso de {_tamanho(mem["MemTotal"])}'
    else:
        memoria = NAO_LIDO
    try:
        usage = shutil.disk_usage('/')
        disco = f'{_tamanho(usage.used / 1024)} em uso de {_tamanho(usage.total / 1024)} ' \
                f'({usage.used * 100 // max(usage.total, 1)}%)'
    except OSError:
        disco = NAO_LIDO
    nucleos = os.cpu_count() or 1
    linhas = [
        {'campo': 'nome', 'valor': nome},
        {'campo': 'sistema', 'valor': sistema},
        {'campo': 'kernel', 'valor': os.uname().release},
        {'campo': 'ligada há', 'valor': ligada},
        {'campo': 'núcleos', 'valor': str(nucleos)},
        {'campo': 'memória', 'valor': memoria},
        {'campo': 'disco /', 'valor': disco},
    ]
    return {'nome': nome, 'nucleos': nucleos, 'linhas': linhas}


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


@service('ajustes.rede')
def rede() -> dict:
    """The network: each interface with its addresses, state and where the
    address came from; the gateway; the DNS servers."""
    d = _doors()
    interfaces = []
    addrs = _json(d['run'](['ip', '-j', 'addr']))
    if addrs:
        for iface in addrs:
            if iface.get('link_type') == 'loopback':
                continue
            enderecos, dinamicos = [], 0
            for a in iface.get('addr_info', []):
                if a.get('family') == 'inet' or a.get('scope') == 'global':
                    enderecos.append(f'{a.get("local")}/{a.get("prefixlen")}')
                    if a.get('dynamic'):
                        dinamicos += 1
            estado = str(iface.get('operstate', '?')).lower()
            interfaces.append({
                'nome': iface.get('ifname', '?'),
                'estado': {'up': 'ligada', 'down': 'desligada', 'unknown': 'ligada'}.get(estado, estado),
                'endereco': ', '.join(enderecos) or 'sem endereço',
                'origem': 'DHCP' if dinamicos else ('fixo' if enderecos else '-'),
            })
    else:
        # no ip: the kernel still names them
        for name in sorted(p.name for p in Path('/sys/class/net').glob('*')) if Path('/sys/class/net').is_dir() else []:
            if name == 'lo':
                continue
            estado = (d['read'](f'/sys/class/net/{name}/operstate') or '?').strip()
            interfaces.append({'nome': name, 'estado': {'up': 'ligada', 'down': 'desligada'}.get(estado, estado),
                               'endereco': NAO_LIDO, 'origem': '?'})
    gateway = 'nenhum'
    for route in _json(d['run'](['ip', '-j', 'route'])):
        if route.get('dst') == 'default':
            gateway = f'{route.get("gateway", "?")} por {route.get("dev", "?")}'
            if route.get('protocol') == 'dhcp':
                gateway += ' (DHCP)'
            break
    dns = _dns(d)
    # the form's choices: the interfaces by name, the first one chosen; what it has now, as the fields' start
    nomes = [i['nome'] for i in interfaces if INTERFACE.match(str(i['nome']))]
    primeira = interfaces[0] if interfaces else {}
    endereco = str(primeira.get('endereco', '')).split(',')[0].strip()
    return {
        'interfaces': interfaces,
        'gateway': gateway,
        'dns': ', '.join(dns) if dns else 'nenhum',
        'opcoes': ','.join(nomes),
        'escolha': nomes[0] if nomes else '',
        'origem': 'fixo' if primeira.get('origem') == 'fixo' else 'dhcp',
        'endereco': endereco if CIDR.match(endereco) else '',
        'via': gateway.split()[0] if gateway != 'nenhum' else '',
        'servidores': ','.join(dns),
        'linhas': [{'campo': 'gateway', 'valor': gateway},
                   {'campo': 'DNS', 'valor': ', '.join(dns) if dns else 'nenhum'}],
    }


# ---------------------------------------------------------------- the keyboard

def _keyboard_file(text: Optional[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (text or '').splitlines():
        m = re.match(r'^\s*(XKB\w+)\s*=\s*"?([^"]*)"?\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


@service('ajustes.teclado')
def teclado() -> dict:
    """The keyboard: the system's layout (/etc/default/keyboard) and the one
    the screen reads, when the page is on the screen."""
    d = _doors()
    keys = _keyboard_file(d['read']('/etc/default/keyboard'))
    layout = keys.get('XKBLAYOUT') or NAO_LIDO
    modelo = keys.get('XKBMODEL') or '-'
    # the keyboard the Hive applied (set-keyboard), which the screen reads first
    hive = (d['read']('/var/lib/hive/settings/keyboard') or '').split()
    ajuste = ' '.join(hive) if hive else 'nenhum (a tela lê o do sistema)'
    tela = _screen_status()
    na_tela = tela.get('keyboard') if tela else 'a página não está na tela'
    escolha = hive[0] if hive and hive[0] in KEYBOARDS else (layout if layout in KEYBOARDS else 'us')
    return {
        'layout': layout,
        'escolha': escolha,
        'linhas': [
            {'campo': 'layout do sistema', 'valor': f'{layout} ({modelo}), de /etc/default/keyboard'},
            {'campo': 'ajuste da Hive', 'valor': ajuste},
            {'campo': 'a tela lê', 'valor': na_tela},
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


@service('ajustes.tela')
def tela() -> dict:
    """The screen: its presentation level, pinned or chosen, what a frame
    costs, whether pages move; and whether the daemon runs."""
    d = _doors()
    servico = (d['run_any'](['systemctl', 'is-active', 'hive-screen']) or NAO_LIDO).strip()
    s = _screen_status()
    if s is None:
        linhas = [{'campo': 'esta página', 'valor': 'não está na tela (abra com hive ajustes)'},
                  {'campo': 'hive-screen', 'valor': servico}]
        return {'na_tela': False, 'servico': servico, 'escolha': 'auto', 'linhas': linhas}
    nivel = f'{s.get("level_name", "?")} ({s.get("level", "?")})'
    escolha = 'pregado por HIVE_SCREEN_LEVEL' if s.get('pinned') else 'escolhido pela medida do quadro'
    quadro = s.get('frame_ms')
    linhas = [
        {'campo': 'nível', 'valor': nivel},
        {'campo': 'escolha', 'valor': escolha},
        {'campo': 'núcleos para a tela', 'valor': str(s.get('cores', '?'))},
        {'campo': 'um quadro custa', 'valor': f'{quadro:.1f} ms'.replace('.', ',') if isinstance(quadro, (int, float)) else '?'},
        {'campo': 'movimento', 'valor': 'ligado' if s.get('motion') else 'desligado (HIVE_SCREEN_MOTION=off)'},
        {'campo': 'cena', 'valor': 'x'.join(str(n) for n in s.get('scene', [])) or '?'},
        {'campo': 'hive-screen', 'valor': servico},
    ]
    escolha = str(s.get('level_name') or 'auto') if s.get('pinned') else 'auto'
    return {'na_tela': True, 'servico': servico, 'nivel': s.get('level_name'), 'escolha': escolha, 'linhas': linhas}


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


@service('ajustes.hive')
def hive() -> dict:
    """The Hive: each daemon and its state, and what the whitelist allows."""
    d = _doors()
    estados = (d['run_any'](['systemctl', 'is-active', *DAEMONS]) or '').split()
    daemons = [{'nome': name, 'estado': estados[i] if i < len(estados) else NAO_LIDO}
               for i, name in enumerate(DAEMONS)]
    wl = _whitelist(d['read']('/etc/hive/whitelist.toml'))
    comandos = [c.get('command', '?') for c in wl.get('run_command', {}).get('allowed', [])]
    servicos = wl.get('service', {}).get('allowed', [])
    caminhos = wl.get('file_ops', {}).get('allowed_paths', [])
    linhas = [
        {'campo': 'comandos', 'valor': ', '.join(dict.fromkeys(comandos)) if comandos else NAO_LIDO},
        {'campo': 'serviços', 'valor': ', '.join(servicos) if servicos else NAO_LIDO},
        {'campo': 'caminhos', 'valor': ', '.join(caminhos) if caminhos else NAO_LIDO},
        {'campo': 'de', 'valor': '/etc/hive/whitelist.toml' if wl else 'sem whitelist legível'},
    ]
    return {'daemons': daemons, 'ativos': sum(1 for x in daemons if x['estado'] == 'active'), 'linhas': linhas}


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


def _rede_args(interface: str, origem: str, endereco: str, gateway: str, dns: str) -> Tuple[Optional[List[str]], str]:
    """The words of `hive request set-network`, or what is wrong with the fields."""
    if not INTERFACE.match(interface):
        return None, f'"{interface}" não é uma interface'
    if origem == 'dhcp':
        return ['set-network', interface, 'dhcp'], f'rede {interface} por DHCP'
    if origem != 'fixo':
        return None, f'"{origem}" não é uma origem: dhcp ou fixo'
    if not _cidr(endereco):
        return None, f'"{endereco}" não é um endereço com prefixo (10.0.2.20/24)'
    if gateway and not _ipv4(gateway):
        return None, f'"{gateway}" não é um gateway IPv4'
    servidores = [s for s in re.split(r'[,\s]+', dns) if s]
    if len(servidores) > 4 or not all(_ipv4(s) for s in servidores):
        return None, f'"{dns}" não são até quatro servidores DNS IPv4'
    args = ['set-network', interface, endereco]
    pedido = f'rede {interface} fixa em {endereco}'
    if gateway:
        args += ['via', gateway]
        pedido += f' via {gateway}'
    if servidores:
        args += ['dns', ','.join(servidores)]
        pedido += f', DNS {", ".join(servidores)}'
    return args, pedido


@service('ajustes.pedir')
def pedir(acao: str, valor: str = '', origem: str = 'dhcp', endereco: str = '', gateway: str = '',
          dns: str = '') -> dict:
    """Asks the Hive for a setting (`hive request`): the name of the machine
    (set-hostname), the keyboard (set-keyboard: us or br, with its model), the
    screen's level (set-screen-level: auto, plain, effects, fine), the network
    (set-network: `valor` is the interface; by DHCP, or fixed at `endereco`
    with its prefix, `gateway` and `dns`). Nothing changes here: the Hive
    offers it, and someone approves it on the screen (F1, Enter; twice for the
    network, which is dangerous) or the dashboard. Answers whether it was
    asked, and what to say."""
    valor = (valor or '').strip()
    perigoso = False
    if acao == 'set-network':
        args, pedido = _rede_args(valor, (origem or 'dhcp').strip(), (endereco or '').strip(),
                                  (gateway or '').strip(), (dns or '').strip())
        if args is None:
            return {'ok': False, 'mensagem': pedido}
        perigoso = True
    elif acao == 'set-hostname':
        if not HOSTNAME.match(valor):
            return {'ok': False, 'mensagem': f'"{valor}" não serve de nome: letras minúsculas, dígitos e hífens, até 63'}
        args = ['set-hostname', valor]
        pedido = f'mudar o nome da máquina para {valor}'
    elif acao == 'set-keyboard':
        if valor not in KEYBOARDS:
            return {'ok': False, 'mensagem': f'"{valor}" não é um teclado que a tela lê: us ou br'}
        args = ['set-keyboard', valor, KEYBOARDS[valor]]
        pedido = f'teclado {valor} ({KEYBOARDS[valor]})'
    elif acao == 'set-screen-level':
        if valor not in LEVELS:
            return {'ok': False, 'mensagem': f'"{valor}" não é um nível: auto, plain, effects ou fine'}
        args = ['set-screen-level', valor]
        pedido = 'nível da tela escolhido pela medida' if valor == 'auto' else f'nível da tela {valor}'
    else:
        return {'ok': False, 'mensagem': f'{acao}: não é um ajuste que se pede'}
    code, said = _doors()['ask'](args)
    if code == 0:
        como = 'É perigoso: aprove na tela com Enter duas vezes (F1)' if perigoso else 'Aprove na tela (F1, Enter)'
        return {'ok': True, 'mensagem': f'Pedido à Hive: {pedido}. {como} ou no dashboard; F5 relê.'}
    return {'ok': False, 'mensagem': f'A Hive não recebeu o pedido ({pedido}): {said or "sem resposta"}'}
