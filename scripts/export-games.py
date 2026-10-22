#!/usr/bin/env python
"""Export the games with Godot's export templates: for the browser, Linux and Windows; macOS, Android, iOS when asked.

    python scripts/export-games.py --install-templates [FILE.tpz]   # once: Godot's templates (1.2 GB)
    python scripts/export-games.py                                  # every game: Web, Linux, Windows
    python scripts/export-games.py hopper chess --preset Web        # some games, one preset
    python scripts/export-games.py keep --preset macOS              # an app for a Mac (unsigned)
    python scripts/export-games.py keep --preset Android            # an .apk (needs the Android SDK, below)
    python scripts/export-games.py keep --preset iOS                # an Xcode project (a Mac builds it)
    python scripts/export-games.py --out /some/dir                  # elsewhere than docs/public/games/

The games are every projects/<name>/<name>.q. Each lands in docs/public/games/<name>/:
the web build as index.html next to its files (threads off, so it runs on
a static host such as GitHub Pages), and <name>-linux.zip / <name>-windows.zip.
docs/public/games/manifest.json lists what was built, and
docs/public/games/index.html is the page that shows every game with its
screenshot, what it is, its keys and its links (from projects/games.json),
and docs/public/games/<name>/source/ the page of each game's source;
docs/targets/play.md links them. The Deploy Docs workflow runs this before the
site is built; nothing here is committed.

Templates: --install-templates downloads Godot's archive for the pinned
version from GitHub (or takes a file) and unpacks it where Godot looks.

macOS: a .zip of an unsigned .app (<name>-macos.zip); a Mac opens it with
"Open" from its context menu. Android: Godot's editor settings name the
Android SDK and a Java SDK (export/android/android_sdk_path and
java_sdk_path); QUANTUM_ANDROID_KEYSTORE, QUANTUM_ANDROID_KEYSTORE_USER and
QUANTUM_ANDROID_KEYSTORE_PASSWORD the key that signs the release (without
them, the debug key signs it); the .apk is <name>-android.apk. iOS: an
Xcode project (<name>-ios.zip) for a Mac with Xcode to build and sign;
QUANTUM_IOS_TEAM_ID is the Apple team. On a phone the games show their
touch controls (qg:touch-button, qg:touch-stick).
"""

import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantum.runtime.godot.schema import STATEMENTS, TAGS  # noqa: E402
from quantum.runtime.godot_bin import GODOT_VERSION, GodotNotFound, ensure_godot, script_errors  # noqa: E402

PRESETS = {
    'Web': ('Web', 'index.html', '''variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
html/export_icon=true
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
progressive_web_app/enabled=false
'''),
    'Linux': ('Linux', '{name}.x86_64', '''binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
'''),
    'Windows': ('Windows Desktop', '{name}.exe', '''binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
codesign/enable=false
application/modify_resources=false
'''),
    'macOS': ('macOS', '{name}.zip', '''binary_format/architecture="universal"
application/bundle_identifier="net.quantumframework.{id}"
application/min_macos_version="10.12"
codesign/codesign=0
notarization/notarization=0
texture_format/s3tc_bptc=true
texture_format/etc2_astc=true
'''),
    'Android': ('Android', '{name}.apk', '''gradle_build/use_gradle_build=false
architectures/armeabi-v7a=true
architectures/arm64-v8a=true
package/unique_name="net.quantumframework.{id}"
package/name="{title}"
screen/immersive_mode=true
keystore/release="{keystore}"
keystore/release_user="{keystore_user}"
keystore/release_password="{keystore_password}"
'''),
    'iOS': ('iOS', '{name}.ipa', '''application/app_store_team_id="{team}"
application/bundle_identifier="net.quantumframework.{id}"
application/export_project_only=true
application/targeted_device_family=2
orientation/landscape_left=true
orientation/landscape_right=true
orientation/portrait=false
orientation/portrait_upside_down=false
'''),
}
# What the site builds: a browser's, and the desktops' downloads.
DEFAULT_PRESETS = ['Web', 'Linux', 'Windows']

