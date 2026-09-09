<q:component name="TestAuthProtected" require_auth="true">
  <!-- Test: Protected component requiring authentication -->

  <q:set name="userEmail" value="{session.userEmail}" />

  <!-- Expected: Only accessible if session.authenticated is true -->
  Welcome back, {userEmail}!
  This is a protected page.
</q:component>
