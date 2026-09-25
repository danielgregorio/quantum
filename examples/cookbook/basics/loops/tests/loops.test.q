<q:test name="a list, with each position" page="/">
  <test:visit />
  <test:expect text="1. Apple" />
  <test:expect text="3. Cherry" />
</q:test>

<q:test name="a range includes both ends" page="/">
  <test:visit />
  <test:expect text="[2] [4] [6] [8] [10]" />
</q:test>

<q:test name="list items lose the spaces around them" page="/">
  <test:visit />
  <test:expect text="(red) (green) (blue)" />
</q:test>
