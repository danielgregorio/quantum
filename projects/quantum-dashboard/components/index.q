<!-- Quantum Dashboard - Task Manager with SQLite CRUD -->
<q:component name="TaskDashboard" xmlns:q="https://quantum.lang/ns">

  <!-- Handle Create Task POST -->
  <q:if condition="{form.action_type} == 'create'">
    <q:query datasource="taskdb" name="insertResult">
      INSERT INTO tasks (title, description, priority) VALUES (:title, :desc, :priority)
      <q:param name="title" value="{form.title}" />
      <q:param name="desc" value="{form.description}" />
      <q:param name="priority" value="{form.priority}" />
    </q:query>
  </q:if>

  <!-- Handle Mark Done POST -->
  <q:if condition="{form.action_type} == 'markdone'">
    <q:query datasource="taskdb" name="updateResult">
      UPDATE tasks SET status = 'done' WHERE id = :id
      <q:param name="id" value="{form.task_id}" />
    </q:query>
  </q:if>

  <!-- Handle Reopen POST -->
  <q:if condition="{form.action_type} == 'reopen'">
    <q:query datasource="taskdb" name="reopenResult">
      UPDATE tasks SET status = 'pending' WHERE id = :id
      <q:param name="id" value="{form.task_id}" />
    </q:query>
  </q:if>

  <!-- Handle Delete POST -->
  <q:if condition="{form.action_type} == 'delete'">
    <q:query datasource="taskdb" name="deleteResult">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{form.task_id}" />
    </q:query>
  </q:if>

  <!-- Query stats -->
  <q:query datasource="taskdb" name="statsTotal">
    SELECT COUNT(*) as cnt FROM tasks
  </q:query>
  <q:query datasource="taskdb" name="statsPending">
    SELECT COUNT(*) as cnt FROM tasks WHERE status = 'pending'
  </q:query>
  <q:query datasource="taskdb" name="statsDone">
    SELECT COUNT(*) as cnt FROM tasks WHERE status = 'done'
  </q:query>

  <!-- Query all tasks (no filter for simplicity - conditions inside loops are unreliable) -->
  <q:query datasource="taskdb" name="tasks">
    SELECT id, title, description, status, priority, created_at FROM tasks ORDER BY id DESC
  </q:query>

  <html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Task Master - Quantum Dashboard</title>
    <link rel="stylesheet" href="static/dashboard.css" />
  </head>
  <body>
    <!-- Header -->
    <div class="header">
      <h1>Task Master</h1>
      <p>Quantum Dashboard - Powered by q:query + SQLite</p>
    </div>

    <div class="container">
      <!-- Stats -->
      <div class="stats">
        <div class="stat-card total">
          <div class="number">
            <q:loop query="statsTotal"><span>{statsTotal.cnt}</span></q:loop>
          </div>
          <div class="label">Total Tasks</div>
        </div>
        <div class="stat-card pending">
          <div class="number">
            <q:loop query="statsPending"><span>{statsPending.cnt}</span></q:loop>
          </div>
          <div class="label">Pending</div>
        </div>
        <div class="stat-card done">
          <div class="number">
            <q:loop query="statsDone"><span>{statsDone.cnt}</span></q:loop>
          </div>
          <div class="label">Completed</div>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="toolbar">
        <div class="filters">
          <a href="/">All</a>
          <a href="/?status=pending">Pending</a>
          <a href="/?status=done">Done</a>
        </div>
        <button class="btn-new" onclick="document.getElementById('create-form').classList.toggle('show')">+ New Task</button>
      </div>

      <!-- Create Form (hidden by default) -->
      <div id="create-form" class="create-form">
        <h3>Create New Task</h3>
        <form method="POST">
          <input type="hidden" name="action_type" value="create" />
          <div class="form-row">
            <label>Title</label>
            <input type="text" name="title" placeholder="What needs to be done?" required="required" />
          </div>
          <div class="form-row">
            <label>Description</label>
            <textarea name="description" placeholder="Optional details..."></textarea>
          </div>
          <div class="form-row">
            <label>Priority</label>
            <select name="priority">
              <option value="low">Low</option>
              <option value="medium" selected="selected">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-submit">Create Task</button>
            <button type="button" class="btn-cancel" onclick="document.getElementById('create-form').classList.remove('show')">Cancel</button>
          </div>
        </form>
      </div>

      <!-- Task list -->
      <div class="task-list">
        <q:loop query="tasks" index="idx">
          <div class="task-item">
            <div class="task-info">
              <div class="task-title">{tasks.title}</div>
              <div class="task-desc">{tasks.description}</div>
              <div class="task-meta">
                <span class="badge badge-{tasks.priority}">{tasks.priority}</span>
              </div>
            </div>
            <span class="badge badge-{tasks.status}">{tasks.status}</span>
            <div class="task-actions">
              <q:if condition="{tasks.status} == 'pending'">
                <form method="POST">
                  <input type="hidden" name="action_type" value="markdone" />
                  <input type="hidden" name="task_id" value="{tasks.id}" />
                  <button type="submit" class="btn-sm btn-done">Done</button>
                </form>
              </q:if>
              <q:if condition="{tasks.status} == 'done'">
                <form method="POST">
                  <input type="hidden" name="action_type" value="reopen" />
                  <input type="hidden" name="task_id" value="{tasks.id}" />
                  <button type="submit" class="btn-sm btn-reopen">Reopen</button>
                </form>
              </q:if>
              <form method="POST" onsubmit="return confirm('Delete this task?')">
                <input type="hidden" name="action_type" value="delete" />
                <input type="hidden" name="task_id" value="{tasks.id}" />
                <button type="submit" class="btn-sm btn-delete">Delete</button>
              </form>
            </div>
          </div>
        </q:loop>
      </div>

      <div class="footer">
        Quantum Framework - Task Master Dashboard
      </div>
    </div>
  </body>
  </html>

</q:component>
