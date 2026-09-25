<q:component name="Books">
  <!-- No q:param: each column but the key becomes one, with the rules the
       schema gives it (UI-10). NOT NULL is required, VARCHAR(120) a
       maxlength, the CHECK a list, the REFERENCES a row that must exist. -->
  <q:action name="add" method="POST" table="books" datasource="db">
    <q:query name="added" datasource="db">
      INSERT INTO books (title, author_id, genre, pages, lent)
      VALUES (:title, :author_id, :genre, :pages, :lent)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="author_id" value="{author_id}" type="integer" />
      <q:param name="genre" value="{genre}" type="string" />
      <q:param name="pages" value="{pages}" type="integer" null="true" />
      <q:param name="lent" value="{lent}" type="boolean" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="books" datasource="db">
    SELECT b.title, a.name AS author, b.genre FROM books b JOIN authors a ON a.id = b.author_id
    ORDER BY b.id
  </q:query>

  <ui:window title="Library">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <!-- A form with no fields draws one per param: a list of authors for
         author_id, a list for genre, a box for lent, and the button. -->
    <ui:form on-submit="add" submit="Add book" />
    <ui:table source="{books}" />
  </ui:window>
</q:component>
