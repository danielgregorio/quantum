<q:component name="TestDataJSON" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import JSON file -->
  <q:data name="products" source="examples/test-data-products.json" type="json" />

  <!-- Loop through products and print -->
  <q:loop items="{products}" var="product">
    Product {product.id}: {product.name} - ${product.price} ({product.category})
  </q:loop>

  <q:return value="{products}" />
</q:component>
