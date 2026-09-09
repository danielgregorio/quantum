/**
 * Quantum Playground - Main JavaScript
 *
 * Handles:
 * - Pyodide loading and execution
 * - CodeMirror editor setup
 * - Live preview updates
 * - Example loading
 * - Share/download functionality
 */

// Global state
let pyodide = null;
let editor = null;
let previewMode = 'rendered'; // 'rendered' or 'source'
let debounceTimer = null;

// Example templates
const EXAMPLES = {
    hello: `<!-- Hello World Component -->
<q:component name="HelloWorld">
  <h1>Hello, Quantum!</h1>
  <p>Welcome to the Quantum Framework playground.</p>
</q:component>`,

    variables: `<!-- Variables and Databinding -->
<q:component name="Variables">
  <q:set name="title" value="Quantum Framework" />
  <q:set name="version" type="number" value="1" />
  <q:set name="description" value="A declarative web framework" />

  <div class="card">
    <h1>{title}</h1>
    <p>Version: {version}</p>
    <p>{description}</p>
  </div>
</q:component>`,

    loop: `<!-- Loop Example (Range) -->
<q:component name="RangeLoop">
  <q:set name="title" value="Counting to 5" />

  <h2>{title}</h2>
  <ul>
    <q:loop type="range" var="i" from="1" to="5">
      <li>Number {i}</li>
    </q:loop>
  </ul>
</q:component>`,

    'loop-array': `<!-- Loop Example (Array) -->
<q:component name="ArrayLoop">
  <q:set name="fruits" type="array" value="Apple,Banana,Cherry,Date,Elderberry" />

  <h2>Fruit List</h2>
  <ul>
    <q:loop type="list" var="fruit" items="{fruits}" index="idx">
      <li>{idx}: {fruit}</li>
    </q:loop>
  </ul>
</q:component>`,

    conditional: `<!-- Conditionals -->
<q:component name="Conditionals">
  <q:set name="score" type="number" value="85" />
  <q:set name="name" value="Alice" />

  <h2>Grade Report for {name}</h2>
  <p>Score: {score}</p>

  <q:if condition="score >= 90">
    <p class="grade-a">Grade: A - Excellent!</p>
  </q:if>

  <q:if condition="score >= 80">
    <q:if condition="score < 90">
      <p class="grade-b">Grade: B - Good job!</p>
    </q:if>
  </q:if>

  <q:if condition="score < 80">
    <p class="grade-c">Grade: C or below - Keep practicing!</p>
  </q:if>
</q:component>`,

    'html-elements': `<!-- HTML Elements -->
<q:component name="HTMLElements">
  <q:set name="imageUrl" value="https://via.placeholder.com/150" />
  <q:set name="linkText" value="Visit Quantum Docs" />

  <style>
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .card { background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 12px 0; }
    .btn { background: #3b82f6; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
    .btn:hover { background: #2563eb; }
  </style>

  <div class="container">
    <h1>HTML Elements Demo</h1>

    <div class="card">
      <h3>Image</h3>
      <img src="{imageUrl}" alt="Placeholder" />
    </div>

    <div class="card">
      <h3>Button</h3>
      <button class="btn">Click Me</button>
    </div>

    <div class="card">
      <h3>Link</h3>
      <a href="https://quantum.dev">{linkText}</a>
    </div>

    <div class="card">
      <h3>Form Elements</h3>
      <input type="text" placeholder="Enter your name" />
      <br /><br />
      <select>
        <option>Option 1</option>
        <option>Option 2</option>
        <option>Option 3</option>
      </select>
    </div>
  </div>
</q:component>`,

    counter: `<!-- Counter App -->
<q:component name="Counter">
  <q:set name="count" type="number" value="0" />
  <q:set name="step" type="number" value="1" />

  <style>
    .counter-app { text-align: center; padding: 40px; font-family: sans-serif; }
    .counter-value { font-size: 72px; font-weight: bold; color: #3b82f6; margin: 20px 0; }
    .counter-label { color: #666; margin-bottom: 20px; }
    .counter-buttons { display: flex; gap: 12px; justify-content: center; }
    .btn { padding: 12px 24px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; }
    .btn-dec { background: #ef4444; color: white; }
    .btn-inc { background: #22c55e; color: white; }
    .btn-reset { background: #6b7280; color: white; }
  </style>

  <div class="counter-app">
    <h1>Quantum Counter</h1>
    <p class="counter-label">Current count (step: {step})</p>
    <div class="counter-value">{count}</div>
    <div class="counter-buttons">
      <button class="btn btn-dec">- Decrease</button>
      <button class="btn btn-reset">Reset</button>
      <button class="btn btn-inc">+ Increase</button>
    </div>
    <p style="margin-top: 20px; color: #999;">
      Note: Interactivity requires server-side execution.
      This is a static preview.
    </p>
  </div>
</q:component>`,

    todo: `<!-- Todo List -->
<q:component name="TodoList">
  <q:set name="todos" type="array" value="Learn Quantum,Build an app,Deploy to production" />
  <q:set name="title" value="My Todo List" />

  <style>
    .todo-app { max-width: 500px; margin: 0 auto; padding: 20px; font-family: sans-serif; }
    .todo-header { margin-bottom: 20px; }
    .todo-input { display: flex; gap: 8px; margin-bottom: 20px; }
    .todo-input input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }
    .todo-input button { padding: 12px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; }
    .todo-list { list-style: none; padding: 0; }
    .todo-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #f5f5f5; border-radius: 6px; margin-bottom: 8px; }
    .todo-item input[type="checkbox"] { width: 20px; height: 20px; }
    .todo-item span { flex: 1; }
    .todo-count { color: #666; font-size: 14px; margin-top: 16px; }
  </style>

  <div class="todo-app">
    <div class="todo-header">
      <h1>{title}</h1>
    </div>

    <div class="todo-input">
      <input type="text" placeholder="Add a new todo..." />
      <button>Add</button>
    </div>

    <ul class="todo-list">
      <q:loop type="list" var="todo" items="{todos}" index="i">
        <li class="todo-item">
          <input type="checkbox" />
          <span>{todo}</span>
          <button style="background: #ef4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">Delete</button>
        </li>
      </q:loop>
    </ul>

    <p class="todo-count">3 items in list</p>
  </div>
</q:component>`
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);

