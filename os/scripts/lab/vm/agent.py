#!/usr/bin/python3
"""The VM lab's guest agent: the host's hands and eyes inside the guest.

It reads one JSON request per line on the virtio-serial port
/dev/virtio-ports/org.quantum.lab and writes one JSON answer per line. No
network, no SSH, no keys: the port exists only between this guest and the
QEMU process that runs it. Runs as root (quantum-lab-agent.service); stdlib
only, since the guest has nothing else to offer at first boot.

Every answer has "ok"; a failed request has "error" instead of its fields.
"""

import base64
import json
import os
import select
import subprocess
import sys
import time
import traceback

PORT = '/dev/virtio-ports/org.quantum.lab'


def op_ping(req):
    with open('/proc/sys/kernel/random/boot_id') as f:
        boot_id = f.read().strip()
    with open('/proc/uptime') as f:
        uptime = float(f.read().split()[0])
    return {'boot_id': boot_id, 'uptime': uptime, 'time': time.time()}


def op_restart(req):
    """Answers, then exits: systemd starts the agent again, from the file
    on disk (how the host updates it)."""
    global RESTART
    RESTART = True
    return {}


RESTART = False


def op_clock(req):
    # After a snapshot is restored the guest's clock is the snapshot's; the
    # host sets it so journal times and timers mean what they say.
    time.clock_settime(time.CLOCK_REALTIME, float(req['epoch']))
    return {'time': time.time()}


def logged_in_as(user):
    """For a program run as `user`: the session's login uid, as a login
    (pam_loginuid) would set it. The kernel audit rule the process nerve
    reads (auid!=-1) only records programs of someone who logged in, and a
    daemon's child (this agent's) has none."""
    if not user:
        return None
    import pwd
    uid = pwd.getpwnam(user).pw_uid

    def setup():
        with open('/proc/self/loginuid', 'w') as f:
            f.write(str(uid))
    return setup


def op_exec(req):
    """Runs argv (or `sh` through /bin/sh -c), as `user` (logged in) if given."""
    argv = req.get('argv') or ['/bin/sh', '-c', req['sh']]
    if req.get('user'):
        argv = ['runuser', '-u', req['user'], '--'] + argv
    env = dict(os.environ, **req.get('env', {}))
    try:
        done = subprocess.run(argv, input=req.get('input', '').encode(), capture_output=True,
                              timeout=req.get('timeout', 60), env=env, cwd=req.get('cwd', '/'),
                              preexec_fn=logged_in_as(req.get('user')))
    except subprocess.TimeoutExpired as e:
        return {'code': None, 'timeout': True,
                'stdout': (e.stdout or b'').decode(errors='replace'),
                'stderr': (e.stderr or b'').decode(errors='replace')}
    return {'code': done.returncode, 'stdout': done.stdout.decode(errors='replace'),
            'stderr': done.stderr.decode(errors='replace')}


def op_put(req):
    path = req['path']
    os.makedirs(os.path.dirname(path) or '/', exist_ok=True)
    tmp = f'{path}.lab-tmp'
    with open(tmp, 'wb') as f:
        f.write(base64.b64decode(req['data']))
    os.chmod(tmp, int(str(req.get('mode', '644')), 8))
    os.replace(tmp, path)
    return {'path': path}


def op_get(req):
    with open(req['path'], 'rb') as f:
        return {'data': base64.b64encode(f.read()).decode()}


def op_mount(req):
    """Mounts a share of the host (9p, read-only), `tag` at `path`. A
    mounted 9p share keeps QEMU from saving a snapshot, so the host unmounts
    it after each use."""
    tag = req.get('tag', 'lab')
    path = req.get('path', f'/mnt/{tag}')
    os.makedirs(path, exist_ok=True)
    if not os.path.ismount(path):
        subprocess.run(['mount', '-t', '9p', '-o', 'trans=virtio,version=9p2000.L,ro,msize=1048576',
                        tag, path], check=True, capture_output=True)
    return {'path': path}


