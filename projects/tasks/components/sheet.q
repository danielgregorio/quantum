<q:component name="Sheet">
  <!-- A table that sorts and edits itself (M16, SPEC UI-13): the headers sort
       in SQL (sortable), and each cell is a form that saves one column of one
       row, validated by the schema's rules: no action written. -->

  <q:query name="tasks" datasource="db" sortable="true" paginate="true" page_size="20">
    SELECT id, title, priority, done FROM tasks ORDER BY id
  </q:query>

  <ui:window title="Task sheet">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:link to="/">Back</ui:link>
        <ui:text>Click a header to sort; edit a cell and confirm with ✓ (or Enter).</ui:text>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
        <ui:column key="title" label="Title" />
        <ui:column key="priority" label="Priority" />
        <ui:column key="done" label="Done" />
      </ui:table>
      <ui:pager for="tasks" />
    </ui:vbox>
  </ui:window>
</q:component>
