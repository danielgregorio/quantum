<!-- Structural checks, never the model's exact words: the same tests run
     against a real model before every release. -->
<q:test name="the answer comes with the document it is from" page="/">
  <test:visit q="How many days do I have to return an order?" />
  <test:expect text="Sources:" />
  <test:expect text="[1] returns.md" />
</q:test>

<q:test name="another question, another document" page="/">
  <test:visit q="Is shipping free for my order?" />
  <test:expect text="[1] shipping.md" />
</q:test>

<q:test name="no question, no model call" page="/">
  <test:visit />
  <test:expect no-text="Sources:" />
</q:test>
