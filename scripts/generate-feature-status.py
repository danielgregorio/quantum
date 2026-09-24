"""Generate FEATURE_STATUS.md by MEASURING the engine, never by hand.

    python scripts/generate-feature-status.py                 # parse + execute
    python scripts/generate-feature-status.py --live-ai       # also run AI examples
    python scripts/generate-feature-status.py --coverage coverage.json

Hand-written status tables rot: this repo had manifests marking implemented
features "planned", a docs page teaching a tag no parser registers, and a
SUPPORT_TIERS table whose "validated" column was filled in from isolated checks.
A generated table cannot drift, because it is derived from the registries and
from what the examples actually do.

What it measures, per tag:
  - examples  — examples/*.q and components/*.q that use it
  - parses    — at least one of those files passes the parser
  - executes  — for Core and AI tags: how many of those files `quantum run`
                executes without error. Run in a TEMPORARY COPY of examples/,
                components/, test_data/ and quantum.config.yaml, because
                examples INSERT into SQLite files and the config points the
                `admin` datasource at the admin's real database.
                Experimental tags are not executed (mail sends mail, jobs start
                schedulers). Interactive targets (terminal, ui, html servers)
                are not executed either — they block. AI examples run only with
                --live-ai, against the real model server; without it they are
                reported as not executed, never as passing.
  - tests     — test files that mention the tag
  - docs      — documentation pages that mention it
"""
import argparse
import collections
import concurrent.futures
import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from quantum.core import tiers  # noqa: E402
from quantum.core.parser import QuantumParser  # noqa: E402
from quantum.runtime.component import ComponentRuntime  # noqa: E402

HTML_TAGS = {
    'div', 'span', 'p', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol',
    'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'form', 'input',
    'button', 'label', 'select', 'option', 'textarea', 'img', 'br', 'hr',
    'pre', 'code', 'style', 'script', 'html', 'head', 'body', 'header',
    'footer', 'nav', 'main', 'section', 'article', 'aside', 'strong', 'em',
    'b', 'i', 'blockquote', 'meta', 'link', 'canvas', 'svg', 'audio', 'video',
    'source',
}

# Application types that start a server or a TUI and never return.
INTERACTIVE_TYPES = {'terminal', 'ui', 'html', 'api', 'microservices'}

# Phase 0 goal (Flawless Core plan): core line coverage for 1.0.
CORE_COVERAGE_TARGET = 90

CORE_MODULES = (
    'quantum/runtime/component.py',
    'quantum/core/expressions.py',
    'quantum/runtime/execution_context.py',
    'quantum/runtime/renderer.py',
    'quantum/core/parser.py',
    'quantum/runtime/executors/control_flow/',
    'quantum/runtime/executors/data/',
    'quantum/runtime/executors/ai/',
    'quantum/core/parsers/control_flow/',
    'quantum/core/parsers/data/',
    'quantum/core/parsers/ai/',
    'quantum/runtime/llm_service.py',
    'quantum/runtime/knowledge_service.py',
    'quantum/runtime/agent_service.py',
)


def registered_tags():
    parser = QuantumParser()
    reg = getattr(parser, '_parser_registry', None)
    names = sorted(getattr(reg, '_parsers', {}).keys())
    return [n for n in names if n not in HTML_TAGS]


def executor_node_types():
    with contextlib.redirect_stdout(io.StringIO()):
        rt = ComponentRuntime()
    reg = rt._executor_registry
    return {t.__name__ for t in getattr(reg, '_executors', {}).keys()}


def q_files():
    for base in ('examples', 'components'):
        yield from sorted((REPO / base).rglob('*.q'))


def usage_index():
    """tag -> [files that use it]"""
    idx = collections.defaultdict(list)
    for f in q_files():
        try:
            text = f.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for tag in set(re.findall(r'<q:([a-zA-Z-]+)', text)):
            idx[tag].append(f)
    return idx


def mention_index(paths):
    """tag -> number of files among `paths` whose text mentions q:tag."""
    texts = []
    for p in paths:
        try:
            texts.append(p.read_text(encoding='utf-8', errors='ignore'))
        except OSError:
            pass

    def count(tag):
        pattern = re.compile(r'q:' + re.escape(tag) + r'(?![A-Za-z-])')
        return sum(1 for t in texts if pattern.search(t))
    return count


def parses(path):
    try:
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            QuantumParser().parse(path.read_text(encoding='utf-8', errors='ignore'))
        return True
    except Exception:
        return False


def requires_params(text):
    """A component whose own q:param is required with no default cannot run alone.

    Asked of the parser: a q:param inside q:function or q:action belongs to
    that function or action, not to the component.
    """
    try:
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            node = QuantumParser().parse(text)
    except Exception:
        return False
    return any(getattr(p, 'required', False) and getattr(p, 'default', None) is None
               for p in getattr(node, 'params', []) or [])


def app_type(path):
    text = path.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'<q:application[^>]*\btype="([^"]+)"', text)
    return m.group(1) if m else 'component'