def op_umount(req):
    path = req.get('path', f'/mnt/{req.get("tag", "lab")}')
    if os.path.ismount(path):
        subprocess.run(['umount', path], check=True, capture_output=True)
    return {}


def op_journal(req):
    """The journal after `cursor` (or the last `lines`), as entries, and the
    cursor to ask from next time."""
    argv = ['journalctl', '--no-pager', '-o', 'json', '--show-cursor']
    if req.get('cursor'):
        argv += ['--after-cursor', req['cursor']]
    else:
        argv += ['-n', str(req.get('lines', 50))]
    for unit in req.get('units', []):
        argv += ['-u', unit]
    done = subprocess.run(argv, capture_output=True, text=True)
    entries, cursor = [], req.get('cursor')
    for line in done.stdout.splitlines():
        if line.startswith('-- cursor: '):
            cursor = line[len('-- cursor: '):]
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        cursor = e.get('__CURSOR', cursor)
        msg = e.get('MESSAGE')
        if isinstance(msg, list):  # journald stores non-UTF-8 text as bytes
            msg = bytes(msg).decode(errors='replace')
        entries.append({'t': int(e.get('__REALTIME_TIMESTAMP', 0)) / 1e6,
                        'unit': e.get('_SYSTEMD_UNIT') or e.get('SYSLOG_IDENTIFIER'),
                        'priority': int(e.get('PRIORITY', 6)), 'message': msg,
                        'cursor': e.get('__CURSOR')})
    return {'entries': entries, 'cursor': cursor}


# Programs the host talks to in JSON lines (hive-lab term: the dashboard or
# grove in a pseudo-terminal, its screen rendered here), by name.
PROCS = {}


def op_proc_start(req):
    name = req['name']
    if name in PROCS and PROCS[name].poll() is None:
        raise RuntimeError(f'{name} is already running')
    PROCS[name] = subprocess.Popen(req['argv'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, env=dict(os.environ, **req.get('env', {})),
                                   cwd=req.get('cwd', '/'), preexec_fn=logged_in_as(req.get('login')))
    return {'pid': PROCS[name].pid}


def op_proc_call(req):
    """Writes one line to the program and answers the line it writes back
    (within `timeout` seconds)."""
    proc = PROCS[req['name']]
    proc.stdin.write((req['line'].rstrip('\n') + '\n').encode())
    proc.stdin.flush()
    r, _, _ = select.select([proc.stdout], [], [], req.get('timeout', 30))
    if not r:
        raise RuntimeError(f'{req["name"]} did not answer in {req.get("timeout", 30)} s')
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError(f'{req["name"]} stopped (exit {proc.wait()})')
    return {'line': line.decode(errors='replace').rstrip('\n')}


def op_proc_stop(req):
    proc = PROCS.pop(req['name'], None)
    if proc and proc.poll() is None:
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return {}


OPS = {name[3:]: fn for name, fn in globals().items() if name.startswith('op_')}


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else PORT
    while not os.path.exists(port):
        time.sleep(0.2)
    fd = os.open(port, os.O_RDWR)
    buf = b''
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            # nobody on the host side: wait for one
            time.sleep(0.1)
            continue
        buf += chunk
        while b'\n' in buf:
            line, buf = buf.split(b'\n', 1)
            if not line.strip():
                continue
            req = {}
            try:
                req = json.loads(line)
                answer = {'ok': True, **OPS[req['op']](req)}
            except Exception as e:  # noqa: BLE001 - every failure becomes an answer
                answer = {'ok': False, 'error': f'{type(e).__name__}: {e}',
                          'trace': traceback.format_exc(limit=3)}
            if isinstance(req, dict) and 'id' in req:
                answer['id'] = req['id']
            out = (json.dumps(answer) + '\n').encode()
            while out:
                out = out[os.write(fd, out):]
            if RESTART:
                os._exit(0)


if __name__ == '__main__':
    main()