async function init() {
    // Setup editor
    setupEditor();

    // Setup event listeners
    setupEventListeners();

    // Load from URL if shared code exists
    loadFromURL();

    // Load Pyodide
    await loadPyodide();
}

function setupEditor() {
    const textarea = document.getElementById('editor');

    // Initialize CodeMirror
    editor = CodeMirror.fromTextArea(textarea, {
        mode: 'xml',
        theme: 'dracula',
        lineNumbers: true,
        lineWrapping: true,
        tabSize: 2,
        indentWithTabs: false,
        autoCloseTags: true,
        matchBrackets: true,
        extraKeys: {
            'Ctrl-Enter': runCode,
            'Cmd-Enter': runCode
        }
    });

    // Set default content
    if (!editor.getValue().trim()) {
        editor.setValue(EXAMPLES.hello);
    }

    // Update cursor position
    editor.on('cursorActivity', () => {
        const cursor = editor.getCursor();
        document.getElementById('cursor-position').textContent =
            `Ln ${cursor.line + 1}, Col ${cursor.ch + 1}`;
    });

    // Debounced live preview
    editor.on('change', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            if (pyodide) {
                runCode();
            }
        }, 500);
    });
}

function setupEventListeners() {
    // Run button
    document.getElementById('run-btn').addEventListener('click', runCode);

    // Example selector
    document.getElementById('example-selector').addEventListener('change', (e) => {
        const example = e.target.value;
        if (example && EXAMPLES[example]) {
            editor.setValue(EXAMPLES[example]);
            if (pyodide) {
                runCode();
            }
        }
    });

    // Share button
    document.getElementById('share-btn').addEventListener('click', shareCode);

    // Download button
    document.getElementById('download-btn').addEventListener('click', downloadHTML);

    // Toggle preview mode
    document.getElementById('toggle-preview-mode').addEventListener('click', togglePreviewMode);

    // Clear console
    document.getElementById('clear-console').addEventListener('click', clearConsole);

    // Resize handle
    setupResizeHandle();
}

function setupResizeHandle() {
    const handle = document.getElementById('resize-handle');
    const editorPanel = document.querySelector('.editor-panel');
    let isResizing = false;
    let startX = 0;
    let startWidth = 0;

    handle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = editorPanel.offsetWidth;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const diff = e.clientX - startX;
        const newWidth = Math.max(300, Math.min(startWidth + diff, window.innerWidth - 400));
        editorPanel.style.flex = `0 0 ${newWidth}px`;
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            // Refresh CodeMirror
            editor.refresh();
        }
    });
}

