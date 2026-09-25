<q:test name="no stock" page="/">
  <test:visit />
  <test:expect text="Out of stock." />
  <test:expect no-text="In stock." />
</q:test>

<q:test name="a little stock" page="/?stock=3">
  <test:visit />
  <test:expect text="Only 3 left." />
  <test:expect no-text="pairs" />
</q:test>

<q:test name="plenty, and an even number" page="/?stock=8">
  <test:visit />
  <test:expect text="In stock." />
  <test:expect text="Sold in pairs: 4 pairs." />
</q:test>
