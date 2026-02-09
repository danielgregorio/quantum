<q:component name="TerminalShowcase" type="page">
<html>
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Quantum Terminal Engine</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&amp;family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet"/>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: #0a0a0a;
      color: #e0e0e0;
      line-height: 1.6;
    }
    a { color: #a78bfa; text-decoration: none; }
    a:hover { color: #c4b5fd; }

    /* Hero */
    .hero {
      text-align: center;
      padding: 80px 20px 60px;
      background: linear-gradient(135deg, #0a0a0a 0%, #1a0a2e 50%, #0a0a0a 100%);
      border-bottom: 1px solid #1e1e2e;
    }
    .hero-badge {
      display: inline-block;
      padding: 4px 16px;
      border-radius: 999px;
      background: rgba(167, 139, 250, 0.15);
      border: 1px solid rgba(167, 139, 250, 0.3);
      color: #a78bfa;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 24px;
      font-family: 'JetBrains Mono', monospace;
    }
    .hero h1 {
      font-size: 48px;
      font-weight: 700;
      background: linear-gradient(135deg, #e0e0e0 0%, #a78bfa 50%, #7c3aed 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 16px;
    }
    .hero p {
      font-size: 18px;
      color: #888;
      max-width: 640px;
      margin: 0 auto 32px;
    }
    .hero-cmd {
      display: inline-block;
      background: #111;
      border: 1px solid #2a2a3a;
      border-radius: 8px;
      padding: 12px 24px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 14px;
      color: #a78bfa;
    }
    .hero-cmd .prompt { color: #4ade80; }
    .hero-cmd .flag { color: #facc15; }

    /* Pipeline */
    .pipeline {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 12px;
      margin: 32px auto 0;
      flex-wrap: wrap;
    }
    .pipeline-step {
      background: #111;
      border: 1px solid #2a2a3a;
      border-radius: 6px;
      padding: 8px 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: #ccc;
    }
    .pipeline-arrow { color: #a78bfa; font-size: 18px; }

    /* Stats */
    .stats {
      display: flex;
      justify-content: center;
      gap: 48px;
      padding: 40px 20px;
      border-bottom: 1px solid #1e1e2e;
    }
    .stat { text-align: center; }
    .stat-num {
      font-size: 32px;
      font-weight: 700;
      color: #a78bfa;
      font-family: 'JetBrains Mono', monospace;
    }
    .stat-label { font-size: 13px; color: #666; margin-top: 4px; }

    /* Content */
    .container { max-width: 1100px; margin: 0 auto; padding: 0 20px; }
    .section { padding: 60px 0; }
    .section-title {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
      color: #f0f0f0;
    }
    .section-desc {
      color: #888;
      margin-bottom: 40px;
      font-size: 15px;
    }

    /* Tag Reference */
    .tag-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 12px;
      margin-bottom: 48px;
    }
    .tag-item {
      background: #111;
      border: 1px solid #1e1e2e;
      border-radius: 8px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .tag-name {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: #7c3aed;
      white-space: nowrap;
    }
    .tag-widget {
      font-size: 12px;
      color: #666;
    }

    /* Example Cards */
    .examples-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .example-card {
      background: #111;
      border: 1px solid #1e1e2e;
      border-radius: 12px;
      overflow: hidden;
      transition: border-color 0.2s;
    }
    .example-card:hover { border-color: #a78bfa40; }
    .example-header {
      padding: 20px 24px 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
    .example-title { font-size: 18px; font-weight: 600; color: #f0f0f0; }
    .example-desc { font-size: 13px; color: #888; margin-top: 4px; }
    .example-badge {
      font-size: 11px;
      padding: 3px 10px;
      border-radius: 999px;
      background: rgba(74, 222, 128, 0.1);
      color: #4ade80;
      border: 1px solid rgba(74, 222, 128, 0.2);
      white-space: nowrap;
    }

    /* Tabs */
    .tab-bar {
      display: flex;
      border-bottom: 1px solid #1e1e2e;
      padding: 0 24px;
    }
    .tab-btn {
      background: none;
      border: none;
      color: #666;
      font-size: 13px;
      font-family: 'JetBrains Mono', monospace;
      padding: 10px 16px;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
    }
    .tab-btn:hover { color: #ccc; }
    .tab-btn.active { color: #a78bfa; border-bottom-color: #a78bfa; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Code Block */
    .code-block {
      background: #0a0a0a;
      padding: 16px 24px;
      max-height: 400px;
      overflow: auto;
    }
    .code-block pre {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      line-height: 1.7;
      color: #ccc;
      white-space: pre;
      margin: 0;
    }
    .code-block::-webkit-scrollbar { width: 6px; height: 6px; }
    .code-block::-webkit-scrollbar-track { background: transparent; }
    .code-block::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

    /* Download Button */
    .download-bar {
      padding: 12px 24px;
      border-top: 1px solid #1e1e2e;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
    .btn-download {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 16px;
      border-radius: 6px;
      background: #7c3aed;
      color: #fff;
      font-size: 13px;
      font-weight: 500;
      transition: background 0.2s;
      text-decoration: none;
    }
    .btn-download:hover { background: #6d28d9; color: #fff; }

    /* Widgets Reference Table */
    .widget-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    .widget-table th {
      text-align: left;
      padding: 12px 16px;
      border-bottom: 2px solid #2a2a3a;
      color: #a78bfa;
      font-weight: 600;
      font-size: 13px;
    }
    .widget-table td {
      padding: 10px 16px;
      border-bottom: 1px solid #1e1e2e;
    }
    .widget-table tr:hover td { background: #111; }
    .widget-table code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #7c3aed;
      background: rgba(124, 58, 237, 0.1);
      padding: 2px 6px;
      border-radius: 3px;
    }

    /* Footer */
    .footer {
      text-align: center;
      padding: 40px 20px;
      border-top: 1px solid #1e1e2e;
      color: #444;
      font-size: 13px;
    }

    /* Responsive */
    @media (max-width: 768px) {
      .hero h1 { font-size: 32px; }
      .stats { gap: 24px; flex-wrap: wrap; }
      .examples-grid { grid-template-columns: 1fr; }
      .tag-grid { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>

  <!-- Hero -->
  <section class="hero">
    <div class="hero-badge">q:application type="terminal"</div>
    <h1>Quantum Terminal Engine</h1>
    <p>Compile declarative XML into standalone Python TUI apps powered by Textual. No JavaScript. No browser. Pure terminal.</p>
    <div class="hero-cmd">
      <span class="prompt">$</span> quantum run dashboard.q <span class="flag">&#8594;</span> server-dashboard.py
    </div>
    <div class="pipeline">
      <span class="pipeline-step">.q (XML + qt: tags)</span>
      <span class="pipeline-arrow">&#8594;</span>
      <span class="pipeline-step">Parser</span>
      <span class="pipeline-arrow">&#8594;</span>
      <span class="pipeline-step">AST</span>
      <span class="pipeline-arrow">&#8594;</span>
      <span class="pipeline-step">TerminalCodeGenerator</span>
      <span class="pipeline-arrow">&#8594;</span>
      <span class="pipeline-step">.py (Textual App)</span>
    </div>
  </section>

  <!-- Stats -->
  <div class="stats">
    <div class="stat">
      <div class="stat-num">23</div>
      <div class="stat-label">qt: tags</div>
    </div>
    <div class="stat">
      <div class="stat-num">22</div>
      <div class="stat-label">AST nodes</div>
    </div>
    <div class="stat">
      <div class="stat-num">4</div>
      <div class="stat-label">examples</div>
    </div>
    <div class="stat">
      <div class="stat-num">49</div>
      <div class="stat-label">tests passing</div>
    </div>
  </div>

  <!-- Tag Reference -->
  <div class="container">
    <section class="section">
      <h2 class="section-title">Widget Tags</h2>
      <p class="section-desc">All qt: namespace tags available in the Terminal Engine, each mapping to a Textual widget.</p>
      <div class="tag-grid">
        <div class="tag-item"><span class="tag-name">qt:screen</span><span class="tag-widget">Screen</span></div>
        <div class="tag-item"><span class="tag-name">qt:panel</span><span class="tag-widget">Vertical + border</span></div>
        <div class="tag-item"><span class="tag-name">qt:layout</span><span class="tag-widget">Horizontal / Vertical</span></div>
        <div class="tag-item"><span class="tag-name">qt:table</span><span class="tag-widget">DataTable</span></div>
        <div class="tag-item"><span class="tag-name">qt:column</span><span class="tag-widget">add_column()</span></div>
        <div class="tag-item"><span class="tag-name">qt:input</span><span class="tag-widget">Input</span></div>
        <div class="tag-item"><span class="tag-name">qt:button</span><span class="tag-widget">Button</span></div>
        <div class="tag-item"><span class="tag-name">qt:menu</span><span class="tag-widget">OptionList</span></div>
        <div class="tag-item"><span class="tag-name">qt:option</span><span class="tag-widget">Item</span></div>
        <div class="tag-item"><span class="tag-name">qt:text</span><span class="tag-widget">Static (Rich)</span></div>
        <div class="tag-item"><span class="tag-name">qt:progress</span><span class="tag-widget">ProgressBar</span></div>
        <div class="tag-item"><span class="tag-name">qt:tree</span><span class="tag-widget">Tree</span></div>
        <div class="tag-item"><span class="tag-name">qt:tabs</span><span class="tag-widget">TabbedContent</span></div>
        <div class="tag-item"><span class="tag-name">qt:tab</span><span class="tag-widget">TabPane</span></div>
        <div class="tag-item"><span class="tag-name">qt:log</span><span class="tag-widget">RichLog</span></div>
        <div class="tag-item"><span class="tag-name">qt:header</span><span class="tag-widget">Header</span></div>
        <div class="tag-item"><span class="tag-name">qt:footer</span><span class="tag-widget">Footer</span></div>
        <div class="tag-item"><span class="tag-name">qt:status</span><span class="tag-widget">Static</span></div>
        <div class="tag-item"><span class="tag-name">qt:keybinding</span><span class="tag-widget">Binding</span></div>
        <div class="tag-item"><span class="tag-name">qt:timer</span><span class="tag-widget">set_interval()</span></div>
        <div class="tag-item"><span class="tag-name">qt:service</span><span class="tag-widget">Async worker</span></div>
        <div class="tag-item"><span class="tag-name">qt:css</span><span class="tag-widget">TCSS block</span></div>
        <div class="tag-item"><span class="tag-name">qt:on</span><span class="tag-widget">Event handler</span></div>
      </div>

      <!-- Examples -->
      <h2 class="section-title">Examples</h2>
      <p class="section-desc">Each example compiles from a .q file into a standalone Python app. Download and run with <code style="font-family: 'JetBrains Mono', monospace; background: #1a1a2e; padding: 2px 8px; border-radius: 4px; color: #a78bfa;">pip install textual &amp;&amp; python app.py</code></p>

      <div class="examples-grid">

        <!-- Dashboard -->
        <div class="example-card" id="card-dashboard">
          <div class="example-header">
            <div>
              <div class="example-title">Server Dashboard</div>
              <div class="example-desc">CPU monitor, process table, auto-refresh timer</div>
            </div>
            <span class="example-badge">dashboard.q</span>
          </div>
          <div class="tab-bar">
            <button class="tab-btn active" onclick="showTab('dashboard','q')">dashboard.q</button>
            <button class="tab-btn" onclick="showTab('dashboard','py')">server-dashboard.py</button>
          </div>
          <div id="dashboard-q" class="tab-content active"><div class="code-block"><pre>&lt;q:application id="server-dashboard" type="terminal"&gt;
  &lt;qt:css&gt;
    #cpu-panel { border: solid green; height: 1fr; }
    #log-panel { border: solid yellow; height: 2fr; }
  &lt;/qt:css&gt;

  &lt;qt:screen name="main" title="Server Dashboard"&gt;
    &lt;qt:header title="Server Dashboard" show-clock="true"/&gt;
    &lt;q:set name="refresh_count" type="number" value="0"/&gt;
    &lt;q:set name="cpu_pct" type="number" value="42"/&gt;

    &lt;qt:layout direction="horizontal"&gt;
      &lt;qt:panel id="cpu-panel" title="CPU Usage"&gt;
        &lt;qt:progress id="cpu-bar" total="100" value-var="cpu_pct"/&gt;
        &lt;qt:text&gt;{cpu_pct}% used&lt;/qt:text&gt;
      &lt;/qt:panel&gt;
    &lt;/qt:layout&gt;

    &lt;qt:panel id="log-panel" title="Processes"&gt;
      &lt;qt:table id="proc-table" zebra="true"&gt;
        &lt;qt:column name="PID" key="pid" width="10"/&gt;
        &lt;qt:column name="Process" key="name" width="30"/&gt;
        &lt;qt:column name="CPU %" key="cpu_percent" align="right"/&gt;
      &lt;/qt:table&gt;
    &lt;/qt:panel&gt;

    &lt;qt:footer/&gt;
    &lt;qt:keybinding key="q" action="quit" description="Quit"/&gt;
    &lt;qt:keybinding key="r" action="refresh_data" description="Refresh"/&gt;
    &lt;qt:timer id="auto-refresh" interval="5.0" action="refresh_data"/&gt;
  &lt;/qt:screen&gt;
&lt;/q:application&gt;</pre></div></div>
          <div id="dashboard-py" class="tab-content"><div class="code-block"><pre>#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, ProgressBar
from textual.binding import Binding
from textual.reactive import reactive

class server_dashboardApp(App):
    TITLE = "server-dashboard"
    CSS = """
      #cpu-panel { border: solid green; height: 1fr; }
      #log-panel { border: solid yellow; height: 2fr; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_data", "Refresh"),
    ]
    refresh_count = reactive(0.0)
    cpu_pct = reactive(42.0)

    def compose(self) -&gt; ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="cpu-panel"):
                yield ProgressBar(total=100.0, id="cpu-bar")
                yield Static("{cpu_pct}% used")
        with Vertical(id="log-panel"):
            yield DataTable(id="proc-table", zebra_stripes=True)
        yield Footer()

    def on_mount(self):
        self.set_interval(5.0, self.action_refresh_data)

    def action_refresh_data(self):
        self.notify("Action: refresh_data")

if __name__ == "__main__":
    app = server_dashboardApp()
    app.run()</pre></div></div>
          <div class="download-bar">
            <a class="btn-download" href="/terminal/static/server-dashboard.py" download="download">Download .py</a>
          </div>
        </div>

        <!-- Chat -->
        <div class="example-card" id="card-chat">
          <div class="example-header">
            <div>
              <div class="example-title">LLM Chat</div>
              <div class="example-desc">Chat interface with RichLog, input + button</div>
            </div>
            <span class="example-badge">chat-tui.q</span>
          </div>
          <div class="tab-bar">
            <button class="tab-btn active" onclick="showTab('chat','q')">chat-tui.q</button>
            <button class="tab-btn" onclick="showTab('chat','py')">llm-chat.py</button>
          </div>
          <div id="chat-q" class="tab-content active"><div class="code-block"><pre>&lt;q:application id="llm-chat" type="terminal"&gt;
  &lt;qt:css&gt;
    #chat-log { height: 1fr; border: solid #444; }
    #input-bar { dock: bottom; height: 3; }
  &lt;/qt:css&gt;

  &lt;qt:screen name="chat" title="Quantum Chat"&gt;
    &lt;qt:header title="Quantum Chat - Ollama"/&gt;
    &lt;q:set name="model" value="llama3"/&gt;
    &lt;q:set name="history" type="array" value="[]"/&gt;

    &lt;qt:log id="chat-log" auto-scroll="true" markup="true"/&gt;
    &lt;qt:layout direction="horizontal" id="input-bar"&gt;
      &lt;qt:input id="user-input" placeholder="Type a message..."
               on-submit="send_message"/&gt;
      &lt;qt:button id="send-btn" label="Send" variant="primary"
                on-click="send_message"/&gt;
    &lt;/qt:layout&gt;

    &lt;qt:footer/&gt;
    &lt;qt:keybinding key="ctrl+c" action="quit" description="Quit"/&gt;

    &lt;q:function name="send_message"&gt;
      &lt;q:set name="placeholder" value="send_message action"/&gt;
    &lt;/q:function&gt;
  &lt;/qt:screen&gt;
&lt;/q:application&gt;</pre></div></div>
          <div id="chat-py" class="tab-content"><div class="code-block"><pre>#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Button, Input, RichLog
from textual.binding import Binding
from textual.reactive import reactive

class llm_chatApp(App):
    TITLE = "llm-chat"
    CSS = """
      #chat-log { height: 1fr; border: solid #444; }
      #input-bar { dock: bottom; height: 3; }
    """
    BINDINGS = [Binding("ctrl+c", "quit", "Quit")]
    model = reactive("llama3")
    history = reactive([])

    def compose(self) -&gt; ComposeResult:
        yield Header()
        yield RichLog(id="chat-log")
        with Horizontal(id="input-bar"):
            yield Input(placeholder="Type a message...", id="user-input")
            yield Button("Send", variant="primary", id="send-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "send-btn":
            self.action_send_message()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "user-input":
            self.action_send_message()

    def send_message(self):
        self.placeholder = "send_message action"

    def action_send_message(self):
        self.send_message()

if __name__ == "__main__":
    app = llm_chatApp()
    app.run()</pre></div></div>
          <div class="download-bar">
            <a class="btn-download" href="/terminal/static/llm-chat.py" download="download">Download .py</a>
          </div>
        </div>

        <!-- Adventure -->
        <div class="example-card" id="card-adventure">
          <div class="example-header">
            <div>
              <div class="example-title">Dungeon Quest</div>
              <div class="example-desc">Text adventure with rooms, inventory tree, HP</div>
            </div>
            <span class="example-badge">adventure.q</span>
          </div>
          <div class="tab-bar">
            <button class="tab-btn active" onclick="showTab('adventure','q')">adventure.q</button>
            <button class="tab-btn" onclick="showTab('adventure','py')">dungeon-quest.py</button>
          </div>
          <div id="adventure-q" class="tab-content active"><div class="code-block"><pre>&lt;q:application id="dungeon-quest" type="terminal"&gt;
  &lt;qt:css&gt;
    #room-desc { height: 1fr; border: solid #666; padding: 1 2; }
    #inventory-panel { width: 30; border: solid yellow; }
  &lt;/qt:css&gt;

  &lt;qt:screen name="game" title="Dungeon Quest"&gt;
    &lt;qt:header title="Dungeon Quest"/&gt;
    &lt;q:set name="current_room" value="entrance"/&gt;
    &lt;q:set name="inventory" type="array" value="[]"/&gt;
    &lt;q:set name="hp" type="number" value="100"/&gt;

    &lt;qt:layout direction="horizontal"&gt;
      &lt;qt:panel id="room-desc" title="Room"&gt;
        &lt;qt:text id="room-text"&gt;You stand at the entrance...&lt;/qt:text&gt;
      &lt;/qt:panel&gt;
      &lt;qt:panel id="inventory-panel" title="Inventory"&gt;
        &lt;qt:text id="hp-display"&gt;[bold red]HP: {hp}/100[/]&lt;/qt:text&gt;
        &lt;qt:tree id="inv-tree" label="Backpack"/&gt;
      &lt;/qt:panel&gt;
    &lt;/qt:layout&gt;

    &lt;qt:log id="action-log" max-lines="50"/&gt;
    &lt;qt:input id="cmd" placeholder="go north, take key, look..."
             on-submit="process_command"/&gt;
    &lt;qt:footer/&gt;
    &lt;qt:keybinding key="q" action="quit" description="Quit"/&gt;
  &lt;/qt:screen&gt;
&lt;/q:application&gt;</pre></div></div>
          <div id="adventure-py" class="tab-content"><div class="code-block"><pre>#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Tree, RichLog
from textual.binding import Binding
from textual.reactive import reactive

class dungeon_questApp(App):
    TITLE = "dungeon-quest"
    CSS = """
      #room-desc { height: 1fr; border: solid #666; padding: 1 2; }
      #inventory-panel { width: 30; border: solid yellow; }
    """
    BINDINGS = [Binding("q", "quit", "Quit")]
    current_room = reactive("entrance")
    inventory = reactive([])
    hp = reactive(100.0)

    def compose(self) -&gt; ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="room-desc"):
                yield Static("You stand at the entrance...", id="room-text")
            with Vertical(id="inventory-panel"):
                yield Static("[bold red]HP: {hp}/100[/]", id="hp-display")
                yield Tree("Backpack", id="inv-tree")
        yield RichLog(max_lines=50, id="action-log")
        yield Input(placeholder="go north, take key, look...", id="cmd")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "cmd":
            self.action_process_command()

    def process_command(self):
        self.placeholder = "process_command action"

    def action_process_command(self):
        self.process_command()

if __name__ == "__main__":
    app = dungeon_questApp()
    app.run()</pre></div></div>
          <div class="download-bar">
            <a class="btn-download" href="/terminal/static/dungeon-quest.py" download="download">Download .py</a>
          </div>
        </div>

        <!-- File Browser -->
        <div class="example-card" id="card-filebrowser">
          <div class="example-header">
            <div>
              <div class="example-title">File Browser</div>
              <div class="example-desc">Directory tree with file preview panel</div>
            </div>
            <span class="example-badge">filebrowser.q</span>
          </div>
          <div class="tab-bar">
            <button class="tab-btn active" onclick="showTab('filebrowser','q')">filebrowser.q</button>
            <button class="tab-btn" onclick="showTab('filebrowser','py')">file-browser.py</button>
          </div>
          <div id="filebrowser-q" class="tab-content active"><div class="code-block"><pre>&lt;q:application id="file-browser" type="terminal"&gt;
  &lt;qt:css&gt;
    #file-tree { width: 40; border: solid green; }
    #preview { height: 1fr; border: solid #444; }
  &lt;/qt:css&gt;

  &lt;qt:screen name="browser" title="File Browser"&gt;
    &lt;qt:header title="Quantum File Browser"/&gt;
    &lt;qt:layout direction="horizontal"&gt;
      &lt;qt:tree id="file-tree" label="."
              on-select="on_file_select"/&gt;
      &lt;qt:panel id="preview" title="Preview"&gt;
        &lt;qt:text id="file-content"&gt;Select a file...&lt;/qt:text&gt;
      &lt;/qt:panel&gt;
    &lt;/qt:layout&gt;
    &lt;qt:footer/&gt;
    &lt;qt:keybinding key="q" action="quit" description="Quit"/&gt;
    &lt;qt:keybinding key="r" action="refresh_tree" description="Refresh"/&gt;
  &lt;/qt:screen&gt;
&lt;/q:application&gt;</pre></div></div>
          <div id="filebrowser-py" class="tab-content"><div class="code-block"><pre>#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Tree
from textual.binding import Binding

class file_browserApp(App):
    TITLE = "file-browser"
    CSS = """
      #file-tree { width: 40; border: solid green; }
      #preview { height: 1fr; border: solid #444; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_tree", "Refresh"),
    ]

    def compose(self) -&gt; ComposeResult:
        yield Header()
        with Horizontal():
            yield Tree(".", id="file-tree")
            with Vertical(id="preview"):
                yield Static("Select a file...", id="file-content")
        yield Footer()

    def action_refresh_tree(self):
        self.notify("Action: refresh_tree")

if __name__ == "__main__":
    app = file_browserApp()
    app.run()</pre></div></div>
          <div class="download-bar">
            <a class="btn-download" href="/terminal/static/file-browser.py" download="download">Download .py</a>
          </div>
        </div>

      </div>
    </section>
  </div>

  <!-- Footer -->
  <div class="footer">
    Quantum Terminal Engine &#183; Built with the Quantum Framework &#183; Powered by <a href="https://textual.textualize.io" target="_blank">Textual</a>
  </div>

  <script>
  function showTab(card, tab) {
    // Hide all tabs for this card
    document.querySelectorAll('#card-' + card + ' .tab-content').forEach(function(el) {
      el.classList.remove('active');
    });
    document.querySelectorAll('#card-' + card + ' .tab-btn').forEach(function(el) {
      el.classList.remove('active');
    });
    // Show selected
    document.getElementById(card + '-' + tab).classList.add('active');
    // Activate button
    var btns = document.querySelectorAll('#card-' + card + ' .tab-btn');
    btns.forEach(function(b) {
      if ((tab === 'q' &amp;&amp; b.textContent.includes('.q')) || (tab === 'py' &amp;&amp; b.textContent.includes('.py'))) {
        b.classList.add('active');
      }
    });
  }
  </script>

</body>
</html>
</q:component>
