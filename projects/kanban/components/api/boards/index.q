<q:component name="ApiBoards" require_auth="true">
  <!-- The boards, as the first page lists them (API-1): the ones whoever signed in belongs to; an admin, all. -->

  <q:endpoint method="GET" description="The boards you belong to (an admin: all), with how many cards each holds">
    <q:query name="boards" datasource="db">
      SELECT b.id, b.name, b.description,
             (SELECT COUNT(*) FROM cards c WHERE c.board_id = b.id AND c.archived = 0) AS cards
      FROM boards b
      WHERE :role = 'admin' OR b.id IN (SELECT board_id FROM members WHERE user_id = :user)
      ORDER BY b.name
      <q:param name="role" value="{session.userRole}" type="string" />
      <q:param name="user" value="{session.userId}" type="integer" />
    </q:query>
    <q:respond json="{ {'boards': boards} }" />
  </q:endpoint>
</q:component>
