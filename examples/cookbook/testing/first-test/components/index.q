<q:component name="Notes">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (title) VALUES (:title)
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="notes" datasource="db">SELECT title FROM notes ORDER BY id</q:query>

  <h1>Notes ({notes_result.recordCount})</h1>
  <q:if condition="flash"><p class="flash">{flash}</p></q:if>
  <form method="POST" action="/?action=add">
    <input name="title" />
    <button>Add</button>
  </form>
  <ul>
    <q:loop query="notes"><li>{notes.title}</li></q:loop>
  </ul>
</q:component>
