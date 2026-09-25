<q:test name="a refused message comes back as it was typed" page="/">
  <test:submit action="send" email="ana@example" body="Your shop is closed on Sundays?" />
  <test:expect redirect="/" />
  <test:expect error="email" message="Must be a valid email" />
  <test:expect text="Your shop is closed on Sundays?" />
  <test:expect table="messages" count="0" />
</q:test>

<q:test name="the values come back once: the next visit is empty" page="/">
  <test:submit action="send" email="ana@example" body="Your shop is closed on Sundays?" />
  <test:visit />
  <test:expect no-text="Your shop is closed on Sundays?" />
</q:test>

<q:test name="a valid message is saved" page="/">
  <test:submit action="send" email="ana@example.com" body="Your shop is closed on Sundays?" />
  <test:expect redirect="/" flash="Thanks, we got your message." />
  <test:expect table="messages" count="1" where="email = 'ana@example.com'" />
</q:test>
