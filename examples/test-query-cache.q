<q:component name="TestQueryCache">
  <!-- Test: Query caching with TTL -->

  <q:query datasource="test-sqlite" name="activeUsers" cache="5m">
    SELECT * FROM users WHERE status = 'active' ORDER BY name
  </q:query>

  <!-- Expected: Query result cached for 5 minutes -->
  Found {activeUsers.recordCount} active users (cached for 5 minutes)
</q:component>
