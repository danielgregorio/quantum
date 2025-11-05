<!-- Positive: Data import with compute transformation -->
<q:component name="DataComputeTransform" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="discountedProducts" source="data/products.json" type="json">
    <q:transform>
      <q:compute field="discountPrice" expression="{price} * 0.9" type="decimal" />
    </q:transform>
  </q:data>

  <q:return value="{discountedProducts}" />
</q:component>
