<q:test name="totals by region, from one query" page="/">
  <test:visit />
  <test:expect text="North 320 2 South 120 2 East 50 1" />
  <test:expect text="5 sales" />
  <test:expect queries="1" />
</q:test>
