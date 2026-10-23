<q:component name="Card" require_auth="true">
  <!-- A card: what it is, who has it, when it is due; split into subtasks by the AI; its history. -->

  <q:action name="save" method="POST" require_role="admin,member">
    <q:param name="title" required="true" minlength="3" maxlength="120" />
    <q:param name="description" default="" maxlength="2000" />
    <q:param name="assignee" type="integer" default="0" />
    <q:param name="due_on" type="date" default="" />
    <q:param name="labels" default="" maxlength="80" pattern="^[a-z0-9, -]*$" />
    <q:query name="saved" datasource="db">
      UPDATE cards SET title = :title, description = :description, assignee_id = NULLIF(:assignee, 0),
                       due_on = NULLIF(:due, ''), labels = :labels
      WHERE id = :card
      <q:param name="title" value="{title}" type="string" />
      <q:param name="description" value="{description}" type="string" />
      <q:param name="assignee" value="{assignee}" type="integer" />
      <q:param name="due" value="{due_on}" type="string" />
      <q:param name="labels" value="{labels}" type="string" />
      <q:param name="card" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/card/{id}" flash="Saved." />
  </q:action>

  <q:action name="archive" method="POST" require_role="admin,member">
    <q:query name="card" datasource="db">
      UPDATE cards SET archived = 1 WHERE id = :card RETURNING board_id
      <q:param name="card" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/board/{card[0].board_id}" flash="Card archived." />
  </q:action>

  <q:action name="remove" method="POST" require_role="admin">
    <q:query name="card" datasource="db">
      DELETE FROM cards WHERE id = :card RETURNING board_id
      <q:param name="card" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/board/{card[0].board_id}" flash="Card deleted." />
  </q:action>

  <!-- the AI splits the card into three to six subtasks, each a card of the first column -->
  <q:action name="split" method="POST" require_role="admin,member">
    <q:query name="card" datasource="db">
      SELECT c.board_id, c.title, c.description,
             (SELECT id FROM columns WHERE board_id = c.board_id ORDER BY position LIMIT 1) AS first
      FROM cards c WHERE c.id = :card
      <q:param name="card" value="{id}" type="integer" />
    </q:query>
    <q:llm name="parts" responseFormat="json" temperature="0" onerror="continue">
      <q:prompt>Split this task into three to six small subtasks. Return JSON: {"subtasks": ["...", "..."]}.
Task: {card[0].title}. {card[0].description}</q:prompt>
    </q:llm>
    <q:if condition="not parts_result.success">
      <q:redirect url="/card/{id}" flash="The AI did not answer: {parts_result.error.message}" flashType="error" />
    </q:if>
    <q:loop items="{parts.subtasks}" var="part">
      <q:query name="added" datasource="db">
        INSERT INTO cards (board_id, column_id, title, labels) VALUES (:board, :column, :title, 'subtask')
        <q:param name="board" value="{card[0].board_id}" type="integer" />
        <q:param name="column" value="{card[0].first}" type="integer" />
        <q:param name="title" value="{part}" type="string" />
      </q:query>
    </q:loop>
    <q:redirect url="/board/{card[0].board_id}" flash="{len(parts.subtasks)} subtasks of {card[0].title} added." />
  </q:action>

  <q:query name="card" datasource="db">
    SELECT c.id, c.board_id, c.title, c.description, c.assignee_id, c.due_on, c.labels, c.source,
           c.created_on, c.started_on, c.done_on, k.name AS column_name, b.name AS board
    FROM cards c JOIN columns k ON k.id = c.column_id JOIN boards b ON b.id = c.board_id
    WHERE c.id = :card AND (:role = 'admin' OR c.board_id IN (SELECT board_id FROM members WHERE user_id = :user))
    <q:param name="card" value="{id}" type="integer" />
    <q:param name="role" value="{session.userRole}" type="string" />
    <q:param name="user" value="{session.userId}" type="integer" />
  </q:query>

  <q:query name="people" datasource="db">
    SELECT u.id, u.name FROM users u JOIN members m ON m.user_id = u.id
    WHERE m.board_id = (SELECT board_id FROM cards WHERE id = :card) ORDER BY u.name
    <q:param name="card" value="{id}" type="integer" />
  </q:query>

  <ui:window title="{card_result.recordCount == 1 and card[0].title or 'Card'}" transition="slide">
    <ui:vbox gap="md" padding="lg">
      <q:if condition="card_result.recordCount == 0">
        <ui:alert variant="danger">There is no card #{id} on a board of yours.</ui:alert>
        <ui:link to="/">Boards</ui:link>
      </q:if>
      <q:else>
        <ui:hbox gap="md">
          <ui:link to="/board/{card[0].board_id}">{card[0].board}</ui:link>
          <ui:text>›</ui:text>
          <ui:text>{card[0].column_name}</ui:text>
        </ui:hbox>
        <q:if condition="flash">
          <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}" enter="fade">{flash}</ui:alert>
        </q:if>
        <ui:header title="#{card[0].id} {card[0].title}" />
        <ui:text>Created {card[0].created_on}; started {card[0].started_on or '-'}; done {card[0].done_on or '-'}.</ui:text>
        <q:if condition="card[0].source">
          <ui:link to="{card[0].source}">From {card[0].source}</ui:link>
        </q:if>
        <q:if condition="session.userRole != 'viewer'">
          <ui:panel title="The card">
            <ui:form on-submit="save" submit="Save">
              <ui:input bind="title" label="Title" value="{card[0].title}" />
              <ui:input bind="description" label="Description" rows="4" value="{card[0].description}" />
              <ui:select bind="assignee" label="Who" value="{card[0].assignee_id or 0}">
                <ui:option value="0">nobody</ui:option>
                <q:loop items="{people}" var="person">
                  <ui:option value="{person.id}">{person.name}</ui:option>
                </q:loop>
              </ui:select>
              <ui:input bind="due_on" type="date" label="Due" value="{card[0].due_on}" />
              <ui:input bind="labels" label="Labels" value="{card[0].labels}" />
            </ui:form>
          </ui:panel>
          <ui:hbox gap="sm">
            <ui:button on-click="split" variant="primary">Split it with the AI</ui:button>
            <ui:button on-click="archive">Archive</ui:button>
            <q:if condition="session.userRole == 'admin'">
              <ui:button on-click="remove" variant="danger">Delete</ui:button>
            </q:if>
          </ui:hbox>
        </q:if>
        <q:else>
          <ui:panel title="The card">
            <ui:text>{card[0].description}</ui:text>
          </ui:panel>
        </q:else>
        <ui:panel title="History">
          <ui:history table="cards" key="{id}" datasource="db" limit="20" />
        </ui:panel>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
