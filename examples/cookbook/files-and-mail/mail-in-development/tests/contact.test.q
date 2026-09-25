<q:test name="a message is sent and the visitor is told" page="/">
  <test:submit action="send" email="ana@example.com" message="Where is my order?" />
  <test:expect redirect="/" flash="Thanks! We will answer ana@example.com." />
</q:test>

<q:test name="an address that is not an e-mail is refused on its field" page="/">
  <test:submit action="send" email="not-an-email" message="Where is my order?" />
  <test:expect error="email" />
</q:test>
