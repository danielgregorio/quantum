<!-- Negative: Header missing required 'name' attribute -->
<!-- Expected error: Data header requires 'name' attribute -->
<q:component name="DataHeaderMissingName" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="apiData" source="https://api.example.com/data.json" type="json">
    <q:header value="Bearer token123" />
  </q:data>

  <q:return value="Error" />
</q:component>
