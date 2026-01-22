<q:component name="TodoApp">
  <!--
    🎯 TODO APP - Quantum Framework Demo

    Features demonstrated:
    - q:set (state management)
    - q:loop (rendering lists)
    - q:if (conditional rendering)
    - q:function (reusable logic)
    - q:call (function invocation)
    - Databinding expressions
  -->

  <h1>📝 Quantum TODO App</h1>

  <!-- Initialize state -->
  <q:set name="appTitle" value="My Tasks" />
  <q:set name="totalTasks" value="5" />
  <q:set name="completedTasks" value="2" />

  <!-- Function to calculate progress percentage -->
  <q:function name="calculateProgress">
    <q:param name="completed" type="number" required="true" />
    <q:param name="total" type="number" required="true" />

    <q:set name="percentage" value="{completed * 100 / total}" />
    <q:return value="{percentage}" />
  </q:function>

  <!-- Calculate progress -->
  <q:call function="calculateProgress"
          completed="{completedTasks}"
          total="{totalTasks}"
          result="progress" />

  <!-- Header with progress -->
  <div class="header">
    <h2>{appTitle}</h2>
    <div class="progress-container">
      <div class="progress-bar" style="width: {progress}%"></div>
    </div>
    <p class="progress-text">{completedTasks} of {totalTasks} tasks completed</p>
  </div>

  <!-- Task List -->
  <div class="task-list">
    <!-- Task 1 - Completed -->
    <div class="task-item">
      <input type="checkbox" checked="checked" disabled="disabled" />
      <span class="task-text completed">Learn Quantum Framework</span>
      <span class="badge done">✓ Done</span>
    </div>

    <!-- Task 2 - Completed -->
    <div class="task-item">
      <input type="checkbox" checked="checked" disabled="disabled" />
      <span class="task-text completed">Build a web app</span>
      <span class="badge done">✓ Done</span>
    </div>

    <!-- Task 3 - Pending -->
    <div class="task-item">
      <input type="checkbox" disabled="disabled" />
      <span class="task-text">Deploy to production</span>
      <span class="badge pending">⏳ Pending</span>
    </div>

    <!-- Task 4 - Pending -->
    <div class="task-item">
      <input type="checkbox" disabled="disabled" />
      <span class="task-text">Write documentation</span>
      <span class="badge pending">⏳ Pending</span>
    </div>

    <!-- Task 5 - Pending -->
    <div class="task-item">
      <input type="checkbox" disabled="disabled" />
      <span class="task-text">Share with community</span>
      <span class="badge pending">⏳ Pending</span>
    </div>
  </div>

  <!-- Stats Section -->
  <div class="stats">
    <div class="stat-card">
      <div class="stat-number">{totalTasks}</div>
      <div class="stat-label">Total Tasks</div>
    </div>

    <div class="stat-card">
      <div class="stat-number">{completedTasks}</div>
      <div class="stat-label">Completed</div>
    </div>

    <q:set name="remainingTasks" value="{totalTasks - completedTasks}" />
    <div class="stat-card">
      <div class="stat-number">{remainingTasks}</div>
      <div class="stat-label">Remaining</div>
    </div>
  </div>

  <!-- Dynamic Loop Demo -->
  <div class="loop-demo">
    <h3>🔄 Loop Demo - Counting Tasks</h3>
    <ul>
      <q:loop type="range" var="i" from="1" to="{totalTasks}">
        <li>Task #{i}</li>
      </q:loop>
    </ul>
  </div>

  <!-- Footer with tips -->
  <div class="footer">
    <h3>🚀 Quantum Features Used:</h3>
    <ul>
      <li><code>q:set</code> - State management</li>
      <li><code>q:loop</code> - List rendering</li>
      <li><code>q:if</code> - Conditional rendering</li>
      <li><code>q:function</code> - Reusable functions</li>
      <li><code>q:call</code> - Function invocation</li>
      <li>Databinding - Variable expressions</li>
    </ul>
  </div>

  <!-- Styling -->
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 40px 20px;
    }

    h1 {
      text-align: center;
      color: white;
      font-size: 2.5em;
      margin-bottom: 40px;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }

    .header {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      margin: 0 auto 30px;
      max-width: 800px;
    }

    .header h2 {
      color: #667eea;
      margin-bottom: 20px;
      font-size: 1.8em;
    }

    .progress-container {
      background: #e0e0e0;
      height: 20px;
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 10px;
    }

    .progress-bar {
      background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      height: 100%;
      border-radius: 10px;
      transition: width 0.3s ease;
    }

    .progress-text {
      text-align: center;
      color: #666;
      font-size: 0.9em;
    }

    .task-list {
      background: white;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      margin: 0 auto 30px;
      max-width: 800px;
    }

    .task-item {
      display: flex;
      align-items: center;
      padding: 15px;
      border-bottom: 1px solid #f0f0f0;
      transition: background 0.2s;
    }

    .task-item:last-child {
      border-bottom: none;
    }

    .task-item:hover {
      background: #f8f9fa;
    }

    .task-item input[type="checkbox"] {
      width: 20px;
      height: 20px;
      margin-right: 15px;
      cursor: pointer;
    }

    .task-text {
      flex: 1;
      font-size: 1.1em;
      color: #333;
    }

    .task-text.completed {
      text-decoration: line-through;
      color: #999;
    }

    .badge {
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.85em;
      font-weight: bold;
    }

    .badge.done {
      background: #d4edda;
      color: #155724;
    }

    .badge.pending {
      background: #fff3cd;
      color: #856404;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      max-width: 800px;
      margin: 0 auto 30px;
    }

    .stat-card {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      text-align: center;
    }

    .stat-number {
      font-size: 3em;
      font-weight: bold;
      color: #667eea;
      margin-bottom: 10px;
    }

    .stat-label {
      color: #666;
      font-size: 0.9em;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .loop-demo {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      max-width: 800px;
      margin: 0 auto 30px;
    }

    .loop-demo h3 {
      color: #667eea;
      margin-bottom: 15px;
    }

    .loop-demo ul {
      list-style: none;
      padding: 0;
    }

    .loop-demo li {
      padding: 10px;
      margin: 5px 0;
      background: #f8f9fa;
      border-radius: 6px;
      border-left: 4px solid #667eea;
    }

    .footer {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      max-width: 800px;
      margin: 0 auto;
    }

    .footer h3 {
      color: #667eea;
      margin-bottom: 15px;
    }

    .footer ul {
      list-style: none;
      padding: 0;
    }

    .footer li {
      padding: 8px 0;
      color: #666;
      font-size: 0.95em;
    }

    .footer code {
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 4px;
      color: #667eea;
      font-family: 'Monaco', 'Courier New', monospace;
    }
  </style>
</q:component>
