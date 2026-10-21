<q:component name="Tasks">
  <!-- An app in ui:*: the layout, the form and the list come from the UI Engine;
       the logic is the page's: queries, actions and the rules of the SPEC. -->

  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <!-- Side by side on a wide screen; stacked below 768 px (UI-2). -->
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:link to="/task/{tasks.id}">Edit</ui:link>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
