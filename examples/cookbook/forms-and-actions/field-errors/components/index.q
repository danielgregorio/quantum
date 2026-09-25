<q:component name="Guests">
  <!-- The rules are written once, on the action. The form reads them (UI-9)
       and the server checks them again (ACT-2), every field at once. -->
  <q:action name="register" method="POST">
    <q:param name="name" required="true" minlength="2" maxlength="60" />
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="integer" required="true" min="18" max="120" />
    <q:query name="added" datasource="db">
      INSERT INTO guests (name, email, age) VALUES (:name, :email, :age)
      <q:param name="name" value="{name}" type="string" />
      <q:param name="email" value="{email}" type="string" />
      <q:param name="age" value="{age}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="{name} is on the list." />
  </q:action>

  <ui:window title="Guest list">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="register">
      <ui:formitem label="Name"><ui:input bind="name" /></ui:formitem>
      <ui:formitem label="E-mail"><ui:input bind="email" /></ui:formitem>
      <ui:formitem label="Age"><ui:input bind="age" /></ui:formitem>
      <ui:button variant="primary">Add guest</ui:button>
    </ui:form>
  </ui:window>
</q:component>
