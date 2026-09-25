<q:test name="both migrations ran, in order" page="/">
  <test:visit />
  <test:expect text="In stock" />
  <test:expect table="products" count="1" where="name = 'Mug' AND stock = 12" />
  <test:expect table="products" count="1" where="name = 'Sticker' AND stock = 0" />
</q:test>
