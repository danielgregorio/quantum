<q:component name="Books">
  <q:query name="books" datasource="db">
    SELECT id, title, genre FROM books ORDER BY id
  </q:query>

  <ui:window title="Books">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <q:loop query="books">
      <ui:hbox gap="sm">
        <ui:text>{books.title} ({books.genre})</ui:text>
        <ui:link to="/book/{books.id}">Edit</ui:link>
      </ui:hbox>
    </q:loop>
  </ui:window>
</q:component>
