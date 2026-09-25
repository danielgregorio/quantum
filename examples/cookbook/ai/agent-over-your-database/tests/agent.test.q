<!-- Structural checks, never the model's exact words: the same tests run
     against a real model before every release. -->
<q:test name="the agent looks at the data through its tool" page="/">
  <test:visit />
  <test:expect text="Called low_stock(" />
  <test:expect no-text="did not finish" />
  <test:expect table="products" count="4" />
</q:test>
