<!-- Positive: Data import from URL with HTTP headers -->
<q:component name="DataHTTPHeaders" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="apiData" source="https://api.example.com/data.json" type="json">
    <q:header name="Authorization" value="Bearer {token}" />
    <q:header name="Content-Type" value="application/json" />
  </q:data>

  <q:return value="{apiData}" />
</q:component>
