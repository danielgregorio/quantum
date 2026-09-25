<q:component name="Signup">
  <q:action name="join" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="email" type="email" required="true" />

    <q:query name="taken" datasource="db">
      SELECT id FROM members WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:if condition="taken_result.recordCount > 0">
      <q:redirect url="/" flash="{email} is already a member." flashType="error" />
    </q:if>

    <q:query name="added" datasource="db">
      INSERT INTO members (name, email) VALUES (:name, :email)
      <q:param name="name" value="{name}" type="string" />
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Welcome, {name}!" />
  </q:action>

  <h1>Join</h1>
  <q:if condition="flash"><p class="flash-{flashType}">{flash}</p></q:if>
  <form method="POST" action="/?action=join">
    <input name="name" />
    <input name="email" type="email" />
    <button>Join</button>
  </form>
</q:component>
