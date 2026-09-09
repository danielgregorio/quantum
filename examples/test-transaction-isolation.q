<q:component name="TestTransactionIsolation">
  <!-- Test: Different isolation levels -->

  <q:transaction isolationLevel="REPEATABLE_READ">
    <q:query datasource="test-sqlite" name="readData">
      SELECT * FROM users WHERE id = 1
    </q:query>

    <q:set name="userName" value="{readData.name}" />
  </q:transaction>

  <!-- Expected: Isolation level set correctly -->
  Read with REPEATABLE_READ isolation: User = {userName}
</q:component>
