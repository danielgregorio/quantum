<q:component name="Logout">
  <!-- A page that clears the session and redirects (ACT-7). -->
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userName" value="" />
  <q:set name="session.userRole" value="" />
  <q:redirect url="/login" flash="You are signed out." />
</q:component>
