<q:component name="Login">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />
  <!--
    Sign in. On a new blog there is no user yet: the page offers to create the
    admin account instead, once. There is no default password.
  -->

  <!-- Already signed in: nothing to do here. A guard also runs before the actions. -->
  <q:if condition="session.authenticated">
    <q:redirect url="/admin" />
  </q:if>

  <q:action name="setup" method="POST">
    <q:param name="username" required="true" minlength="3" maxlength="40" pattern="^[a-z0-9_]+$" />
    <q:param name="display_name" required="true" minlength="2" maxlength="80" />
    <q:param name="password" required="true" minlength="12" />
    <q:param name="password2" required="true" />

    <!-- Only while there is no user: after that, this form does not exist. -->
    <q:query name="existing" datasource="blog-db">SELECT COUNT(*) AS n FROM users</q:query>
    <q:if condition="existing.n > 0">
      <q:redirect url="/login" flash="The blog already has an admin." flashType="error" />
    </q:if>
    <q:if condition="password != password2">
      <q:redirect url="/login" flash="The passwords do not match." flashType="error" />
    </q:if>

    <q:query name="createAdmin" datasource="blog-db">
      INSERT INTO users (username, password_hash, role, display_name)
      VALUES (:username, :hash, 'admin', :name)
      <q:param name="username" value="{username}" type="string" />
      <q:param name="hash" value="{hashPassword(password)}" type="string" />
      <q:param name="name" value="{display_name}" type="string" />
    </q:query>
    <q:redirect url="/login" flash="Account created. Sign in." />
  </q:action>

  <q:action name="signIn" method="POST">
    <q:param name="username" required="true" />
    <q:param name="password" required="true" />

    <q:query name="account" datasource="blog-db">
      SELECT id, password_hash, role, display_name FROM users WHERE username = :username
      <q:param name="username" value="{username}" type="string" />
    </q:query>

    <q:if condition="account_result.recordCount == 1 and verifyPassword(password, account.password_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userId" value="{account.id}" />
      <q:set name="session.userRole" value="{account.role}" />
      <q:set name="session.userName" value="{account.display_name}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" type="string" />
      <q:redirect url="/admin" />
    </q:if>
    <!-- Same message for an unknown user and a wrong password. -->
    <q:redirect url="/login" flash="Wrong username or password." flashType="error" />
  </q:action>

  <q:query name="users" datasource="blog-db">SELECT COUNT(*) AS n FROM users</q:query>

  <html>
  <head>
    <title>Sign in - Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />
    <main class="main">
      <div class="panel" style="max-width: 420px; margin: 40px auto;">
        <q:if condition="flash">
          <div class="flash flash-{flashType}">{flash}</div>
        </q:if>

        <q:if condition="users.n == 0">
          <h2>Create the admin account</h2>
          <p>This blog has no user yet. The account you create here is its admin.</p>
          <form method="POST" action="/login">
            <input type="hidden" name="action" value="setup" />
            <label>Username (lowercase letters, digits, _)</label>
            <input type="text" name="username" required="required" />
            <label>Display name</label>
            <input type="text" name="display_name" required="required" />
            <label>Password (12 characters or more)</label>
            <input type="password" name="password" required="required" />
            <label>Password again</label>
            <input type="password" name="password2" required="required" />
            <button type="submit" class="btn-primary">Create account</button>
          </form>
        </q:if>
        <q:else>
          <h2>Sign in</h2>
          <form method="POST" action="/login">
            <input type="hidden" name="action" value="signIn" />
            <label>Username</label>
            <input type="text" name="username" required="required" />
            <label>Password</label>
            <input type="password" name="password" required="required" />
            <button type="submit" class="btn-primary">Sign in</button>
          </form>
        </q:else>
      </div>
    </main>
    <Footer />
  </body>
  </html>
</q:component>
