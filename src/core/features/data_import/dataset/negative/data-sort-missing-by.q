<!-- Negative: Sort missing required 'by' attribute -->
<!-- Expected error: Sort requires 'by' attribute -->
<q:component name="DataSortMissingBy" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="products" source="data/products.json" type="json">
    <q:transform>
      <q:sort order="desc" />
    </q:transform>
  </q:data>

  <q:return value="Error" />
</q:component>
