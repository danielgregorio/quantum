<!-- The bank app, tested in its own language: `quantum test` in projects/bank-transfer.
     Each q:test starts from a fresh database built by migrations/: Alice 100,
     Bob 50, Carol 0. -->

<q:test name="the page lists the accounts" page="/">
  <test:visit />
  <test:expect status="200" />
  <test:expect text="Alice" />
  <test:expect text="Carol" />
</q:test>

<q:test name="a transfer moves the money and records it" page="/">
  <test:submit action="transfer" from_account="1" to_account="2" amount="30.5" />
  <test:expect redirect="/" flash="Transferred $30.5 from account 1 to 2." />
  <test:expect table="accounts" count="1" where="id = 1 AND balance = 69.5" />
  <test:expect table="accounts" count="1" where="id = 2 AND balance = 80.5" />
  <test:expect table="transfers" count="1" where="from_account_id = 1 AND to_account_id = 2 AND amount = 30.5" />
</q:test>

<q:test name="insufficient funds move nothing" page="/">
  <test:submit action="transfer" from_account="3" to_account="1" amount="10" />
  <test:expect redirect="/" flash="Insufficient funds in account 3." />
  <test:expect table="accounts" count="1" where="id = 1 AND balance = 100" />
  <test:expect table="transfers" count="0" />
</q:test>

<q:test name="an account that does not exist moves nothing" page="/">
  <test:submit action="transfer" from_account="1" to_account="99" amount="10" />
  <test:expect redirect="/" flash="There is no such account." />
  <test:expect table="accounts" count="1" where="id = 1 AND balance = 100" />
  <test:expect table="transfers" count="0" />
</q:test>

<q:test name="the same account on both sides is refused" page="/">
  <test:submit action="transfer" from_account="2" to_account="2" amount="10" />
  <test:expect flash="Choose two different accounts." />
  <test:expect table="transfers" count="0" />
</q:test>

<q:test name="an amount below one cent is refused on its field" page="/">
  <test:submit action="transfer" from_account="1" to_account="2" amount="0" />
  <test:expect error="amount" />
  <test:expect table="transfers" count="0" />
</q:test>
