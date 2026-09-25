<q:test name="the page lists the notes" page="/">
  <test:visit />
  <test:expect status="200" text="Notes (1)" />
  <test:expect text="Read the guide" />
</q:test>

<q:test name="adding a note stores it and says so" page="/">
  <test:submit action="add" title="Buy bread" />
  <test:expect redirect="/" flash="Added: Buy bread" />
  <test:expect table="notes" count="1" where="title = 'Buy bread'" />
  <test:expect text="Notes (2)" />
</q:test>

<q:test name="a title that is too short is refused on its field" page="/">
  <test:submit action="add" title="x" />
  <test:expect error="title" />
  <test:expect table="notes" count="1" />
</q:test>
