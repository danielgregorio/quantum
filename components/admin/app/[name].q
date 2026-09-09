<q:component name="AdminAppDetail">

  <!-- Action: Update project info -->
  <q:action name="updateProject" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="name" type="string" />
    <q:param name="description" type="string" />
    <q:param name="status" type="string" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id, now_iso

pid = q.form.get('project_id', '').strip()
projects = load_yaml('projects.yaml')
proj = find_by_id(projects, pid)

if proj:
    new_name = q.form.get('name', '').strip()
    desc = q.form.get('description', '').strip()
    status = q.form.get('status', '').strip()
    if new_name:
        proj['name'] = new_name
    if desc is not None:
        proj['description'] = desc
    if status in ('active', 'archived', 'error'):
        proj['status'] = status
    proj['updated_at'] = now_iso()
    save_yaml('projects.yaml', projects)
    # Redirect using the (possibly updated) project name
    q._redirect_name = proj['name']
    </q:python>

    <q:redirect url="/admin/app/{_redirect_name}?flash=Project+updated" />
  </q:action>

  <!-- Action: Create a project-scoped connector -->
  <q:action name="createProjectConnector" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />
    <q:param name="name" type="string" required="true" />
    <q:param name="conn_type" type="string" required="true" />
    <q:param name="provider" type="string" required="true" />
    <q:param name="host" type="string" />
    <q:param name="port" type="string" />
    <q:param name="database" type="string" />
    <q:param name="username" type="string" />
    <q:param name="password" type="string" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, gen_id, now_iso

pid = q.form.get('project_id', '').strip()
name = q.form.get('name', '').strip()
conn_type = q.form.get('conn_type', '').strip()
provider = q.form.get('provider', '').strip()

if name and conn_type and provider:
    connectors = load_yaml('connectors.yaml')
    port_str = q.form.get('port', '0').strip()
    try:
        port_val = int(port_str) if port_str else 0
    except:
        port_val = 0

    docker_images = {
        'postgres': 'postgres:16-alpine', 'mysql': 'mysql:8', 'mariadb': 'mariadb:11',
        'mongodb': 'mongo:7', 'sqlite': '', 'rabbitmq': 'rabbitmq:3-management-alpine',
        'redis_queue': 'redis:7-alpine', 'kafka': 'confluentinc/cp-kafka:7.5.0',
        'redis': 'redis:7-alpine', 'memcached': 'memcached:1.6-alpine',
        's3': '', 'minio': 'minio/minio:latest', 'local': '',
        'ollama': 'ollama/ollama:latest', 'lmstudio': '', 'anthropic': '', 'openai': '', 'openrouter': '',
    }

    connector = {
        'id': gen_id(),
        'name': name,
        'type': conn_type,
        'provider': provider,
        'host': q.form.get('host', '').strip(),
        'port': port_val,
        'database': q.form.get('database', '').strip(),
        'username': q.form.get('username', '').strip(),
        'password': q.form.get('password', '').strip(),
        'options': {},
        'is_default': False,
        'docker_auto': False,
        'docker_image': docker_images.get(provider, ''),
        'docker_container_id': '',
        'status': 'unknown',
        'last_tested': None,
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'application_id': pid,
        'scope': 'application',
    }
    connectors.append(connector)
    save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Connector+created" />
  </q:action>

  <!-- Action: Test a connector -->
  <q:action name="testConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />

    <q:python>
import sys, os, socket, datetime
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id

cid = q.form.get('connector_id', '').strip()
connectors = load_yaml('connectors.yaml')
conn = find_by_id(connectors, cid)

if conn:
    host = conn.get('host', '')
    port = conn.get('port', 0)
    provider = conn.get('provider', '')
    status = 'unknown'

    if provider in ('anthropic', 'openai', 'openrouter'):
        status = 'unknown'
    elif provider in ('ollama', 'lmstudio'):
        urls = {'ollama': '/api/tags', 'lmstudio': '/v1/models'}
        path = urls.get(provider, '/')
        try:
            import http.client
            c = http.client.HTTPConnection(host, int(port), timeout=5)
            c.request('GET', path)
            resp = c.getresponse()
            status = 'connected' if resp.status &lt; 400 else 'error'
            c.close()
        except:
            status = 'error'
    elif provider == 'sqlite':
        db = conn.get('database', '')
        status = 'connected' if (not db or os.path.isfile(db)) else 'error'
    elif host and port:
        try:
            sock = socket.create_connection((host, int(port)), timeout=3)
            sock.close()
            status = 'connected'
        except:
            status = 'error'

    conn['status'] = status
    conn['last_tested'] = datetime.datetime.now().isoformat()
    save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Connection+tested" />
  </q:action>

  <!-- Action: Detach connector from project -->
  <q:action name="detachConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id

cid = q.form.get('connector_id', '').strip()
connectors = load_yaml('connectors.yaml')
conn = find_by_id(connectors, cid)

if conn:
    # If scoped, delete it; if public, just detach
    if conn.get('scope') == 'application':
        connectors = [c for c in connectors if c.get('id') != cid]
    else:
        conn['application_id'] = None
        conn['scope'] = 'public'
    save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Connector+detached" />
  </q:action>

  <!-- Action: Save project config (full YAML editor) -->
  <q:action name="saveProjectConfig" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />
    <q:param name="config_yaml" type="string" required="true" />

    <q:python>
import sys, os, yaml
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id, now_iso

pid = q.form.get('project_id', '').strip()
q.redir_name = q.form.get('app_name', '').strip()
q.redir_flash = 'Configuration+saved'
config_yaml = q.form.get('config_yaml', '')

projects = load_yaml('projects.yaml')
proj = find_by_id(projects, pid)

if not proj:
    q.redir_flash = 'Project+not+found'
else:
    source = proj.get('source_path', '')
    config_path = os.path.join(os.getcwd(), source, 'quantum.config.yaml')

    # Validate YAML syntax
    valid = True
    try:
        parsed = yaml.safe_load(config_yaml)
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            q.redir_flash = 'YAML+must+be+a+mapping'
            valid = False
    except yaml.YAMLError as e:
        q.redir_flash = 'YAML+syntax+error'
        valid = False

    if valid:
        # Write validated YAML to disk (preserves comments and formatting)
        try:
            with open(config_path, 'w', encoding='utf-8') as fh:
                fh.write(config_yaml)
        except Exception as e:
            q.redir_flash = 'Error+writing+config'
            valid = False

    if valid:
        # Update project metadata
        proj['config'] = parsed.get('server', {})
        proj['config_snapshot'] = config_yaml
        proj['updated_at'] = now_iso()
        save_yaml('projects.yaml', projects)
        q.redir_flash = 'Configuration+saved'
    </q:python>

    <q:redirect url="/admin/app/{redir_name}?flash={redir_flash}" />
  </q:action>

  <!-- Action: Run component tests -->
  <q:action name="runComponentTests" method="POST">
    <q:param name="test_file" type="string" required="true" />
    <q:param name="comp_path" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />

    <q:python>
import sys, os, subprocess, json

base = os.getcwd()
test_file = q.form.get('test_file', '').strip()
comp_path = q.form.get('comp_path', '').strip()
q.redir_name = q.form.get('app_name', '').strip()
q.redir_flash = 'Tests+executed'

