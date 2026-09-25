<q:test name="the guard sends a visitor to sign in" page="/">
  <test:visit />
  <test:expect status="302" redirect="/login" />
  <test:expect text="Sign in to write notes." />
</q:test>

<q:test name="the guard also stops the action: nothing is written" page="/">
  <test:submit action="add" body="Sneaky note" />
  <test:expect status="302" redirect="/login" />
  <test:expect table="notes" count="0" />
</q:test>

<q:test name="a signed-in user writes a note" page="/">
  <test:as user="ana" role="member" />
  <test:submit action="add" body="Buy coffee" />
  <test:expect redirect="/" flash="Saved." />
  <test:expect table="notes" count="1" where="author = 'ana' AND body = 'Buy coffee'" />
  <test:expect text="ana: Buy coffee" />
</q:test>
