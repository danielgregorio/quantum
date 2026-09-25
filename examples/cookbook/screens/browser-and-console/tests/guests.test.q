<q:test name="an empty list to start" page="/">
  <test:visit />
  <test:expect text="0 signed so far." />
</q:test>

<q:test name="signing adds the name" page="/">
  <test:submit action="sign" name="Ana" />
  <test:expect redirect="/" flash="Welcome, Ana!" />
  <test:expect text="1 signed so far." />
  <test:expect text="Ana" />
</q:test>

<q:test name="a name that is too short is refused on its field" page="/">
  <test:submit action="sign" name="A" />
  <test:expect error="name" message="Must be at least 2 characters" />
  <test:expect text="0 signed so far." />
</q:test>
