<q:component name="Login">
  <q:action name="signin" method="POST">
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
      <q:redirect url="/" flash="Welcome, {user[0].name}!" />
    </q:if>
    <!-- The same message whether the address or the password is wrong. -->
    <q:redirect url="/login" flash="Wrong e-mail or password." flashType="error" />
  </q:action>

  <h1>Sign in</h1>
  <q:if condition="flash"><p class="flash-{flashType}">{flash}</p></q:if>
  <form method="POST">
    <input name="email" type="email" placeholder="E-mail" />
    <input name="password" type="password" placeholder="Password" />
    <button>Sign in</button>
  </form>
</q:component>
