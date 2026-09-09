<q:component name="HTMXAddTodo">
  <!-- Phase B: HTMX Partial - Add todo item -->

  <q:action name="add" method="POST">
    <q:param name="task" type="string" required="true" />
  </q:action>

  <q:set name="task" value="{form.task}" />

  <q:if condition="{task} != ''">
    <div class="todo-item">
      <span>✅ {task}</span>
      <small style="color: #95a5a6;">Just now</small>
    </div>
  </q:if>
</q:component>
