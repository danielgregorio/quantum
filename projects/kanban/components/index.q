<q:component name="Boards" require_auth="true">
  <!-- The boards the signed-in person belongs to (an admin sees them all), and a new one (admins). -->

  <q:action name="createBoard" method="POST" require_role="admin">
    <q:param name="name" required="true" minlength="3" maxlength="60" />
    <q:param name="description" default="" maxlength="200" />
    <q:transaction datasource="db">
      <q:query name="board" datasource="db">
        INSERT INTO boards (name, description) VALUES (:name, :description) RETURNING id
        <q:param name="name" value="{name}" type="string" />
        <q:param name="description" value="{description}" type="string" />
      </q:query>
      <q:query name="columns" datasource="db">
        INSERT INTO columns (board_id, name, position, wip_limit, is_done) VALUES
          (:board, 'To do', 1, NULL, 0), (:board, 'Doing', 2, 3, 0), (:board, 'Done', 3, NULL, 1)
        <q:param name="board" value="{board[0].id}" type="integer" />
      </q:query>
      <q:query name="member" datasource="db">
        INSERT INTO members (board_id, user_id) VALUES (:board, :user)
        <q:param name="board" value="{board[0].id}" type="integer" />
        <q:param name="user" value="{session.userId}" type="integer" />
      </q:query>
    </q:transaction>
    <q:redirect url="/board/{board[0].id}" flash="Board created: {name}" />
  </q:action>

  <q:query name="boards" datasource="db">
    SELECT b.id, b.name, b.description,
           (SELECT COUNT(*) FROM cards c WHERE c.board_id = b.id AND c.archived = 0) AS cards,
           (SELECT COUNT(*) FROM cards c JOIN columns k ON k.id = c.column_id
             WHERE c.board_id = b.id AND c.archived = 0 AND k.is_done = 0
               AND c.due_on IS NOT NULL AND c.due_on &lt; date('now')) AS late
    FROM boards b
    WHERE :role = 'admin' OR b.id IN (SELECT board_id FROM members WHERE user_id = :user)
    ORDER BY b.name
    <q:param name="role" value="{session.userRole}" type="string" />
    <q:param name="user" value="{session.userId}" type="integer" />
  </q:query>

  <ui:window title="Kanban">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:header title="Boards" />
        <ui:spacer />
        <ui:text>{session.userName} ({session.userRole})</ui:text>
        <ui:link to="/logout">Sign out</ui:link>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <q:if condition="boards_result.recordCount == 0">
        <ui:text>No boards yet.</ui:text>
      </q:if>
      <ui:grid columns="1 sm:2 lg:3" gap="md">
        <q:loop items="{boards}" var="b">
          <ui:card title="{b.name}">
            <ui:text>{b.description}</ui:text>
            <ui:hbox gap="sm">
              <ui:badge>{b.cards} cards</ui:badge>
              <q:if condition="b.late > 0"><ui:badge variant="danger">{b.late} late</ui:badge></q:if>
            </ui:hbox>
            <ui:link to="/board/{b.id}">Open {b.name}</ui:link>
          </ui:card>
        </q:loop>
      </ui:grid>
      <q:if condition="session.userRole == 'admin'">
        <ui:panel title="New board">
          <ui:form on-submit="createBoard" submit="Create">
            <ui:input bind="name" label="Name" />
            <ui:input bind="description" label="What it is for" />
          </ui:form>
        </ui:panel>
      </q:if>
    </ui:vbox>
  </ui:window>
</q:component>
