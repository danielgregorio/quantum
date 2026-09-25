<q:test name="the options come from the enum" page="/">
  <test:visit />
  <test:expect text="small" />
  <test:expect text="large" />
  <test:expect text="oat" />
</q:test>

<q:test name="an order with the defaults" page="/">
  <test:submit action="order" size="large" />
  <test:expect redirect="/" flash="A large coffee, milk: none." />
  <test:expect table="orders" count="1" where="size = 'large' AND milk = 'none' AND to_go = 0" />
</q:test>

<q:test name="the box, when sent, is true" page="/">
  <test:submit action="order" size="small" milk="oat" to_go="on" />
  <test:expect flash="A small coffee, milk: oat, to go." />
  <test:expect table="orders" count="1" where="to_go = 1" />
</q:test>

<q:test name="a value outside the list is refused" page="/">
  <test:submit action="order" size="huge" milk="soy" />
  <test:expect error="size" message="Must be one of: small, medium, large" />
  <test:expect error="milk" message="Must be one of: none, whole, oat" />
  <test:expect table="orders" count="0" />
</q:test>
