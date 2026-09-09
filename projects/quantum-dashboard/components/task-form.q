<!-- Standalone task form page -->
<q:component name="TaskForm" xmlns:q="https://quantum.lang/ns">

  <!-- Handle Create Task POST -->
  <q:if condition="{form.action_type} == 'create'">
    <q:query datasource="taskdb" name="insertResult">
      INSERT INTO tasks (title, description, priority) VALUES (:title, :desc, :priority)
      <q:param name="title" value="{form.title}" />
      <q:param name="desc" value="{form.description}" />
      <q:param name="priority" value="{form.priority}" />
    </q:query>
    <q:set name="session.taskCreated" value="true" />
  </q:if>

  <html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>New Task - Task Master</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; min-height: 100vh; }

      .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 32px; display: flex; align-items: center; gap: 16px; }
      .header a { color: white; text-decoration: none; font-size: 14px; opacity: 0.85; }
      .header a:hover { opacity: 1; }
      .header h1 { font-size: 24px; font-weight: 700; }

      .container { max-width: 600px; margin: 32px auto; padding: 0 24px; }

      .card { background: white; border-radius: 12px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
      .card h2 { margin-bottom: 24px; color: #333; }

      .form-row { margin-bottom: 16px; }
      .form-row label { display: block; font-size: 14px; font-weight: 500; color: #555; margin-bottom: 6px; }
      .form-row input, .form-row textarea, .form-row select { width: 100%; padding: 12px 16px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 15px; outline: none; font-family: inherit; }
      .form-row input:focus, .form-row textarea:focus, .form-row select:focus { border-color: #667eea; }
      .form-row textarea { resize: vertical; min-height: 100px; }

      .form-actions { display: flex; gap: 12px; margin-top: 24px; }
      .btn-submit { padding: 12px 32px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
      .btn-back { padding: 12px 32px; background: #f0f0f0; color: #666; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; }

      .success-msg { background: #d1fae5; color: #065f46; padding: 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
    </style>
  </head>
  <body>
    <div class="header">
      <a href="/">&#8592; Back to Dashboard</a>
      <h1>New Task</h1>
    </div>

    <div class="container">
      <div class="card">
        <q:if condition="{session.taskCreated} == 'true'">
          <div class="success-msg">Task created successfully! <a href="/">Go to dashboard</a></div>
          <q:set name="session.taskCreated" value="" />
        </q:if>

        <h2>Create a New Task</h2>
        <form method="POST">
          <input type="hidden" name="action_type" value="create" />
          <div class="form-row">
            <label>Title *</label>
            <input type="text" name="title" placeholder="What needs to be done?" required="required" />
          </div>
          <div class="form-row">
            <label>Description</label>
            <textarea name="description" placeholder="Add details about this task..."></textarea>
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
            <a href="/" class="btn-back">Cancel</a>
          </div>
        </form>
      </div>
    </div>
  </body>
  </html>

</q:component>