def make_sandbox():
    root = pathlib.Path(tempfile.mkdtemp(prefix='quantum-feature-status-'))
    for name in ('examples', 'components', 'test_data'):
        if (REPO / name).exists():
            shutil.copytree(REPO / name, root / name,
                            ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
    shutil.copy2(REPO / 'quantum.config.yaml', root / 'quantum.config.yaml')
    (root / 'quantum_admin').mkdir()     # the `admin` datasource lands here, empty
    return root


def expects_failure(rel):
    # Examples named *-invalid* exist to show a validation error.
    return 'invalid' in pathlib.Path(rel).stem


def execute(sandbox, rel, timeout):
    """-> ('ok' | 'error' | 'timeout', first error line)

    For an example that exists to fail (see expects_failure), failing with an
    [ERROR] is 'ok' and running cleanly is the error.
    """
    status, msg = _execute(sandbox, rel, timeout)
    if expects_failure(rel) and status != 'timeout':
        return ('ok', '') if status == 'error' else ('error', 'should have failed and ran')
    return status, msg


def _execute(sandbox, rel, timeout):
    env = dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8')
    try:
        proc = subprocess.run(
            [sys.executable, '-m', 'quantum.cli.runner', 'run', str(rel)],
            cwd=sandbox, env=env, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        return 'timeout', f'did not finish in {timeout}s'
    output = (proc.stdout or '') + (proc.stderr or '')
    if proc.returncode == 0 and '[ERROR]' not in output:
        return 'ok', ''
    all_lines = [l.strip() for l in output.splitlines()]
    for i, line in enumerate(all_lines):
        if '[ERROR]' in line or 'Error' in line or 'error' in line:
            # "Validation errors:" puts the actual message on the next line.
            if line.endswith(':') and i + 1 < len(all_lines):
                line = f'{line} {all_lines[i + 1]}'
            return 'error', line[:160]
    return 'error', f'exit {proc.returncode}'


def coverage_rows(path):
    data = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    files = {k.replace('\\', '/'): v['summary'] for k, v in data.get('files', {}).items()}
    rows = []
    for module in CORE_MODULES:
        hit = total = 0
        for name, summary in files.items():
            rel = name.split('quantum/', 1)
            rel = ('quantum/' + rel[1]) if len(rel) == 2 else name
            if rel == module or (module.endswith('/') and rel.startswith(module)):
                hit += summary['covered_lines']
                total += summary['num_statements']
        if total:
            rows.append((module, hit, total))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live-ai', action='store_true',
                    help='also execute examples that use AI tags (needs a model server)')
    ap.add_argument('--coverage', help='coverage.json from pytest --cov-report=json')
    ap.add_argument('--timeout', type=int, default=40)
    args = ap.parse_args()

    tags = registered_tags()
    executors = executor_node_types()
    usage = usage_index()
    tests_count = mention_index(list((REPO / 'tests').rglob('*.py')))
    doc_pages = [p for p in (REPO / 'docs').rglob('*.md')
                 if not {'archive', 'devlog', 'node_modules'} & set(p.parts)]
    docs_count = mention_index(doc_pages)

    # Which files to execute: those using a supported tag, not interactive,
    # AI ones only when asked to.
    to_run, skipped = {}, {}
    for tag in tiers.SUPPORTED:
        for f in usage.get(tag, []):
            if f in to_run or f in skipped:
                continue
            text = f.read_text(encoding='utf-8', errors='ignore')
            used = set(re.findall(r'<q:([a-zA-Z-]+)', text))
            kind = app_type(f)
            root = re.search(r'<(q:[A-Za-z]+|[A-Za-z]+:[A-Za-z]+)', re.sub(r'<!--.*?-->', '', text, flags=re.S))
            if root and root.group(1) not in ('q:component', 'q:application'):
                skipped[f] = f'fragment, not a root file ({root.group(1)})'
            elif tiers.app_tier_of(kind or '') == 'laboratory':
                # A game uses q:set and q:function, but it is Laboratory
                # (SUPPORT_TIERS.md): its failures are not Core failures.
                skipped[f] = f'Laboratory ({kind})'
            elif kind in INTERACTIVE_TYPES:
                skipped[f] = f'interactive target ({kind})'
            elif requires_params(text):
                skipped[f] = 'component requires parameters'
            elif 'datasource="admin"' in text:
                skipped[f] = 'needs the admin database'
            elif used & tiers.EXPERIMENTAL:
                skipped[f] = 'uses an experimental tag'
            elif used & tiers.AI and not args.live_ai:
                skipped[f] = 'uses AI (run with --live-ai)'
            else:
                to_run[f] = None

    sandbox = make_sandbox()
    results = {}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(execute, sandbox, f.relative_to(REPO), args.timeout): f
                       for f in to_run}
            for fut in concurrent.futures.as_completed(futures):
                results[futures[fut]] = fut.result()
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    rows = []
    for tag in tags:
        files = usage.get(tag, [])
        ran = [results[f] for f in files if f in results]
        rows.append({
            'tag': tag,
            'tier': tiers.tier_of(tag),
            'examples': len(files),
            'parses': any(parses(f) for f in files) if files else None,
            'ran': len(ran),
            'ok': sum(1 for status, _ in ran if status == 'ok'),
            'not_run': sum(1 for f in files if f in skipped),
            'tests': tests_count(tag),
            'docs': docs_count(tag),
        })

    by_tier = collections.defaultdict(list)
    for r in rows:
        by_tier[r['tier']].append(r)

    out = [
        '# FEATURE_STATUS — generated, not written',
        '',
        '> **Do not edit this file.** It is produced by',
        '> `python scripts/generate-feature-status.py`, measuring the engine.',
        '> Hand-written status tables rot.',
        '',
        f'**{len(tags)} registered `q:` tags · {len(executors)} executors · '
        f'{len(results)} examples executed · live AI: '
        f'{"yes" if args.live_ai else "no"}.**',
        '',
        'Columns: **tier** comes from `quantum/core/tiers.py`. **examples**: files in',
        '`examples/` and `components/` that use the tag. **parses**: at least one of them',
        'passes the parser. **executes**: of the executable examples, how many',
        '`quantum run` executes without error, in a temporary copy of the repository (only',
        'Core and AI; interactive targets and experimental tags are not executed).',
        '**tests** and **docs**: files that mention the tag.',
        '',
    ]

    order = [('core', 'Core'), ('ai', 'AI'),
             ('experimental', 'Experimental'), ('unknown', 'Unclassified')]
    for key, title in order:
        group = sorted(by_tier.get(key, []), key=lambda r: r['tag'])
        if not group:
            continue
        executes_col = key in ('core', 'ai')
        header = '| Tag | Examples | Parses |' + (' Executes |' if executes_col else '') + ' Tests | Docs |'
        out += [f'## {title} ({len(group)} tags)', '', header,
                '|' + '---|' * (header.count('|') - 1)]
        for r in group:
            if r['examples'] == 0:
                parse = '— no example'
            elif r['parses']:
                parse = 'yes'
            else:
                parse = '**NO**'
            line = f"| `q:{r['tag']}` | {r['examples']} | {parse} |"
            if executes_col:
                if r['ran']:
                    cell = f"{r['ok']}/{r['ran']}"
                    if r['ok'] < r['ran']:
                        cell = f"**{cell}**"
                else:
                    cell = '—'
                if r['not_run']:
                    cell += f" ({r['not_run']} not executed)"
                line += f" {cell} |"
            line += f" {r['tests']} | {r['docs']} |"
            out.append(line)
        out.append('')

    failures = sorted((f, res) for f, res in results.items() if res[0] != 'ok')
    out += ['## Core/AI examples that do not execute', '']
    if failures:
        out += ['| File | Result | First error line |', '|---|---|---|']
        for f, (status, msg) in failures:
            msg = msg.replace('|', '\\|')
            out.append(f"| `{f.relative_to(REPO).as_posix()}` | {status} | {msg} |")
    else:
        out.append('None.')
    out.append('')

    reasons = collections.Counter(skipped.values())
    out += ['## Not executed, and why', '']
    out += [f'- {n} file(s): {reason}' for reason, n in reasons.most_common()] or ['- none']
    out.append('')

    if args.coverage:
        out += ['## Core module coverage', '',
                'Lines covered by the suite (`pytest --cov=quantum --cov-report=json`).', '',
                '| Module | Coverage | Lines |', '|---|---|---|']
        hit_all = total_all = 0
        for module, hit, total in coverage_rows(args.coverage):
            hit_all += hit
            total_all += total
            out.append(f"| `{module}` | {100 * hit / total:.0f}% | {hit}/{total} |")
        if total_all:
            out.append(f"| **whole core** | **{100 * hit_all / total_all:.0f}%** | {hit_all}/{total_all} |")
            out += ['', f"**Goal for 1.0: {CORE_COVERAGE_TARGET}%.** Modules below it: "
                    + (', '.join(f"`{m}`" for m, h, tt in coverage_rows(args.coverage)
                                 if 100 * h / tt < CORE_COVERAGE_TARGET) or 'none') + '.']
        out.append('')

    no_example = [r['tag'] for r in rows if r['examples'] == 0]
    broken = [r['tag'] for r in rows if r['examples'] and not r['parses']]
    out += ['## Gaps this measurement exposes', '',
            f'- **{len(no_example)} tags without any example**: '
            + (', '.join(f'`q:{t}`' for t in sorted(no_example)) or 'none') + '.',
            f'- **{len(broken)} tags whose examples do not parse**: '
            + (', '.join(f'`q:{t}`' for t in sorted(broken)) or 'none') + '.',
            f'- **{len(failures)} Core/AI examples that do not execute** (table above).',
            '']

    (REPO / 'FEATURE_STATUS.md').write_text('\n'.join(out), encoding='utf-8')
    print(f"{len(tags)} tags measured, {len(results)} examples executed -> FEATURE_STATUS.md")
    print(f"  fail to execute: {len(failures)} | not executed: {len(skipped)}")


if __name__ == '__main__':
    main()
