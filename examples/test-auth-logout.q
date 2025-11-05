<q:component name="TestAuthLogout">
  <!-- Test: User logout clearing session -->

  <q:action name="logout" method="POST">
    <!-- Clear authentication session variables -->
    <q:set name="session.authenticated" value="false" />
    <q:set name="session.userId" value="" />
    <q:set name="session.userEmail" value="" />
    <q:set name="session.userRole" value="" />

    <q:redirect url="/login" flash="You have been logged out." />
  </q:action>

  <!-- Expected: Session cleared, user redirected to login -->
  Logout action configured
</q:component>
