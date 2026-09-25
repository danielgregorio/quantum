<!-- Structural checks, never the model's exact words: the same tests run
     against a real model before every release. -->
<q:test name="a question the FAQ covers" page="/">
  <test:visit q="How can I export my invoices as PDF?" />
  <test:expect text="From the FAQ: How do I export my invoices?" />
</q:test>

<q:test name="a question it does not" page="/">
  <test:visit q="What is the weather tomorrow?" />
  <test:expect text="The FAQ does not cover that yet." />
</q:test>
