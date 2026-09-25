<q:test name="each form runs its own action" page="/">
  <test:submit action="add" item="Milk" quantity="3" />
  <test:expect flash="Added 3 × Milk." />
  <test:submit action="remove" id="1" />
  <test:expect flash="Removed." />
  <test:expect table="cart" count="2" />
  <test:expect table="cart" count="0" where="item = 'Coffee'" />
</q:test>

<q:test name="the button with no fields empties the cart" page="/">
  <test:submit action="empty" />
  <test:expect redirect="/" flash="The cart is empty." />
  <test:expect table="cart" count="0" />
</q:test>

<q:test name="a post that names no action of the page is refused" page="/">
  <test:submit action="checkout" />
  <test:expect status="400" />
  <test:expect text="No q:action named 'checkout' on this page. Available: add, remove, empty." />
  <test:expect table="cart" count="2" />
</q:test>
