<q:component name="Logout">
  <!-- Clears the session and goes home (ACT-7: q:redirect ends the page). -->
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userId" value="" />
  <q:set name="session.userRole" value="" />
  <q:set name="session.userName" value="" />
  <q:redirect url="/" flash="You are signed out." />
</q:component>
