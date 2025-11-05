<q:component name="TestAuthLogin">
  <!-- Test: User login with session authentication -->

  <q:action name="login" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" type="string" required="true" />

    <!-- Simulate successful login -->
    <q:set name="session.authenticated" value="true" />
    <q:set name="session.userId" value="1" />
    <q:set name="session.userEmail" value="{email}" />
    <q:set name="session.userRole" value="user" />

    <q:flash message="Login successful!" type="success" />
  </q:action>

  <!-- Expected: Session variables set for authenticated user -->
  Login action configured
</q:component>
