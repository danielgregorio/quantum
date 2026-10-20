<q:component name="SignUp">
  <!-- M1 (SPEC UI-9): the form takes each field's rules from the q:action it
       posts to. Open the page source: name has required minlength="3",
       age has type="number" min="18". When the server refuses a field, the
       page comes back with the values sent and each error next to its field.
       Serve it from an app's components/ with `quantum start`. -->

  <q:action name="sign-up" method="POST">
    <q:param name="name" required="true" minlength="3" maxlength="60" />
    <q:param name="age" type="integer" min="18" max="120" />
    <q:param name="plan" enum="free,pro" default="free" />
    <q:param name="notices" default="off" />
    <q:redirect url="/form-rules" flash="Signed up: {name} ({plan}, notices {notices})" />
  </q:action>

  <ui:window title="Sign up">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="sign-up">
      <ui:formitem label="Name"><ui:input bind="name" /></ui:formitem>
      <ui:formitem label="Age"><ui:input bind="age" /></ui:formitem>
      <ui:formitem label="Plan"><ui:select bind="plan" /></ui:formitem>
      <ui:checkbox bind="notices" label="Receive notices" />
      <ui:button variant="primary">Sign up</ui:button>
    </ui:form>
  </ui:window>
</q:component>
