<q:test name="a valid guest is added" page="/">
  <test:submit action="register" name="Ana" email="ana@example.com" age="30" />
  <test:expect redirect="/" flash="Ana is on the list." />
  <test:expect table="guests" count="1" where="name = 'Ana' AND age = 30" />
</q:test>

<q:test name="every broken field gets its own message" page="/">
  <test:submit action="register" name="A" email="not an address" age="12" />
  <test:expect redirect="/" />
  <test:expect error="name" message="Must be at least 2 characters" />
  <test:expect error="email" message="Must be a valid email" />
  <test:expect error="age" message="Must be at least 18 (got 12)" />
  <test:expect text="Must be at least 2 characters" />
  <test:expect table="guests" count="0" />
</q:test>

<q:test name="a missing field is refused as Required" page="/">
  <test:submit action="register" name="Ana" email="ana@example.com" />
  <test:expect error="age" message="Required" />
  <test:expect table="guests" count="0" />
</q:test>
