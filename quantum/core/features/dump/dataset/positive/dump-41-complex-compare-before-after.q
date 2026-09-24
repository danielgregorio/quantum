<!-- Positive: Compare state before and after transformation -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexCompareBeforeAfter" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="before" value='[1, 2, 3, 4, 5]' operation="json" />
  <q:dump var="{before}" label="Before Filter" />
  <q:data name="after" source="{before}" type="transform">
    <q:transform>
      <q:filter condition="{value > 2}" />
    </q:transform>
  </q:data>
  <q:dump var="{after}" label="After Filter" />

  <q:return value="Dumped" />
</q:component>
