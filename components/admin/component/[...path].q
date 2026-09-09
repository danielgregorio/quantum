<q:component name="AdminComponentDetail">

  <!-- ========== ACTION: Run Tests ========== -->
  <q:action name="runTests" method="POST">
    <q:param name="test_file" type="string" required="true" />
    <q:param name="comp_path" type="string" required="true" />

    <q:python>
import sys, os, subprocess, json

base = os.getcwd()
test_file = q.form.get('test_file', '').strip()
comp_path = q.form.get('comp_path', '').strip()
q.redir_flash = 'Tests+executed'
q.redir_file = comp_path

# Security: reject path traversal
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

            # Parse individual test results from pytest -v output
            import re as _re
            tests_detail = []
            for line in result.stdout.splitlines():
                # pytest -v format: "tests/test_foo.py::test_name PASSED"
                tm = _re.match(r'^(.+?::(\S+))\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s.*)?$', line)
                if tm:
                    tests_detail.append({
                        'full_id': tm.group(1),
                        'name': tm.group(2),
                        'status': tm.group(3),
                    })

            # Parse summary line: "X passed, Y failed, Z error" etc.
            summary = {}
            sum_m = _re.search(r'(\d+) passed', output)
            if sum_m: summary['passed'] = int(sum_m.group(1))
            sum_m = _re.search(r'(\d+) failed', output)
            if sum_m: summary['failed'] = int(sum_m.group(1))
            sum_m = _re.search(r'(\d+) error', output)
            if sum_m: summary['errors'] = int(sum_m.group(1))
            sum_m = _re.search(r'(\d+) skipped', output)
            if sum_m: summary['skipped'] = int(sum_m.group(1))
            # Duration
            dur_m = _re.search(r'in ([\d.]+)s', output)
            if dur_m: summary['duration'] = dur_m.group(1)

            settings_dir = os.path.join(base, 'quantum_admin', 'settings')
            os.makedirs(settings_dir, exist_ok=True)
            with open(os.path.join(settings_dir, 'last_test_result.json'), 'w') as f:
                json.dump({
                    'test_file': test_file,
                    'comp_path': comp_path,
                    'output': output,
                    'passed': passed,
                    'returncode': result.returncode,
                    'tests': tests_detail,
                    'summary': summary,
                }, f)
            q.redir_flash = 'Tests+passed' if passed else 'Tests+failed'
        except subprocess.TimeoutExpired:
            q.redir_flash = 'Test+timed+out'
        except Exception as e:
            q.redir_flash = 'Test+error'
    </q:python>

    <q:redirect url="/admin/component/{redir_file}?showResults=1&amp;flash={redir_flash}" />
  </q:action>

  <!-- ========== ACTION: Generate Tests ========== -->
  <q:action name="generateTests" method="POST">
    <q:param name="comp_path" type="string" required="true" />

    <q:python>
import sys, os

base = os.getcwd()
comp_path = q.form.get('comp_path', '').strip()
q.redir_flash = 'Tests+generated'
q.redir_file = comp_path

if '..' in comp_path:
    q.redir_flash = 'Invalid+path'
else:
    full_path = os.path.join(base, comp_path)
    if not os.path.isfile(full_path):
        q.redir_flash = 'Component+not+found'
    else:
        sys.path.insert(0, os.path.join(base, 'components', 'admin'))
        from _test_generator import ComponentTestGenerator
        # comp_path is like "components/admin/connectors.q", generator expects path relative to components/
        rel_to_components = comp_path
        if rel_to_components.startswith('components/'):
            rel_to_components = rel_to_components[len('components/'):]
        gen = ComponentTestGenerator(rel_to_components, base)
        gen.analyze()
        code = gen.generate()

        # Save test file directly to tests/
        sanitized = comp_path.replace('/', '_').replace('.q', '')
        test_filename = f'test_{sanitized}.py'
        test_path = os.path.join(base, 'tests', test_filename)
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(code)

        q.redir_flash = 'Tests+saved+to+tests/' + test_filename
    </q:python>

    <q:redirect url="/admin/component/{redir_file}?flash={redir_flash}" />
  </q:action>

  <!-- ========== DATA PREP ========== -->
  <q:python>
import os, re, json, datetime

base = os.getcwd()

