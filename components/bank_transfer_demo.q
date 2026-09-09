<q:component name="BankTransferDemo">
  <!-- Phase D: Database Backend - Transaction Example -->

  <h1>Bank Transfer Demo</h1>

  <q:if condition="{flash}">
    <div class="flash-{flashType}">
      <p>{flash}</p>
    </div>
  </q:if>

  <h2>Transfer Money Between Accounts</h2>

  <form method="POST" action="/bank_transfer_demo?action=transfer">
    <div>
      <label for="from_account">From Account ID:</label>
      <input type="number" id="from_account" name="from_account" required />
    </div>

    <div>
      <label for="to_account">To Account ID:</label>
      <input type="number" id="to_account" name="to_account" required />
    </div>

    <div>
      <label for="amount">Amount:</label>
      <input type="number" id="amount" name="amount" step="0.01" min="0.01" required />
    </div>

    <button type="submit">Transfer</button>
  </form>

  <!-- Action: Transfer money atomically using transaction -->
  <q:action name="transfer" method="POST">
    <q:param name="from_account" type="integer" required="true" />
    <q:param name="to_account" type="integer" required="true" />
    <q:param name="amount" type="decimal" required="true" />

    <!-- Validate amount -->
    <q:if condition="{amount} &lt;= 0">
      <q:redirect url="/bank_transfer_demo" flash="Amount must be greater than zero" />
    </q:if>

    <!-- Use transaction to ensure atomicity -->
    <q:transaction isolationLevel="READ_COMMITTED">
      <!-- Debit from source account -->
      <q:query datasource="default" name="debit">
        UPDATE accounts
        SET balance = balance - :amount
        WHERE id = :from_account AND balance >= :amount
        <q:param name="amount" type="decimal" value="{amount}" />
        <q:param name="from_account" type="integer" value="{from_account}" />
      </q:query>

      <!-- Credit to destination account -->
      <q:query datasource="default" name="credit">
        UPDATE accounts
        SET balance = balance + :amount
        WHERE id = :to_account
        <q:param name="amount" type="decimal" value="{amount}" />
        <q:param name="to_account" type="integer" value="{to_account}" />
      </q:query>

      <!-- Record transfer in history -->
      <q:query datasource="default" name="history">
        INSERT INTO transfers (from_account_id, to_account_id, amount, transfer_date)
        VALUES (:from_account, :to_account, :amount, NOW())
        <q:param name="from_account" type="integer" value="{from_account}" />
        <q:param name="to_account" type="integer" value="{to_account}" />
        <q:param name="amount" type="decimal" value="{amount}" />
      </q:query>
    </q:transaction>

    <q:redirect url="/bank_transfer_demo"
                flash="Transfer of ${amount} from account {from_account} to {to_account} completed successfully!" />
  </q:action>

  <!-- Display account balances -->
  <h2>Account Balances</h2>

  <q:query datasource="default" name="accounts">
    SELECT id, account_name, balance
    FROM accounts
    ORDER BY id
  </q:query>

  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Account Name</th>
        <th>Balance</th>
      </tr>
    </thead>
    <tbody>
      <q:loop query="accounts">
        <tr>
          <td>{accounts.id}</td>
          <td>{accounts.account_name}</td>
          <td>${accounts.balance}</td>
        </tr>
      </q:loop>
    </tbody>
  </table>

  <!-- Display recent transfers -->
  <h2>Recent Transfers</h2>

  <q:query datasource="default" name="transfers">
    SELECT t.*,
           a1.account_name as from_name,
           a2.account_name as to_name
    FROM transfers t
    JOIN accounts a1 ON t.from_account_id = a1.id
    JOIN accounts a2 ON t.to_account_id = a2.id
    ORDER BY t.transfer_date DESC
    LIMIT 10
  </q:query>

  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>From</th>
        <th>To</th>
        <th>Amount</th>
      </tr>
    </thead>
    <tbody>
      <q:loop query="transfers">
        <tr>
          <td>{transfers.transfer_date}</td>
          <td>{transfers.from_name} (ID: {transfers.from_account_id})</td>
          <td>{transfers.to_name} (ID: {transfers.to_account_id})</td>
          <td>${transfers.amount}</td>
        </tr>
      </q:loop>
    </tbody>
  </table>

  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }

    form {
      background: #f5f5f5;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 30px;
    }

    form div {
      margin-bottom: 15px;
    }

    label {
      display: block;
      margin-bottom: 5px;
      font-weight: bold;
    }

    input {
      width: 100%;
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }

    button {
      background: #007bff;
      color: white;
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }

    button:hover {
      background: #0056b3;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 30px;
    }

    th, td {
      padding: 10px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }

    th {
      background: #f8f9fa;
      font-weight: bold;
    }

    .flash-success {
      background: #d4edda;
      border: 1px solid #c3e6cb;
      color: #155724;
      padding: 12px;
      border-radius: 4px;
      margin-bottom: 20px;
    }

    .flash-error {
      background: #f8d7da;
      border: 1px solid #f5c6cb;
      color: #721c24;
      padding: 12px;
      border-radius: 4px;
      margin-bottom: 20px;
    }
  </style>
</q:component>
