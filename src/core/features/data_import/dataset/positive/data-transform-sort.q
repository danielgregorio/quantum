<!-- Positive: Data import with sort transformation -->
<q:component name="DataSortTransform" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="sortedProducts" source="data/products.json" type="json">
    <q:transform>
      <q:sort by="price" order="desc" />
    </q:transform>
  </q:data>

  <q:return value="{sortedProducts}" />
</q:component>
