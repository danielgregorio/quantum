<q:component name="Logout" type="page">

  <q:set name="application.basePath" value="/quantum-blog" scope="application" />

  <!-- Clear session -->
  <q:set name="session.authenticated" value="" scope="session" />
  <q:set name="session.username" value="" scope="session" />

  <!-- Redirect to home -->
  <q:redirect url="{application.basePath}/" />

</q:component>
