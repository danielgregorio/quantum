<q:component name="Attachment">
  <!-- The ticket's attachment, and nothing else under paths.uploads: the
       stored name comes from the database, never from the URL (FILE-2). -->
  <q:query name="ticket" datasource="db">
    SELECT attachment, attachment_name FROM tickets WHERE id = :id AND attachment IS NOT NULL
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <q:if condition="ticket_result.recordCount == 1">
    <q:file action="send" file="{ticket[0].attachment}" name="{ticket[0].attachment_name}" />
  </q:if>
  <p>There is no attachment for ticket #{id}.</p>
</q:component>
