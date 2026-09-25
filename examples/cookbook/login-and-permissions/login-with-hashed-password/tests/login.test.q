<q:test name="a visitor who is not signed in is sent to sign in" page="/">
  <test:visit />
  <test:expect text="Sign in" />
  <test:expect no-text="Hello," />
</q:test>

<q:test name="the right password signs in" page="/login">
  <test:submit action="signin" email="ana@example.com" password="correct horse battery" />
  <test:expect redirect="/" flash="Welcome, Ana!" />
  <test:expect text="Hello, Ana" />
  <test:expect text="You are signed in as admin." />
</q:test>

<q:test name="a wrong password is refused, with the same message as an unknown address" page="/login">
  <test:submit action="signin" email="ana@example.com" password="guess" />
  <test:expect redirect="/login" flash="Wrong e-mail or password." />
  <test:submit action="signin" email="nobody@example.com" password="guess" />
  <test:expect redirect="/login" flash="Wrong e-mail or password." />
</q:test>