# Get file path from route param (catch-all [...path])
# The router strips .q from URLs, so we restore it
from flask import request as flask_request
file_param = getattr(q, 'path', '') or ''
if file_param and not os.path.splitext(file_param)[1]:
    file_param = file_param + '.q'

q.file_param = file_param
q.file_found = 'no'
q.error_message = ''
q.comp_name = '-'
q.comp_path = file_param
q.file_size = '-'
q.line_count = '0'
q.file_modified = '-'
q.file_type = '-'
q.file_type_badge = 'qa-badge-info'
q.actions_list = []
q.queries_list = []
q.feature_tags_list = []
q.has_test = 'no'
q.test_file = ''
q.test_count = '0'
q.test_badge = 'qa-badge-danger'
q.test_label = 'No Tests'
q.source_link = ''

# Flash and query params
q.flash_message = ''
q.flash_style = ''
q.show_results = ''
q.test_output = ''
q.test_file_label = ''
q.test_passed = ''
q.test_result_badge = ''
q.test_result_label = ''
q.test_results_list = []
q.test_summary_passed = '0'
q.test_summary_failed = '0'
q.test_summary_errors = '0'
q.test_summary_skipped = '0'
q.test_summary_duration = '-'
q.test_summary_total = '0'
q.test_functions = []
q.has_run_results = 'no'
q.active_tab = 'general'

try:
    q.flash_message = flask_request.args.get('flash', '')
    q.show_results = flask_request.args.get('showResults', '')
except:
    pass

# Compute flash style from message content
if q.flash_message:
    flash_lower = q.flash_message.lower().replace('+', ' ')
    if 'failed' in flash_lower or 'error' in flash_lower or 'invalid' in flash_lower or 'not found' in flash_lower or 'timed out' in flash_lower:
        q.flash_style = 'background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: var(--q-danger);'
    else:
        q.flash_style = 'background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.3); color: var(--q-success);'

# Auto-switch to Tests tab when showing results
if q.show_results == '1':
    q.active_tab = 'tests'