TEMPLATES_URL = (f'https://github.com/godotengine/godot/releases/download/{GODOT_VERSION}-stable/'
                 f'Godot_v{GODOT_VERSION}-stable_export_templates.tpz')


def templates_dir() -> Path:
    """Where Godot looks for its export templates, on this system."""
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Godot'
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'Godot'
    else:
        base = Path.home() / '.local' / 'share' / 'godot'
    return base / 'export_templates' / f'{GODOT_VERSION}.stable'


def games() -> dict:
    return {p.parent.name: p for p in sorted(REPO.glob('projects/*/*.q')) if p.stem == p.parent.name}


def install_templates(source: str = '') -> int:
    target = templates_dir()
    if target.is_dir() and any(target.iterdir()):
        print(f'templates already in {target}')
        return 0
    if source:
        archive = Path(source)
    else:
        archive = Path.home() / '.cache' / 'quantum' / f'godot-{GODOT_VERSION}-export-templates.tpz'
        if not archive.is_file():
            archive.parent.mkdir(parents=True, exist_ok=True)
            print(f'downloading {TEMPLATES_URL} (about 1.2 GB)...')
            urllib.request.urlretrieve(TEMPLATES_URL, archive)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():   # the archive holds templates/<file>; Godot wants <version>.stable/<file>
            if info.is_dir():
                continue
            name = info.filename.split('/', 1)[1] if '/' in info.filename else info.filename
            with z.open(info) as src, open(target / name, 'wb') as dst:
                shutil.copyfileobj(src, dst)
    print(f'installed {len(list(target.iterdir()))} templates in {target}')
    return 0


def preset_file(name: str, preset: str, target: Path) -> str:
    platform, _, options = PRESETS[preset]
    titles = {}
    if (REPO / 'projects' / 'games.json').is_file():
        titles = {g['name']: g['title'] for g in
                  json.loads((REPO / 'projects' / 'games.json').read_text(encoding='utf-8'))['games']}
    options = options.format(id=re.sub(r'[^a-z0-9]', '', name.lower()), title=titles.get(name, name.title()),
                             keystore=os.environ.get('QUANTUM_ANDROID_KEYSTORE', ''),
                             keystore_user=os.environ.get('QUANTUM_ANDROID_KEYSTORE_USER', ''),
                             keystore_password=os.environ.get('QUANTUM_ANDROID_KEYSTORE_PASSWORD', ''),
                             team=os.environ.get('QUANTUM_IOS_TEAM_ID', ''))
    return (f'[preset.0]\n\nname="{preset}"\nplatform="{platform}"\nrunnable=true\n'
            f'export_filter="all_resources"\ninclude_filter=""\nexclude_filter=""\nexport_path="{target.as_posix()}"\n'
            f'\n[preset.0.options]\n\n{options}')


