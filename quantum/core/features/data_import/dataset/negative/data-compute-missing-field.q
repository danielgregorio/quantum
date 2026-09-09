<!-- Negative: Compute missing required 'field' attribute -->
<!-- Expected error: Compute requires 'field' attribute -->
<q:component name="DataComputeMissingField" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="products" source="data/products.json" type="json">
    <q:transform>
      <q:compute expression="{price} * 0.9" type="decimal" />
    </q:transform>
  </q:data>

  <q:return value="Error" />
</q:component>
