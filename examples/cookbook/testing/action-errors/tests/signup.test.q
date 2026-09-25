<q:test name="a short name is refused on its field, with the rule's message" page="/">
  <test:submit action="join" name="A" email="bia@example.com" />
  <test:expect error="name" message="Must be at least 2 characters" />
  <test:expect table="members" count="0" where="email = 'bia@example.com'" />
</q:test>

<q:test name="an address that is not an e-mail is refused on its field" page="/">
  <test:submit action="join" name="Bia" email="bia-at-example" />
  <test:expect error="email" />
  <test:expect table="members" count="1" />
</q:test>

<q:test name="an address that is already a member is refused with a flash" page="/">
  <test:submit action="join" name="Ana Again" email="ana@example.com" />
  <test:expect redirect="/" flash="ana@example.com is already a member." />
  <test:expect table="members" count="1" />
</q:test>

<q:test name="a new member is welcomed" page="/">
  <test:submit action="join" name="Bia" email="bia@example.com" />
  <test:expect redirect="/" flash="Welcome, Bia!" />
  <test:expect table="members" count="1" where="email = 'bia@example.com'" />
</q:test>