if file_param:
    # Security: prevent directory traversal
    normalized = os.path.normpath(file_param)
    if '..' in normalized or normalized.startswith('/') or normalized.startswith('\\'):
        q.error_message = 'Invalid file path: directory traversal not allowed'
    else:
        full_path = os.path.join(base, normalized)
        real_base = os.path.realpath(base)
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(real_base):
            q.error_message = 'Invalid file path: outside project root'
        elif not os.path.isfile(full_path):
            q.error_message = f'File not found: {file_param}'
        else:
            q.file_found = 'yes'
            q.source_link = f'/admin/source?file={file_param}'

            # File type detection
            ext = os.path.splitext(file_param)[1].lower()
            type_map = {
                '.q': ('Quantum', 'qa-badge-primary'),
                '.py': ('Python', 'qa-badge-success'),
                '.yaml': ('YAML', 'qa-badge-warning'),
                '.yml': ('YAML', 'qa-badge-warning'),
                '.json': ('JSON', 'qa-badge-info'),
                '.html': ('HTML', 'qa-badge-danger'),
                '.css': ('CSS', 'qa-badge-info'),
                '.js': ('JavaScript', 'qa-badge-warning'),
            }
            ft, fb = type_map.get(ext, ('Unknown', 'qa-badge-info'))
            q.file_type = ft
            q.file_type_badge = fb

            # File metadata
            file_size = os.path.getsize(full_path)
            if file_size >= 1048576:
                q.file_size = f"{file_size / 1048576:.1f} MB"
            elif file_size >= 1024:
                q.file_size = f"{file_size / 1024:.1f} KB"
            else:
                q.file_size = f"{file_size} B"

            try:
                mtime = os.path.getmtime(full_path)
                dt = datetime.datetime.fromtimestamp(mtime)
                q.file_modified = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass

            # Read content
            content = ''
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                    q.line_count = str(content.count('\n') + 1)
            except:
                pass

            # Component name
            m = re.search(r'&lt;q:component\s+name="([^"]+)"', content)
            if m:
                q.comp_name = m.group(1)

            # Actions list with params
            actions = []
            # Find each q:action block
            action_pattern = re.compile(r'&lt;q:action\s+name="([^"]+)"(.*?)(?:&lt;/q:action&gt;|&lt;q:python&gt;)', re.DOTALL)
            for am in action_pattern.finditer(content):
                action_name = am.group(1)
                action_block = am.group(2)
                # Extract method
                method_m = re.search(r'method="([^"]+)"', am.group(0))
                method = method_m.group(1) if method_m else 'POST'
                # Extract params
                params = []
                for pm in re.finditer(r'&lt;q:param\s+name="([^"]+)"(?:\s+type="([^"]*)")?(?:\s+required="([^"]*)")?', action_block):
                    pname = pm.group(1)
                    ptype = pm.group(2) or 'string'
                    preq = pm.group(3) == 'true' if pm.group(3) else False
                    params.append({'name': pname, 'type': ptype, 'required': 'yes' if preq else 'no'})
                params_str = ', '.join([f"{p['name']}:{p['type']}" + (' *' if p['required'] == 'yes' else '') for p in params]) if params else '-'
                actions.append({
                    'name': action_name,
                    'method': method,
                    'params': params,
                    'params_str': params_str,
                })
            q.actions_list = actions
            q.actions_count = str(len(actions))

            # Queries list
            queries = []
            for qm in re.finditer(r'&lt;q:query\s+name="([^"]+)"', content):
                queries.append({'name': qm.group(1)})
            q.queries_list = queries
            q.queries_count = str(len(queries))

            # Feature tags
            feature_tags_set = set(re.findall(r'&lt;q:(\w+)', content))
            feature_tags_set.discard('component')
            feature_tags_set.discard('param')
            feature_tags = sorted(feature_tags_set)
            q.feature_tags_list = [{'name': t} for t in feature_tags]
            q.feature_tags_count = str(len(feature_tags))

            # Test discovery
            tests_dir = os.path.join(base, 'tests')
            # file_param could be "components/admin/connectors.q"
            sanitized = file_param.replace('/', '_').replace('.q', '')
            basename = os.path.splitext(os.path.basename(file_param))[0]
            candidates = [
                (f'tests/test_{sanitized}.py', os.path.join(tests_dir, f'test_{sanitized}.py')),
                (f'tests/test_{basename}.py', os.path.join(tests_dir, f'test_{basename}.py')),
            ]
            for rel_tf, abs_tf in candidates:
                if os.path.isfile(abs_tf):
                    q.test_file = rel_tf
                    q.has_test = 'yes'
                    try:
                        with open(abs_tf, 'r', encoding='utf-8', errors='ignore') as tf:
                            tc = tf.read()
                            # Extract test function names
                            test_names = re.findall(r'def (test_\w+)', tc)
                            q.test_count = str(len(test_names))
                            q.test_functions = [{'name': n, 'status': 'PENDING', 'badge': 'qa-badge-muted'} for n in test_names]
                    except:
                        pass
                    break

            q.test_badge = 'qa-badge-success' if q.has_test == 'yes' else 'qa-badge-danger'
            q.test_label = f'Tested ({q.test_count})' if q.has_test == 'yes' else 'No Tests'

    # Load test results if requested
    if q.show_results == '1':
        result_path = os.path.join(base, 'quantum_admin', 'settings', 'last_test_result.json')
        if os.path.isfile(result_path):
            try:
                with open(result_path, 'r') as f:
                    tr = json.load(f)
                q.test_output = tr.get('output', '')
                q.test_file_label = tr.get('test_file', '')
                q.test_passed = 'yes' if tr.get('passed', False) else 'no'
                q.test_result_badge = 'qa-badge-success' if tr.get('passed', False) else 'qa-badge-danger'
                q.test_result_label = 'PASSED' if tr.get('passed', False) else 'FAILED'
                q.has_run_results = 'yes'

                # Build a lookup from run results
                run_results = {}
                for t in tr.get('tests', []):
                    run_results[t.get('name', '')] = t.get('status', 'UNKNOWN')

                # Merge run results into test_functions
                def _badge_for(st):
                    if st == 'PASSED': return 'qa-badge-success'
                    if st in ('FAILED', 'ERROR'): return 'qa-badge-danger'
                    if st == 'SKIPPED': return 'qa-badge-warning'
                    return 'qa-badge-muted'

                merged = []
                seen = set()
                for tf in q.test_functions:
                    name = tf['name']
                    seen.add(name)
                    st = run_results.get(name, 'PENDING')
                    merged.append({'name': name, 'status': st, 'badge': _badge_for(st)})
                # Add any run results not in the source file (renamed/dynamic tests)
                for name, st in run_results.items():
                    if name not in seen:
                        merged.append({'name': name, 'status': st, 'badge': _badge_for(st)})

                # Sort: FAILED/ERROR first, then PASSED, then rest
                status_order = {'FAILED': 0, 'ERROR': 0, 'PASSED': 2, 'SKIPPED': 3, 'PENDING': 4}
                merged.sort(key=lambda x: (status_order.get(x['status'], 5), x['name']))
                q.test_functions = merged

                # Summary counts
                summary = tr.get('summary', {})
                s_passed = summary.get('passed', 0)
                s_failed = summary.get('failed', 0)
                s_errors = summary.get('errors', 0)
                s_skipped = summary.get('skipped', 0)
                q.test_summary_passed = str(s_passed)
                q.test_summary_failed = str(s_failed)
                q.test_summary_errors = str(s_errors)
                q.test_summary_skipped = str(s_skipped)
                q.test_summary_total = str(s_passed + s_failed + s_errors + s_skipped)
                q.test_summary_duration = summary.get('duration', '-')
            except:
                pass
