<q:component name="TestAuthRole" require_auth="true" require_role="admin">
  <!-- Test: Role-based access control (RBAC) -->

  <!-- Expected: Only accessible if user has 'admin' role -->
  Admin Panel
  User role: {session.userRole}
  This page requires admin privileges.
</q:component>
