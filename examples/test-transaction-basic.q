<q:component name="TestTransactionBasic">
  <!-- Test: Basic transaction with multiple queries -->

  <q:transaction isolationLevel="READ_COMMITTED">
    <q:query datasource="test-sqlite" name="updateUser">
      UPDATE users SET status = 'updated' WHERE id = 1
    </q:query>

    <q:query datasource="test-sqlite" name="logActivity">
      INSERT INTO activity_log (user_id, action) VALUES (1, 'transaction_test')
    </q:query>
  </q:transaction>

  <!-- Expected: Transaction executes both queries atomically -->
  Transaction completed successfully
</q:component>
