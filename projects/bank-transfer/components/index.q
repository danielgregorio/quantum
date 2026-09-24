<q:component name="BankTransfer">
  <!-- Money moves between two accounts inside one q:transaction (DB-4): the
       debit, the credit and the history row commit together, or none does. -->

  <q:action name="transfer" method="POST">
    <q:param name="from_account" type="integer" required="true" />
    <q:param name="to_account" type="integer" required="true" />
    <q:param name="amount" type="decimal" required="true" min="0.01" />

    <q:if condition="from_account == to_account">
      <q:redirect url="/" flash="Choose two different accounts." flashType="error" />
    </q:if>

    <!-- Both accounts exist and the source can pay. A transfer to an account
         that does not exist would otherwise debit one side and credit nobody. -->
    <q:query name="check" datasource="db">
      SELECT (SELECT COUNT(*) FROM accounts WHERE id = :from_account) AS from_found,
             (SELECT COUNT(*) FROM accounts WHERE id = :to_account) AS to_found,
             COALESCE((SELECT balance FROM accounts WHERE id = :from_account), 0) AS from_balance
      <q:param name="from_account" type="integer" value="{from_account}" />
      <q:param name="to_account" type="integer" value="{to_account}" />
    </q:query>
    <q:if condition="check.from_found == 0 or check.to_found == 0">
      <q:redirect url="/" flash="There is no such account." flashType="error" />
    </q:if>
    <q:if condition="check.from_balance &lt; amount">
      <q:redirect url="/" flash="Insufficient funds in account {from_account}." flashType="error" />
    </q:if>

    <!-- If any of the three fails (the CHECK on the balance refuses an
         overdraft that slipped past the check above), all three roll back. -->
    <q:transaction datasource="db" isolationLevel="READ_COMMITTED">
      <q:query name="debit">
        UPDATE accounts SET balance = balance - :amount WHERE id = :from_account
        <q:param name="amount" type="decimal" value="{amount}" />
        <q:param name="from_account" type="integer" value="{from_account}" />
      </q:query>
      <q:query name="credit">
        UPDATE accounts SET balance = balance + :amount WHERE id = :to_account
        <q:param name="amount" type="decimal" value="{amount}" />
        <q:param name="to_account" type="integer" value="{to_account}" />
      </q:query>
      <q:query name="history">
        INSERT INTO transfers (from_account_id, to_account_id, amount)
        VALUES (:from_account, :to_account, :amount)
        <q:param name="from_account" type="integer" value="{from_account}" />
        <q:param name="to_account" type="integer" value="{to_account}" />
        <q:param name="amount" type="decimal" value="{amount}" />
      </q:query>
    </q:transaction>

    <q:redirect url="/" flash="Transferred ${amount} from account {from_account} to {to_account}." />
  </q:action>

  <q:query name="accounts" datasource="db">
    SELECT id, account_name, balance FROM accounts ORDER BY id
  </q:query>

  <q:query name="transfers" datasource="db">
    SELECT t.transfer_date, t.amount, t.from_account_id, t.to_account_id,
           a1.account_name AS from_name, a2.account_name AS to_name
    FROM transfers t
    JOIN accounts a1 ON t.from_account_id = a1.id
    JOIN accounts a2 ON t.to_account_id = a2.id
    ORDER BY t.id DESC
    LIMIT 10
  </q:query>

  <html>
  <head>
    <meta charset="utf-8" />
    <title>Bank Transfer</title>
    <style>
      body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
      form { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
      form div { margin-bottom: 15px; }
      label { display: block; margin-bottom: 5px; font-weight: bold; }
      input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
      button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
      table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
      th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
      th { background: #f8f9fa; }
      .flash { padding: 12px; border-radius: 4px; margin-bottom: 20px; }
      .flash-success { background: #d4edda; color: #155724; }
      .flash-error { background: #f8d7da; color: #721c24; }
    </style>
  </head>
  <body>
    <h1>Bank Transfer</h1>

    <q:if condition="flash">
      <div class="flash flash-{flashType}">{flash}</div>
    </q:if>

    <h2>Transfer money between accounts</h2>
    <form method="POST" action="/?action=transfer">
      <div>
        <label for="from_account">From account ID</label>
        <input type="number" id="from_account" name="from_account" required />
      </div>
      <div>
        <label for="to_account">To account ID</label>
        <input type="number" id="to_account" name="to_account" required />
      </div>
      <div>
        <label for="amount">Amount</label>
        <input type="number" id="amount" name="amount" step="0.01" min="0.01" required />
      </div>
      <button type="submit">Transfer</button>
    </form>

    <h2>Account balances</h2>
    <table>
      <thead><tr><th>ID</th><th>Account</th><th>Balance</th></tr></thead>
      <tbody>
        <q:loop query="accounts">
          <tr><td>{accounts.id}</td><td>{accounts.account_name}</td><td>${accounts.balance}</td></tr>
        </q:loop>
      </tbody>
    </table>

    <h2>Recent transfers</h2>
    <table>
      <thead><tr><th>Date</th><th>From</th><th>To</th><th>Amount</th></tr></thead>
      <tbody>
        <q:loop query="transfers">
          <tr>
            <td>{transfers.transfer_date}</td>
            <td>{transfers.from_name} (ID {transfers.from_account_id})</td>
            <td>{transfers.to_name} (ID {transfers.to_account_id})</td>
            <td>${transfers.amount}</td>
          </tr>
        </q:loop>
      </tbody>
    </table>
  </body>
  </html>
</q:component>
