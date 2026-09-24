<q:component name="LoginSimple">
  <q:param name="flash" type="string" default="" />

  <q:action name="login" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" type="string" required="true" />

    <q:set name="validEmail" value="admin@quantum.dev" />
    <q:set name="validPassword" value="quantum123" />

    <q:set name="emailMatch" value="{email} == {validEmail}" />
    <q:set name="passwordMatch" value="{password} == {validPassword}" />

    <q:if condition="{emailMatch}">
      <q:if condition="{passwordMatch}">
        <q:set name="session.authenticated" value="true" />
        <q:set name="session.userId" value="1" />
        <q:set name="session.userName" value="Admin" />
        <q:set name="session.userRole" value="admin" />
        <q:redirect url="/dashboard" flash="Login successful!" />
      </q:if>
    </q:if>

    <q:redirect url="/login_simple" flash="Invalid credentials" />
  </q:action>

  <html>
  <head><title>Login</title></head>
  <body>
    <h1>Login</h1>
    <p>{flash}</p>
    <form method="POST">
      <input type="email" name="email" placeholder="Email" required="required" />
      <input type="password" name="password" placeholder="Password" required="required" />
      <button type="submit">Login</button>
    </form>
    <p>Demo: admin @ quantum.dev / quantum123</p>
  </body>
  </html>
</q:component>
