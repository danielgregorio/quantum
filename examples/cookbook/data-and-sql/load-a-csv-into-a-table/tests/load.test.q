<q:test name="the file's rows land in the table" page="/">
  <test:submit action="load" />
  <test:expect redirect="/" flash="Loaded 3 products." />
  <test:expect table="products" count="3" />
  <test:expect table="products" count="1" where="sku = 'TEE-1' AND price = 80" />
  <test:expect text="3 products" />
</q:test>

<q:test name="a file that fails halfway leaves nothing behind" page="/">
  <!-- TEE-1 is already there: the second row fails, so the first is undone too. -->
  <test:given table="products" sku="TEE-1" name="T-shirt" price="80" />
  <test:submit action="load" />
  <test:expect status="500" />
  <test:expect table="products" count="1" />
  <test:expect table="products" count="0" where="sku = 'MUG-1'" />
</q:test>
