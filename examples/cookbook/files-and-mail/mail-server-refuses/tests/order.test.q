<q:test name="the order is saved and the visitor told the e-mail failed" page="/">
  <test:submit action="order" email="ana@example.com" item="Blue mug" />
  <test:expect redirect="/" flash="Ordered Blue mug. We could not send the confirmation e-mail." />
  <test:expect table="orders" count="1" where="email = 'ana@example.com' AND item = 'Blue mug'" />
</q:test>
