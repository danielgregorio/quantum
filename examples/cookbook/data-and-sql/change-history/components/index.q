<q:component name="Wiki">
  <!-- history: true on the datasource: each write below is recorded with
       the session's user, the action, and the row before and after. -->
  <q:action name="edit" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:param name="body" default="" />
    <q:query name="saved" datasource="db">
      UPDATE pages SET title = :title, body = :body WHERE id = 1
      <q:param name="title" value="{title}" type="string" />
      <q:param name="body" value="{body}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Saved." />
  </q:action>

  <q:query name="page" datasource="db">SELECT id, title, body FROM pages WHERE id = 1</q:query>

  <ui:window title="{page.title}">
    <ui:text>{page.body}</ui:text>
    <ui:form on-submit="edit" values="{page}" submit="Save" />
    <!-- Newest first: when, who, which action, and each changed column. -->
    <ui:history table="pages" key="{page.id}" datasource="db" />
  </ui:window>
</q:component>
