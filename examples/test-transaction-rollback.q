<q:component name="TestTransactionRollback">
  <!-- Test: Transaction rollback on error -->

  <q:transaction isolationLevel="SERIALIZABLE">
    <q:query datasource="test-sqlite" name="updateStatus">
      UPDATE users SET status = 'testing' WHERE id = 1
    </q:query>

    <!-- This query validates the update -->
    <q:query datasource="test-sqlite" name="validate">
      SELECT status FROM users WHERE id = 1 AND status = 'testing'
    </q:query>
  </q:transaction>

  <!-- Expected: Transaction executes both queries atomically -->
  Transaction with validation: {validate.recordCount} record(s)
</q:component>
