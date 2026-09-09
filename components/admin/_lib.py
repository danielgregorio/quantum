# components/admin/_lib.py
# Shared YAML persistence utilities for Quantum Native Admin
import os
import yaml
import uuid
import datetime

ADMIN_DIR = os.path.join(os.getcwd(), 'quantum_admin', 'settings')


def _ensure_dir():
    os.makedirs(ADMIN_DIR, exist_ok=True)


def load_yaml(filename):
    path = os.path.join(ADMIN_DIR, filename)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or []
    return []


def save_yaml(filename, data):
    _ensure_dir()
    path = os.path.join(ADMIN_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def gen_id():
    return uuid.uuid4().hex[:8]


def now_iso():
    return datetime.datetime.now().isoformat(timespec='seconds')


def find_by_id(items, item_id):
    for item in items:
        if item.get('id') == item_id:
            return item
    return None


def find_by_name(items, name):
    for item in items:
        if item.get('name') == name:
            return item
    return None


# =============================================================================
# Process Management
# =============================================================================

PIDS_DIR = os.path.join(ADMIN_DIR, 'pids')
LOGS_DIR = os.path.join(ADMIN_DIR, 'logs')


def _ensure_pids_dir():
    os.makedirs(PIDS_DIR, exist_ok=True)


def _ensure_logs_dir():
    os.makedirs(LOGS_DIR, exist_ok=True)


def get_pid_path(project_name):
    _ensure_pids_dir()
    return os.path.join(PIDS_DIR, f'{project_name}.pid')


def get_log_path(project_name):
    _ensure_logs_dir()
    return os.path.join(LOGS_DIR, f'{project_name}.log')


def read_pid(project_name):
    path = get_pid_path(project_name)
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            pass
    return None


def write_pid(project_name, pid):
    path = get_pid_path(project_name)
    with open(path, 'w') as f:
        f.write(str(pid))


def remove_pid(project_name):
    path = get_pid_path(project_name)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def is_process_running(pid):
    if pid is None:
        return False
    try:
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


def get_process_status(project_name):
    pid = read_pid(project_name)
    running = is_process_running(pid) if pid else False
    if pid and not running:
        remove_pid(project_name)
        pid = None
    return {'running': running, 'pid': pid}


def get_log_tail(project_name, n=50):
    path = get_log_path(project_name)
    if not os.path.isfile(path):
        return ''
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        return ''.join(lines[-n:])
    except OSError:
        return ''


# =============================================================================
# Environment Helpers
# =============================================================================

def find_env_by_name(environments, env_name):
    for env in (environments or []):
        if env.get('name') == env_name:
            return env
    return None
