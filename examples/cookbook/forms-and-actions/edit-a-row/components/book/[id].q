<q:component name="EditBook">
  <!-- /book/2 gives id = 2. The action takes title and genre, with their
       rules, from the table (UI-10); id comes from the URL. -->
  <q:action name="save" method="POST" table="books" datasource="db" columns="title,genre">
    <q:query name="saved" datasource="db">
      UPDATE books SET title = :title, genre = :genre WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="genre" value="{genre}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="book" datasource="db">
    SELECT id, title, genre FROM books WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Edit a book">
    <q:if condition="book_result.recordCount == 0">
      <ui:alert variant="danger">There is no book {id}.</ui:alert>
    </q:if>
    <q:else>
      <!-- values= opens the form with the row's values; a one-row query works. -->
      <ui:form on-submit="save" values="{book}" submit="Save" />
    </q:else>
    <ui:link to="/">Back</ui:link>
  </ui:window>
</q:component>
