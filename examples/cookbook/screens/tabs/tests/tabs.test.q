<q:test name="every tab has its title" page="/">
  <test:visit />
  <test:expect text="Profile" />
  <test:expect text="Plan" />
  <test:expect text="Security" />
</q:test>

<q:test name="every tab's content is on the page" page="/">
  <test:visit />
  <test:expect text="Name: Ana Lima" />
  <test:expect text="Current plan: Pro" />
  <test:expect text="Two-step sign-in is off." />
</q:test>

<q:test name="renewing comes back on the Plan tab" page="/">
  <test:submit action="renew" />
  <test:expect status="302" redirect="/?tab=Plan" flash="Plan renewed." />
</q:test>
