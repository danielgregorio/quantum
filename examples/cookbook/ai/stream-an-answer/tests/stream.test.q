<!-- Structural checks, never the model's exact words: the same tests run
     against a real model before every release. -->
<q:test name="the page renders with its sources before the answer" page="/">
  <test:visit q="How many days do I have to return an order?" />
  <test:expect text="[1] returns.md" />
  <test:expect text="Read the answer" />
</q:test>