def export(name: str, source: Path, preset: str, out_root: Path, godot: Path) -> dict:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    project = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(source)),
                                str(source.parent / 'godot'), source_dir=str(source.parent)))
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    platform, filename, _ = PRESETS[preset]
    if preset == 'Web':
        target = out / 'index.html'
        work = target
    else:
        work_dir = out / f'.{preset.lower()}'
        shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True)
        work = work_dir / filename.format(name=name)
        target = out / f'{name}-{preset.lower()}.zip'
    (project / 'export_presets.cfg').write_text(preset_file(name, preset, work), encoding='utf-8')
    if preset in ('macOS', 'Android', 'iOS'):   # Apple's chips and phones read ETC2/ASTC textures
        settings = (project / 'project.godot').read_text(encoding='utf-8')
        if 'import_etc2_astc' not in settings:
            (project / 'project.godot').write_text(settings.replace(
                '[rendering]\n', '[rendering]\ntextures/vram_compression/import_etc2_astc=true\n', 1), encoding='utf-8')
    # Android without a release key of its own: the debug key signs it
    how = '--export-debug' if preset == 'Android' and not os.environ.get('QUANTUM_ANDROID_KEYSTORE') else '--export-release'
    result = subprocess.run([str(godot), '--headless', '--path', str(project), how, preset, str(work)],
                            capture_output=True, text=True, timeout=900)
    errors = script_errors(result.stdout + result.stderr)
    # iOS writes an Xcode project next to where the .ipa would be
    made = work.is_file() or (preset == 'iOS' and work.parent.is_dir() and any(work.parent.iterdir()))
    if errors or not made:
        raise RuntimeError(f'{name} ({preset}): export failed\n' + '\n'.join(errors) + result.stderr[-2000:])
    if preset in ('macOS', 'Android'):   # one file already: a .zip of the .app, an .apk
        target = out / f'{name}-{preset.lower()}{work.suffix}'
        shutil.move(str(work), target)
        shutil.rmtree(work.parent)
    elif preset != 'Web':
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(work.parent.iterdir()):
                z.write(f, f'{name}/{f.name}')
        shutil.rmtree(work.parent)
    size = sum(f.stat().st_size for f in out.iterdir() if f.is_file()) if preset == 'Web' else target.stat().st_size
    print(f'{name} {preset}: {target.relative_to(REPO) if target.is_relative_to(REPO) else target} ({size // 1024} KB)')
    return {'preset': preset, 'file': target.name}


