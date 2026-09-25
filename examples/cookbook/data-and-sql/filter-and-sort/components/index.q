<q:component name="Tasks">
  <!-- ?show=open|done|all, from the links below; open by default. -->
  <q:set name="show" value="{query.show}" default="open" />

  <!-- sortable: the table's headers order the query in SQL (?sort= and ?dir=). -->
  <q:query name="tasks" datasource="db" sortable="true">
    SELECT id, title, priority FROM tasks
    WHERE :show = 'all' OR done = CASE :show WHEN 'done' THEN 1 ELSE 0 END
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="md">
      <ui:link to="/?show=open">Open</ui:link>
      <ui:link to="/?show=done">Done</ui:link>
      <ui:link to="/?show=all">All</ui:link>
    </ui:hbox>
    <ui:text>Showing {show}: {tasks_result.recordCount}</ui:text>
    <ui:table source="{tasks}" sort="true">
      <ui:column key="title" label="Title" />
      <ui:column key="priority" label="Priority" />
    </ui:table>
  </ui:window>
</q:component>
