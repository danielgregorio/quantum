<q:component name="TaskDashboard">
  <!-- Task list: add, finish, reopen, delete, filter by status. -->

  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="description" default="" maxlength="1000" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="insertTask" datasource="taskdb">
      INSERT INTO tasks (title, description, priority) VALUES (:title, :description, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="description" value="{description}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Task created: {title}" />
  </q:action>

  <q:action name="markDone" method="POST">
    <q:param name="task_id" type="integer" required="true" />
    <q:query name="done" datasource="taskdb">
      UPDATE tasks SET status = 'done' WHERE id = :id
      <q:param name="id" value="{task_id}" type="integer" />
    </q:query>
    <q:redirect url="/?status={form.back}" />
  </q:action>

  <q:action name="reopen" method="POST">
    <q:param name="task_id" type="integer" required="true" />
    <q:query name="reopened" datasource="taskdb">
      UPDATE tasks SET status = 'pending' WHERE id = :id
      <q:param name="id" value="{task_id}" type="integer" />
    </q:query>
    <q:redirect url="/?status={form.back}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="task_id" type="integer" required="true" />
    <q:query name="deleted" datasource="taskdb">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{task_id}" type="integer" />
    </q:query>
    <q:redirect url="/?status={form.back}" flash="Task deleted." />
  </q:action>

  <q:set name="status" value="{query.status}" default="all" />

  <q:query name="counts" datasource="taskdb">
    SELECT COUNT(*) AS total,
           COALESCE(SUM(status = 'pending'), 0) AS pending,
           COALESCE(SUM(status = 'done'), 0) AS done
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="taskdb">
    SELECT id, title, description, status, priority, created_at FROM tasks
    WHERE :status = 'all' OR status = :status
    ORDER BY status = 'done', CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="status" value="{status}" type="string" />
  </q:query>

  <html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Task Master - Quantum Dashboard</title>
    <link rel="stylesheet" href="/static/dashboard.css" />
  </head>
  <body>
    <div class="header">
      <h1>Task Master</h1>
      <p>Quantum Dashboard - q:action and q:query over SQLite</p>
    </div>

    <div class="container">
      <q:if condition="flash">
        <div class="flash flash-{flashType}">{flash}</div>
      </q:if>

      <div class="stats">
        <div class="stat-card total"><div class="number">{counts.total}</div><div class="label">Total tasks</div></div>
        <div class="stat-card pending"><div class="number">{counts.pending}</div><div class="label">Pending</div></div>
        <div class="stat-card done"><div class="number">{counts.done}</div><div class="label">Completed</div></div>
      </div>

      <div class="toolbar">
        <div class="filters">
          <a href="/?status=all" class="{'active' if status == 'all' else ''}">All</a>
          <a href="/?status=pending" class="{'active' if status == 'pending' else ''}">Pending</a>
          <a href="/?status=done" class="{'active' if status == 'done' else ''}">Done</a>
        </div>
      </div>

      <details class="create-form">
        <summary class="btn-new">+ New task</summary>
        <form method="POST" action="/">
          <input type="hidden" name="action" value="create" />
          <div class="form-row">
            <label>Title</label>
            <input type="text" name="title" placeholder="What needs to be done?" required="required" />
          </div>
          <div class="form-row">
            <label>Description</label>
            <textarea name="description" placeholder="Optional details"></textarea>
          </div>
          <div class="form-row">
            <label>Priority</label>
            <select name="priority">
              <option value="low">Low</option>
              <option value="medium" selected="selected">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <button type="submit" class="btn-submit">Create task</button>
        </form>
      </details>

      <div class="task-list">
        <q:loop query="tasks">
          <div class="task-item">
            <div class="task-info">
              <div class="task-title">{tasks.title}</div>
              <q:if condition="tasks.description">
                <div class="task-desc">{tasks.description}</div>
              </q:if>
              <div class="task-meta"><span class="badge badge-{tasks.priority}">{tasks.priority}</span></div>
            </div>
            <span class="badge badge-{tasks.status}">{tasks.status}</span>
            <div class="task-actions">
              <form method="POST" action="/">
                <input type="hidden" name="action" value="{'markDone' if tasks.status == 'pending' else 'reopen'}" />
                <input type="hidden" name="task_id" value="{tasks.id}" />
                <input type="hidden" name="back" value="{status}" />
                <button type="submit" class="btn-sm {'btn-done' if tasks.status == 'pending' else 'btn-reopen'}">{'Done' if tasks.status == 'pending' else 'Reopen'}</button>
              </form>
              <form method="POST" action="/">
                <input type="hidden" name="action" value="delete" />
                <input type="hidden" name="task_id" value="{tasks.id}" />
                <input type="hidden" name="back" value="{status}" />
                <button type="submit" class="btn-sm btn-delete">Delete</button>
              </form>
            </div>
          </div>
        </q:loop>
        <q:if condition="tasks_result.recordCount == 0">
          <p class="empty">No tasks here.</p>
        </q:if>
      </div>

      <div class="footer">Quantum Framework - Task Master</div>
    </div>
  </body>
  </html>
</q:component>
