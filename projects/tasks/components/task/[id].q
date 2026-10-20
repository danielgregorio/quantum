<q:component name="EditTask">
  <!-- A form from the table (M17, SPEC UI-10): the action takes the rules of
       `title` and `priority` from the schema of `tasks` (NOT NULL,
       CHECK … IN), and the form, with no fields of its own, draws a field per
       column, filled in with the task's values. -->

  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:query name="saved" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">
    SELECT id, title, priority FROM tasks WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Edit task">
    <ui:vbox gap="md" padding="lg">
      <ui:link to="/">Back</ui:link>
      <q:if condition="task_result.recordCount == 0">
        <ui:alert variant="danger">That task does not exist.</ui:alert>
      </q:if>
      <q:else>
        <ui:form on-submit="save" values="{task}" submit="Save" />
        <ui:section title="History">
          <ui:history table="tasks" key="{id}" datasource="db" />
        </ui:section>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