if '..' in test_file or '..' in comp_path:
    q.redir_flash = 'Invalid+path'
else:
    full_path = os.path.join(base, test_file)
    if not os.path.isfile(full_path):
        q.redir_flash = 'Test+file+not+found'
    else:
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', full_path, '-v', '--tb=short', '--no-header'],
                capture_output=True, text=True, timeout=120, cwd=base
            )
            output = result.stdout + result.stderr
            passed = result.returncode == 0
            settings_dir = os.path.join(base, 'quantum_admin', 'settings')
            os.makedirs(settings_dir, exist_ok=True)
            with open(os.path.join(settings_dir, 'last_test_result.json'), 'w') as f:
                json.dump({
                    'test_file': test_file,
                    'comp_path': comp_path,
                    'output': output,
                    'passed': passed,
                    'returncode': result.returncode,
                }, f)
            q.redir_flash = 'Tests+passed' if passed else 'Tests+failed'
        except subprocess.TimeoutExpired:
            q.redir_flash = 'Test+timed+out'
        except Exception as e:
            q.redir_flash = 'Test+error'
    </q:python>

    <q:redirect url="/admin/app/{redir_name}?flash={redir_flash}&amp;showResults=1" />
  </q:action>

  <!-- Action: Generate tests for a project component (generates + saves directly) -->
  <q:action name="generateComponentTests" method="POST">
    <q:param name="comp_path" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />

    <q:python>
import sys, os, json

base = os.getcwd()
comp_path = q.form.get('comp_path', '').strip()
q.redir_name = q.form.get('app_name', '').strip()
q.redir_flash = 'Tests+generated'

if '..' in comp_path:
    q.redir_flash = 'Invalid+path'
else:
    full_path = os.path.join(base, comp_path)
    if not os.path.isfile(full_path):
        q.redir_flash = 'Component+not+found'
    else:
        sys.path.insert(0, os.path.join(base, 'components', 'admin'))
        from _test_generator import ComponentTestGenerator
        gen = ComponentTestGenerator.__new__(ComponentTestGenerator)
        gen.component_path = comp_path
        gen.base_dir = base
        gen.full_path = full_path
        gen.content = ''
        gen.component_name = ''
        gen.actions = []
        gen.queries = []
        gen.feature_tags = set()
        gen.analyze()
        code = gen.generate()

        # Save test file directly to tests/
        sanitized = comp_path.replace('/', '_').replace('\\', '_').replace('.q', '')
        test_filename = f'test_{sanitized}.py'
        test_path = os.path.join(base, 'tests', test_filename)
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(code)

        q.redir_flash = 'Tests+saved+to+tests/' + test_filename
    </q:python>

    <q:redirect url="/admin/app/{redir_name}?flash={redir_flash}" />
  </q:action>

  <!-- Action: Create environment -->
  <q:action name="createEnvironment" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />
    <q:param name="env_name" type="string" required="true" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id, now_iso, find_env_by_name

pid = q.form.get('project_id', '').strip()
env_name = q.form.get('env_name', '').strip().lower()

if env_name:
    projects = load_yaml('projects.yaml')
    proj = find_by_id(projects, pid)
    if proj:
        envs = proj.get('environments', [])
        if not find_env_by_name(envs, env_name):
            envs.append({
                'name': env_name,
                'variables': {},
                'config_overrides': {},
                'created_at': now_iso(),
            })
            proj['environments'] = envs
            proj['updated_at'] = now_iso()
            save_yaml('projects.yaml', projects)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Environment+created" />
  </q:action>

  <!-- Action: Update environment -->
  <q:action name="updateEnvironment" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />
    <q:param name="env_name" type="string" required="true" />
    <q:param name="variables" type="string" />
    <q:param name="port" type="string" />
    <q:param name="host" type="string" />
    <q:param name="debug" type="string" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id, now_iso, find_env_by_name

pid = q.form.get('project_id', '').strip()
env_name = q.form.get('env_name', '').strip()

