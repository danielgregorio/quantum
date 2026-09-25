<q:component name="Library">
  <!-- The search is the URL's ?q=; the page's own query does the searching. -->
  <q:set name="term" value="{query.q}" default="" />
  <q:query name="found" datasource="db">
    SELECT title, author FROM books
    WHERE title LIKE :pattern OR author LIKE :pattern
    ORDER BY title
    <q:param name="pattern" value="%{term}%" type="string" />
  </q:query>

  <ui:window title="Library">
    <!-- search="results": after a pause in typing, the page is asked again
         with ?q=… and only #results is swapped. Enter works without JavaScript. -->
    <ui:input bind="q" value="{term}" search="results" placeholder="Title or author" />
    <ui:vbox id="results">
      <ui:text>{found_result.recordCount} books</ui:text>
      <ui:list source="{found}" as="b">
        <ui:item><ui:text>{b.title} — {b.author}</ui:text></ui:item>
      </ui:list>
    </ui:vbox>
  </ui:window>
</q:component>
