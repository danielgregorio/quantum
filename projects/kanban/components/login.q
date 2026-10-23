<q:component name="Login">
  <!-- Who is signing in: the same message for a wrong password and an unknown e-mail. -->
  <q:if condition="session.authenticated">
    <q:redirect url="/" />
  </q:if>

  <q:action name="signIn" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" required="true" />
    <q:query name="user" datasource="db">
      SELECT id, name, role, password_hash FROM users WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:if condition="user_result.recordCount == 1 and verifyPassword(password, user[0].password_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userId" value="{user[0].id}" />
      <q:set name="session.userName" value="{user[0].name}" />
      <q:set name="session.userRole" value="{user[0].role}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/" />
    </q:if>
    <q:redirect url="/login" flash="Wrong e-mail or password." flashType="error" />
  </q:action>

  <ui:window title="Kanban">
    <ui:vbox gap="md" padding="lg" width="420">
      <ui:header title="Kanban" />
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'info'}">{flash}</ui:alert>
      </q:if>
      <q:if condition="query.expired">
        <ui:alert variant="info">Your session expired. Sign in again.</ui:alert>
      </q:if>
      <ui:panel title="Sign in">
        <ui:form on-submit="signIn" submit="Sign in">
          <ui:input bind="email" type="email" label="E-mail" />
          <ui:input bind="password" type="password" label="Password" />
        </ui:form>
      </ui:panel>
      <ui:text>Demo: ana@, bruno@ or carla@example.com, password kanban-demo.</ui:text>
    </ui:vbox>
  </ui:window>
</q:component>
