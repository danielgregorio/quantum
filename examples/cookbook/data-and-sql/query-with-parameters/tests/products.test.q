<q:test name="without a filter, every product" page="/">
  <test:visit />
  <test:expect text="4 products" />
  <test:expect text="Notebook" />
</q:test>

<q:test name="the value from the URL filters" page="/">
  <test:visit name="mouse" />
  <test:expect text="2 products" />
  <test:expect text="Mousepad" />
  <test:expect no-text="Monitor" />
</q:test>

<q:test name="SQL in the URL is only text to search for" page="/">
  <test:visit name="' OR '1'='1" />
  <test:expect text="0 products" />
  <test:expect table="products" count="4" />
</q:test>
