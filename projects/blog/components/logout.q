<q:component name="Logout" type="page">
  <!--
    Quantum Blog - Logout
    Clears all session data and redirects to home
  -->

  <q:set name="application.basePath" value="/quantum-blog" scope="application" />

  <!-- Clear all session variables -->
  <q:set name="session.authenticated" value="" scope="session" />
  <q:set name="session.userId" value="" scope="session" />
  <q:set name="session.username" value="" scope="session" />
  <q:set name="session.displayName" value="" scope="session" />
  <q:set name="session.role" value="" scope="session" />

  <!-- Redirect to home -->
  <q:redirect url="{application.basePath}/" />

</q:component>
