<q:component name="Assistant">
  <!-- The model never writes SQL: it picks a tool and its arguments. The
       tool is a read-only query you wrote; its q:param says the argument's
       type, and the model's value is converted to it before the query runs. -->
  <q:agent name="stock" maxIterations="4" timeout="60000" onerror="continue">
    <q:instruction>You help a shop owner. Use the tools to look at the data,
      then answer in one sentence.</q:instruction>

    <q:tool name="low_stock" description="Products with fewer units in stock than `below`">
      <q:param name="below" type="integer" default="5" />
      <q:function name="lowStock">
        <q:query name="rows" datasource="db">
          SELECT name, stock FROM products WHERE stock &lt; :below ORDER BY stock
          <q:param name="below" value="{below}" type="integer" />
        </q:query>
        <q:return value="{rows}" />
      </q:function>
    </q:tool>

    <q:execute task="Which products are running out of stock?" />
  </q:agent>

  <ui:window title="Stock assistant">
    <q:if condition="stock_result.success">
      <ui:text>{stock}</ui:text>
      <q:else>
        <ui:alert variant="warning">The assistant did not finish: {stock_result.error.message}</ui:alert>
      </q:else>
    </q:if>
    <!-- Every tool call the agent made, written out. -->
    <q:loop items="{stock_result.actions}" var="a">
      <ui:text>Called {a.call}</ui:text>
    </q:loop>
  </ui:window>
</q:component>
