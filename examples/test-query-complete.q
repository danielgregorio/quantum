<!-- Test Query Complete -->
<!-- Demonstrates all q:query patterns -->
<q:component name="TestQueryComplete" xmlns:q="https://quantum.lang/ns">

  <!-- Basic SELECT query -->
  <q:query name="allUsers" datasource="test-sqlite">
    SELECT id, name, email, created_at
    FROM users
    ORDER BY id ASC
    LIMIT 5
  </q:query>

  <!-- Query with parameters - uses :param_name binding -->
  <q:query name="userByName" datasource="test-sqlite">
    <q:param name="searchName" value="John" />
    SELECT id, name, email
    FROM users
    WHERE name LIKE :searchName
    LIMIT 1
  </q:query>

  <!-- Aggregate query -->
  <q:query name="userCount" datasource="test-sqlite">
    SELECT COUNT(*) as total FROM users
  </q:query>

  <!-- Query loop shorthand -->
  <q:set name="userList" type="array" value="[]" />
  <q:loop query="allUsers">
    <q:set name="userList" operation="append" value="{allUsers.name}" />
  </q:loop>

  <!-- Access query metadata -->
  <q:set name="recordCount" value="{allUsers_result.recordCount}" />

  <q:return value="Users: {userList} | Total: {recordCount}" />
</q:component>
