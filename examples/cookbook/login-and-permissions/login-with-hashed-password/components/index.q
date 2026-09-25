<q:component name="Home" require_auth="true">
  <q:if condition="flash"><p>{flash}</p></q:if>
  <h1>Hello, {session.userName}</h1>
  <p>You are signed in as {session.userRole}.</p>
</q:component>
