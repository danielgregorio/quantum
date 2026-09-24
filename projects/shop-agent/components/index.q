<q:component name="ShopAgent">
  <!-- Ask the shop's data. A q:agent answers by calling the tools below:
       read-only queries with parameters; the model never writes SQL. Every
       call it made is listed with the answer (IA-4). When the model server
       fails, the page says so (IA-5). -->

  <q:action name="ask" method="POST">
    <q:param name="question" required="true" minlength="3" maxlength="300" />
    <q:redirect url="/?q={urlencode(question)}" />
  </q:action>

  <q:set name="question" value="{query.q}" default="" />
  <q:set name="question" value="{trim(question)}" />

  <q:if condition="question">
    <q:agent name="agent" model="phi3" maxIterations="5" timeout="240000" onerror="continue">
      <q:instruction>You answer questions about a shop using only the tools. Call a tool, read its result, then answer in one or two sentences with the numbers from the result. If the tools cannot answer, say so.</q:instruction>

      <q:tool name="find_products" description="Products whose name or category contains the text, with price and stock">
        <q:param name="text" type="string" required="true" />
        <q:function name="findProducts">
          <q:query name="rows" datasource="db">
            SELECT name, category, price, stock FROM products
            WHERE name LIKE '%' || :text || '%' OR category LIKE '%' || :text || '%'
            ORDER BY name
            <q:param name="text" value="{text}" type="string" />
          </q:query>
          <q:return value="{rows}" />
        </q:function>
      </q:tool>

      <q:tool name="low_stock" description="Products with fewer than 'below' units in stock">
        <q:param name="below" type="integer" required="true" />
        <q:function name="lowStock">
          <q:query name="rows" datasource="db">
            SELECT name, stock FROM products WHERE stock &lt; :below ORDER BY stock
            <q:param name="below" value="{below}" type="integer" />
          </q:query>
          <q:return value="{rows}" />
        </q:function>
      </q:tool>

      <q:tool name="orders_by_status" description="Orders with a status: open, shipped or cancelled">
        <q:param name="status" type="string" required="true" />
        <q:function name="ordersByStatus">
          <q:query name="rows" datasource="db">
            SELECT o.id, c.name AS customer, p.name AS product, o.quantity, o.ordered_on
            FROM orders o JOIN customers c ON c.id = o.customer_id JOIN products p ON p.id = o.product_id
            WHERE o.status = lower(:status) ORDER BY o.ordered_on
            <q:param name="status" value="{status}" type="string" />
          </q:query>
          <q:return value="{rows}" />
        </q:function>
      </q:tool>

      <q:tool name="customer_orders" description="The orders of customers whose name contains the text">
        <q:param name="name" type="string" required="true" />
        <q:function name="customerOrders">
          <q:query name="rows" datasource="db">
            SELECT c.name AS customer, p.name AS product, o.quantity, o.status, o.ordered_on
            FROM orders o JOIN customers c ON c.id = o.customer_id JOIN products p ON p.id = o.product_id
            WHERE c.name LIKE '%' || :name || '%' ORDER BY o.ordered_on
            <q:param name="name" value="{name}" type="string" />
          </q:query>
          <q:return value="{rows}" />
        </q:function>
      </q:tool>

      <q:execute task="{question}" />
    </q:agent>
  </q:if>

  <ui:window title="Shop agent">
    <ui:vbox gap="md" padding="lg">
      <ui:header title="Ask the shop" />
      <q:if condition="flash">
        <ui:alert variant="danger">{flash}</ui:alert>
      </q:if>

      <ui:form on-submit="ask">
        <ui:hbox gap="sm" stack-below="sm">
          <ui:input bind="question" value="{question}" placeholder="Which products are almost out of stock?" grow="true" />
          <ui:button variant="primary">Ask</ui:button>
        </ui:hbox>
      </ui:form>

      <q:if condition="question">
        <q:if condition="not agent_result.success">
          <ui:alert variant="danger" id="agent-error">The agent could not answer: {agent_result.error.message}</ui:alert>
          <q:else>
            <ui:panel title="Answer">
              <ui:text id="answer">{agent}</ui:text>
            </ui:panel>
          </q:else>
        </q:if>
        <q:if condition="agent_result.actions">
          <ui:panel title="What the agent looked up">
            <ui:list source="{agent_result.actions}" as="a">
              <ui:item><ui:text>{a.call}: {len(a.result)} rows</ui:text></ui:item>
            </ui:list>
          </ui:panel>
        </q:if>
      </q:if>
    </ui:vbox>
  </ui:window>
</q:component>
