<q:component name="Logout">
  <!-- Phase G: Logout Action -->

  <!-- Clear all authentication session data -->
  <q:set name="session.authenticated" value="false" />
  <q:set name="session.userId" value="" />
  <q:set name="session.userName" value="" />
  <q:set name="session.userRole" value="" />
  <q:set name="session.loginTime" value="" />
  <q:set name="session.sessionExpiry" value="" />

  <!-- Redirect to login with success message -->
  <q:redirect url="/login" flash="You have been logged out successfully." flashType="info" />
</q:component>
