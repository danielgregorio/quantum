<q:component name="HTMXDemo">
  <!-- Phase B: HTMX Partials Demo -->

  <h1>🚀 HTMX Partials Demo</h1>

  <p>This page demonstrates HTMX-style progressive enhancement with Quantum partials!</p>

  <div class="container">
    <!-- Live Counter Section -->
    <div class="section">
      <h2>📊 Live Counter (Auto-Updates)</h2>

      <div id="counter"
           hx-get="/_partial/htmx_counter"
           hx-trigger="every 2s"
           hx-swap="innerHTML">
        <p>Loading counter...</p>
      </div>

      <p class="info">This counter updates automatically every 2 seconds using HTMX!</p>
    </div>

    <!-- Click Counter Section -->
    <div class="section">
      <h2>🖱️ Click Counter</h2>

      <div id="clicks">
        <p>Clicks: <span id="click-count">0</span></p>
      </div>

      <button
        hx-post="/_partial/htmx_click"
        hx-target="#click-count"
        hx-swap="innerHTML"
        class="btn">
        Click Me! <span class="htmx-indicator">⏳</span>
      </button>

      <p class="info">Button updates without full page reload!</p>
    </div>

    <!-- Search Section -->
    <div class="section">
      <h2>🔍 Live Search</h2>

      <input
        type="text"
        name="search"
        placeholder="Type to search..."
        hx-post="/_partial/htmx_search"
        hx-trigger="keyup changed delay:500ms"
        hx-target="#search-results"
        hx-swap="innerHTML"
        class="search-input" />

      <div id="search-results">
        <p class="muted">Type something to search...</p>
      </div>

      <p class="info">Search results appear as you type (debounced)!</p>
    </div>

    <!-- Todo List Section -->
    <div class="section">
      <h2>✅ Interactive Todo List</h2>

      <form hx-post="/_partial/htmx_add_todo"
            hx-target="#todo-list"
            hx-swap="beforeend">
        <input
          type="text"
          name="task"
          placeholder="New task..."
          required
          class="todo-input" />

        <button type="submit" class="btn btn-primary">
          Add <span class="htmx-indicator">⏳</span>
        </button>
      </form>

      <div id="todo-list" class="todo-list">
        <!-- Todos will be added here -->
      </div>

      <p class="info">Add todos without page reload!</p>
    </div>

    <!-- Features Summary -->
    <div class="section features">
      <h2>✨ HTMX Features Demonstrated</h2>

      <ul>
        <li>✅ <strong>hx-get</strong> - Partial loading via GET</li>
        <li>✅ <strong>hx-post</strong> - Form submission via POST</li>
        <li>✅ <strong>hx-trigger</strong> - Custom events (click, keyup, every Xs)</li>
        <li>✅ <strong>hx-target</strong> - Update specific elements</li>
        <li>✅ <strong>hx-swap</strong> - Swap strategies (innerHTML, beforeend)</li>
        <li>✅ <strong>Loading indicators</strong> - Visual feedback</li>
        <li>✅ <strong>Debouncing</strong> - Delay triggers (delay:500ms)</li>
        <li>✅ <strong>Auto-updates</strong> - Polling (every 2s)</li>
      </ul>
    </div>
  </div>

  <style>
    body {
      background: #f5f7fa;
    }

    h1 {
      color: #2c3e50;
      text-align: center;
      margin: 30px 0;
    }

    h1 + p {
      text-align: center;
      color: #7f8c8d;
      margin-bottom: 40px;
    }

    .container {
      max-width: 1000px;
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

    .section h2 {
      color: #34495e;
      margin-bottom: 20px;
      font-size: 1.5rem;
    }

    .info {
      background: #e8f4fd;
      border-left: 4px solid #3498db;
      padding: 12px;
      margin-top: 15px;
      border-radius: 4px;
      color: #2980b9;
      font-size: 0.9rem;
    }

    .muted {
      color: #95a5a6;
      font-style: italic;
    }

    .btn {
      background: #3498db;
      color: white;
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 1rem;
      transition: background 0.3s;
    }

    .btn:hover {
      background: #2980b9;
    }

    .btn-primary {
      background: #2ecc71;
    }

    .btn-primary:hover {
      background: #27ae60;
    }

    .search-input,
    .todo-input {
      width: 100%;
      padding: 12px;
      border: 2px solid #dfe6e9;
      border-radius: 6px;
      font-size: 1rem;
      margin-bottom: 10px;
      transition: border-color 0.3s;
    }

    .search-input:focus,
    .todo-input:focus {
      outline: none;
      border-color: #3498db;
    }

    #counter {
      background: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
      text-align: center;
      font-size: 2rem;
      color: #2c3e50;
    }

    #clicks {
      text-align: center;
      font-size: 1.5rem;
      margin-bottom: 20px;
    }

    #click-count {
      color: #e74c3c;
      font-weight: bold;
    }

    #search-results {
      margin-top: 15px;
      min-height: 50px;
    }

    .search-result {
      background: #f8f9fa;
      padding: 10px 15px;
      margin-bottom: 8px;
      border-radius: 6px;
      border-left: 4px solid #3498db;
    }

    .todo-list {
      margin-top: 20px;
    }

    .todo-item {
      background: #f8f9fa;
      padding: 12px 15px;
      margin-bottom: 8px;
      border-radius: 6px;
      border-left: 4px solid #2ecc71;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    form {
      display: flex;
      gap: 10px;
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

    .htmx-indicator {
      display: none;
    }

    .htmx-request .htmx-indicator {
      display: inline;
    }
  </style>
</q:component>
