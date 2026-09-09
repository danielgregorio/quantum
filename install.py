#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quantum installer.

    python install.py --check       # so diagnostica, nao instala nada
    python install.py               # instala num venv ./.venv
    python install.py --venv ~/q    # instala num venv escolhido
    python install.py --system      # instala no Python atual (sem venv)
    python install.py --dev         # inclui as dependencias de teste
    python install.py --all-extras  # inclui db, rag, jobs, websocket

Este arquivo roda ANTES do Quantum existir na maquina, e a maquina pode nao
atender os requisitos — que e justamente quando a mensagem precisa ser boa.
Por isso:

- **Nao importa nada do Quantum.** Nem para descobrir a versao.
- **Nao usa f-string, walrus, nem match.** Um f-string e erro de SINTAXE no
  Python 2 e no 3.5, e erro de sintaxe acontece ao compilar o arquivo
  inteiro: o script morreria com um traceback ilegivel exatamente na maquina
  velha para quem a checagem de versao existe. Com `.format()`, o
  interpretador antigo consegue ler o arquivo, chegar na checagem e dizer o
  que falta.
- **Diagnostica tudo antes de tentar qualquer coisa**, e sai com codigo
  diferente de zero se algo bloqueia, para poder ser usado em CI.
"""

import os
import platform
import shutil
import subprocess
import sys

MIN_PYTHON = (3, 11)
RECOMMENDED_PYTHON = (3, 12)
MIN_DISK_MB = 400
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

EXIT_OK = 0
EXIT_REQUIREMENTS = 1
EXIT_INSTALL_FAILED = 2
EXIT_VERIFY_FAILED = 3


# ----------------------------------------------------------------- saida

class Out(object):
    """Cores quando o terminal aceita, texto puro quando nao."""

    def __init__(self):
        self.color = self._supports_color()

    def _supports_color(self):
        if os.environ.get('NO_COLOR'):
            return False
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        if sys.platform == 'win32':
            # Windows Terminal e o console novo entendem ANSI; o cmd antigo
            # nao, e sujaria a tela com escapes.
            return bool(os.environ.get('WT_SESSION') or
                        os.environ.get('TERM_PROGRAM'))
        return True

    def _wrap(self, code, text):
        if not self.color:
            return text
        return '\033[{0}m{1}\033[0m'.format(code, text)

    def dim(self, t):
        return self._wrap('2', t)

    def bold(self, t):
        return self._wrap('1', t)

    def green(self, t):
        return self._wrap('32', t)

    def yellow(self, t):
        return self._wrap('33', t)

    def red(self, t):
        return self._wrap('31', t)

    def title(self, text):
        print('')
        print(self.bold(text))
        print(self.dim('-' * len(text)))


out = Out()

OK, WARN, FAIL = 'ok', 'warn', 'fail'
MARK = {OK: '+', WARN: '!', FAIL: 'x'}


def mark(status):
    text = MARK[status]
    if status == OK:
        return out.green(text)
    if status == WARN:
        return out.yellow(text)
    return out.red(text)


# ----------------------------------------------------------- diagnostico

class Check(object):
    def __init__(self, name, status, found, note=''):
        self.name = name
        self.status = status
        self.found = found
        self.note = note


def check_python():
    version = sys.version_info[:3]
    text = '.'.join(str(n) for n in version)
    if version[:2] < MIN_PYTHON:
        return Check(
            'Python', FAIL, text,
            'Quantum precisa de {0}+. Instale uma versao mais nova e rode '
            'este script com ela.'.format(
                '.'.join(str(n) for n in MIN_PYTHON)))
    if version[:2] < RECOMMENDED_PYTHON:
        return Check('Python', WARN, text, 'funciona; 3.12+ e o testado')
    return Check('Python', OK, text)


def check_pip():
    try:
        result = subprocess.check_output(
            [sys.executable, '-m', 'pip', '--version'],
            stderr=subprocess.STDOUT)
        version = result.decode('utf-8', 'replace').split()[1]
        return Check('pip', OK, version)
    except Exception:
        return Check(
            'pip', FAIL, 'ausente',
            'sem pip nao da para instalar. Tente: python -m ensurepip '
            '--upgrade')


def check_venv():
    try:
        import venv  # noqa: F401
        return Check('modulo venv', OK, 'disponivel')
    except ImportError:
        return Check(
            'modulo venv', WARN, 'ausente',
            'no Debian/Ubuntu: apt install python3-venv. Sem ele, use '
            '--system')


def check_disk():
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        free_mb = usage.free // (1024 * 1024)
    except Exception:
        return Check('espaco em disco', WARN, 'desconhecido')
    if free_mb < MIN_DISK_MB:
        return Check(
            'espaco em disco', FAIL, '{0} MB'.format(free_mb),
            'precisa de ~{0} MB'.format(MIN_DISK_MB))
    return Check('espaco em disco', OK, '{0} MB livres'.format(free_mb))


def check_write_permission():
    probe = os.path.join(PROJECT_ROOT, '.quantum-install-probe')
    try:
        handle = open(probe, 'w')
        handle.write('x')
        handle.close()
        os.remove(probe)
        return Check('escrita no diretorio', OK, PROJECT_ROOT)
    except Exception as exc:
        return Check('escrita no diretorio', FAIL, PROJECT_ROOT, str(exc))


def check_network():
    try:
        if sys.version_info[0] >= 3:
            from urllib.request import urlopen
        else:
            from urllib2 import urlopen
        urlopen('https://pypi.org/simple/', timeout=8).close()
        return Check('acesso ao PyPI', OK, 'alcancavel')
    except Exception:
        return Check(
            'acesso ao PyPI', WARN, 'sem resposta',
            'instalacao offline so funciona com --no-deps e as rodas ja '
            'baixadas')


def check_os():
    system = platform.system()
    detail = '{0} {1}'.format(system, platform.release())
    if system == 'Windows':
        return Check(
            'sistema', WARN, detail,
            'gunicorn nao roda no Windows; para servir use waitress '
            '(ver DEPLOYMENT.md)')
    return Check('sistema', OK, detail)


def check_project():
    marker = os.path.join(PROJECT_ROOT, 'pyproject.toml')
    if not os.path.exists(marker):
        return Check(
            'fonte do Quantum', FAIL, PROJECT_ROOT,
            'rode este script de dentro do repositorio')
    return Check('fonte do Quantum', OK, PROJECT_ROOT)


def check_git():
    path = shutil.which('git') if hasattr(shutil, 'which') else None
    if not path:
        return Check('git', WARN, 'ausente', 'opcional; so para desenvolver')
    return Check('git', OK, path)


def run_checks():
    return [
        check_project(),
        check_python(),
        check_pip(),
        check_venv(),
        check_os(),
        check_disk(),
        check_write_permission(),
        check_network(),
        check_git(),
    ]


def print_checks(checks):
    out.title('Requisitos')
    width = max(len(c.name) for c in checks)
    for check in checks:
        line = '  {0} {1}  {2}'.format(
            mark(check.status), check.name.ljust(width), check.found)
        print(line)
        if check.note:
            print('      {0}'.format(out.dim(check.note)))
    return checks


# ------------------------------------------------------------ instalacao

def venv_python(venv_dir):
    if sys.platform == 'win32':
        return os.path.join(venv_dir, 'Scripts', 'python.exe')
    return os.path.join(venv_dir, 'bin', 'python')


def run(command, description):
    print('  {0}'.format(out.dim(description)))
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, _ = process.communicate()
    except Exception as exc:
        print('  {0} {1}'.format(mark(FAIL), exc))
        return False, str(exc)
    text = output.decode('utf-8', 'replace') if output else ''
    if process.returncode != 0:
        print('  {0} falhou (codigo {1})'.format(mark(FAIL), process.returncode))
        for line in text.strip().splitlines()[-12:]:
            print('      {0}'.format(line))
        return False, text
    return True, text


def create_venv(venv_dir):
    out.title('Ambiente virtual')
    if os.path.exists(venv_python(venv_dir)):
        print('  {0} ja existe em {1}'.format(mark(OK), venv_dir))
        return True
    ok, _ = run([sys.executable, '-m', 'venv', venv_dir],
                'criando {0}'.format(venv_dir))
    return ok


def install(python_exe, extras, editable):
    out.title('Instalacao')
    ok, _ = run([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'],
                'atualizando o pip')
    if not ok:
        return False

    target = PROJECT_ROOT
    if extras:
        target = '{0}[{1}]'.format(target, ','.join(extras))
    command = [python_exe, '-m', 'pip', 'install']
    if editable:
        command.append('-e')
    command.append(target)
    ok, _ = run(command, 'instalando {0}'.format(target))
    return ok


# ----------------------------------------------------------- verificacao

SMOKE = (
    '<q:component name="Smoke">'
    '<q:set name="n" value="2" type="number" />'
    '<q:return value="{n}" />'
    '</q:component>'
)


def verify(python_exe):
    """Instalado nao e o mesmo que funcionando."""
    out.title('Verificacao')
    results = []

    ok, text = run([python_exe, '-c', 'import quantum; print(quantum.__file__)'],
                   'importando o pacote')
    results.append(('import quantum', ok))

    ok, _ = run([python_exe, '-c',
                 'from quantum.core.parser import QuantumParser;'
                 'from quantum.runtime.component import ComponentRuntime;'
                 'print("ok")'],
                'carregando parser e runtime')
    results.append(('parser + runtime', ok))

    smoke_path = os.path.join(PROJECT_ROOT, '.quantum-smoke.q')
    try:
        handle = open(smoke_path, 'w')
        handle.write(SMOKE)
        handle.close()
        ok, text = run(
            [python_exe, '-c',
             'import sys;'
             'from quantum.core.parser import QuantumParser;'
             'from quantum.runtime.component import ComponentRuntime;'
             'node = QuantumParser().parse_file(sys.argv[1]);'
             'print("RESULT=%s" % ComponentRuntime().execute_component(node, {}))',
             smoke_path],
            'executando um componente de verdade')
        ok = ok and 'RESULT=2' in text
        results.append(('executa um .q', ok))
    finally:
        if os.path.exists(smoke_path):
            os.remove(smoke_path)

    # `--help` de proposito, e nao um subcomando: a primeira versao chamava
    # `quantum apps`, que fala com um servidor de deploy remoto. A verificacao
    # da instalacao reprovava por DNS numa maquina onde tudo tinha instalado
    # certo. Uma checagem de instalacao nao pode depender de rede.
    ok, _ = run([python_exe, '-m', 'quantum.cli.runner', '--help'],
                'chamando a CLI')
    results.append(('CLI responde', ok))

    print('')
    for name, passed in results:
        print('  {0} {1}'.format(mark(OK if passed else FAIL), name))
    return all(passed for _, passed in results)


# ------------------------------------------------------------------ main

def parse_args(argv):
    options = {
        'check_only': False,
        'venv': os.path.join(PROJECT_ROOT, '.venv'),
        'system': False,
        'extras': [],
        'editable': True,
        'yes': False,
    }
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ('--check', '-c'):
            options['check_only'] = True
        elif arg == '--venv':
            i += 1
            if i >= len(argv):
                die('--venv precisa de um caminho')
            options['venv'] = os.path.abspath(argv[i])
        elif arg == '--system':
            options['system'] = True
        elif arg == '--dev':
            options['extras'].append('dev')
        elif arg == '--all-extras':
            options['extras'].extend(['db', 'rag', 'jobs', 'websocket'])
        elif arg == '--no-editable':
            options['editable'] = False
        elif arg in ('--yes', '-y'):
            options['yes'] = True
        elif arg in ('--help', '-h'):
            print(__doc__)
            sys.exit(EXIT_OK)
        else:
            die('opcao desconhecida: {0}'.format(arg))
        i += 1
    return options


def die(message):
    print('{0} {1}'.format(mark(FAIL), message))
    sys.exit(EXIT_REQUIREMENTS)


def main(argv):
    options = parse_args(argv)

    print('')
    # A marca compacta (assets/logo.txt). ASCII puro de proposito: as versoes
    # em blocos dependem da fonte do console, e este script tem que sair
    # legivel tambem quando a saida vai para um log ou um terminal antigo.
    print('  {0} {1}'.format(out.bold('Q/>'), out.bold('Quantum')))
    print(out.dim('  instalador - sem GUI, sem magica'))

    checks = print_checks(run_checks())
    blocking = [c for c in checks if c.status == FAIL]
    warnings = [c for c in checks if c.status == WARN]

    print('')
    if blocking:
        print('{0} {1} requisito(s) bloqueiam a instalacao:'.format(
            mark(FAIL), len(blocking)))
        for check in blocking:
            print('    - {0}: {1}'.format(check.name, check.note or check.found))
        print('')
        print(out.dim('  Nada foi instalado.'))
        return EXIT_REQUIREMENTS

    if warnings:
        print('{0} {1} aviso(s); da para prosseguir.'.format(
            mark(WARN), len(warnings)))
    else:
        print('{0} todos os requisitos atendidos.'.format(mark(OK)))

    if options['check_only']:
        print('')
        print(out.dim('  --check: nada foi instalado.'))
        return EXIT_OK

    if options['system']:
        python_exe = sys.executable
        print('')
        print('{0} instalando no Python atual (--system), sem venv.'.format(
            mark(WARN)))
    else:
        if not create_venv(options['venv']):
            return EXIT_INSTALL_FAILED
        python_exe = venv_python(options['venv'])

    if not install(python_exe, options['extras'], options['editable']):
        print('')
        print('{0} a instalacao falhou. Nada mais foi feito.'.format(mark(FAIL)))
        return EXIT_INSTALL_FAILED

    if not verify(python_exe):
        print('')
        print('{0} instalou, mas a verificacao falhou — o pacote esta la e '
              'nao funciona.'.format(mark(FAIL)))
        return EXIT_VERIFY_FAILED

    out.title('Pronto')
    if options['system']:
        print('  quantum run examples/hello.q')
    else:
        if sys.platform == 'win32':
            activate = os.path.join(options['venv'], 'Scripts', 'activate')
        else:
            activate = 'source ' + os.path.join(options['venv'], 'bin', 'activate')
        print('  {0}'.format(activate))
        print('  quantum run examples/hello.q')
    print('')
    print(out.dim('  Antes de servir isto em producao, leia DEPLOYMENT.md e'))
    print(out.dim('  PRODUCTION_READINESS.md — ha criticos conhecidos em aberto.'))
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print('')
        print('interrompido.')
        sys.exit(130)
