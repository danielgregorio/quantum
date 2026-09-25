<!-- Structural checks, never the model's exact words: the same tests run
     against a real model before every release. -->
<q:test name="a message is filed with the model's fields" page="/">
  <test:submit action="open" message="I was charged twice for order 1042, please refund one." />
  <test:expect redirect="/" />
  <test:expect table="tickets" count="1" where="category = 'billing'" />
</q:test>

<q:test name="a message too short never reaches the model" page="/">
  <test:submit action="open" message="help" />
  <test:expect error="message" />
  <test:expect table="tickets" count="0" />
</q:test>

<q:test name="a category the model made up is filed as other" page="/">
  <test:submit action="open" message="Please write me a poem about the sea." />
  <test:expect redirect="/" flash="Filed under other." />
  <test:expect table="tickets" count="1" where="category = 'other'" />
</q:test>
