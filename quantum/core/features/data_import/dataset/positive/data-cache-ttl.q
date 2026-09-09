<!-- Positive: Data import with caching and TTL -->
<q:component name="DataCacheTTL" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="cachedProducts" source="data/products.json" type="json" cache="true" ttl="300" />

  <q:return value="{cachedProducts}" />
</q:component>
