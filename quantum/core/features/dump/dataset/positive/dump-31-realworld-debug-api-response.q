<!-- Positive: Debug API response structure -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldDebugApiResponse" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api" url="https://api.example.com/users/1" method="GET" />
  <q:dump var="{api}" when="{!api_result.success}" label="API Error Debug" />

  <q:return value="Dumped" />
</q:component>
