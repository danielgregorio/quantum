<q:test name="the table shows the rows and the column labels" page="/">
  <test:visit />
  <test:expect text="Item" />
  <test:expect text="Washers" />
</q:test>

<q:test name="a cell edit saves one column of one row" page="/">
  <test:submit action="__edit" __table="items" __key="2" __column="quantity" value="75" />
  <test:expect redirect="/" flash="Saved: quantity" />
  <test:expect table="items" count="1" where="id = 2 AND quantity = 75 AND name = 'Nuts'" />
</q:test>

<q:test name="a value the schema refuses is not saved" page="/">
  <test:submit action="__edit" __table="items" __key="1" __column="shelf" value="Z" />
  <test:expect table="items" count="1" where="id = 1 AND shelf = 'A'" />
  <test:expect var="flashType" value="error" />
  <test:expect flash="Parameter 'value' must be one of: A, B, C" />
</q:test>

<q:test name="a column with edit=false cannot be changed" page="/">
  <test:submit action="__edit" __table="items" __key="1" __column="name" value="Screws" />
  <test:expect status="400" text="items.name is not editable on this page." />
  <test:expect table="items" count="1" where="id = 1 AND name = 'Bolts'" />
</q:test>

<q:test name="a header sorts the rows" page="/">
  <test:visit sort="quantity" dir="asc" />
  <test:expect text="Washers A B C ✓ ✓ Nuts A B C ✓ ✓ Bolts" />
</q:test>
