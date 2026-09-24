<q:component name="IslandsDemo" interactive="true">
  <!-- Phase E: Islands Architecture Demo -->

  <h1>🏝️ Islands Architecture Demo</h1>

  <p>This page demonstrates <strong>Islands of Interactivity</strong> - client-side reactive components!</p>

  <div class="container">
    <!-- Counter Island -->
    <div class="section island">
      <h2>🔢 Interactive Counter (Island)</h2>

      <div class="counter-display" id="counter-value">0</div>

      <div class="button-group">
        <button onclick="decrementCounter()" class="btn btn-danger">-</button>
        <button onclick="resetCounter()" class="btn btn-secondary">Reset</button>
        <button onclick="incrementCounter()" class="btn btn-success">+</button>
      </div>

      <p class="info">This counter runs entirely on the client - no server requests!</p>
    </div>

    <!-- Input Island -->
    <div class="section island">
      <h2>✏️ Live Input (Two-way Binding)</h2>

      <input
        type="text"
        id="user-input"
        placeholder="Type something..."
        oninput="updateOutput(this.value)"
        class="text-input" />

      <div class="output-display">
        <p>You typed: <strong id="output-text">nothing yet</strong></p>
        <p>Character count: <span id="char-count">0</span></p>
      </div>

      <p class="info">Changes reflect instantly without server round-trips!</p>
    </div>

    <!-- Todo Island -->
    <div class="section island">
      <h2>✅ Client-Side Todo List</h2>

      <div class="todo-input-group">
        <input
          type="text"
          id="todo-input"
          placeholder="New task..."
          onkeypress="if(event.key==='Enter') addTodo()"
          class="text-input" />

        <button onclick="addTodo()" class="btn btn-primary">Add</button>
      </div>

      <div id="todo-list" class="todo-list">
        <!-- Todos will be added here -->
      </div>

      <p class="info">Todos are managed in memory - pure client-side!</p>
    </div>

    <!-- Visibility Toggle Island -->
    <div class="section island">
      <h2>👁️ Conditional Rendering</h2>

      <button onclick="toggleVisibility()" class="btn">
        Toggle Content <span id="toggle-icon">▼</span>
      </button>

      <div id="toggleable-content" style="display: none;" class="toggleable">
        <p>🎉 This content can be shown or hidden dynamically!</p>
        <p>Islands architecture allows this without server communication.</p>
      </div>

      <p class="info">Show/hide content based on client state!</p>
    </div>

    <!-- Features Summary -->
    <div class="section features">
      <h2>✨ Islands Architecture Features</h2>

      <ul>
        <li>✅ <strong>Client-side state</strong> - Reactive without server</li>
        <li>✅ <strong>Event handlers</strong> - onclick, oninput, onkeypress</li>
        <li>✅ <strong>Two-way binding</strong> - Input ↔ Display sync</li>
        <li>✅ <strong>Conditional rendering</strong> - Dynamic show/hide</li>
        <li>✅ <strong>Islands of interactivity</strong> - Interactive where needed</li>
        <li>✅ <strong>No framework required</strong> - Plain JavaScript</li>
        <li>✅ <strong>Progressive enhancement</strong> - Works with/without JS</li>
      </ul>

      <div class="architecture">
        <h3>Architecture Diagram:</h3>
        <pre>
