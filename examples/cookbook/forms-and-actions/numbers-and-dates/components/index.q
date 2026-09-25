<q:component name="Expenses">
  <q:action name="split" method="POST">
    <!-- decimal and integer arrive as numbers, date as a checked date:
         the arithmetic below needs no conversion. -->
    <q:param name="amount" type="decimal" required="true" min="0.01" max="10000" />
    <q:param name="people" type="integer" required="true" min="1" max="50" />
    <q:param name="spent_on" type="date" required="true" />
    <q:query name="saved" datasource="db">
      INSERT INTO expenses (amount, people, spent_on) VALUES (:amount, :people, :spent_on)
      <q:param name="amount" value="{amount}" type="decimal" />
      <q:param name="people" value="{people}" type="integer" />
      <q:param name="spent_on" value="{spent_on}" type="string" />
    </q:query>
    <q:redirect url="/" flash="{amount} on {spent_on}: {round(amount / people, 2)} each." />
  </q:action>

  <ui:window title="Split an expense">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <!-- The form gets type="number" (with min and max) and type="date". -->
    <ui:form on-submit="split" submit="Split">
      <ui:formitem label="Amount"><ui:input bind="amount" /></ui:formitem>
      <ui:formitem label="People"><ui:input bind="people" /></ui:formitem>
      <ui:formitem label="Date"><ui:input bind="spent_on" /></ui:formitem>
    </ui:form>
  </ui:window>
</q:component>
