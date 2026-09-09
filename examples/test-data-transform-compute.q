<q:component name="TestDataTransformCompute" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import JSON and compute discounted price -->
  <q:data name="discountedProducts" source="examples/test-data-products.json" type="json">
    <q:transform>
      <q:compute field="discountedPrice" expression="{price} * 0.9" type="decimal" />
    </q:transform>
  </q:data>

  <!-- Loop through products with discount -->
  <q:loop items="{discountedProducts}" var="product">
    {product.name}: ${product.price} -> ${product.discountedPrice}
  </q:loop>

  <q:return value="{discountedProducts}" />
</q:component>
