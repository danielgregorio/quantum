<q:test name="signing out ends the session" page="/">
  <test:as user="ana" role="member" />
  <test:visit />
  <test:expect text="Hello, ana" />
  <test:visit path="/logout" />
  <test:expect status="302" redirect="/login" />
  <test:expect text="You are signed out." />
  <test:visit path="/" />
  <test:expect status="302" redirect="/login" />
</q:test>
