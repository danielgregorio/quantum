<q:test name="a transfer moves the money and logs it" page="/">
  <test:submit action="transfer" amount="300" />
  <test:expect redirect="/" flash="Moved 300 from Ana to Bruno." />
  <test:expect table="accounts" count="1" where="owner = 'Ana' AND balance = 1200" />
  <test:expect table="accounts" count="1" where="owner = 'Bruno' AND balance = 500" />
  <test:expect table="transfers" count="1" />
</q:test>

<q:test name="the page refuses what the account cannot pay" page="/">
  <test:submit action="transfer" amount="5000" />
  <test:expect flash="Not enough money in Ana's account." />
  <test:expect table="transfers" count="0" />
</q:test>

<q:test name="when the last write fails, the first two are undone" page="/">
  <!-- 1200 passes the balance check, but the log refuses more than 1000:
       the debit and the credit already ran, and are rolled back. -->
  <test:submit action="transfer" amount="1200" />
  <test:expect status="500" />
  <test:expect table="accounts" count="1" where="owner = 'Ana' AND balance = 1500" />
  <test:expect table="accounts" count="1" where="owner = 'Bruno' AND balance = 200" />
  <test:expect table="transfers" count="0" />
</q:test>