GITHUB = 'https://github.com/danielgregorio/quantum/blob/main/'

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quantum games</title>
<meta name="description" content="Games written in Quantum's game language, playable in the browser.">
<style>
:root {{ --bg: #0f1020; --card: #1a1b33; --text: #ecebf5; --muted: #a9a8c3; --accent: #7c6cff; --line: #2b2c4d; }}
@media (prefers-color-scheme: light) {{
  :root {{ --bg: #f4f4fb; --card: #ffffff; --text: #1b1b2f; --muted: #5d5d78; --accent: #5a48f0; --line: #dcdcec; }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
header {{ max-width: 1180px; margin: 0 auto; padding: 40px 16px 8px; }}
header h1 {{ margin: 0 0 6px; font-size: 2rem; }}
header p {{ margin: 0; color: var(--muted); max-width: 760px; }}
header a {{ color: var(--accent); }}
main {{ max-width: 1180px; margin: 0 auto; padding: 24px 16px 56px;
  display: grid; gap: 20px; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
  display: flex; flex-direction: column; }}
.shot {{ display: block; position: relative; background: #000; aspect-ratio: 16 / 10; overflow: hidden; }}
.shot img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; }}
.body {{ padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 8px; flex: 1; }}
.title {{ display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }}
.title h2 {{ margin: 0; font-size: 1.25rem; }}
.badge {{ font-size: .75rem; color: var(--muted); border: 1px solid var(--line); border-radius: 999px;
  padding: 1px 8px; white-space: nowrap; }}
.blurb {{ margin: 0; }}
.keys {{ margin: 0; color: var(--muted); font-size: .875rem; }}
.links {{ margin-top: auto; padding-top: 6px; display: flex; flex-wrap: wrap; gap: 8px; }}
.links a {{ text-decoration: none; font-size: .875rem; padding: 6px 12px; border-radius: 8px;
  border: 1px solid var(--line); color: var(--text); }}
.links a.play {{ background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }}
.links a:hover {{ border-color: var(--accent); }}
footer {{ max-width: 1180px; margin: 0 auto; padding: 0 16px 40px; color: var(--muted); font-size: .875rem; }}
footer a {{ color: var(--accent); }}
.room {{ display: none; margin-top: 10px; font-size: .875rem; }}
.room input {{ width: 100%; font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--line); }}
</style>
</head>
<body>
<header>
<h1>Quantum games</h1>
<p>Each of these is one <code>.q</code> file in Quantum's game language, compiled for Godot {godot} and played here in
the browser, or downloaded for Linux and Windows. Two-player games run on one keyboard or between two machines
(<a href="../targets/play.html">how to play over the network</a>).</p>
</header>
<main>
{cards}
</main>
<footer>The game language: <a href="../targets/games.html">its reference</a>. The source of every game:
<a href="https://github.com/danielgregorio/quantum/tree/main/projects">projects/</a>.</footer>
<script>
// "Play online": a room of its own at the relay, as a link to send to a friend; both open it
// and choose Join on the title (the address field already holds the room).
for (const a of document.querySelectorAll('a.online')) {{
  a.addEventListener('click', (e) => {{
    e.preventDefault();
    const room = Math.random().toString(36).slice(2, 8);
    const link = new URL(a.dataset.game + '/?join=' + a.dataset.relay + '/' + a.dataset.game + '/' + room, location.href).href;
    const box = a.closest('.body').querySelector('.room');
    box.querySelector('input').value = link;
    box.querySelector('a').href = link;
    box.style.display = 'block';
    if (navigator.clipboard) navigator.clipboard.writeText(link).catch(() => {{}});
  }});
}}
</script>
</body>
</html>
"""


SOURCE_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} source</title>
<meta name="description" content="The source of {title}, a game written in Quantum's game language.">
<style>
:root {{ --bg: #0f1020; --card: #1a1b33; --text: #ecebf5; --muted: #a9a8c3; --accent: #7c6cff; --line: #2b2c4d;
  --mark: #2e2a63; --tag: #aab4ff; --core: #f0a6ca; --other: #8fd3dc; --attr: #f6c177; --value: #a6e3a1;
  --expr: #f5a97f; --comment: #8b8fa8; }}
@media (prefers-color-scheme: light) {{
  :root {{ --bg: #f4f4fb; --card: #ffffff; --text: #1b1b2f; --muted: #5d5d78; --accent: #5a48f0; --line: #dcdcec;
    --mark: #ebe8ff; --tag: #3a2fd1; --core: #b4237a; --other: #1d6f7a; --attr: #8a5a00; --value: #2f7d32;
    --expr: #b5480f; --comment: #6b6f80; }}
}}
* {{ box-sizing: border-box; }}
[hidden] {{ display: none !important; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
header, main {{ max-width: 1180px; margin: 0 auto; padding: 0 16px; }}
header {{ padding-top: 28px; }}
header h1 {{ margin: 4px 0 6px; font-size: 1.75rem; }}
header p {{ margin: 0; color: var(--muted); max-width: 760px; }}
header a {{ color: var(--accent); }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .9em; }}
a.back {{ color: var(--muted); font-size: .875rem; text-decoration: none; }}
a.back:hover {{ color: var(--accent); }}
.actions, .bar, .tabs {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}
.actions {{ margin-top: 14px; }}
.actions a, .actions button, .bar a, .bar button, .tabs button {{ font: inherit; font-size: .875rem;
  padding: 6px 12px; border-radius: 8px; border: 1px solid var(--line); background: var(--card);
  color: var(--text); text-decoration: none; cursor: pointer; }}
.actions a.play {{ background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }}
.actions a:hover, .actions button:hover, .bar a:hover, .bar button:hover, .tabs button:hover,
.tabs button[aria-selected="true"], .actions button[aria-pressed="true"] {{ border-color: var(--accent); }}
details {{ margin-top: 14px; color: var(--muted); font-size: .875rem; }}
summary {{ cursor: pointer; }}
details a {{ display: inline-block; margin: 6px 4px 0 0; padding: 1px 8px; border: 1px solid var(--line);
  border-radius: 999px; color: var(--tag); text-decoration: none;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
details a:hover {{ border-color: var(--accent); }}
main {{ padding-top: 20px; padding-bottom: 48px; }}
.tabs {{ margin-bottom: 10px; }}
.file {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
  margin-bottom: 20px; }}
.bar {{ padding: 10px 14px; border-bottom: 1px solid var(--line); }}
.bar strong {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
.bar .info {{ color: var(--muted); font-size: .875rem; margin-right: auto; }}
pre {{ margin: 0; padding: 12px 0; overflow-x: auto;
  font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; tab-size: 4; }}
.l {{ display: block; padding-right: 16px; white-space: pre; }}
.l:target {{ background: var(--mark); }}
.wrap .l {{ white-space: pre-wrap; overflow-wrap: anywhere; padding-left: 6ch; text-indent: -6ch; }}
.n {{ display: inline-block; width: 6ch; padding-right: 2ch; text-align: right; text-indent: 0;
  color: var(--muted); opacity: .55; text-decoration: none; user-select: none; }}
.n::before {{ content: attr(data-n); }}
.n:hover, .l:target .n {{ opacity: 1; color: var(--accent); }}
.b {{ color: var(--muted); }}
.t {{ color: var(--tag); font-weight: 600; text-decoration: none; }}
.k {{ color: var(--core); font-weight: 600; text-decoration: none; }}
.g {{ color: var(--other); }}
.a {{ color: var(--attr); text-decoration: none; }}
.a[data-t] {{ text-decoration: underline dotted; text-underline-offset: 3px; cursor: help; }}
a.t:hover, a.k:hover, a.a:hover {{ text-decoration: underline; }}
.v {{ color: var(--value); }}
.e {{ color: var(--expr); }}
.c {{ color: var(--comment); font-style: italic; }}
.p {{ color: var(--comment); }}
</style>
</head>
<body>
<header>
<a class="back" href="../../">← All the games</a>
<h1>{title}</h1>
<p>All of {title} is here, in Quantum's game language: {files}, compiled for Godot {godot}, with no script
besides. Point at a tag or an attribute to see what it does; a tag opens its entry in
<a href="{reference}">the language's reference</a>.</p>
<div class="actions">{play}<button id="wrap" type="button" aria-pressed="false" hidden>Wrap long lines</button></div>
<details><summary>The {used} tags it uses, of the language's {tags}</summary>
{chips}</details>
</header>
<main>
<nav class="tabs" hidden>{tabs}</nav>
{sections}
</main>
<script>
// What a tag or an attribute does, from the schema the compiler checks against: shown when pointed at.
const DOCS = {docs};
for (const el of document.querySelectorAll('[data-t]')) el.title = DOCS[el.dataset.t] || '';
// Several files: one at a time, as tabs; a link to a line opens the file it is in.
const files = [...document.querySelectorAll('.file')];
const tabs = [...document.querySelectorAll('.tabs button')];
function show(i) {{
  files.forEach((f, j) => {{ f.hidden = j !== i; }});
  tabs.forEach((t, j) => t.setAttribute('aria-selected', String(j === i)));
}}
if (tabs.length) {{
  document.querySelector('.tabs').hidden = false;
  tabs.forEach((t, i) => t.addEventListener('click', () => show(i)));
  show(0);
}}
function follow() {{
  const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (!target) return;
  if (tabs.length && target.closest('.file')) show(files.indexOf(target.closest('.file')));
  target.scrollIntoView({{ block: 'center' }});
}}
follow();
addEventListener('hashchange', follow);
for (const button of document.querySelectorAll('.copy')) {{
  button.hidden = !navigator.clipboard;
  button.addEventListener('click', () => {{
    const lines = [...button.closest('.file').querySelectorAll('.l')].map((l) => l.textContent);
    navigator.clipboard.writeText(lines.join('\\n') + '\\n').then(() => {{
      button.textContent = 'Copied';
      setTimeout(() => {{ button.textContent = 'Copy'; }}, 1500);
    }}, () => {{}});
  }});
}}
const wrap = document.getElementById('wrap');
function setWrap(on) {{
  document.querySelector('main').classList.toggle('wrap', on);
  wrap.setAttribute('aria-pressed', String(on));
  try {{ localStorage.setItem('quantum-source-wrap', on ? '1' : ''); }} catch (e) {{}}
}}
let wrapped = false;
try {{ wrapped = localStorage.getItem('quantum-source-wrap') === '1'; }} catch (e) {{}}
setWrap(wrapped);
wrap.hidden = false;
wrap.addEventListener('click', () => setWrap(wrap.getAttribute('aria-pressed') !== 'true'));
</script>
</body>
</html>
"""

SOURCE_SUFFIXES = ('.tmx', '.tsx', '.csv')   # what a game reads besides its .q: Tiled's maps and tilesets
REFERENCE = '../../../targets/games.html'      # the language's reference, from games/<name>/source/

_XML = re.compile(r'(?P<comment><!--.*?-->)|(?P<pi><\?.*?\?>|<!\[CDATA\[.*?\]\]>)'
                  r'|(?P<open></?)(?P<name>[A-Za-z_][\w:.-]*)'
                  r'(?P<attrs>(?:[^<>"\']|"[^"]*"|\'[^\']*\')*?)(?P<close>/?>)', re.S)
_ATTR = re.compile(r'(?P<name>[A-Za-z_][\w:.-]*)(?P<eq>\s*=\s*)(?P<value>"[^"]*"|\'[^\']*\')')
_EXPR = re.compile(r'\{[^{}]*\}')


def source_files(name: str) -> list:
    """The game's .q, then the text files it reads (a level drawn in Tiled), from projects/<name>/
    but not its build (godot/)."""
    project = REPO / 'projects' / name
    rest = sorted(p for p in project.rglob('*') if p.suffix in SOURCE_SUFFIXES
                  and 'godot' not in p.relative_to(project).parts)
    return [project / f'{name}.q'] + rest


def describe(key: str) -> str:
    """What a tag ('character') or one of its attributes ('character controller') does, as the
    schema says it, without the reference's backticks."""
    tag, _, attr = key.partition(' ')
    return (TAGS[tag].attrs[attr].doc if attr else TAGS[tag].doc).replace('`', '')


def _tag(name: str) -> tuple:
    """A tag name's class, link and tooltip: qg: tags have an entry of their own in the reference,
    the q: statements a section; anything else (Tiled's tags) is only coloured."""
    prefix, _, local = name.rpartition(':')
    if prefix == 'qg' and local in TAGS:
        return 't', f'{REFERENCE}#qg-{local}', local
    if prefix == 'q':
        return 'k', f'{REFERENCE}#statements' if local in STATEMENTS else None, None
    return 'g', None, None


def _expressions(text: str, cls) -> list:
    out, at = [], 0
    for m in _EXPR.finditer(text):
        if m.start() > at:
            out.append((cls, text[at:m.start()], None, None))
        out.append(('e', m.group(), None, None))
        at = m.end()
    if at < len(text):
        out.append((cls, text[at:], None, None))
    return out


def tokens(text: str) -> list:
    """An XML source (a .q, a .tmx) as (class, text, link, tooltip) runs that add up to it exactly."""
    out, at = [], 0
    for m in _XML.finditer(text):
        out += _expressions(text[at:m.start()], None)
        at = m.end()
        if m.group('comment') or m.group('pi'):
            out.append(('c' if m.group('comment') else 'p', m.group(), None, None))
            continue
        cls, href, tag = _tag(m.group('name'))
        out += [('b', m.group('open'), None, None), (cls, m.group('name'), href, tag)]
        attrs, a = m.group('attrs'), 0
        for am in _ATTR.finditer(attrs):
            out.append((None, attrs[a:am.start()], None, None))
            name = am.group('name')
            known = tag and name in TAGS[tag].attrs and TAGS[tag].attrs[name].doc
            href = f'{REFERENCE}#gd-attributes' if name.startswith('gd:') else None
            out += [('a', name, href, f'{tag} {name}' if known else None), ('o', am.group('eq'), None, None)]
            out += _expressions(am.group('value'), 'v')
            a = am.end()
        out += [(None, attrs[a:], None, None), ('b', m.group('close'), None, None)]
    out += _expressions(text[at:], None)
    return [t for t in out if t[1]]


def highlight(text: str, docs: dict) -> list:
    """The lines of an XML source as HTML, each closing what it opens. The tooltips the lines
    refer to are added to docs."""
    lines, line = [], []
    for cls, part, href, tip in tokens(text):
        if tip:
            docs[tip] = describe(tip)
        tip = f' data-t="{html.escape(tip)}"' if tip else ''
        for i, piece in enumerate(part.split('\n')):
            if i:
                lines.append(''.join(line))
                line = []
            if not piece:
                continue
            body = html.escape(piece, quote=False)
            if href:
                line.append(f'<a class="{cls}" href="{href}"{tip}>{body}</a>')
            elif cls and cls != 'o':
                line.append(f'<span class="{cls}"{tip}>{body}</span>')
            else:
                line.append(body)
    lines.append(''.join(line))
    if text.endswith('\n'):
        lines.pop()
    return lines


def write_source(name: str, title: str, folder: Path) -> Path:
    """<name>/source/index.html: every line of the game, highlighted and numbered (a line is a link:
    source/#L42), and a copy of each file to download next to it. A tag links to its entry in the
    language's reference; a tag or an attribute says what it does when pointed at, in the schema's
    own words, which are the reference's."""
    project = REPO / 'projects' / name
    out = folder / 'source'
    out.mkdir(parents=True, exist_ok=True)
    files = source_files(name)
    docs, sections, tabs = {}, [], []
    for i, path in enumerate(files):
        rel = path.relative_to(project).as_posix()
        text = path.read_text(encoding='utf-8')
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out / rel)
        prefix = re.sub(r'[^a-z0-9]+', '-', rel.lower()).strip('-') + '-' if i else ''
        lines = highlight(text, docs)
        body = ''.join(f'<span class="l" id="{prefix}L{n}"><a class="n" href="#{prefix}L{n}" data-n="{n}"></a>'
                       f'{line}</span>' for n, line in enumerate(lines, 1))
        sections.append(f"""<section class="file" id="{prefix or 'main-'}file">
<div class="bar"><strong>{html.escape(rel)}</strong><span class="info">{len(lines)} lines</span>
<button class="copy" type="button" hidden>Copy</button> <a href="{html.escape(rel)}" download>Download</a>
<a href="{GITHUB}projects/{name}/{html.escape(rel)}">On GitHub</a></div>
<pre><code>{body}</code></pre>
</section>""")
        tabs.append(f'<button type="button">{html.escape(rel)}</button>')
    used = sorted(set(re.findall(r'<qg:([a-z-]+)', files[0].read_text(encoding='utf-8'))) & set(TAGS))
    for tag in used:
        docs[tag] = describe(tag)
    chips = ' '.join(f'<a href="{REFERENCE}#qg-{tag}" data-t="{tag}">qg:{tag}</a>' for tag in used)
    rels = [f'<code>{html.escape(p.relative_to(project).as_posix())}</code>' for p in files]
    page = out / 'index.html'
    page.write_text(SOURCE_PAGE.format(
        title=html.escape(title), godot=GODOT_VERSION, reference=REFERENCE, used=len(used), tags=len(TAGS),
        files=rels[0] + (', with ' + ', '.join(rels[1:]) if rels[1:] else ''), chips=chips,
        play='<a class="play" href="../">Play in the browser</a>' if (folder / 'index.html').is_file() else '',
        tabs=''.join(tabs) if len(files) > 1 else '', sections='\n'.join(sections),
        docs=json.dumps(docs, sort_keys=True).replace('<', '\\u003c')), encoding='utf-8')
    return page


def write_index(out_root: Path) -> Path:
    """games/index.html: every game that is built under out_root, in the order of projects/games.json.

    Each game also gets <name>/source/, the page of its source (write_source). With a relay (projects/games.json's "relay", or QUANTUM_RELAY_URL: wss://relay.example), each
    networked game also has "Play online", which makes a room's link to send to a friend."""
    listing = json.loads((REPO / 'projects' / 'games.json').read_text(encoding='utf-8'))
    meta = listing['games']
    relay = (os.environ.get('QUANTUM_RELAY_URL') or listing.get('relay') or '').rstrip('/')
    cards = []
    for g in meta:
        name = g['name']
        folder = out_root / name
        if not folder.is_dir():
            continue
        shot = REPO / 'projects' / name / 'screenshot.png'
        if shot.is_file():
            shutil.copyfile(shot, folder / 'screenshot.png')
        links = []
        if (folder / 'index.html').is_file():
            links.append(f'<a class="play" href="{name}/">Play in the browser</a>')
            source = REPO / 'projects' / name / f'{name}.q'
            if relay and '<qg:multiplayer' in source.read_text(encoding='utf-8'):
                links.append(f'<a class="online" href="#" data-game="{name}" data-relay="{html.escape(relay)}">'
                             'Play online with a friend</a>')
        for preset, label in (('linux', 'Linux'), ('windows', 'Windows'), ('macos', 'macOS')):
            if (folder / f'{name}-{preset}.zip').is_file():
                links.append(f'<a href="{name}/{name}-{preset}.zip">{label}</a>')
        if (folder / f'{name}-android.apk').is_file():
            links.append(f'<a href="{name}/{name}-android.apk">Android</a>')
        write_source(name, g['title'], folder)
        links.append(f'<a class="source" href="{name}/source/">View the source</a>')
        img = (f'<a class="shot" href="{name}/"><img src="{name}/screenshot.png" alt="{html.escape(g["title"])}" '
               f'loading="lazy"></a>') if shot.is_file() else ''
        cards.append(f"""<article class="card" id="{name}">
{img}
<div class="body">
<div class="title"><h2>{html.escape(g['title'])}</h2><span class="badge">{html.escape(g['players'])}</span></div>
<p class="blurb">{html.escape(g['blurb'])}</p>
<p class="keys">{html.escape(g['controls'])}</p>
<div class="links">{' '.join(links)}</div>
<div class="room">Send this link to your friend (it is copied), then both choose Join:
<input readonly> <a href="#">Open the room</a></div>
</div>
</article>""")
    out_root.mkdir(parents=True, exist_ok=True)
    page = out_root / 'index.html'
    page.write_text(PAGE.format(godot=GODOT_VERSION, cards='\n'.join(cards)), encoding='utf-8')
    return page


def main(argv) -> int:
    if '--install-templates' in argv:
        i = argv.index('--install-templates')
        return install_templates(argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith('--') else '')
    all_games = games()
    names = [a for a in argv if not a.startswith('--') and a in all_games]
    presets = [argv[argv.index('--preset') + 1]] if '--preset' in argv else list(DEFAULT_PRESETS)
    out_root = Path(argv[argv.index('--out') + 1]) if '--out' in argv else REPO / 'docs' / 'public' / 'games'
    known = {a for a in argv if not a.startswith('--')} - set(all_games) - set(PRESETS) - {str(out_root)}
    known -= {argv[argv.index('--preset') + 1]} if '--preset' in argv else set()
    if known - {str(out_root)}:
        print(f'unknown game(s): {", ".join(sorted(known - {str(out_root)}))} (there are: {", ".join(all_games)})',
              file=sys.stderr)
        return 2
    try:
        godot = ensure_godot()
    except GodotNotFound as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    if not templates_dir().is_dir():
        print(f'error: Godot {GODOT_VERSION} export templates are not installed ({templates_dir()}): '
              f'python scripts/export-games.py --install-templates', file=sys.stderr)
        return 1
    manifest = {'godot': GODOT_VERSION, 'games': {}}
    for name in names or list(all_games):
        manifest['games'][name] = []
        for preset in presets:
            manifest['games'][name].append(export(name, all_games[name], preset, out_root, godot))
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / 'manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    print(f'the page: {write_index(out_root)}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
