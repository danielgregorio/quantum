<q:component name="TestDataTransformSort" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import JSON and sort by price -->
  <q:data name="sortedProducts" source="examples/test-data-products.json" type="json">
    <q:transform>
      <q:sort by="price" order="desc" />
    </q:transform>
  </q:data>

  <!-- Loop through sorted products -->
  <q:loop items="{sortedProducts}" var="product">
    {product.name}: ${product.price}
  </q:loop>

  <q:return value="{sortedProducts}" />
</q:component>
