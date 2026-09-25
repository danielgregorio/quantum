<q:test name="expressions compute with the variables" page="/">
  <test:visit />
  <test:expect text="COFFEE BEANS" />
  <test:expect text="4 bags at 12.5 = 37.5" />
  <test:expect text="With the extra bag: 50.0" />
  <test:expect var="total" value="37.5" />
</q:test>

<q:test name="the default fills an empty value" page="/">
  <test:visit />
  <test:expect text="Note: no note" />
</q:test>

<q:test name="a value from the URL replaces the default" page="/?note=gift">
  <test:visit />
  <test:expect text="Note: gift" />
</q:test>
