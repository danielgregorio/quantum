<q:test name="the URL segment becomes a variable" page="/product/2">
  <test:visit />
  <test:expect text="Teapot" />
  <test:expect text="Product 2: $22" />
  <test:expect var="id" value="2" />
</q:test>

<q:test name="one file answers every id" page="/product/1">
  <test:visit />
  <test:expect text="Kettle" />
</q:test>

<q:test name="an id with no product says so" page="/product/9">
  <test:visit />
  <test:expect text="No product 9" />
</q:test>
