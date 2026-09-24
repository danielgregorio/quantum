<!-- Positive: Real-world cache invalidation logging -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldCacheInvalidation" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="cacheEvent" value='{"key": "user:123:profile", "reason": "data_updated", "ttl": 3600}' operation="json" />

  <q:log level="debug"
         message="Cache invalidated: {cacheEvent.key}"
         context="{cacheEvent}" />

  <q:return value="Cache event logged" />
</q:component>
