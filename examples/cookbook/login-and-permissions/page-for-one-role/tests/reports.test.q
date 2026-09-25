<q:test name="an admin sees the page" page="/reports">
  <test:as user="ana" role="admin" />
  <test:visit />
  <test:expect status="200" text="Only admins see this, ana." />
</q:test>

<q:test name="a member is refused with 403" page="/reports">
  <test:as user="bruno" role="member" />
  <test:visit />
  <test:expect status="403" />
</q:test>

<q:test name="a visitor who is not signed in is sent to sign in" page="/reports">
  <test:visit />
  <test:expect status="302" redirect="/login" />
</q:test>
