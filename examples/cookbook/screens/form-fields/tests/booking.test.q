<q:test name="the form shows its labels, the option texts and the button" page="/">
  <test:visit />
  <test:expect text="Name" />
  <test:expect text="Single Double Suite" />
  <test:expect text="Breakfast" />
  <test:expect text="morning" />
  <test:expect text="Book" />
</q:test>

<q:test name="the fields reach the action typed" page="/">
  <test:submit action="book" name="Ana" nights="3" room="suite" breakfast="on" arrival="night" />
  <test:expect redirect="/" flash="Ana: 3 nights, suite, breakfast yes, night." />
</q:test>

<q:test name="left out, the defaults apply" page="/">
  <test:submit action="book" name="Ana" nights="1" />
  <test:expect flash="Ana: 1 nights, double, breakfast no, afternoon." />
</q:test>

<q:test name="a refused field keeps the others as typed" page="/">
  <test:submit action="book" name="Ana" nights="20" notes="Late check-in, please." />
  <test:expect error="nights" message="Must be at most 14 (got 20)" />
  <test:expect text="Late check-in, please." />
</q:test>
