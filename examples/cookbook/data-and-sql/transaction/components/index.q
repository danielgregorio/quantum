<q:component name="Bank">
  <q:action name="transfer" method="POST">
    <q:param name="amount" type="integer" required="true" min="1" />

    <q:query name="source" datasource="db">
      SELECT balance FROM accounts WHERE id = 1
    </q:query>
    <q:if condition="source.balance &lt; amount">
      <q:redirect url="/" flash="Not enough money in Ana's account." flashType="error" />
    </q:if>

    <!-- The debit, the credit and the log line commit together. If one of
         them fails, the ones before it are undone and the page stops with
         the error: no money appears or disappears. -->
    <q:transaction datasource="db">
      <q:query name="debit">
        UPDATE accounts SET balance = balance - :amount WHERE id = 1
        <q:param name="amount" value="{amount}" type="integer" />
      </q:query>
      <q:query name="credit">
        UPDATE accounts SET balance = balance + :amount WHERE id = 2
        <q:param name="amount" value="{amount}" type="integer" />
      </q:query>
      <q:query name="logged">
        INSERT INTO transfers (from_id, to_id, amount) VALUES (1, 2, :amount)
        <q:param name="amount" value="{amount}" type="integer" />
      </q:query>
    </q:transaction>

    <q:redirect url="/" flash="Moved {amount} from Ana to Bruno." />
  </q:action>

  <q:query name="accounts" datasource="db">
    SELECT owner, balance FROM accounts ORDER BY id
  </q:query>

  <ui:window title="Bank">
    <q:if condition="flash">
      <ui:alert variant="info">{flash}</ui:alert>
    </q:if>
    <q:loop query="accounts">
      <ui:text>{accounts.owner}: {accounts.balance}</ui:text>
    </q:loop>
    <ui:form on-submit="transfer">
      <ui:input bind="amount" placeholder="Amount" />
      <ui:button variant="primary">Move from Ana to Bruno</ui:button>
    </ui:form>
  </ui:window>
</q:component>
