<q:test name="open tasks by default" page="/">
  <test:visit />
  <test:expect text="Showing open: 2" />
  <test:expect no-text="Pay the rent" />
</q:test>

<q:test name="the links filter" page="/">
  <test:visit show="done" />
  <test:expect text="Showing done: 1" />
  <test:expect text="Pay the rent" />
</q:test>

<q:test name="a header sorts in SQL" page="/">
  <test:visit show="all" sort="priority" dir="desc" />
  <test:expect text="Pay the rent 3 Write the report 2 Call the bank 1" />
</q:test>

<q:test name="a column the query does not return is ignored" page="/">
  <test:visit sort="password" />
  <test:expect text="Showing open: 2" />
</q:test>