┌─────────────────────────────────────┐
│     Server-Side Rendered HTML       │
│  (Static, SEO-friendly, fast load) │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   🏝️  Islands of Interactivity  🏝️  │
│  - Counter (client state)           │
│  - Input (two-way binding)          │
│  - Todo (client-side CRUD)          │
│  - Toggle (conditional render)      │
└─────────────────────────────────────┘
           ↓
    Hydration on client
    (JavaScript activates islands)
        </pre>
      </div>
    </div>
  </div>

  <script>
    // Phase E: Islands Architecture - Client-side JavaScript

    // Counter Island State
    let counterValue = 0;

    function incrementCounter() {
      counterValue++;
      updateCounterDisplay();
    }

    function decrementCounter() {
      counterValue--;
      updateCounterDisplay();
    }

    function resetCounter() {
      counterValue = 0;
      updateCounterDisplay();
    }

    function updateCounterDisplay() {
      document.getElementById('counter-value').textContent = counterValue;
    }

    // Input Island State
    function updateOutput(value) {
      document.getElementById('output-text').textContent = value || 'nothing yet';
      document.getElementById('char-count').textContent = value.length;
    }

    // Todo Island State
    let todos = [];
    let todoId = 0;

    function addTodo() {
      const input = document.getElementById('todo-input');
      const task = input.value.trim();

      if (task) {
        const todo = {
          id: todoId++,
          task: task,
          completed: false
        };

        todos.push(todo);
        input.value = '';
        renderTodos();
      }
    }

    function toggleTodo(id) {
      const todo = todos.find(t => t.id === id);
      if (todo) {
        todo.completed = !todo.completed;
        renderTodos();
      }
    }

    function deleteTodo(id) {
      todos = todos.filter(t => t.id !== id);
      renderTodos();
    }

    function renderTodos() {
      const list = document.getElementById('todo-list');

      if (todos.length === 0) {
        list.innerHTML = '<p class="empty">No todos yet. Add one above!</p>';
        return;
      }

      list.innerHTML = todos.map(todo => `
        <div class="todo-item ${todo.completed ? 'completed' : ''}">
          <input
            type="checkbox"
            ${todo.completed ? 'checked' : ''}
            onchange="toggleTodo(${todo.id})" />
          <span>${todo.task}</span>
          <button onclick="deleteTodo(${todo.id})" class="btn-delete">×</button>
        </div>
      `).join('');
    }

    // Toggle Island State
    let isVisible = false;

    function toggleVisibility() {
      isVisible = !isVisible;
      const content = document.getElementById('toggleable-content');
      const icon = document.getElementById('toggle-icon');

      content.style.display = isVisible ? 'block' : 'none';
      icon.textContent = isVisible ? '▲' : '▼';
    }

    // Initialize
    renderTodos();

    console.log('🏝️ Islands Architecture initialized!');
    console.log('Islands are hydrated and interactive.');
  </script>

  <style>
    body {
      background: #f5f7fa;
      margin: 0;
      padding: 0;
    }

    h1 {
      color: #2c3e50;
      text-align: center;
      margin: 30px 0 10px;
    }

    h1 + p {
      text-align: center;
      color: #7f8c8d;
      margin-bottom: 40px;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    .section {
      background: white;
      padding: 30px;
      margin-bottom: 30px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .island {
      border: 3px solid #3498db;
      position: relative;
    }

    .island::before {
      content: "🏝️ Interactive Island";
      position: absolute;
      top: -12px;
      right: 20px;
      background: #3498db;
      color: white;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: bold;
    }

    .section h2 {
      color: #34495e;
      margin-bottom: 20px;
      margin-top: 0;
    }

    .info {
      background: #e8f4fd;
      border-left: 4px solid #3498db;
      padding: 12px;
      margin-top: 20px;
      border-radius: 4px;
      color: #2980b9;
      font-size: 0.9rem;
    }

    .counter-display {
      font-size: 4rem;
      text-align: center;
      color: #2ecc71;
      font-weight: bold;
      margin: 20px 0;
    }

    .button-group {
      display: flex;
      gap: 10px;
      justify-content: center;
    }

    .btn {
      padding: 12px 24px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 600;
      transition: all 0.3s;
    }

    .btn-success {
      background: #2ecc71;
      color: white;
    }

    .btn-success:hover {
      background: #27ae60;
    }

    .btn-danger {
      background: #e74c3c;
      color: white;
    }

    .btn-danger:hover {
      background: #c0392b;
    }

    .btn-secondary {
      background: #95a5a6;
      color: white;
    }

    .btn-secondary:hover {
      background: #7f8c8d;
    }

    .btn-primary {
      background: #3498db;
      color: white;
    }

    .btn-primary:hover {
      background: #2980b9;
    }

    .text-input {
      width: 100%;
      padding: 12px;
      border: 2px solid #dfe6e9;
      border-radius: 6px;
      font-size: 1rem;
      transition: border-color 0.3s;
    }

    .text-input:focus {
      outline: none;
      border-color: #3498db;
    }

    .output-display {
      margin-top: 20px;
      background: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
    }

    .output-display p {
      margin: 10px 0;
    }

    .todo-input-group {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
    }

    .todo-list {
      min-height: 100px;
    }

    .todo-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      background: #f8f9fa;
      border-radius: 6px;
      margin-bottom: 8px;
      border-left: 4px solid #2ecc71;
    }

    .todo-item.completed {
      opacity: 0.6;
      border-left-color: #95a5a6;
    }

    .todo-item.completed span {
      text-decoration: line-through;
    }

    .todo-item input[type="checkbox"] {
      width: 20px;
      height: 20px;
      cursor: pointer;
    }

    .todo-item span {
      flex: 1;
    }

    .btn-delete {
      background: #e74c3c;
      color: white;
      border: none;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 1.2rem;
      line-height: 1;
    }

    .btn-delete:hover {
      background: #c0392b;
    }

    .empty {
      text-align: center;
      color: #95a5a6;
      padding: 40px;
      font-style: italic;
    }

    .toggleable {
      margin-top: 20px;
      padding: 20px;
      background: #d4edda;
      border: 2px solid #28a745;
      border-radius: 8px;
      animation: fadeIn 0.3s;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .features ul {
      list-style: none;
      padding: 0;
    }

    .features li {
      padding: 10px 0;
      border-bottom: 1px solid #ecf0f1;
    }

    .features li:last-child {
      border-bottom: none;
    }

    .features strong {
      color: #2c3e50;
      font-family: 'Courier New', monospace;
    }

    .architecture {
      margin-top: 30px;
      background: #2c3e50;
      padding: 20px;
      border-radius: 8px;
    }

    .architecture h3 {
      color: white;
      margin-top: 0;
    }

    .architecture pre {
      color: #2ecc71;
      font-family: 'Courier New', monospace;
      line-height: 1.6;
      overflow-x: auto;
    }
  </style>
</q:component>
