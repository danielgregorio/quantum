<!-- Structural checks, never the model's exact words: the same tests run
     against a real model before every release. -->
<q:test name="a question the documents answer" page="/">
  <test:visit q="How many days do I have to return an order?" />
  <test:expect text="[1] returns.md" />
  <test:expect no-text="do not answer that" />
</q:test>

<q:test name="a question they do not answer" page="/">
  <test:visit q="What is the capital of France?" />
  <test:expect text="Our documents do not answer that." />
  <test:expect no-text="[1]" />
</q:test>
