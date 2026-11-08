<q:component name="ApiSession">
  <!-- The API's sign in (API-1, API-3): whoever calls the API — a script, another program — signs in here once
       and keeps the session's cookie; the endpoints then know who it is, as the pages do. -->

  <q:endpoint method="POST" limit="10/minute"
              description="Sign in: the session's cookie is what the other endpoints know you by">
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
      <q:respond json="{ {'name': user[0].name, 'role': user[0].role} }" />
    </q:if>
    <!-- the same answer for a wrong password and an unknown e-mail -->
    <q:respond status="401" json="{ {'error': 'unauthenticated', 'message': 'Wrong e-mail or password.'} }" />
  </q:endpoint>

  <q:endpoint method="GET" description="Who is signed in">
    <q:if condition="session.authenticated">
      <q:respond json="{ {'name': session.userName, 'role': session.userRole} }" />
    </q:if>
    <q:respond status="401" json="{ {'error': 'unauthenticated', 'message': 'Sign in first.'} }" />
  </q:endpoint>

  <q:endpoint method="DELETE" description="Sign out">
    <q:set name="session.authenticated" value="false" type="boolean" />
    <q:set name="session.userId" value="" />
    <q:set name="session.userRole" value="" />
  </q:endpoint>
</q:component>
