#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quantum installer.

    python install.py --check       # only diagnoses, installs nothing
    python install.py               # installs into a venv ./.venv
    python install.py --venv ~/q    # installs into a chosen venv
    python install.py --system      # installs into the current Python (no venv)
    python install.py --dev         # includes the test dependencies
    python install.py --all-extras  # includes db, rag, jobs, websocket

This file runs BEFORE Quantum exists on the machine, and the machine may not
meet the requirements — which is exactly when the message needs to be good.
That is why:

- **It imports nothing from Quantum.** Not even to find out the version.
- **It uses no f-string, walrus or match.** An f-string is a SYNTAX error in
  Python 2 and in 3.5, and a syntax error happens when compiling the whole
  file: the script would die with an unreadable traceback exactly on the old
  machine the version check exists for. With `.format()`, the old
  interpreter can read the file, reach the check and say what is missing.
- **It diagnoses everything before trying anything**, and exits with a
  non-zero code if something blocks, so it can be used in CI.
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


# ---------------------------------------------------------------- output

class Out(object):
    """Colors when the terminal supports them, plain text when not."""

    def __init__(self):
        self.color = self._supports_color()

    def _supports_color(self):
        if os.environ.get('NO_COLOR'):
            return False
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        if sys.platform == 'win32':
            # Windows Terminal and the new console understand ANSI; the old cmd
            # does not, and would litter the screen with escapes.
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


# ------------------------------------------------------------ diagnosis

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
            'Quantum needs {0}+. Install a newer version and run '
            'this script with it.'.format(
                '.'.join(str(n) for n in MIN_PYTHON)))
    if version[:2] < RECOMMENDED_PYTHON:
        return Check('Python', WARN, text, 'works; 3.12+ is what is tested')
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
            'pip', FAIL, 'missing',
            'without pip nothing can be installed. Try: python -m ensurepip '
            '--upgrade')


def check_venv():
    try:
        import venv  # noqa: F401
        return Check('venv module', OK, 'available')
    except ImportError:
        return Check(
            'venv module', WARN, 'missing',
            'on Debian/Ubuntu: apt install python3-venv. Without it, use '
            '--system')


def check_disk():
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        free_mb = usage.free // (1024 * 1024)
    except Exception:
        return Check('disk space', WARN, 'unknown')
    if free_mb < MIN_DISK_MB:
        return Check(
            'disk space', FAIL, '{0} MB'.format(free_mb),
            'needs ~{0} MB'.format(MIN_DISK_MB))
    return Check('disk space', OK, '{0} MB free'.format(free_mb))


def check_write_permission():
    # One name per process: two checks running at once (the test suite runs
    # them in parallel) removed each other's probe and reported the folder
    # as not writable.
    probe = os.path.join(PROJECT_ROOT,
                         '.quantum-install-probe-{0}'.format(os.getpid()))
    try:
        handle = open(probe, 'w')
        handle.write('x')
        handle.close()
        os.remove(probe)
        return Check('directory write access', OK, PROJECT_ROOT)
    except Exception as exc:
        return Check('directory write access', FAIL, PROJECT_ROOT, str(exc))


def check_network():
    try:
        if sys.version_info[0] >= 3:
            from urllib.request import urlopen
        else:
            from urllib2 import urlopen
        urlopen('https://pypi.org/simple/', timeout=8).close()
        return Check('PyPI access', OK, 'reachable')
    except Exception:
        return Check(
            'PyPI access', WARN, 'no response',
            'an offline install only works with --no-deps and the wheels already '
            'downloaded')


def check_os():
    system = platform.system()
    detail = '{0} {1}'.format(system, platform.release())
    if system == 'Windows':
        return Check(
            'system', WARN, detail,
            'gunicorn does not run on Windows; to serve use waitress '
            '(see DEPLOYMENT.md)')
    return Check('system', OK, detail)


def check_project():
    marker = os.path.join(PROJECT_ROOT, 'pyproject.toml')
    if not os.path.exists(marker):
        return Check(
            'Quantum source', FAIL, PROJECT_ROOT,
            'run this script from inside the repository')
    return Check('Quantum source', OK, PROJECT_ROOT)


def check_git():
    path = shutil.which('git') if hasattr(shutil, 'which') else None
    if not path:
        return Check('git', WARN, 'missing', 'optional; only for development')
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
    out.title('Requirements')
    width = max(len(c.name) for c in checks)
    for check in checks:
        line = '  {0} {1}  {2}'.format(
            mark(check.status), check.name.ljust(width), check.found)
        print(line)
        if check.note:
            print('      {0}'.format(out.dim(check.note)))
    return checks


