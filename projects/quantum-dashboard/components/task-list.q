<!-- Task list partial for HTMX polling -->
<q:component name="TaskList" xmlns:q="https://quantum.lang/ns">

  <!-- Query based on filter -->
  <q:if condition="{query.status} == 'pending'">
    <q:query datasource="taskdb" name="tasks">
      SELECT id, title, description, status, priority, created_at FROM tasks WHERE status = 'pending' ORDER BY id DESC
    </q:query>
  </q:if>

  <q:if condition="{query.status} == 'done'">
    <q:query datasource="taskdb" name="tasks">
      SELECT id, title, description, status, priority, created_at FROM tasks WHERE status = 'done' ORDER BY id DESC
    </q:query>
  </q:if>

  <q:if condition="{query.status} == ''">
    <q:query datasource="taskdb" name="tasks">
      SELECT id, title, description, status, priority, created_at FROM tasks ORDER BY id DESC
    </q:query>
  </q:if>

  <q:loop query="tasks" index="idx">
    <div class="task-item">
      <div class="task-info">
        <div class="task-title">{tasks.title}</div>
        <q:if condition="{tasks.description} != ''">
          <div class="task-desc">{tasks.description}</div>
        </q:if>
        <div class="task-meta">
          <span class="badge badge-{tasks.priority}">{tasks.priority}</span>
          Created: {tasks.created_at}
        </div>
      </div>
      <span class="badge badge-{tasks.status}">{tasks.status}</span>
      <div class="task-actions">
        <q:if condition="{tasks.status} == 'pending'">
          <form method="POST" action="/">
            <input type="hidden" name="action_type" value="markdone" />
            <input type="hidden" name="task_id" value="{tasks.id}" />
            <button type="submit" class="btn-sm btn-done">Done</button>
          </form>
        </q:if>
        <q:if condition="{tasks.status} == 'done'">
          <form method="POST" action="/">
            <input type="hidden" name="action_type" value="reopen" />
            <input type="hidden" name="task_id" value="{tasks.id}" />
            <button type="submit" class="btn-sm btn-reopen">Reopen</button>
          </form>
        </q:if>
        <form method="POST" action="/" onsubmit="return confirm('Delete this task?')">
          <input type="hidden" name="action_type" value="delete" />
          <input type="hidden" name="task_id" value="{tasks.id}" />
          <button type="submit" class="btn-sm btn-delete">Delete</button>
        </form>
      </div>
    </div>
  </q:loop>

</q:component>
