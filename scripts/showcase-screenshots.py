"""Screenshots of the proving apps for docs/showcase, taken from the real running apps.

    python scripts/showcase-screenshots.py            # every app
    python scripts/showcase-screenshots.py blog       # one or more by name

Each app is copied to a temporary folder (its database, logs and uploads go
there, never into the repository), migrated, and started with `quantum start`
on a free port. Playwright opens it in Chromium, does what the app is for, and
saves docs/public/showcase/<app>.png, the only files this script writes. The
AI apps talk to tests/fake_ollama.py, so no model server is needed and the
screenshots are the same on every run.

Needs: pip install playwright && python -m playwright install chromium
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'docs' / 'public' / 'showcase'
sys.path.insert(0, str(REPO))


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_until_up(url, proc, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f'the app exited with {proc.returncode}')
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f'{url} did not answer in {timeout}s')


def stop(proc):
    """Stops the server this script started, with its reloader child if any."""
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
    else:
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=10)


# -- the fake model's answers ------------------------------------------------

def docs_answer(messages):
    return ('Add paginate="true" and a page_size to the q:query, then put a '
            'ui:pager under the table: it draws the page links [1].')


def keyword_embed(words):
    """Embeddings for the docs assistant's screenshot: the fake server's own
    bag of words, plus the question's key words weighted far above the rest.
    The chunks of the guide about the question are then the relevant ones, as
    a real embedding model would find them, and the app's relevance threshold
    (IA-9) behaves as it does live. Every chunk keeps a distinct vector: many
    identical ones make the vector index's search unreliable."""
    import math
    import re
    from tests.fake_ollama import embed as bag_of_words

    def embed(text):
        found = re.findall(r'[a-z_]+', text.lower())
        vector = bag_of_words(text) + [10.0 * found.count(w) for w in words]
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
    return embed


def shop_script():
    """First ask for the tool, then answer from its rows (the agent's protocol)."""
    calls = {'n': 0}

    def reply(messages):
        calls['n'] += 1
        if calls['n'] == 1:
            return json.dumps({'action': 'low_stock', 'args': {'below': '5'}})
        return json.dumps({'action': 'finish',
                           'result': 'Three products are almost out: paper filters, '
                                     'the pour-over kettle and the grinder.'})
    return reply


# -- what each screenshot shows ----------------------------------------------

def open_path(path):
    def scene(page, base):
        page.goto(base + path)
        page.wait_for_load_state('networkidle')
    return scene


def chat(page, base):
    page.goto(base + '/')
    page.fill('input[name="username"]', 'Ana')
    page.click('button.btn-join')
    page.wait_for_load_state('networkidle')
    for text in ('Hi! Is the release notes page up?', 'It is: the changelog is on the site.'):
        page.fill('input[name="message"]', text)
        page.click('button.btn-send')
        page.wait_for_load_state('networkidle')


def helpdesk(page, base):
    page.goto(base + '/')
    page.fill('input[name="title"]', 'Export to CSV cuts accents')
    page.fill('input[name="email"]', 'ana@example.com')
    page.fill('textarea[name="description"]', 'Names like José come out as Jos? in the exported file.')
    page.click('button:has-text("Open ticket")')
    page.wait_for_load_state('networkidle')
    page.goto(base + '/')
    page.wait_for_load_state('networkidle')


def bank(page, base):
    page.goto(base + '/')
    page.fill('input[name="from_account"]', '1')
    page.fill('input[name="to_account"]', '3')
    page.fill('input[name="amount"]', '25')
    page.click('button:has-text("Transfer")')
    page.wait_for_load_state('networkidle')


APPS = {
    'tarefas': {'scene': open_path('/')},
    'blog': {'scene': open_path('/')},
    'helpdesk': {'scene': helpdesk},
    'bank-transfer': {'scene': bank},
    'docs-assistant': {'scene': open_path('/?q=How+do+I+paginate+a+query%3F'),
                       'model': lambda: docs_answer, 'guide': True,
                       'embed': keyword_embed(['paginate', 'page_size', 'pager'])},
    'shop-agent': {'scene': open_path('/?q=Which+products+are+almost+out%3F'),
                   'model': shop_script},
    'quantum-chat': {'scene': chat},
}


def shoot(name, browser):
    spec = APPS[name]
    source = REPO / 'projects' / name
    with tempfile.TemporaryDirectory(prefix=f'showcase-{name}-') as tmp:
        root = Path(tmp)
        app = root / 'projects' / name
        shutil.copytree(source, app, ignore=shutil.ignore_patterns('data', '.quantum', '__pycache__', '*.db'))
        if spec.get('guide'):                                 # the docs assistant indexes docs/guide
            shutil.copytree(REPO / 'docs' / 'guide', root / 'docs' / 'guide')
        env = dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8')

        if (app / 'migrations').is_dir():
            subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'migrate', 'up'],
                           cwd=app, env=env, check=True, capture_output=True)

        model = None
        if spec.get('model'):
            import tests.fake_ollama as fake
            if spec.get('embed'):
                fake.embed = spec['embed']        # the fake server runs in this process
            model = fake.FakeOllama().__enter__()
            model.reply = spec['model']()
            env['QUANTUM_LLM_BASE_URL'] = model.url

        port = free_port()
        proc = subprocess.Popen(
            [sys.executable, '-m', 'quantum.cli.runner', 'start', '--port', str(port)],
            cwd=app, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=(os.name != 'nt'))
        try:
            base = f'http://127.0.0.1:{port}'
            wait_until_up(base + '/', proc)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            spec['scene'](page, base)
            OUT.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(OUT / f'{name}.png'))
            page.close()
        finally:
            stop(proc)
            if model is not None:
                model.__exit__(None, None, None)
    print(f'  {name}.png')


def main(names):
    from playwright.sync_api import sync_playwright
    unknown = [n for n in names if n not in APPS]
    if unknown:
        sys.exit(f'unknown app(s): {", ".join(unknown)}; known: {", ".join(APPS)}')
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for name in names or list(APPS):
                shoot(name, browser)
        finally:
            browser.close()


if __name__ == '__main__':
    main(sys.argv[1:])
