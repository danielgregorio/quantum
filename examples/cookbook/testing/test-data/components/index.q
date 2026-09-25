<q:component name="MyTasks" require_auth="true">
  <q:query name="mine" datasource="db">
    SELECT title FROM tasks WHERE owner = :me AND done = 0 ORDER BY id
    <q:param name="me" value="{session.userName}" type="string" />
  </q:query>

  <h1>{session.userName}'s open tasks</h1>
  <q:if condition="mine_result.recordCount == 0">
    <p>Nothing to do.</p>
  </q:if>
  <ul>
    <q:loop query="mine"><li>{mine.title}</li></q:loop>
  </ul>
</q:component>
