<q:test name="opening the link only asks" page="/delete/1">
  <test:visit />
  <test:expect text="Delete Ana? This cannot be undone." />
  <test:expect table="contacts" count="2" />
</q:test>

<q:test name="yes deletes that contact and goes back to the list" page="/delete/1">
  <test:submit action="remove" id="1" />
  <test:expect redirect="/" flash="Deleted." />
  <test:expect table="contacts" count="0" where="name = 'Ana'" />
  <test:expect no-text="Ana" />
  <test:expect text="Bruno" />
</q:test>

<q:test name="a contact already deleted says so" page="/delete/9">
  <test:visit />
  <test:expect text="That contact is already gone." />
  <test:expect no-text="Yes, delete" />
</q:test>
