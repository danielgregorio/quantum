<q:component name="ApiCards" require_auth="true">
  <!-- A board's cards, and a new one (API-1 to API-3): what a script or another program does with the board
       its pages show. Only a member of the board (or an admin) reaches it; a viewer reads, and does not add. -->

  <q:endpoint method="GET" description="The board's cards that are not archived, column by column">
    <q:param name="column" default="" maxlength="60" description="Only the cards of the column of this name" />
    <q:query name="board" datasource="db">
      SELECT id, name FROM boards
      WHERE id = :board AND (:role = 'admin' OR id IN (SELECT board_id FROM members WHERE user_id = :user))
      <q:param name="board" value="{id}" type="integer" />
      <q:param name="role" value="{session.userRole}" type="string" />
      <q:param name="user" value="{session.userId}" type="integer" />
    </q:query>
    <q:if condition="board_result.recordCount == 0">
      <q:respond status="404" json="{ {'error': 'not_found', 'message': 'No such board among yours.'} }" />
    </q:if>
    <q:query name="cards" datasource="db">
      SELECT c.id, c.title, c.description, k.name AS column_name, u.name AS assignee, c.labels, c.due_on,
             c.done_on, c.source
      FROM cards c JOIN columns k ON k.id = c.column_id LEFT JOIN users u ON u.id = c.assignee_id
      WHERE c.board_id = :board AND c.archived = 0 AND (:column = '' OR k.name = :column)
      ORDER BY k.position, c.id
      <q:param name="board" value="{id}" type="integer" />
      <q:param name="column" value="{column}" type="string" />
    </q:query>
    <q:respond json="{ {'board': board[0].name, 'cards': cards} }" />
  </q:endpoint>

  <q:endpoint method="POST" require_role="admin,member" maxsize="16kb"
              description="A new card, in the board's first column, as the board's Add a card does">
    <q:param name="title" required="true" minlength="3" maxlength="120" />
    <q:param name="description" default="" maxlength="2000" />
    <q:param name="labels" default="" maxlength="200" description="Comma-separated" />
    <q:param name="due_on" type="date" default="" description="A day, YYYY-MM-DD" />
    <q:query name="board" datasource="db">
      SELECT id FROM boards
      WHERE id = :board AND (:role = 'admin' OR id IN (SELECT board_id FROM members WHERE user_id = :user))
      <q:param name="board" value="{id}" type="integer" />
      <q:param name="role" value="{session.userRole}" type="string" />
      <q:param name="user" value="{session.userId}" type="integer" />
    </q:query>
    <q:if condition="board_result.recordCount == 0">
      <q:respond status="404" json="{ {'error': 'not_found', 'message': 'No such board among yours.'} }" />
    </q:if>
    <q:query name="first" datasource="db">
      SELECT id, name FROM columns WHERE board_id = :board ORDER BY position LIMIT 1
      <q:param name="board" value="{id}" type="integer" />
    </q:query>
    <q:query name="added" datasource="db">
      INSERT INTO cards (board_id, column_id, title, description, labels, due_on)
      VALUES (:board, :column, :title, :description, :labels, NULLIF(:due, '')) RETURNING id
      <q:param name="board" value="{id}" type="integer" />
      <q:param name="column" value="{first[0].id}" type="integer" />
      <q:param name="title" value="{title}" type="string" />
      <q:param name="description" value="{description}" type="string" />
      <q:param name="labels" value="{labels}" type="string" />
      <q:param name="due" value="{due_on}" type="string" />
    </q:query>
    <q:respond status="201" json="{ {'id': added[0].id, 'title': title, 'column': first[0].name} }" />
  </q:endpoint>
</q:component>
