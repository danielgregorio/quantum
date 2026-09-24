<!-- Positive: Inspect data after transformation -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldInspectTransformedData" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="raw" source="data/products.csv" type="csv">
    <q:column name="price" type="decimal" />
    <q:transform>
      <q:filter condition="{price > 50}" />
    </q:transform>
  </q:data>
  <q:dump var="{raw}" label="Filtered Products" />

  <q:return value="Dumped" />
</q:component>
