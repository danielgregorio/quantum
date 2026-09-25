<q:component name="SignUp">
  <q:action name="register" method="POST">
    <q:param name="name" required="true" minlength="2" maxlength="80" />
    <q:param name="email" type="email" required="true" />
    <q:param name="password" required="true" minlength="12" />

    <q:query name="taken" datasource="db">
      SELECT id FROM users WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:if condition="taken_result.recordCount > 0">
      <q:redirect url="/" flash="There is already an account for {email}." flashType="error" />
    </q:if>

    <!-- hashPassword: bcrypt, with a new salt every time. -->
    <q:query name="created" datasource="db">
      INSERT INTO users (email, name, password_hash) VALUES (:email, :name, :hash)
      <q:param name="email" value="{email}" type="string" />
      <q:param name="name" value="{name}" type="string" />
      <q:param name="hash" value="{hashPassword(password)}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Account created for {name}." />
  </q:action>

  <h1>Create an account</h1>
  <q:if condition="flash"><p class="flash-{flashType}">{flash}</p></q:if>
  <form method="POST">
    <input name="name" placeholder="Name" />
    <input name="email" type="email" placeholder="E-mail" />
    <input name="password" type="password" placeholder="Password (12 characters or more)" />
    <button>Create account</button>
  </form>
</q:component>
