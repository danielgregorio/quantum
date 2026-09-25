<q:test name="the numbers arrive as numbers" page="/">
  <test:submit action="split" amount="100" people="3" spent_on="2026-09-20" />
  <test:expect redirect="/" flash="100.0 on 2026-09-20: 33.33 each." />
  <test:expect table="expenses" count="1" where="amount = 100 AND people = 3 AND spent_on = '2026-09-20'" />
</q:test>

<q:test name="text where a number goes is refused" page="/">
  <test:submit action="split" amount="ten" people="3" spent_on="2026-09-20" />
  <test:expect error="amount" message="Must be a number, got 'ten'" />
</q:test>

<q:test name="min and max hold" page="/">
  <test:submit action="split" amount="0" people="51" spent_on="2026-09-20" />
  <test:expect error="amount" message="Must be at least 0.01 (got 0.0)" />
  <test:expect error="people" message="Must be at most 50 (got 51)" />
</q:test>

<q:test name="a date that does not exist is refused" page="/">
  <test:submit action="split" amount="10" people="2" spent_on="2026-02-30" />
  <test:expect error="spent_on" message="Must be a date (YYYY-MM-DD), got '2026-02-30'" />
  <test:expect table="expenses" count="0" />
</q:test>