async function loadPyodide() {
    try {
        logConsole('Loading Pyodide...', 'info');

        // Load Pyodide from CDN
        pyodide = await loadPyodideModule({
            indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/'
        });

        logConsole('Pyodide loaded successfully', 'success');

        // Load the Quantum parser code
        const parserCode = document.getElementById('quantum-parser-code').textContent;
        await pyodide.runPythonAsync(parserCode);

        logConsole('Quantum parser initialized', 'success');

        // Update UI
        document.getElementById('loading-overlay').classList.add('hidden');
        document.getElementById('run-btn').disabled = false;
        document.getElementById('status-indicator').className = 'status-indicator status-ready';
        document.getElementById('status-text').textContent = 'Ready';

        // Run initial code
        runCode();

    } catch (error) {
        logConsole(`Failed to load Pyodide: ${error.message}`, 'error');
        document.getElementById('status-indicator').className = 'status-indicator status-error';
        document.getElementById('status-text').textContent = 'Error loading Pyodide';
        document.getElementById('loading-overlay').querySelector('.loading-text').textContent = 'Failed to load';
        document.getElementById('loading-overlay').querySelector('.loading-subtext').textContent = error.message;
    }
}

async function runCode() {
    if (!pyodide) {
        logConsole('Pyodide not loaded yet', 'warning');
        return;
    }

    const source = editor.getValue();

    try {
        // Call the Python compiler
        const result = pyodide.runPython(`
import json
result = compile_quantum('''${source.replace(/'/g, "\\'")}''')
json.dumps(result)
`);

        const parsed = JSON.parse(result);

        if (parsed.success) {
            updatePreview(parsed.html);
            logConsole('Compiled successfully', 'success');
        } else {
            updatePreview(`<div style="color: #ef4444; padding: 20px; font-family: monospace;">
                <h3>Compilation Error</h3>
                <pre>${escapeHTML(parsed.error)}</pre>
            </div>`);
            logConsole(`Error: ${parsed.error}`, 'error');
        }

    } catch (error) {
        logConsole(`Runtime error: ${error.message}`, 'error');
        updatePreview(`<div style="color: #ef4444; padding: 20px; font-family: monospace;">
            <h3>Runtime Error</h3>
            <pre>${escapeHTML(error.message)}</pre>
        </div>`);
    }
}

function updatePreview(html) {
    const frame = document.getElementById('preview-frame');
    const source = document.getElementById('preview-source');

    // Wrap HTML in a complete document
    const fullHTML = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 16px;
            margin: 0;
            line-height: 1.5;
        }
        * { box-sizing: border-box; }
    </style>
</head>
<body>
${html}
</body>
</html>`;

    // Update iframe
    frame.srcdoc = fullHTML;

    // Update source view
    source.textContent = fullHTML;

    // Store for download
    window._lastHTML = fullHTML;
}

function togglePreviewMode() {
    const frame = document.getElementById('preview-frame');
    const source = document.getElementById('preview-source');
    const btn = document.getElementById('toggle-preview-mode');

    if (previewMode === 'rendered') {
        previewMode = 'source';
        frame.classList.add('hidden');
        source.classList.remove('hidden');
        btn.textContent = 'Preview';
    } else {
        previewMode = 'rendered';
        frame.classList.remove('hidden');
        source.classList.add('hidden');
        btn.textContent = 'HTML Source';
    }
}

function shareCode() {
    const source = editor.getValue();
    const encoded = btoa(encodeURIComponent(source));
    const url = `${window.location.origin}${window.location.pathname}?code=${encoded}`;

    // Copy to clipboard
    navigator.clipboard.writeText(url).then(() => {
        logConsole('Share URL copied to clipboard!', 'success');
    }).catch(() => {
        // Fallback: show in prompt
        prompt('Share URL:', url);
    });
}

function loadFromURL() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');

    if (code) {
        try {
            const decoded = decodeURIComponent(atob(code));
            editor.setValue(decoded);
            logConsole('Loaded code from shared URL', 'info');
        } catch (e) {
            logConsole('Failed to load shared code', 'error');
        }
    }
}

function downloadHTML() {
    const html = window._lastHTML || '';

    if (!html) {
        logConsole('No HTML to download. Run the code first.', 'warning');
        return;
    }

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'quantum-output.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    logConsole('HTML file downloaded', 'success');
}

function logConsole(message, type = 'info') {
    const output = document.getElementById('console-output');
    const line = document.createElement('div');
    line.className = `console-line ${type}`;

    const timestamp = new Date().toLocaleTimeString();

    line.innerHTML = `
        <span class="console-timestamp">[${timestamp}]</span>
        <span class="console-message">${escapeHTML(message)}</span>
    `;

    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function clearConsole() {
    document.getElementById('console-output').innerHTML = '';
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Load Pyodide script dynamically
function loadPyodideModule(config) {
    return new Promise((resolve, reject) => {
        if (window.loadPyodide) {
            window.loadPyodide(config).then(resolve).catch(reject);
            return;
        }

        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js';
        script.onload = () => {
            window.loadPyodide(config).then(resolve).catch(reject);
        };
        script.onerror = () => reject(new Error('Failed to load Pyodide script'));
        document.head.appendChild(script);
    });
}
