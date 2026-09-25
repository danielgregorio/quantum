<q:test name="adding a note redirects back with a success flash" page="/">
  <test:submit action="add" text="Buy bread" />
  <test:expect status="302" redirect="/" flash="Added: Buy bread" />
  <test:expect var="flashType" value="success" />
  <test:expect text="Buy bread" />
</q:test>

<q:test name="the flash shows once" page="/">
  <test:submit action="add" text="Buy bread" />
  <test:expect text="Added: Buy bread" />
  <test:visit />
  <test:expect no-text="Added: Buy bread" />
  <test:expect var="flash" value="" />
</q:test>

<q:test name="clearing sends the browser to another page" page="/">
  <test:given table="notes" text="Buy bread" />
  <test:given table="notes" text="Call Ana" />
  <test:submit action="clear" />
  <test:expect redirect="/done" flash="Cleared 2 notes." />
  <test:expect text="All clear" />
  <test:expect table="notes" count="0" where="done = 0" />
</q:test>

<q:test name="nothing to clear is a warning, on the same page" page="/">
  <test:submit action="clear" />
  <test:expect redirect="/" flash="There was nothing to clear." />
  <test:expect var="flashType" value="warning" />
</q:test>
