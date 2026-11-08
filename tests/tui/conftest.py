"""The TUI's tests (SPEC.md UI-20): a small application served on a local port, and the TUI headless on it."""

import logging
import shutil
import sqlite3
import threading
from pathlib import Path

import pytest

HERE = Path(__file__).parent
NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

INDEX = f'''<q:component name="Fruits" {NS}>
  <q:set name="q" value="{{query.q}}" default="" />
  <q:action name="send" method="POST">
    <q:param name="doc" type="file" required="true" accept=".txt" />
    <q:file action="upload" file="{{doc}}" result="saved" />
    <q:redirect url="/" flash="Got {{saved.filename}}" />
  </q:action>
  <q:query name="fruits" datasource="db">
    SELECT id, name, stock FROM fruits WHERE (:q = '' OR name LIKE '%' || :q || '%') ORDER BY id
    <q:param name="q" value="{{q}}" type="string" />
  </q:query>
  <ui:window title="Fruits">
    <q:if condition="flash"><ui:alert>{{flash}}</ui:alert></q:if>
    <ui:input bind="q" search="fruits" delay="150" placeholder="Search" />
    <ui:table source="{{fruits}}" edit="fruits" datasource="db" id="fruits">
      <ui:column key="name" label="Name" /><ui:column key="stock" label="Stock" /><ui:column key="id" label="#" edit="false" />
    </ui:table>
    <ui:panel title="日本の果物">
      <ui:text>りんご と みかん 🍎</ui:text>
    </ui:panel>
    <ui:image src="/static/brick.png" alt="Brick" />
    <ui:form on-submit="send" submit="Send">
      <ui:input bind="doc" type="file" />
    </ui:form>
    <ui:accordion><ui:text>Folded</ui:text></ui:accordion>
  </ui:window>
</q:component>'''

LONG = f'''<q:component name="Long" {NS}>
  <ui:window title="Long" transition="slide">
    <q:loop type="range" var="i" from="1" to="80"><ui:text>Line {{i}}</ui:text></q:loop>
    <ui:input bind="last" enter="fade" placeholder="At the end" />
  </ui:window>
</q:component>'''


@pytest.fixture
def godot():
    from tests.apps.ui_drivers import tui_godot
    return tui_godot()


@pytest.fixture
def app_url(tmp_path, monkeypatch):
    """The fruits application, served; its base URL."""
    project = tmp_path / 'fruits'
    (project / 'components').mkdir(parents=True)
    (project / 'static').mkdir()
    (project / 'uploads').mkdir()
    shutil.copy(HERE / 'brick.png', project / 'static' / 'brick.png')
    (project / 'components' / 'index.q').write_text(INDEX, encoding='utf-8')
    (project / 'components' / 'long.q').write_text(LONG, encoding='utf-8')
    db = sqlite3.connect(project / 'fruits.db')
    db.executescript("CREATE TABLE fruits (id INTEGER PRIMARY KEY, name TEXT NOT NULL, stock INTEGER NOT NULL);"
                     "INSERT INTO fruits (name, stock) VALUES ('Apple', 4), ('Banana', 7), ('Cherry', 2);")
    db.close()
    (project / 'quantum.config.yaml').write_text(
        'server:\n  debug: false\npaths:\n  components: ./components\n  static: ./static\n  uploads: ./uploads\n'
        'datasources:\n  db:\n    driver: sqlite\n    database: ./fruits.db\n'
        'logging:\n  level: ERROR\n  console: false\n  file: false\n', encoding='utf-8')
    monkeypatch.chdir(project)
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    server = make_server('127.0.0.1', 0, QuantumWebServer(str(project / 'quantum.config.yaml')).app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_port}/', project
    server.shutdown()
    logging.disable(logging.NOTSET)