else:
    q.error_message = 'No file specified. Use ?file=path/to/file in the URL.'
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{comp_name} - Component Detail - Quantum Admin</title>
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
            <a href="/admin/applications" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              Applications
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Framework</div>
            <a href="/admin/components" class="qa-sidebar-link active">
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
          <div>
            <h1 class="qa-header-title" style="font-size: 1.1rem;"><span class="qa-font-mono">{comp_name}</span></h1>
            <div class="qa-text-sm qa-text-muted" style="margin-top: 2px;">{file_param}</div>
          </div>
          <div class="qa-header-actions">
            <span class="qa-badge {file_type_badge}">{file_type}</span>
            <a href="/admin/components" style="color: var(--q-primary-400); text-decoration: none; font-size: 0.875rem; margin-left: 12px;">Back to Components</a>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Error state -->
          <q:if condition="{file_found} != 'yes'">
            <div class="qa-card">
              <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display: inline-block;"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                </div>
                <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">Cannot Load Component</div>
                <div class="qa-text-sm qa-text-muted">{error_message}</div>
                <div style="margin-top: 24px;">
                  <a href="/admin/components" style="color: var(--q-primary-400); text-decoration: none;">Back to Components</a>
                </div>
              </div>
            </div>
          </q:if>

          <!-- Main content when file found -->
          <q:if condition="{file_found} == 'yes'">

            <!-- Flash message -->
            <q:if condition="{flash_message} != ''">
              <div style="padding: 12px 16px; margin-bottom: 24px; border-radius: 8px; {flash_style}">
                <span class="qa-text-sm qa-font-medium">{flash_message}</span>
              </div>
            </q:if>

            <!-- Tab system (CSS-only radio trick) -->
            <q:if condition="{active_tab} == 'tests'">
              <input type="radio" name="cdtabs" id="cdtab-general" class="qa-tab-radio" />
              <input type="radio" name="cdtabs" id="cdtab-tests" class="qa-tab-radio" checked="checked" />
            </q:if>
            <q:if condition="{active_tab} != 'tests'">
              <input type="radio" name="cdtabs" id="cdtab-general" class="qa-tab-radio" checked="checked" />
              <input type="radio" name="cdtabs" id="cdtab-tests" class="qa-tab-radio" />
            </q:if>

            <div class="qa-tabs-bar">
              <label for="cdtab-general" class="qa-tab-label">General</label>
              <label for="cdtab-tests" class="qa-tab-label">Tests</label>
            </div>

            <div class="qa-tabs-content">

              <!-- ==================== GENERAL TAB ==================== -->
              <div class="qa-panel-cd-general">

                <!-- Metadata Card -->
                <div class="qa-card qa-mb-6">
                  <div class="qa-card-header">
                    <div class="qa-card-title">Component Metadata</div>
                  </div>
                  <div class="qa-card-body">
                    <div class="qa-grid qa-grid-3" style="gap: 20px;">
                      <div>
                        <div class="qa-text-xs qa-text-muted" style="margin-bottom: 4px;">Component Name</div>
                        <div class="qa-font-medium">{comp_name}</div>
                      </div>
                      <div>
                        <div class="qa-text-xs qa-text-muted" style="margin-bottom: 4px;">Path</div>
                        <div class="qa-font-mono qa-text-sm">{file_param}</div>
                      </div>
                      <div>
                        <div class="qa-text-xs qa-text-muted" style="margin-bottom: 4px;">File Type</div>
                        <div><span class="qa-badge {file_type_badge}">{file_type}</span></div>
                      </div>
                      <div>
                        <div class="qa-text-xs qa-text-muted" style="margin-bottom: 4px;">File Size</div>
                        <div class="qa-text-sm">{file_size}</div>
                      </div>
                      <div>
                        <div class="qa-text-xs qa-text-muted" style="margin-bottom: 4px;">Lines</div>
                        <div class="qa-text-sm">{line_count}</div>
                      </div>
                      <div>
                        <div class="qa-text-xs qa-text-muted" style="margin-bottom: 4px;">Last Modified</div>
                        <div class="qa-text-sm">{file_modified}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Actions Card -->
                <q:if condition="{actions_count} != '0'">
                  <div class="qa-card qa-mb-6">
                    <div class="qa-card-header">
                      <div>
                        <div class="qa-card-title">Actions</div>
                        <div class="qa-card-subtitle">{actions_count} actions defined</div>
                      </div>
                    </div>
                    <div class="qa-card-body qa-p-0">
                      <table class="qa-table">
                        <thead>
                          <tr>
                            <th>Action Name</th>
                            <th>Parameters</th>
                            <th>Method</th>
                          </tr>
                        </thead>
                        <tbody>
                          <q:loop type="array" var="act" items="{actions_list}">
                            <tr>
                              <td><span class="qa-font-mono qa-font-medium">{act.name}</span></td>
                              <td><span class="qa-text-sm qa-text-muted">{act.params_str}</span></td>
                              <td><span class="qa-badge qa-badge-info">{act.method}</span></td>
                            </tr>
                          </q:loop>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </q:if>

                <!-- Queries Card -->
                <q:if condition="{queries_count} != '0'">
                  <div class="qa-card qa-mb-6">
                    <div class="qa-card-header">
                      <div>
                        <div class="qa-card-title">Queries</div>
                        <div class="qa-card-subtitle">{queries_count} queries defined</div>
                      </div>
                    </div>
                    <div class="qa-card-body qa-p-0">
                      <table class="qa-table">
                        <thead>
                          <tr>
                            <th>Query Name</th>
                          </tr>
                        </thead>
                        <tbody>
                          <q:loop type="array" var="qry" items="{queries_list}">
                            <tr>
                              <td><span class="qa-font-mono">{qry.name}</span></td>
                            </tr>
                          </q:loop>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </q:if>

                <!-- Feature Tags Card -->
                <q:if condition="{feature_tags_count} != '0'">
                  <div class="qa-card qa-mb-6">
                    <div class="qa-card-header">
                      <div>
                        <div class="qa-card-title">Feature Tags</div>
                        <div class="qa-card-subtitle">{feature_tags_count} tags used</div>
                      </div>
                    </div>
                    <div class="qa-card-body">
                      <div class="qa-flex" style="flex-wrap: wrap; gap: 8px;">
                        <q:loop type="array" var="tag" items="{feature_tags_list}">
                          <span class="qa-badge qa-badge-primary">q:{tag.name}</span>
                        </q:loop>
                      </div>
                    </div>
                  </div>
                </q:if>

                <!-- View Source Link -->
                <div style="margin-top: 8px;">
                  <a href="{source_link}" style="color: var(--q-primary-400); text-decoration: none; font-size: 0.875rem;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 6px;"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                    View Full Source
                  </a>
                </div>

              </div>

              <!-- ==================== TESTS TAB ==================== -->
              <div class="qa-panel-cd-tests">

                <!-- A) Header Card -->
                <div class="qa-card qa-mb-6">
                  <div class="qa-card-header">
                    <div class="qa-flex qa-items-center qa-gap-2">
                      <div class="qa-card-title" style="margin: 0;">Tests</div>
                      <span class="qa-badge {test_badge}">{test_label}</span>
                    </div>
                    <div class="qa-flex qa-gap-2 qa-items-center">
                      <form method="POST" action="/admin/component/{file_param}" style="display: inline;">
                        <input type="hidden" name="action" value="generateTests" />
                        <input type="hidden" name="comp_path" value="{file_param}" />
                        <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Generate Tests</button>
                      </form>
                      <q:if condition="{has_test} == 'yes'">
                        <form method="POST" action="/admin/component/{file_param}" style="display: inline;">
                          <input type="hidden" name="action" value="runTests" />
                          <input type="hidden" name="test_file" value="{test_file}" />
                          <input type="hidden" name="comp_path" value="{file_param}" />
                          <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Run Tests</button>
                        </form>
                      </q:if>
                    </div>
                  </div>
                  <div class="qa-card-body" style="padding-top: 0;">
                    <q:if condition="{has_test} == 'yes'">
                      <div class="qa-text-sm qa-text-muted qa-font-mono">{test_file}</div>
                    </q:if>
                    <q:if condition="{has_test} != 'yes'">
                      <div class="qa-text-sm qa-text-muted">No test file found for this component. Use "Generate Tests" to create one.</div>
                    </q:if>
                  </div>
                </div>

                <!-- B) Summary Stats (only after run) -->
                <q:if condition="{has_run_results} == 'yes'">
                  <div class="qa-grid qa-grid-4 qa-mb-6" style="gap: 16px;">
                    <div class="qa-stat-card" style="border-left: 3px solid var(--q-success);">
                      <div class="qa-stat-label">Passed</div>
                      <div class="qa-stat-value" style="color: var(--q-success);">{test_summary_passed}</div>
                    </div>
                    <div class="qa-stat-card" style="border-left: 3px solid var(--q-danger);">
                      <div class="qa-stat-label">Failed</div>
                      <div class="qa-stat-value" style="color: var(--q-danger);">{test_summary_failed}</div>
                    </div>
                    <div class="qa-stat-card" style="border-left: 3px solid var(--q-warning);">
                      <div class="qa-stat-label">Skipped</div>
                      <div class="qa-stat-value" style="color: var(--q-warning);">{test_summary_skipped}</div>
                    </div>
                    <div class="qa-stat-card" style="border-left: 3px solid var(--q-info);">
                      <div class="qa-stat-label">Duration</div>
                      <div class="qa-stat-value" style="font-size: var(--q-text-lg);">{test_summary_duration}s</div>
                    </div>
                  </div>
                </q:if>

                <!-- C) Test Functions List -->
                <q:if condition="{has_test} == 'yes'">
                  <div class="qa-card qa-mb-6">
                    <div class="qa-card-header">
                      <div>
                        <div class="qa-card-title">Test Functions</div>
                        <div class="qa-card-subtitle">{test_count} tests in file</div>
                      </div>
                      <q:if condition="{has_run_results} == 'yes'">
                        <span class="qa-badge {test_result_badge}">{test_result_label}</span>
                      </q:if>
                    </div>
                    <div class="qa-card-body qa-p-0">
                      <table class="qa-table">
                        <thead>
                          <tr>
                            <th style="width: 90px;">Status</th>
                            <th>Test Name</th>
                          </tr>
                        </thead>
                        <tbody>
                          <q:loop type="array" var="tf" items="{test_functions}">
                            <tr>
                              <td><span class="qa-badge {tf.badge}">{tf.status}</span></td>
                              <td><span class="qa-font-mono qa-text-sm">{tf.name}</span></td>
                            </tr>
                          </q:loop>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <!-- View test source link -->
                  <div style="margin-bottom: 16px;">
                    <a href="/admin/source?file={test_file}" style="color: var(--q-primary-400); text-decoration: none; font-size: 0.875rem;">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 6px;"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                      View test source
                    </a>
                  </div>
                </q:if>

                <!-- D) Raw Output (only after run, collapsed) -->
                <q:if condition="{has_run_results} == 'yes'">
                  <div class="qa-card qa-mb-6">
                    <details>
                      <summary style="padding: 12px 16px; cursor: pointer; color: var(--q-text-secondary); font-size: var(--q-text-sm); font-weight: 500; list-style: none; display: flex; align-items: center; gap: 8px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transition: transform 0.2s;"><polyline points="6 9 12 15 18 9"/></svg>
                        Raw pytest output
                      </summary>
                      <div class="qa-card-body qa-p-0" style="border-top: 1px solid var(--q-border);">
                        <div class="qa-log-viewer">{test_output}</div>
                      </div>
                    </details>
                  </div>
                </q:if>

              </div>

            </div>

          </q:if>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
