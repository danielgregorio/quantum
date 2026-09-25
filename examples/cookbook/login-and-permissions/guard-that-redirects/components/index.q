<q:component name="Notes">
  <!-- The guard: it runs before the page AND before each of its actions. -->
  <q:if condition="not session.authenticated">
    <q:redirect url="/login" flash="Sign in to write notes." />
  </q:if>

  <q:action name="add" method="POST">
    <q:param name="body" required="true" minlength="2" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (author, body) VALUES (:author, :body)
      <q:param name="author" value="{session.userName}" type="string" />
      <q:param name="body" value="{body}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Saved." />
  </q:action>

  <q:query name="notes" datasource="db">
    SELECT author, body FROM notes ORDER BY id DESC
  </q:query>

  <h1>Notes</h1>
  <q:if condition="flash"><p>{flash}</p></q:if>
  <form method="POST"><input name="body" /><button>Add</button></form>
  <q:loop query="notes"><p>{notes.author}: {notes.body}</p></q:loop>
</q:component>