projects = load_yaml('projects.yaml')
proj = find_by_id(projects, pid)
if proj:
    env = find_env_by_name(proj.get('environments', []), env_name)
    if env:
        # Parse key=value pairs from textarea
        raw = q.form.get('variables', '')
        variables = {}
        for line in raw.split('\n'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                variables[k.strip()] = v.strip()
        env['variables'] = variables

        # Config overrides
        overrides = {}
        port_str = q.form.get('port', '').strip()
        host_str = q.form.get('host', '').strip()
        debug_str = q.form.get('debug', '').strip()
        if port_str:
            try:
                overrides['port'] = int(port_str)
            except:
                pass
        if host_str:
            overrides['host'] = host_str
        overrides['debug'] = debug_str == 'on'
        env['config_overrides'] = overrides

        proj['updated_at'] = now_iso()
        save_yaml('projects.yaml', projects)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Environment+updated" />
  </q:action>

  <!-- Action: Delete environment -->
  <q:action name="deleteEnvironment" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />
    <q:param name="env_name" type="string" required="true" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id, now_iso

pid = q.form.get('project_id', '').strip()
env_name = q.form.get('env_name', '').strip()

projects = load_yaml('projects.yaml')
proj = find_by_id(projects, pid)
if proj:
    envs = proj.get('environments', [])
    proj['environments'] = [e for e in envs if e.get('name') != env_name]
    proj['updated_at'] = now_iso()
    save_yaml('projects.yaml', projects)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Environment+deleted" />
  </q:action>

  <!-- Action: Start server -->
  <q:action name="startServer" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />

    <q:python>
import sys, os, subprocess
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, find_by_id, write_pid, get_log_path, get_process_status

pid = q.form.get('project_id', '').strip()
projects = load_yaml('projects.yaml')
proj = find_by_id(projects, pid)

if proj:
    name = proj.get('name', '')
    source = proj.get('source_path', '')
    config = proj.get('config', {})
    port = config.get('port', 8080)

    # Don't start if already running
    status = get_process_status(name)
    if not status['running']:
        base = os.getcwd()
        config_path = os.path.join(base, source, 'quantum.config.yaml')
        log_path = get_log_path(name)

        log_fh = open(log_path, 'a', encoding='utf-8')

        cmd = [sys.executable, os.path.join(base, 'src', 'cli', 'runner.py'), 'start', '--config', config_path, '--port', str(port)]

        kwargs = {
            'stdout': log_fh,
            'stderr': log_fh,
            'cwd': os.path.join(base, source),
        }

        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(cmd, **kwargs)
        write_pid(name, proc.pid)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Server+started" />
  </q:action>

  <!-- Action: Stop server -->
  <q:action name="stopServer" method="POST">
    <q:param name="project_id" type="string" required="true" />
    <q:param name="app_name" type="string" required="true" />

    <q:python>
import sys, os, signal
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, find_by_id, read_pid, remove_pid, is_process_running

pid = q.form.get('project_id', '').strip()
projects = load_yaml('projects.yaml')
proj = find_by_id(projects, pid)

if proj:
    name = proj.get('name', '')
    proc_pid = read_pid(name)
    if proc_pid and is_process_running(proc_pid):
        try:
            if os.name == 'nt':
                import subprocess
                subprocess.run(['taskkill', '/F', '/PID', str(proc_pid)], capture_output=True)
            else:
                os.kill(proc_pid, signal.SIGTERM)
        except (OSError, PermissionError):
            pass
    remove_pid(name)
    </q:python>

    <q:redirect url="/admin/app/{form.app_name}?flash=Server+stopped" />
  </q:action>

  <!-- Collect data for the project detail view -->
  <q:python>
import sys, os, yaml, re
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, find_by_name, get_process_status, get_log_tail

# Get project name from dynamic route path parameter
app_name = getattr(q, 'name', '')

# Flash message from query string
try:
    from flask import request as flask_request
    q.flash_message = flask_request.args.get('flash', '')
    q.show_results = flask_request.args.get('showResults', '')
except:
    q.flash_message = ''
    q.show_results = ''

projects = load_yaml('projects.yaml')
proj = find_by_name(projects, app_name)

if not proj:
    q.project_found = 'no'
    q.project_id = ''
    q.project_name = 'Not Found'
    q.project_description = ''
    q.project_status = ''
    q.project_source = ''
    q.project_port = '-'
    q.project_host = '-'
    q.project_debug = '-'
    q.project_created = '-'
    q.project_updated = '-'
    q.component_count = '0'
    q.static_count = '0'
    q.disk_size = '-'
    q.project_components = []
    q.project_connectors = []
    q.public_connectors = []
    q.config_raw = ''
    q.config_diff = ''
    q.config_has_diff = 'no'
    q.environments = []
    q.env_count = '0'
    q.status_badge = 'qa-badge-gray'
    q.app_name = app_name
    q.server_running = 'no'
    q.server_pid = ''
    q.log_content = ''
    q.project_routes = []
    q.route_count = '0'
    q.comp_tested_count = '0'
    q.test_output = ''
    q.test_file_label = ''
    q.test_result_badge = ''
    q.test_result_label = ''
else:
    q.project_found = 'yes'
    q.project_id = proj.get('id', '')
    q.project_name = proj.get('name', '')
    q.project_description = proj.get('description', '') or ''
    _status = proj.get('status', 'active')
    q.project_status = _status
    _source = proj.get('source_path', '')
    q.project_source = _source
    q.project_created = proj.get('created_at', '-')
    q.project_updated = proj.get('updated_at', '-')
    q.app_name = proj.get('name', '')

    config = proj.get('config', {})
    q.project_port = str(config.get('port', '-'))
    q.project_host = str(config.get('host', '-'))
    q.project_debug = str(config.get('debug', '-'))

    q.status_badge = {
        'active': 'qa-badge-success',
        'archived': 'qa-badge-gray',
        'error': 'qa-badge-danger',
    }.get(_status, 'qa-badge-info')

    base = os.getcwd()
    proj_dir = os.path.join(base, _source)

    # ---- Process status (Runtime) ----
    proc_status = get_process_status(proj.get('name', ''))
    q.server_running = 'yes' if proc_status['running'] else 'no'
    q.server_pid = str(proc_status.get('pid') or '')
    q.log_content = get_log_tail(proj.get('name', ''), 50)

    # Server URL
    _port = config.get('port', 8080)
    _host = config.get('host', '0.0.0.0')
    display_host = 'localhost' if _host == '0.0.0.0' else _host
    q.server_url = f"http://{display_host}:{_port}"

    # ---- Environments ----
    raw_envs = proj.get('environments', [])
    display_envs = []
    for env in raw_envs:
        de = dict(env)
        ename = env.get('name', '').lower()
        # Determine color class
        if 'dev' in ename:
            de['env_class'] = 'qa-env-dev'
        elif 'stag' in ename:
            de['env_class'] = 'qa-env-staging'
        elif 'prod' in ename:
            de['env_class'] = 'qa-env-prod'
        else:
            de['env_class'] = ''
        # Format variables as key=value text
        variables = env.get('variables', {})
        de['variables_text'] = '\n'.join(f"{k}={v}" for k, v in variables.items()) if variables else ''
        de['var_count'] = str(len(variables))
        # Config overrides
        co = env.get('config_overrides', {})
        de['override_port'] = str(co.get('port', ''))
        de['override_host'] = str(co.get('host', ''))
        de['override_debug'] = 'on' if co.get('debug') else ''
        display_envs.append(de)
    q.environments = display_envs
    q.env_count = str(len(display_envs))

    # ---- Components (with name extraction + test discovery) ----
    comp_dir = os.path.join(proj_dir, 'components')
    tests_dir = os.path.join(base, 'tests')
    components = []
    comp_tested_count = 0
    if os.path.isdir(comp_dir):
        for root, dirs, files in os.walk(comp_dir):
            for f in files:
                if f.endswith('.q'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, proj_dir).replace('\\', '/')
                    full_rel = os.path.relpath(full, base).replace('\\', '/')
                    comp_name = '-'
                    try:
                        size = os.path.getsize(full)
                        lines = 0
                        with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                            content = fh.read()
                            lines = content.count('\n') + 1
                        # Extract component name
                        m = re.search(r'&lt;q:component\s+name="([^"]+)"', content)
                        if m:
                            comp_name = m.group(1)

                        # Test discovery
                        sanitized = full_rel.replace('/', '_').replace('.q', '')
                        basename = os.path.splitext(f)[0]
                        test_file = ''
                        test_count = 0
                        for rel_tf, abs_tf in [
                            (f'tests/test_{sanitized}.py', os.path.join(tests_dir, f'test_{sanitized}.py')),
                            (f'tests/test_{basename}.py', os.path.join(tests_dir, f'test_{basename}.py')),
                        ]:
                            if os.path.isfile(abs_tf):
                                test_file = rel_tf
                                try:
                                    with open(abs_tf, 'r', encoding='utf-8', errors='ignore') as tf:
                                        test_count = len(re.findall(r'def test_', tf.read()))
                                except:
                                    pass
                                break

                        has_test = 'yes' if test_file else 'no'
                        if has_test == 'yes':
                            comp_tested_count += 1

                        # Feature tags
                        feature_tags_set = set(re.findall(r'&lt;q:(\w+)', content))
                        feature_tags_set.discard('component')
                        feature_tags_set.discard('param')
                        feature_tags = ', '.join(sorted(feature_tags_set)) if feature_tags_set else '-'

                        components.append({
                            'path': rel,
                            'full_path': full_rel,
                            'comp_name': comp_name,
                            'lines': str(lines),
                            'size': f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B",
                            'source_link': f"/admin/source?file={_source}/{rel}",
                            'detail_link': f"/admin/component/{_source}/{rel}",
                            'has_test': has_test,
                            'test_file': test_file,
                            'test_count': str(test_count),
                            'test_badge': 'qa-badge-success' if has_test == 'yes' else 'qa-badge-danger',
                            'test_label': f'Tested ({test_count})' if has_test == 'yes' else 'No Tests',
                            'feature_tags': feature_tags,
                        })
                    except:
                        components.append({'path': rel, 'full_path': rel, 'comp_name': comp_name, 'lines': '?', 'size': '?', 'source_link': '#', 'detail_link': '#', 'has_test': 'no', 'test_file': '', 'test_count': '0', 'test_badge': 'qa-badge-danger', 'test_label': 'No Tests', 'feature_tags': '-'})
    q.project_components = components
    q.component_count = str(len(components))
    q.comp_tested_count = str(comp_tested_count)

    # ---- Test result / generated test viewers ----
    import json as _json
    q.test_output = ''
    q.test_file_label = ''
    q.test_result_badge = ''
    q.test_result_label = ''

    if getattr(q, 'show_results', '') == '1':
        result_path = os.path.join(base, 'quantum_admin', 'settings', 'last_test_result.json')
        if os.path.isfile(result_path):
            try:
                with open(result_path, 'r') as _f:
                    _tr = _json.load(_f)
                q.test_output = _tr.get('output', '')
                q.test_file_label = _tr.get('test_file', '')
                q.test_result_badge = 'qa-badge-success' if _tr.get('passed', False) else 'qa-badge-danger'
                q.test_result_label = 'PASSED' if _tr.get('passed', False) else 'FAILED'
            except:
                pass


    # ---- Static files ----
    static_dir = os.path.join(proj_dir, 'static')
    static_count = 0
    if os.path.isdir(static_dir):
        for root, dirs, files in os.walk(static_dir):
            static_count += len(files)
    q.static_count = str(static_count)

    # ---- Disk size ----
    total_bytes = 0
    if os.path.isdir(proj_dir):
        for root, dirs, files in os.walk(proj_dir):
            for f in files:
                try:
                    total_bytes += os.path.getsize(os.path.join(root, f))
                except:
                    pass
    if total_bytes >= 1048576:
        q.disk_size = f"{total_bytes / 1048576:.1f} MB"
    elif total_bytes >= 1024:
        q.disk_size = f"{total_bytes / 1024:.1f} KB"
    elif total_bytes > 0:
        q.disk_size = f"{total_bytes} B"
    else:
        q.disk_size = '-'

    # ---- Routes (scan .q files -> route mapping) ----
    routes = []
    if os.path.isdir(comp_dir):
        for root, dirs, files in os.walk(comp_dir):
            for f in files:
                if f.endswith('.q'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, comp_dir).replace('\\', '/')
                    # Convert filepath to route path
                    route = '/' + rel
                    # Remove .q extension
                    if route.endswith('.q'):
                        route = route[:-2]
                    # index files map to parent
                    if route.endswith('/index'):
                        route = route[:-6] or '/'
                    # Detect dynamic segments [param]
                    is_dynamic = 'yes' if '[' in route else 'no'
                    dynamic_badge = 'qa-badge-warning' if is_dynamic == 'yes' else 'qa-badge-gray'
                    # Line count
                    try:
                        with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                            line_count = sum(1 for _ in fh)
                    except:
                        line_count = 0
                    routes.append({
                        'route_path': route,
                        'file_path': 'components/' + rel,
                        'is_dynamic': is_dynamic,
                        'dynamic_badge': dynamic_badge,
                        'dynamic_label': 'Dynamic' if is_dynamic == 'yes' else 'Static',
                        'lines': str(line_count),
                        'source_link': f"/admin/source?file={_source}/components/{rel}",
                    })
    q.project_routes = routes
    q.route_count = str(len(routes))

    # ---- Connectors ----
    connectors = load_yaml('connectors.yaml')
    provider_names = {
        'postgres': 'PostgreSQL', 'mysql': 'MySQL', 'mariadb': 'MariaDB',
        'mongodb': 'MongoDB', 'sqlite': 'SQLite', 'influxdb': 'InfluxDB',
        'rabbitmq': 'RabbitMQ', 'redis_queue': 'Redis Queue', 'kafka': 'Kafka',
        'redis': 'Redis', 'memcached': 'Memcached', 's3': 'Amazon S3',
        'minio': 'MinIO', 'local': 'Local FS', 'ollama': 'Ollama',
        'lmstudio': 'LM Studio', 'anthropic': 'Anthropic', 'openai': 'OpenAI',
        'openrouter': 'OpenRouter',
    }
    type_labels = {
        'database': 'Database', 'mq': 'Message Queue', 'message_queue': 'Message Queue',
        'cache': 'Cache', 'storage': 'Storage', 'ai': 'AI',
    }
    type_badge_class = {
        'database': 'qa-type-database', 'mq': 'qa-type-message_queue',
        'message_queue': 'qa-type-message_queue', 'cache': 'qa-type-cache',
        'storage': 'qa-type-storage', 'ai': 'qa-type-ai',
    }

    pid = proj.get('id', '')
    proj_conns = []
    pub_conns = []
    for c in connectors:
        dc = dict(c)
        dc['provider_name'] = provider_names.get(c.get('provider', ''), c.get('provider', ''))
        dc['type_label'] = type_labels.get(c.get('type', ''), c.get('type', ''))
        dc['type_badge'] = type_badge_class.get(c.get('type', ''), 'qa-badge-gray')
        dc['status_class'] = c.get('status', 'unknown')
        host = c.get('host', '')
        port = c.get('port', 0)
        dc['host_port'] = f"{host}:{port}" if host and port else host or '-'
        dc['port'] = str(port)

        app_id = str(c.get('application_id', '') or '')
        if app_id == str(pid):
            proj_conns.append(dc)
        elif c.get('scope', 'public') == 'public':
            pub_conns.append(dc)

    q.project_connectors = proj_conns
    q.public_connectors = pub_conns

    # Raw config
    config_path = os.path.join(proj_dir, 'quantum.config.yaml')
    config_raw = ''
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as fh:
                config_raw = fh.read()
        except:
            config_raw = '# Error reading config'
    q.config_raw = config_raw

    # Config diff: compare disk content with last-saved snapshot
    config_snapshot = proj.get('config_snapshot', '')
    if config_snapshot and config_snapshot != config_raw:
        import difflib
        saved_lines = config_snapshot.splitlines()
        current_lines = config_raw.splitlines()
        diff_lines = list(difflib.unified_diff(saved_lines, current_lines, lineterm='', fromfile='last saved', tofile='current', n=2))
        q.config_diff = '\n'.join(diff_lines)
        q.config_has_diff = 'yes'
    else:
        q.config_diff = ''
        q.config_has_diff = 'no'
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name} - Quantum Admin</title>
    <link rel="stylesheet" href="/static/quantum-admin.css" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet" />
  </head>
  <body>
    <div class="qa-layout">

      <!-- ============ SIDEBAR ============ -->
      <aside class="qa-sidebar">
        <div class="qa-sidebar-header">
          <a href="/admin" class="qa-sidebar-logo">
            <div class="qa-sidebar-logo-icon">Q</div>
            <span class="qa-sidebar-logo-text">Quantum<span class="qa-sidebar-version">Admin</span></span>
          </a>
        </div>

        <nav class="qa-sidebar-nav">
          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Overview</div>
            <a href="/admin/dashboard" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              Dashboard
            </a>
            <a href="/admin/applications" class="qa-sidebar-link active">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              Applications
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Framework</div>
            <a href="/admin/components" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              Components
            </a>
            <a href="/admin/features" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              Features
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Runtime</div>
            <a href="/admin/connectors" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M6 8H5a4 4 0 0 0 0 8h1"/><line x1="6" y1="12" x2="18" y2="12"/></svg>
              Connectors
            </a>
            <a href="/admin/database" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
              Database
            </a>
            <a href="/admin/agents" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Agents
            </a>
            <a href="/admin/jobs" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              Jobs
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">System</div>
            <a href="/admin/settings" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              Settings
            </a>
          </div>
        </nav>

        <div class="qa-sidebar-footer">
          <div class="qa-sidebar-user">
            <div class="qa-sidebar-user-avatar">Q</div>
            <div class="qa-sidebar-user-info">
              <div class="qa-sidebar-user-name">Quantum Admin</div>
              <div class="qa-sidebar-user-role">Native</div>
            </div>
          </div>
        </div>
      </aside>

      <!-- ============ MAIN CONTENT ============ -->
      <main class="qa-main">

        <!-- Header -->
        <header class="qa-header">
          <div class="qa-flex qa-items-center qa-gap-3">
            <a href="/admin/applications" class="qa-btn qa-btn-ghost qa-btn-sm">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
            </a>
            <h1 class="qa-header-title">{project_name}</h1>
          </div>
          <div class="qa-header-actions">
            <span class="qa-badge {status_badge}">{project_status}</span>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Not Found -->
          <q:if condition="{project_found} == 'no'">
            <div class="qa-card">
              <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">Project Not Found</div>
                <div class="qa-text-sm qa-text-muted" style="margin-bottom: 16px;">The requested project does not exist.</div>
                <a href="/admin/applications" class="qa-btn qa-btn-primary">Back to Applications</a>
              </div>
            </div>
          </q:if>

          <q:if condition="{project_found} == 'yes'">

            <!-- Flash Message -->
            <q:if condition="{flash_message} != ''">
              <div style="padding: 12px 16px; margin-bottom: 24px; border-radius: 8px; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: var(--q-success);">
                <span class="qa-text-sm qa-font-medium">{flash_message}</span>
              </div>
            </q:if>

            <!-- CSS-only Tab System -->
            <input type="radio" name="tab" id="tab-general" checked="" class="qa-tab-radio" />
            <input type="radio" name="tab" id="tab-connectors" class="qa-tab-radio" />
            <input type="radio" name="tab" id="tab-components" class="qa-tab-radio" />
            <input type="radio" name="tab" id="tab-config" class="qa-tab-radio" />
            <input type="radio" name="tab" id="tab-environments" class="qa-tab-radio" />
            <input type="radio" name="tab" id="tab-runtime" class="qa-tab-radio" />
            <input type="radio" name="tab" id="tab-routes" class="qa-tab-radio" />

            <div class="qa-tabs-bar">
              <label for="tab-general" class="qa-tab-label">General</label>
              <label for="tab-connectors" class="qa-tab-label">Connectors</label>
              <label for="tab-components" class="qa-tab-label">Components</label>
              <label for="tab-config" class="qa-tab-label">Config</label>
              <label for="tab-environments" class="qa-tab-label">Environments</label>
              <label for="tab-runtime" class="qa-tab-label">Runtime</label>
              <label for="tab-routes" class="qa-tab-label">Routes</label>
            </div>

            <div class="qa-tabs-content">

              <!-- ========== TAB: GENERAL ========== -->
              <div class="qa-panel-general">

                <!-- Quick Stats -->
                <div class="qa-grid qa-grid-4 qa-mb-6">
                  <div class="qa-stat-card">
                    <div class="qa-stat-label">Components</div>
                    <div class="qa-stat-value">{component_count}</div>
                  </div>
                  <div class="qa-stat-card">
                    <div class="qa-stat-label">Size on Disk</div>
                    <div class="qa-stat-value">{disk_size}</div>
                  </div>
                  <div class="qa-stat-card">
                    <div class="qa-stat-label">Environments</div>
                    <div class="qa-stat-value">{env_count}</div>
                  </div>
                  <div class="qa-stat-card">
                    <div class="qa-stat-label">Routes</div>
                    <div class="qa-stat-value">{route_count}</div>
                  </div>
                </div>

                <!-- Project Info Card -->
                <div class="qa-card qa-mb-6">
                  <div class="qa-card-header">
                    <div class="qa-card-title">Project Information</div>
                  </div>
                  <div class="qa-card-body">
                    <div style="display: flex; flex-direction: column; gap: 12px;">
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Source Path</span>
                        <span class="qa-font-mono qa-text-sm">{project_source}</span>
                      </div>
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Port</span>
                        <span class="qa-font-mono qa-text-sm">{project_port}</span>
                      </div>
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Debug</span>
                        <span class="qa-text-sm">{project_debug}</span>
                      </div>
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Static Files</span>
                        <span class="qa-text-sm">{static_count}</span>
                      </div>
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Created</span>
                        <span class="qa-text-sm">{project_created}</span>
                      </div>
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Updated</span>
                        <span class="qa-text-sm">{project_updated}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Edit Project Form -->
                <div class="qa-card">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Edit Project</div>
                      <div class="qa-card-subtitle">Update project details</div>
                    </div>
                  </div>
                  <div class="qa-card-body">
                    <form method="POST" action="/admin/app/{app_name}">
                      <input type="hidden" name="action" value="updateProject" />
                      <input type="hidden" name="project_id" value="{project_id}" />

                      <div class="qa-form-row qa-mb-4">
                        <div class="qa-form-group">
                          <label class="qa-label">Name</label>
                          <input type="text" name="name" class="qa-input" value="{project_name}" />
                        </div>
                        <div class="qa-form-group">
                          <label class="qa-label">Status</label>
                          <select name="status" class="qa-input qa-select">
                            <option value="active">Active</option>
                            <option value="archived">Archived</option>
                            <option value="error">Error</option>
                          </select>
                        </div>
                      </div>

                      <div class="qa-form-group qa-mb-4">
                        <label class="qa-label">Description</label>
                        <input type="text" name="description" class="qa-input" value="{project_description}" />
                      </div>

                      <div style="padding-top: 16px; border-top: 1px solid var(--q-border);">
                        <button type="submit" class="qa-btn qa-btn-primary">Save Changes</button>
                      </div>
                    </form>
                  </div>
                </div>
              </div>

              <!-- ========== TAB: CONNECTORS ========== -->
              <div class="qa-panel-connectors">

                <!-- Sub-tab radios (must be direct children for ~ combinator) -->
                <input type="radio" name="conn-subtab" id="conn-subtab-public" class="qa-conn-subtab-radio" checked="" />
                <input type="radio" name="conn-subtab" id="conn-subtab-private" class="qa-conn-subtab-radio" />
                <input type="radio" name="conn-subtab" id="conn-subtab-new" class="qa-conn-subtab-radio" />

                <!-- Sub-tab pill bar -->
                <div class="qa-conn-subtabs-bar">
                  <label for="conn-subtab-public" class="qa-conn-subtab-label">Public Connectors</label>
                  <label for="conn-subtab-private" class="qa-conn-subtab-label">Private Connectors</label>
                  <label for="conn-subtab-new" class="qa-conn-subtab-label">New Connector</label>
                </div>

                <!-- Sub-tab content panels -->
                <div class="qa-conn-subtabs-content">

                  <!-- SUB-TAB: Public Connectors (read-only) -->
                  <div class="qa-conn-panel-public">
                    <div class="qa-card">
                      <div class="qa-card-header">
                        <div>
                          <div class="qa-card-title">Public Connectors</div>
                          <div class="qa-card-subtitle">Available to all projects</div>
                        </div>
                      </div>
                      <div class="qa-card-body" style="padding: 0;">
                        <table class="qa-table">
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Type</th>
                              <th>Provider</th>
                              <th>Host:Port</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            <q:loop type="array" var="conn" items="{public_connectors}">
                              <tr>
                                <td><span class="qa-font-medium">{conn.name}</span></td>
                                <td><span class="qa-badge {conn.type_badge}">{conn.type_label}</span></td>
                                <td><span class="qa-text-sm">{conn.provider_name}</span></td>
                                <td><span class="qa-font-mono qa-text-sm">{conn.host_port}</span></td>
                                <td>
                                  <div class="qa-status-badge">
                                    <span class="qa-status-dot {conn.status_class}"></span>
                                    <span class="qa-status-text">{conn.status}</span>
                                  </div>
                                </td>
                              </tr>
                            </q:loop>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  <!-- SUB-TAB: Private Connectors (project-scoped, with actions) -->
                  <div class="qa-conn-panel-private">
                    <div class="qa-card">
                      <div class="qa-card-header">
                        <div>
                          <div class="qa-card-title">Private Connectors</div>
                          <div class="qa-card-subtitle">Connectors scoped to this project</div>
                        </div>
                      </div>
                      <div class="qa-card-body" style="padding: 0;">
                        <table class="qa-table">
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Type</th>
                              <th>Provider</th>
                              <th>Host:Port</th>
                              <th>Status</th>
                              <th>Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            <q:loop type="array" var="conn" items="{project_connectors}">
                              <tr>
                                <td><span class="qa-font-medium">{conn.name}</span></td>
                                <td><span class="qa-badge {conn.type_badge}">{conn.type_label}</span></td>
                                <td><span class="qa-text-sm">{conn.provider_name}</span></td>
                                <td><span class="qa-font-mono qa-text-sm">{conn.host_port}</span></td>
                                <td>
                                  <div class="qa-status-badge">
                                    <span class="qa-status-dot {conn.status_class}"></span>
                                    <span class="qa-status-text">{conn.status}</span>
                                  </div>
                                </td>
                                <td>
                                  <div class="qa-flex qa-gap-1">
                                    <form method="POST" action="/admin/app/{app_name}" style="display: inline;">
                                      <input type="hidden" name="action" value="testConnector" />
                                      <input type="hidden" name="connector_id" value="{conn.id}" />
                                      <input type="hidden" name="app_name" value="{app_name}" />
                                      <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Test</button>
                                    </form>
                                    <form method="POST" action="/admin/app/{app_name}" style="display: inline;">
                                      <input type="hidden" name="action" value="detachConnector" />
                                      <input type="hidden" name="connector_id" value="{conn.id}" />
                                      <input type="hidden" name="app_name" value="{app_name}" />
                                      <button type="submit" class="qa-btn qa-btn-danger qa-btn-sm">Remove</button>
                                    </form>
                                  </div>
                                </td>
                              </tr>
                            </q:loop>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  <!-- SUB-TAB: New Connector -->
                  <div class="qa-conn-panel-new">
                    <div class="qa-card">
                      <div class="qa-card-header">
                        <div>
                          <div class="qa-card-title">New Project Connector</div>
                          <div class="qa-card-subtitle">Create a connector scoped to this project</div>
                        </div>
                      </div>
                      <div class="qa-card-body">
                        <form method="POST" action="/admin/app/{app_name}">
                          <input type="hidden" name="action" value="createProjectConnector" />
                          <input type="hidden" name="project_id" value="{project_id}" />
                          <input type="hidden" name="app_name" value="{app_name}" />

                          <div class="qa-form-row qa-mb-4">
                            <div class="qa-form-group">
                              <label class="qa-label">Name</label>
                              <input type="text" name="name" class="qa-input" placeholder="e.g. App Redis" required="" />
                            </div>
                            <div class="qa-form-group">
                              <label class="qa-label">Type</label>
                              <select name="conn_type" class="qa-input qa-select" required="">
                                <option value="">Select type...</option>
                                <option value="database">Database</option>
                                <option value="mq">Message Queue</option>
                                <option value="cache">Cache</option>
                                <option value="storage">Storage</option>
                                <option value="ai">AI</option>
                              </select>
                            </div>
                          </div>

                          <div class="qa-form-row qa-mb-4">
                            <div class="qa-form-group">
                              <label class="qa-label">Provider</label>
                              <select name="provider" class="qa-input qa-select" required="">
                                <option value="">Select...</option>
                                <optgroup label="Database">
                                  <option value="postgres">PostgreSQL</option>
                                  <option value="mysql">MySQL</option>
                                  <option value="mariadb">MariaDB</option>
                                  <option value="mongodb">MongoDB</option>
                                  <option value="sqlite">SQLite</option>
                                </optgroup>
                                <optgroup label="Cache / MQ">
                                  <option value="redis">Redis</option>
                                  <option value="memcached">Memcached</option>
                                  <option value="rabbitmq">RabbitMQ</option>
                                  <option value="kafka">Kafka</option>
                                </optgroup>
                                <optgroup label="Storage">
                                  <option value="s3">Amazon S3</option>
                                  <option value="minio">MinIO</option>
                                  <option value="local">Local FS</option>
                                </optgroup>
                                <optgroup label="AI">
                                  <option value="ollama">Ollama</option>
                                  <option value="lmstudio">LM Studio</option>
                                  <option value="anthropic">Anthropic</option>
                                  <option value="openai">OpenAI</option>
                                </optgroup>
                              </select>
                            </div>
                            <div class="qa-form-group">
                              <label class="qa-label">Host</label>
                              <input type="text" name="host" class="qa-input" placeholder="localhost" />
                            </div>
                          </div>

                          <div class="qa-form-row qa-mb-4">
                            <div class="qa-form-group">
                              <label class="qa-label">Port</label>
                              <input type="number" name="port" class="qa-input" placeholder="6379" />
                            </div>
                            <div class="qa-form-group">
                              <label class="qa-label">Database</label>
                              <input type="text" name="database" class="qa-input" placeholder="Database name" />
                            </div>
                          </div>

                          <div class="qa-form-row qa-mb-4">
                            <div class="qa-form-group">
                              <label class="qa-label">Username</label>
                              <input type="text" name="username" class="qa-input" />
                            </div>
                            <div class="qa-form-group">
                              <label class="qa-label">Password</label>
                              <input type="password" name="password" class="qa-input" />
                            </div>
                          </div>

                          <div style="padding-top: 16px; border-top: 1px solid var(--q-border);">
                            <button type="submit" class="qa-btn qa-btn-primary">Create Connector</button>
                          </div>
                        </form>
                      </div>
                    </div>
                  </div>

                </div>
              </div>

              <!-- ========== TAB: COMPONENTS ========== -->
              <div class="qa-panel-components">

                <!-- Test Results Log Viewer -->
                <q:if condition="{show_results} == '1'">
                  <div class="qa-card qa-mb-6">
                    <div class="qa-card-header">
                      <div>
                        <div class="qa-card-title">Test Results</div>
                        <div class="qa-card-subtitle">{test_file_label}</div>
                      </div>
                      <span class="qa-badge {test_result_badge}">{test_result_label}</span>
                    </div>
                    <div class="qa-card-body" style="padding: 0;">
                      <div class="qa-log-viewer">{test_output}</div>
                    </div>
                  </div>
                </q:if>

                <div class="qa-card">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Project Components</div>
                      <div class="qa-card-subtitle">{component_count} .q files found &#8212; {comp_tested_count} tested</div>
                    </div>
                  </div>
                  <div class="qa-card-body" style="padding: 0;">
                    <q:if condition="{component_count} != '0'">
                      <table class="qa-table">
                        <thead>
                          <tr>
                            <th>Component Name</th>
                            <th>Path</th>
                            <th>Lines</th>
                            <th>Size</th>
                            <th>Tests</th>
                            <th>Tags</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          <q:loop type="array" var="comp" items="{project_components}">
                            <tr>
                              <td><a href="{comp.detail_link}" class="qa-font-medium" style="color: var(--q-primary-400); text-decoration: none;">{comp.comp_name}</a></td>
                              <td><a href="{comp.detail_link}" class="qa-font-mono qa-text-sm" style="color: var(--q-text-secondary); text-decoration: none;">{comp.path}</a></td>
                              <td><span class="qa-text-sm">{comp.lines}</span></td>
                              <td><span class="qa-text-sm qa-text-muted">{comp.size}</span></td>
                              <td><span class="qa-badge {comp.test_badge}">{comp.test_label}</span></td>
                              <td><span class="qa-text-sm qa-text-muted">{comp.feature_tags}</span></td>
                              <td>
                                <div class="qa-flex qa-gap-1" style="flex-wrap: wrap;">
                                  <a href="{comp.detail_link}" class="qa-btn qa-btn-ghost qa-btn-sm">Detail</a>
                                  <q:if condition="{comp.has_test} == 'yes'">
                                    <form method="POST" action="/admin/app/{app_name}" style="display: inline;">
                                      <input type="hidden" name="action" value="runComponentTests" />
                                      <input type="hidden" name="test_file" value="{comp.test_file}" />
                                      <input type="hidden" name="comp_path" value="{comp.full_path}" />
                                      <input type="hidden" name="app_name" value="{app_name}" />
                                      <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Run Tests</button>
                                    </form>
                                  </q:if>
                                  <form method="POST" action="/admin/app/{app_name}" style="display: inline;">
                                    <input type="hidden" name="action" value="generateComponentTests" />
                                    <input type="hidden" name="comp_path" value="{comp.full_path}" />
                                    <input type="hidden" name="app_name" value="{app_name}" />
                                    <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Generate Tests</button>
                                  </form>
                                </div>
                              </td>
                            </tr>
                          </q:loop>
                        </tbody>
                      </table>
                    </q:if>
                    <q:if condition="{component_count} == '0'">
                      <div class="qa-empty">
                        <div class="qa-empty-icon">
                          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                        </div>
                        <div class="qa-empty-title">No Components</div>
                        <div class="qa-empty-text">No .q files found in the project's components directory. Create your first component to get started.</div>
                      </div>
                    </q:if>
                  </div>
                </div>
              </div>

              <!-- ========== TAB: CONFIG ========== -->
              <div class="qa-panel-config">

                <!-- Current Config Display (read-only reference) -->
                <div class="qa-card qa-mb-6">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">quantum.config.yaml</div>
                      <div class="qa-card-subtitle">Current file on disk (read-only reference)</div>
                    </div>
                  </div>
                  <div class="qa-card-body" style="padding: 0;">
                    <div class="qa-config-viewer">
                      <pre class="qa-config-pre">{config_raw}</pre>
                    </div>
                  </div>
                </div>

                <!-- Config Diff (shown when file differs from last save) -->
                <q:if condition="{config_has_diff} == 'yes'">
                  <div class="qa-card qa-mb-6" style="border-color: var(--q-warning);">
                    <div class="qa-card-header">
                      <div>
                        <div class="qa-card-title" style="color: var(--q-warning);">External Changes Detected</div>
                        <div class="qa-card-subtitle">The config file on disk differs from the last version saved through this admin</div>
                      </div>
                    </div>
                    <div class="qa-card-body" style="padding: 0;">
                      <pre class="qa-config-diff">{config_diff}</pre>
                    </div>
                  </div>
                </q:if>

                <!-- Full YAML Editor -->
                <div class="qa-card">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Edit Configuration</div>
                      <div class="qa-card-subtitle">Edit the full YAML configuration. Invalid YAML will be rejected on save.</div>
                    </div>
                  </div>
                  <div class="qa-card-body">
                    <form method="POST" action="/admin/app/{app_name}">
                      <input type="hidden" name="action" value="saveProjectConfig" />
                      <input type="hidden" name="project_id" value="{project_id}" />
                      <input type="hidden" name="app_name" value="{app_name}" />

                      <div class="qa-form-group qa-mb-4">
                        <label class="qa-label">YAML Configuration</label>
                        <textarea name="config_yaml" class="qa-config-editor" rows="20" spellcheck="false">{config_raw}</textarea>
                        <div class="qa-input-hint">Edit the raw YAML content. Validates syntax before writing to disk. Comments and formatting are preserved.</div>
                      </div>

                      <div style="padding-top: 16px; border-top: 1px solid var(--q-border); display: flex; gap: 12px; align-items: center;">
                        <button type="submit" class="qa-btn qa-btn-primary">Save Configuration</button>
                        <span class="qa-text-xs qa-text-muted">Validates YAML syntax before writing</span>
                      </div>
                    </form>
                  </div>
                </div>
              </div>

              <!-- ========== TAB: ENVIRONMENTS ========== -->
              <div class="qa-panel-environments">

                <!-- Create Environment -->
                <div class="qa-card qa-mb-6">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Create Environment</div>
                      <div class="qa-card-subtitle">Add a new environment configuration</div>
                    </div>
                  </div>
                  <div class="qa-card-body">
                    <form method="POST" action="/admin/app/{app_name}" style="display: flex; align-items: flex-end; gap: 12px;">
                      <input type="hidden" name="action" value="createEnvironment" />
                      <input type="hidden" name="project_id" value="{project_id}" />
                      <input type="hidden" name="app_name" value="{app_name}" />
                      <div class="qa-form-group" style="flex: 1; margin-bottom: 0;">
                        <label class="qa-label">Environment Name</label>
                        <input type="text" name="env_name" class="qa-input" placeholder="e.g. development, staging, production" required="" />
                        <div class="qa-input-hint">Use lowercase. Common: development, staging, production</div>
                      </div>
                      <button type="submit" class="qa-btn qa-btn-primary" style="margin-bottom: 18px;">Create</button>
                    </form>
                  </div>
                </div>

                <!-- Environment Cards -->
                <q:if condition="{env_count} != '0'">
                  <div style="display: flex; flex-direction: column; gap: 16px;">
                    <q:loop type="array" var="env" items="{environments}">
                      <div class="qa-env-card {env.env_class}">
                        <div class="qa-flex qa-items-center qa-justify-between qa-mb-4">
                          <div>
                            <span class="qa-font-semibold qa-text-lg">{env.name}</span>
                            <span class="qa-text-xs qa-text-muted qa-ml-2">{env.var_count} variables</span>
                          </div>
                          <form method="POST" action="/admin/app/{app_name}" style="margin: 0;" onsubmit="return confirm('Delete environment {env.name}?');">
                            <input type="hidden" name="action" value="deleteEnvironment" />
                            <input type="hidden" name="project_id" value="{project_id}" />
                            <input type="hidden" name="app_name" value="{app_name}" />
                            <input type="hidden" name="env_name" value="{env.name}" />
                            <button type="submit" class="qa-btn qa-btn-danger qa-btn-sm">Delete</button>
                          </form>
                        </div>

                        <!-- Edit environment form -->
                        <form method="POST" action="/admin/app/{app_name}">
                          <input type="hidden" name="action" value="updateEnvironment" />
                          <input type="hidden" name="project_id" value="{project_id}" />
                          <input type="hidden" name="app_name" value="{app_name}" />
                          <input type="hidden" name="env_name" value="{env.name}" />

                          <div class="qa-form-group qa-mb-4">
                            <label class="qa-label">Variables (KEY=value, one per line)</label>
                            <textarea name="variables" class="qa-input qa-textarea" rows="4" placeholder="DATABASE_URL=sqlite:///dev.db&#10;DEBUG=true">{env.variables_text}</textarea>
                          </div>

                          <div class="qa-form-row qa-mb-4">
                            <div class="qa-form-group">
                              <label class="qa-label">Port Override</label>
                              <input type="number" name="port" class="qa-input" value="{env.override_port}" placeholder="e.g. 8081" />
                            </div>
                            <div class="qa-form-group">
                              <label class="qa-label">Host Override</label>
                              <input type="text" name="host" class="qa-input" value="{env.override_host}" placeholder="e.g. 0.0.0.0" />
                            </div>
                          </div>

                          <div class="qa-flex qa-items-center qa-gap-2 qa-mb-4">
                            <input type="checkbox" name="debug" id="env_debug_{env.name}" style="accent-color: var(--q-primary-400);" />
                            <label for="env_debug_{env.name}" class="qa-text-sm qa-text-muted">Debug Mode</label>
                          </div>

                          <button type="submit" class="qa-btn qa-btn-secondary qa-btn-sm">Save Environment</button>
                        </form>
                      </div>
                    </q:loop>
                  </div>
                </q:if>

                <q:if condition="{env_count} == '0'">
                  <div class="qa-card">
                    <div class="qa-empty">
                      <div class="qa-empty-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 3v18"/><path d="M3 12h18"/><rect x="3" y="3" width="18" height="18" rx="2"/></svg>
                      </div>
                      <div class="qa-empty-title">No Environments</div>
                      <div class="qa-empty-text">Environments let you manage variables and config overrides per deployment stage. Create your first environment above.</div>
                    </div>
                  </div>
                </q:if>
              </div>

              <!-- ========== TAB: RUNTIME ========== -->
              <div class="qa-panel-runtime">

                <!-- Server Status Card -->
                <div class="qa-card qa-mb-6">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Server Status</div>
                      <div class="qa-card-subtitle">Process management for this application</div>
                    </div>
                    <q:if condition="{server_running} == 'yes'">
                      <span class="qa-process-running">Running</span>
                    </q:if>
                    <q:if condition="{server_running} == 'no'">
                      <span class="qa-process-stopped">Stopped</span>
                    </q:if>
                  </div>
                  <div class="qa-card-body">
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;">
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Port</span>
                        <span class="qa-font-mono qa-text-sm">{project_port}</span>
                      </div>
                      <div class="qa-flex qa-items-center qa-justify-between">
                        <span class="qa-text-sm qa-text-muted">Host</span>
                        <span class="qa-font-mono qa-text-sm">{project_host}</span>
                      </div>
                      <q:if condition="{server_running} == 'yes'">
                        <div class="qa-flex qa-items-center qa-justify-between">
                          <span class="qa-text-sm qa-text-muted">PID</span>
                          <span class="qa-font-mono qa-text-sm">{server_pid}</span>
                        </div>
                        <div class="qa-flex qa-items-center qa-justify-between">
                          <span class="qa-text-sm qa-text-muted">URL</span>
                          <a href="{server_url}" target="_blank" class="qa-font-mono qa-text-sm">{server_url}</a>
                        </div>
                      </q:if>
                    </div>

                    <!-- Start / Stop buttons -->
                    <div class="qa-flex qa-gap-2">
                      <q:if condition="{server_running} == 'no'">
                        <form method="POST" action="/admin/app/{app_name}">
                          <input type="hidden" name="action" value="startServer" />
                          <input type="hidden" name="project_id" value="{project_id}" />
                          <input type="hidden" name="app_name" value="{app_name}" />
                          <button type="submit" class="qa-btn qa-btn-success">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            Start Server
                          </button>
                        </form>
                      </q:if>
                      <q:if condition="{server_running} == 'yes'">
                        <form method="POST" action="/admin/app/{app_name}" onsubmit="return confirm('Stop the running server?');">
                          <input type="hidden" name="action" value="stopServer" />
                          <input type="hidden" name="project_id" value="{project_id}" />
                          <input type="hidden" name="app_name" value="{app_name}" />
                          <button type="submit" class="qa-btn qa-btn-danger">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                            Stop Server
                          </button>
                        </form>
                      </q:if>
                    </div>
                  </div>
                </div>

                <!-- Log Viewer -->
                <div class="qa-card">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Server Logs</div>
                      <div class="qa-card-subtitle">Last 50 lines of output</div>
                    </div>
                  </div>
                  <div class="qa-card-body">
                    <q:if condition="{log_content} != ''">
                      <div class="qa-log-viewer">{log_content}</div>
                    </q:if>
                    <q:if condition="{log_content} == ''">
                      <div class="qa-empty" style="padding: 32px 16px;">
                        <div class="qa-empty-icon">
                          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                        </div>
                        <div class="qa-empty-title">No Logs Yet</div>
                        <div class="qa-empty-text">Start the server to see log output here.</div>
                      </div>
                    </q:if>
                  </div>
                </div>
              </div>

              <!-- ========== TAB: ROUTES ========== -->
              <div class="qa-panel-routes">
                <div class="qa-card">
                  <div class="qa-card-header">
                    <div>
                      <div class="qa-card-title">Discovered Routes</div>
                      <div class="qa-card-subtitle">{route_count} routes from component files</div>
                    </div>
                  </div>
                  <div class="qa-card-body" style="padding: 0;">
                    <q:if condition="{route_count} != '0'">
                      <table class="qa-table">
                        <thead>
                          <tr>
                            <th>Path</th>
                            <th>File</th>
                            <th>Type</th>
                            <th>Lines</th>
                          </tr>
                        </thead>
                        <tbody>
                          <q:loop type="array" var="rt" items="{project_routes}">
                            <tr>
                              <td><span class="qa-font-mono qa-font-medium">{rt.route_path}</span></td>
                              <td><a href="{rt.source_link}" class="qa-font-mono qa-text-sm">{rt.file_path}</a></td>
                              <td><span class="qa-badge {rt.dynamic_badge}">{rt.dynamic_label}</span></td>
                              <td><span class="qa-text-sm">{rt.lines}</span></td>
                            </tr>
                          </q:loop>
                        </tbody>
                      </table>
                    </q:if>
                    <q:if condition="{route_count} == '0'">
                      <div class="qa-empty">
                        <div class="qa-empty-icon">
                          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                        </div>
                        <div class="qa-empty-title">No Routes Found</div>
                        <div class="qa-empty-text">Add .q component files to the project's components directory to generate routes automatically.</div>
                      </div>
                    </q:if>
                  </div>
                </div>
              </div>

            </div>
          </q:if>

        </div>
      </main>

    </div>
  <script src="/static/quantum-admin-connectors.js"></script>
  </body>
  </html>
</q:component>