# ---------------------------------------------------------- installation

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
        print('  {0} failed (exit code {1})'.format(mark(FAIL), process.returncode))
        for line in text.strip().splitlines()[-12:]:
            print('      {0}'.format(line))
        return False, text
    return True, text


def create_venv(venv_dir):
    out.title('Virtual environment')
    if os.path.exists(venv_python(venv_dir)):
        print('  {0} already exists at {1}'.format(mark(OK), venv_dir))
        return True
    ok, _ = run([sys.executable, '-m', 'venv', venv_dir],
                'creating {0}'.format(venv_dir))
    return ok


def install(python_exe, extras, editable):
    out.title('Installation')
    ok, _ = run([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'],
                'upgrading pip')
    if not ok:
        return False

    target = PROJECT_ROOT
    if extras:
        target = '{0}[{1}]'.format(target, ','.join(extras))
    command = [python_exe, '-m', 'pip', 'install']
    if editable:
        command.append('-e')
    command.append(target)
    ok, _ = run(command, 'installing {0}'.format(target))
    return ok


# ---------------------------------------------------------- verification

SMOKE = (
    '<q:component name="Smoke">'
    '<q:set name="n" value="2" type="number" />'
    '<q:return value="{n}" />'
    '</q:component>'
)


def verify(python_exe):
    """Installed is not the same as working."""
    out.title('Verification')
    results = []

    ok, text = run([python_exe, '-c', 'import quantum; print(quantum.__file__)'],
                   'importing the package')
    results.append(('import quantum', ok))

    ok, _ = run([python_exe, '-c',
                 'from quantum.core.parser import QuantumParser;'
                 'from quantum.runtime.component import ComponentRuntime;'
                 'print("ok")'],
                'loading parser and runtime')
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
            'running a real component')
        ok = ok and 'RESULT=2' in text
        results.append(('runs a .q', ok))
    finally:
        if os.path.exists(smoke_path):
            os.remove(smoke_path)

    # `--help` on purpose, and not a subcommand: an installation check
    # cannot depend on the network or on a project being present.
    ok, _ = run([python_exe, '-m', 'quantum.cli.runner', '--help'],
                'calling the CLI')
    results.append(('CLI answers', ok))

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
                die('--venv needs a path')
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
            die('unknown option: {0}'.format(arg))
        i += 1
    return options


def die(message):
    print('{0} {1}'.format(mark(FAIL), message))
    sys.exit(EXIT_REQUIREMENTS)


def main(argv):
    options = parse_args(argv)

    print('')
    # The compact mark (assets/logo.txt). Pure ASCII on purpose: the block
    # versions depend on the console font, and this script has to come out
    # readable also when the output goes to a log or an old terminal.
    print('  {0} {1}'.format(out.bold('Q/>'), out.bold('Quantum')))
    print(out.dim('  installer - no GUI, no magic'))

    checks = print_checks(run_checks())
    blocking = [c for c in checks if c.status == FAIL]
    warnings = [c for c in checks if c.status == WARN]

    print('')
    if blocking:
        print('{0} {1} requirement(s) block the installation:'.format(
            mark(FAIL), len(blocking)))
        for check in blocking:
            print('    - {0}: {1}'.format(check.name, check.note or check.found))
        print('')
        print(out.dim('  Nothing was installed.'))
        return EXIT_REQUIREMENTS

    if warnings:
        print('{0} {1} warning(s); it is fine to proceed.'.format(
            mark(WARN), len(warnings)))
    else:
        print('{0} all requirements met.'.format(mark(OK)))

    if options['check_only']:
        print('')
        print(out.dim('  --check: nothing was installed.'))
        return EXIT_OK

    if options['system']:
        python_exe = sys.executable
        print('')
        print('{0} installing into the current Python (--system), without a venv.'.format(
            mark(WARN)))
    else:
        if not create_venv(options['venv']):
            return EXIT_INSTALL_FAILED
        python_exe = venv_python(options['venv'])

    if not install(python_exe, options['extras'], options['editable']):
        print('')
        print('{0} the installation failed. Nothing else was done.'.format(mark(FAIL)))
        return EXIT_INSTALL_FAILED

    if not verify(python_exe):
        print('')
        print('{0} it installed, but the verification failed — the package is there and '
              'does not work.'.format(mark(FAIL)))
        return EXIT_VERIFY_FAILED

    out.title('Done')
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
    print(out.dim('  Before serving this in production, read DEPLOYMENT.md and'))
    print(out.dim('  PRODUCTION_READINESS.md — there are known open criticals.'))
    return EXIT_OK


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print('')
        print('interrupted.')
        sys.exit(130)
