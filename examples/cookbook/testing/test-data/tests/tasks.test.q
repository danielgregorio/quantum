<q:test name="a user sees only their own open tasks" page="/">
  <test:given table="tasks" owner="Ana" title="Write the report" />
  <test:given table="tasks" owner="Ana" title="Old task" done="1" />
  <test:given table="tasks" owner="Bruno" title="Fix the printer" />
  <test:as user="Ana" />
  <test:visit />
  <test:expect status="200" text="Ana's open tasks" />
  <test:expect text="Write the report" />
  <test:expect no-text="Old task" />
  <test:expect no-text="Fix the printer" />
</q:test>

<q:test name="a user with nothing open is told so" page="/">
  <test:given table="tasks" owner="Bruno" title="Fix the printer" />
  <test:as user="Ana" />
  <test:visit />
  <test:expect text="Nothing to do." />
</q:test>

<q:test name="the page needs a signed-in user" page="/">
  <test:visit />
  <test:expect status="302" />
</q:test>
