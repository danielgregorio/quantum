"""The TUI's tests (SPEC.md UI-20): a small application served on a local port, and the TUI headless on it."""

import json
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
  </ui:window>
</q:component>'''

LONG = f'''<q:component name="Long" {NS}>
  <ui:window title="Long" transition="slide">
    <q:loop type="range" var="i" from="1" to="80"><ui:text>Line {{i}}</ui:text></q:loop>
    <ui:input bind="last" enter="fade" placeholder="At the end" />
  </ui:window>
</q:component>'''


LAYERS = f'''<q:component name="Layers" {NS}>
  <ui:window title="Layers">
    <ui:modal title="Hello" open="true"><ui:text>In the modal</ui:text></ui:modal>
    <ui:toast message="Kept" duration="0" position="bottom-right" />
    <ui:tooltip content="Type a name"><ui:input bind="name" /></ui:tooltip>
    <ui:carousel auto-play="true" interval="500" loop="false">
      <ui:slide><ui:text>One</ui:text></ui:slide><ui:slide><ui:text>Two</ui:text></ui:slide>
    </ui:carousel>
    <q:loop type="range" var="i" from="1" to="60"><ui:text>Row {{i}}</ui:text></q:loop>
  </ui:window>
</q:component>'''


# UI-21: a calendar's weeks from Monday with their numbers, and the days that cannot be picked
DATES = f'''<q:component name="Dates" {NS}>
  <ui:window title="Dates">
    <ui:calendar bind="day" value="2026-03-04" min-date="2026-03-03" max-date="2026-04-10"
                 disabled-dates="2026-03-12" disabled-days="0,6" first-day-of-week="1" show-week-numbers="true" />
  </ui:window>
</q:component>'''


def with_a_kind_none_draws(app):
    """UI-7: /hologram is a page whose view names a kind no renderer knows (a newer server's; every ui:* tag is
    drawn, UI_PARITY.md), for the test that the TUI says so instead of drawing something else in its place."""
    def serve(environ, start_response):
        if environ.get('PATH_INFO') != '/hologram':
            return app(environ, start_response)
        body = json.dumps({'title': 'Hologram', 'flash': '', 'flashType': '', 'flashShown': False, 'motion': False,
                           'view': [{'type': 'hologram', 'props': {}, 'children': []},
                                    {'type': 'text', 'props': {'text': 'Still drawn'}, 'children': []}]}).encode()
        start_response('200 OK', [('Content-Type', 'application/vnd.quantum.view+json'),
                                   ('Content-Length', str(len(body)))])
        return [body]
    return serve


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
    (project / 'components' / 'layers.q').write_text(LAYERS, encoding='utf-8')
    (project / 'components' / 'dates.q').write_text(DATES, encoding='utf-8')
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
    app = with_a_kind_none_draws(QuantumWebServer(str(project / 'quantum.config.yaml')).app)
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_port}/', project
    server.shutdown()
    logging.disable(logging.NOTSET)
