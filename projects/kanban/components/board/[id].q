<q:component name="Board" require_auth="true">
  <!-- A board: its columns side by side with their cards; asking the AI about it; its flow; its settings.
       Members and admins change it; viewers look. -->

  <q:set name="tab" value="{query.tab}" default="Board" />
  <q:set name="who" value="{query.who}" default="" />
  <q:set name="label" value="{query.label}" default="" />
  <q:set name="due" value="{query.due}" default="" />

  <!-- ===== Cards ===== -->

  <q:action name="addCard" method="POST" require_role="admin,member">
    <q:param name="title" required="true" minlength="3" maxlength="120" />
    <q:query name="first" datasource="db">
      SELECT id FROM columns WHERE board_id = :board ORDER BY position LIMIT 1
      <q:param name="board" value="{id}" type="integer" />
    </q:query>
    <q:query name="added" datasource="db">
      INSERT INTO cards (board_id, column_id, title) VALUES (:board, :column, :title)
      <q:param name="board" value="{id}" type="integer" />
      <q:param name="column" value="{first[0].id}" type="integer" />
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/board/{id}" flash="Card added: {title}" />
  </q:action>

  <!-- a card to another column: started when it leaves the first, done when it reaches the done column;
       the column says when it holds more than its limit, and the board's webhook is told of a card done -->
  <q:action name="move" method="POST" require_role="admin,member">
    <q:param name="card" type="integer" required="true" />
    <q:param name="to" type="integer" required="true" />
    <q:query name="target" datasource="db">
      SELECT k.id, k.name, k.position, k.wip_limit, k.is_done,
             (SELECT MIN(position) FROM columns WHERE board_id = :board) AS first_position,
             (SELECT COUNT(*) FROM cards c WHERE c.column_id = k.id AND c.archived = 0 AND c.id != :card) AS holding
      FROM columns k WHERE k.id = :to AND k.board_id = :board
      <q:param name="to" value="{to}" type="integer" />
      <q:param name="card" value="{card}" type="integer" />
      <q:param name="board" value="{id}" type="integer" />
    </q:query>
    <q:if condition="target_result.recordCount == 0">
      <q:redirect url="/board/{id}" flash="That column is not on this board." flashType="error" />
    </q:if>
    <q:query name="moved" datasource="db">
      UPDATE cards SET column_id = :to,
        started_on = CASE WHEN :position > :first THEN COALESCE(started_on, datetime('now')) ELSE NULL END,
        done_on = CASE WHEN :done = 1 THEN datetime('now') ELSE NULL END
      WHERE id = :card AND board_id = :board
      <q:param name="to" value="{to}" type="integer" />
      <q:param name="position" value="{target[0].position}" type="integer" />
      <q:param name="first" value="{target[0].first_position}" type="integer" />
      <q:param name="done" value="{target[0].is_done}" type="integer" />
      <q:param name="card" value="{card}" type="integer" />
      <q:param name="board" value="{id}" type="integer" />
    </q:query>
    <q:if condition="target[0].is_done == 1">
      <q:set name="told" value="{tellWebhook(card)}" />
    </q:if>
    <q:if condition="target[0].wip_limit and target[0].holding + 1 > target[0].wip_limit">
      <q:redirect url="/board/{id}" flash="{target[0].name} holds {target[0].holding + 1} cards, over its limit of {target[0].wip_limit}." flashType="error" />
    </q:if>
    <q:redirect url="/board/{id}" />
  </q:action>

  <!-- the board's webhook, told of a card done (a failure is the flash's, never the move's) -->
  <q:function name="tellWebhook">
    <q:param name="card" type="integer" required="true" />
    <q:query name="hook" datasource="db">
      SELECT b.webhook_url, b.name AS board, c.title, c.id FROM boards b JOIN cards c ON c.board_id = b.id
      WHERE b.id = :board AND c.id = :card
      <q:param name="board" value="{id}" type="integer" />
      <q:param name="card" value="{card}" type="integer" />
    </q:query>
    <q:if condition="hook[0].webhook_url">
      <q:invoke name="told" url="{hook[0].webhook_url}" method="POST" timeout="5000" onerror="continue">
        <q:body>{"event": "card.done", "board": "{hook[0].board}", "card": {hook[0].id}, "title": "{hook[0].title}", "by": "{session.userName}"}</q:body>
      </q:invoke>
    </q:if>
  </q:function>

  <!-- ===== AI ===== -->

  <!-- the board's summary, written as it is read -->
  <q:set name="summarize" value="{query.summary}" default="" />
  <q:set name="question" value="{query.q}" default="" />
  <q:set name="lateQuestion" value="{query.late}" default="" />

  <q:action name="ask" method="POST">
    <q:param name="question" required="true" minlength="3" maxlength="300" />
    <q:redirect url="/board/{id}?tab=Ask&amp;q={urlencode(question)}" />
  </q:action>

  <!-- ===== Settings ===== -->

  <q:action name="saveSettings" method="POST" require_role="admin">
    <q:param name="webhook_url" type="url" default="" />
    <q:param name="issues_api" type="url" required="true" />
    <q:query name="saved" datasource="db">
      UPDATE boards SET webhook_url = NULLIF(:hook, ''), issues_api = :api WHERE id = :board
      <q:param name="hook" value="{webhook_url}" type="string" />
      <q:param name="api" value="{issues_api}" type="string" />
      <q:param name="board" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/board/{id}?tab=Settings" flash="Settings saved." />
  </q:action>

  <!-- a repository's open issues as cards of the first column, each once -->
  <q:action name="importIssues" method="POST" require_role="admin,member">
    <q:param name="repository" required="true" pattern="^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$" />
    <q:query name="board" datasource="db">
      SELECT b.issues_api, (SELECT id FROM columns WHERE board_id = b.id ORDER BY position LIMIT 1) AS first
      FROM boards b WHERE b.id = :board
      <q:param name="board" value="{id}" type="integer" />
    </q:query>
    <q:invoke name="issues" url="{board[0].issues_api}/repos/{repository}/issues" method="GET"
              responseFormat="json" timeout="10000" onerror="continue">
      <q:param name="state" value="open" />
      <q:param name="per_page" value="20" />
      <q:header name="Accept" value="application/vnd.github+json" />
    </q:invoke>
    <q:if condition="not issues_result.success">
      <q:redirect url="/board/{id}?tab=Settings" flash="Could not read {repository}: {issues_result.error.message}" flashType="error" />
    </q:if>
    <q:set name="count" value="0" type="number" />
    <q:loop items="{issues}" var="issue">
      <q:query name="known" datasource="db">
        SELECT id FROM cards WHERE board_id = :board AND source = :url
        <q:param name="board" value="{id}" type="integer" />
        <q:param name="url" value="{issue.html_url}" type="string" />
      </q:query>
      <q:if condition="known_result.recordCount == 0">
        <q:query name="added" datasource="db">
          INSERT INTO cards (board_id, column_id, title, description, labels, source)
          VALUES (:board, :column, :title, :body, 'issue', :url)
          <q:param name="board" value="{id}" type="integer" />
          <q:param name="column" value="{board[0].first}" type="integer" />
          <q:param name="title" value="{issue.title}" type="string" />
          <q:param name="body" value="{issue.body}" type="string" />
          <q:param name="url" value="{issue.html_url}" type="string" />
        </q:query>
        <q:set name="count" value="{count + 1}" type="number" />
      </q:if>
    </q:loop>
    <q:redirect url="/board/{id}" flash="{count} issues of {repository} imported." />
  </q:action>

  <!-- ===== What the page shows ===== -->

  <q:query name="board" datasource="db">
    SELECT id, name, description, webhook_url, issues_api FROM boards
    WHERE id = :board AND (:role = 'admin' OR id IN (SELECT board_id FROM members WHERE user_id = :user))
    <q:param name="board" value="{id}" type="integer" />
    <q:param name="role" value="{session.userRole}" type="string" />
    <q:param name="user" value="{session.userId}" type="integer" />
  </q:query>

  <q:query name="columns" datasource="db">
    SELECT k.id, k.name, k.wip_limit, k.is_done,
           LAG(k.id) OVER (ORDER BY k.position) AS prev_id,
           LEAD(k.id) OVER (ORDER BY k.position) AS next_id,
           (SELECT COUNT(*) FROM cards c WHERE c.column_id = k.id AND c.archived = 0) AS holding
    FROM columns k WHERE k.board_id = :board ORDER BY k.position
    <q:param name="board" value="{id}" type="integer" />
  </q:query>

  <q:query name="cards" datasource="db">
    SELECT c.id, c.column_id, c.title, c.labels, c.due_on, u.name AS assignee,
           CASE WHEN c.due_on IS NOT NULL AND c.due_on &lt; date('now') AND c.done_on IS NULL THEN 1 ELSE 0 END AS late
    FROM cards c LEFT JOIN users u ON u.id = c.assignee_id
    WHERE c.board_id = :board AND c.archived = 0
      AND (:who = '' OR u.name = :who)
      AND (:label = '' OR (',' || c.labels || ',') LIKE '%,' || :label || ',%')
      AND (:due = ''
           OR (:due = 'late' AND c.due_on &lt; date('now') AND c.done_on IS NULL)
           OR (:due = 'week' AND c.due_on BETWEEN date('now') AND date('now', '+7 days') AND c.done_on IS NULL))
    ORDER BY c.due_on IS NULL, c.due_on, c.id
    <q:param name="board" value="{id}" type="integer" />
    <q:param name="who" value="{who}" type="string" />
    <q:param name="label" value="{label}" type="string" />
    <q:param name="due" value="{due}" type="string" />
  </q:query>

  <q:query name="people" datasource="db">
    SELECT DISTINCT u.name FROM users u JOIN members m ON m.user_id = u.id WHERE m.board_id = :board ORDER BY u.name
    <q:param name="board" value="{id}" type="integer" />
  </q:query>

  <!-- the flow: how long the cards done took, from start to done, in days -->
  <q:query name="flow" datasource="db">
    SELECT c.title, u.name AS assignee, date(c.started_on) AS started, date(c.done_on) AS done,
           ROUND(julianday(c.done_on) - julianday(c.started_on), 1) AS days
    FROM cards c LEFT JOIN users u ON u.id = c.assignee_id
    WHERE c.board_id = :board AND c.done_on IS NOT NULL AND c.started_on IS NOT NULL
    ORDER BY c.done_on DESC LIMIT 20
    <q:param name="board" value="{id}" type="integer" />
  </q:query>
  <q:query name="average" datasource="db">
    SELECT ROUND(AVG(julianday(done_on) - julianday(started_on)), 1) AS days, COUNT(*) AS done
    FROM cards WHERE board_id = :board AND done_on IS NOT NULL AND started_on IS NOT NULL
    <q:param name="board" value="{id}" type="integer" />
  </q:query>

  <!-- the cards, as a knowledge base: questions answered with the cards they come from -->
  <q:query name="texts" datasource="db">
    SELECT '#' || c.id || ' ' || c.title || ' (' || k.name || ', ' || COALESCE(u.name, 'nobody') || ', due ' ||
           COALESCE(c.due_on, 'never') || '): ' || c.description AS content
    FROM cards c JOIN columns k ON k.id = c.column_id LEFT JOIN users u ON u.id = c.assignee_id
    WHERE c.board_id = :board AND c.archived = 0
    <q:param name="board" value="{id}" type="integer" />
  </q:query>

  <q:if condition="summarize">
    <q:llm name="summary" stream="true" temperature="0" maxTokens="200" onerror="continue">
      <q:message role="system">You summarise a Kanban board in three sentences: what is done, what is in progress, what is late or stuck.</q:message>
      <q:message role="user">{join(texts, '\n')}</q:message>
    </q:llm>
  </q:if>

  <q:if condition="question">
    <q:knowledge name="cards{id}" embedModel="nomic-embed-text" chunkSize="400" chunkOverlap="0">
      <q:source type="query" datasource="db">
        SELECT '#' || c.id || ' ' || c.title || ' (' || k.name || ', ' || COALESCE(u.name, 'nobody') || ', due ' ||
               COALESCE(c.due_on, 'never') || '): ' || c.description AS content
        FROM cards c JOIN columns k ON k.id = c.column_id LEFT JOIN users u ON u.id = c.assignee_id
        WHERE c.board_id = :board AND c.archived = 0
        <q:param name="board" value="{id}" type="integer" />
      </q:source>
    </q:knowledge>
    <q:llm name="answer" knowledge="cards{id}" top="4" temperature="0" onerror="continue">
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <q:if condition="lateQuestion">
    <q:agent name="late" maxIterations="5" timeout="120000" onerror="continue">
      <q:instruction>You say which cards of the board are late and who has them, using only the tools, in two or three sentences.</q:instruction>
      <q:tool name="late_cards" description="Cards not done whose due date has passed, with who has them">
        <q:function name="lateCards">
          <q:query name="rows" datasource="db">
            SELECT c.title, c.due_on, COALESCE(u.name, 'nobody') AS assignee, k.name AS column_name
            FROM cards c JOIN columns k ON k.id = c.column_id LEFT JOIN users u ON u.id = c.assignee_id
            WHERE c.board_id = :board AND c.archived = 0 AND k.is_done = 0 AND c.due_on &lt; date('now')
            ORDER BY c.due_on
            <q:param name="board" value="{id}" type="integer" />
          </q:query>
          <q:return value="{rows}" />
        </q:function>
      </q:tool>
      <q:tool name="workload" description="How many cards in progress each person has">
        <q:function name="workload">
          <q:query name="rows" datasource="db">
            SELECT COALESCE(u.name, 'nobody') AS assignee, COUNT(*) AS cards
            FROM cards c JOIN columns k ON k.id = c.column_id LEFT JOIN users u ON u.id = c.assignee_id
            WHERE c.board_id = :board AND c.archived = 0 AND k.is_done = 0 AND c.started_on IS NOT NULL
            GROUP BY u.name ORDER BY cards DESC
            <q:param name="board" value="{id}" type="integer" />
          </q:query>
          <q:return value="{rows}" />
        </q:function>
      </q:tool>
      <q:execute task="Which cards are late, and who has them?" />
    </q:agent>
  </q:if>

  <ui:window title="{board_result.recordCount == 1 and board[0].name or 'Board'}">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:link to="/">Boards</ui:link>
        <ui:spacer />
        <ui:text>{session.userName} ({session.userRole})</ui:text>
        <ui:link to="/logout">Sign out</ui:link>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <q:if condition="board_result.recordCount == 0">
        <ui:alert variant="danger">There is no board #{id} that you belong to.</ui:alert>
      </q:if>
      <q:else>
        <ui:header title="{board[0].name}" />
        <ui:text>{board[0].description}</ui:text>
        <ui:tabpanel open="{tab}">

          <ui:tab title="Board">
            <ui:hbox gap="sm">
              <ui:text>Who:</ui:text>
              <ui:link to="/board/{id}">everyone</ui:link>
              <q:loop items="{people}" var="person">
                <ui:link to="/board/{id}?who={urlencode(person.name)}">{person.name}</ui:link>
              </q:loop>
              <ui:text>Due:</ui:text>
              <ui:link to="/board/{id}?due=late">late</ui:link>
              <ui:link to="/board/{id}?due=week">this week</ui:link>
              <q:if condition="who or label or due">
                <ui:badge variant="info">filtered: {who} {label} {due}</ui:badge>
              </q:if>
            </ui:hbox>
            <q:if condition="session.userRole != 'viewer'">
              <ui:form on-submit="addCard" submit="Add a card">
                <ui:input bind="title" label="New card" placeholder="What needs doing?" />
              </ui:form>
            </q:if>
            <ui:hbox gap="md" stack-below="md">
              <q:loop items="{columns}" var="col">
                <ui:panel title="{col.name} {col.holding}{col.wip_limit and '/' + str(col.wip_limit) or ''}" grow="true">
                  <ui:vbox gap="sm">
                    <q:if condition="col.wip_limit and col.holding > col.wip_limit">
                      <ui:badge variant="danger">over the limit</ui:badge>
                    </q:if>
                    <q:loop items="{cards}" var="card">
                      <q:if condition="card.column_id == col.id">
                        <ui:card title="{card.title}">
                          <ui:hbox gap="sm">
                            <q:if condition="card.assignee"><ui:badge>{card.assignee}</ui:badge></q:if>
                            <q:if condition="card.due_on"><ui:badge variant="{card.late == 1 and 'danger' or 'info'}">due {card.due_on}</ui:badge></q:if>
                            <q:if condition="card.labels"><ui:link to="/board/{id}?label={urlencode(card.labels)}">{card.labels}</ui:link></q:if>
                          </ui:hbox>
                          <ui:hbox gap="sm">
                            <q:if condition="col.prev_id and session.userRole != 'viewer'">
                              <ui:button on-click="move" with="card={card.id}, to={col.prev_id}">◀</ui:button>
                            </q:if>
                            <ui:link to="/card/{card.id}">Open</ui:link>
                            <q:if condition="col.next_id and session.userRole != 'viewer'">
                              <ui:button on-click="move" with="card={card.id}, to={col.next_id}">▶</ui:button>
                            </q:if>
                          </ui:hbox>
                        </ui:card>
                      </q:if>
                    </q:loop>
                  </ui:vbox>
                </ui:panel>
              </q:loop>
            </ui:hbox>
          </ui:tab>

          <ui:tab title="Ask">
            <ui:panel title="Summary">
              <q:if condition="summarize">
                <ui:stream for="summary" />
              </q:if>
              <q:else>
                <ui:link to="/board/{id}?tab=Ask&amp;summary=1">Summarise the board</ui:link>
              </q:else>
            </ui:panel>
            <ui:panel title="Ask the board">
              <ui:form on-submit="ask" submit="Ask">
                <ui:input bind="question" label="Question" value="{question}" />
              </ui:form>
              <q:if condition="question">
                <q:if condition="answer_result.success and answer_result.found">
                  <ui:text>{answer}</ui:text>
                  <q:loop items="{answer_result.sources}" var="s">
                    <ui:text>[{s.n}] {s.text}</ui:text>
                  </q:loop>
                  <q:else>
                    <ui:alert variant="info">The cards say nothing about that.</ui:alert>
                  </q:else>
                </q:if>
              </q:if>
            </ui:panel>
            <ui:panel title="What is late?">
              <q:if condition="lateQuestion">
                <q:if condition="late_result.success">
                  <ui:text>{late}</ui:text>
                  <q:loop items="{late_result.actions}" var="a">
                    <ui:text>{a.call}</ui:text>
                  </q:loop>
                  <q:else>
                    <ui:alert variant="danger">The model did not answer: {late_result.error.message}</ui:alert>
                  </q:else>
                </q:if>
              </q:if>
              <q:else>
                <ui:link to="/board/{id}?tab=Ask&amp;late=1">Ask the agent</ui:link>
              </q:else>
            </ui:panel>
          </ui:tab>

          <ui:tab title="Flow">
            <q:if condition="average[0].done > 0">
              <ui:text>Done: {average[0].done}, in {average[0].days} days on average from start to done.</ui:text>
            </q:if>
            <q:else>
              <ui:text>No card done yet.</ui:text>
            </q:else>
            <ui:table source="{flow}" as="f">
              <ui:column key="title" label="Card" />
              <ui:column key="assignee" label="Who" />
              <ui:column key="started" label="Started" />
              <ui:column key="done" label="Done" />
              <ui:column key="days" label="Days" />
            </ui:table>
          </ui:tab>

          <ui:tab title="Settings">
            <q:if condition="session.userRole == 'admin'">
              <ui:panel title="The board">
                <ui:form on-submit="saveSettings" submit="Save">
                  <ui:input bind="webhook_url" label="Webhook told of a card done" value="{board[0].webhook_url}" />
                  <ui:input bind="issues_api" label="Issues from (GitHub, Gitea or Forgejo)" value="{board[0].issues_api}" />
                </ui:form>
              </ui:panel>
              <ui:panel title="Columns">
                <ui:table source="{columns}" as="k" edit="columns" datasource="db">
                  <ui:column key="name" label="Column" />
                  <ui:column key="wip_limit" label="Limit" />
                </ui:table>
              </ui:panel>
            </q:if>
            <q:if condition="session.userRole != 'viewer'">
              <ui:panel title="Import issues">
                <ui:form on-submit="importIssues" submit="Import">
                  <ui:input bind="repository" label="Repository (owner/name)" placeholder="danielgregorio/quantum" />
                </ui:form>
              </ui:panel>
            </q:if>
          </ui:tab>
        </ui:tabpanel>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
