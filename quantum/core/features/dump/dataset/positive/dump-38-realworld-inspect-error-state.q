<!-- Positive: Inspect error state object -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldInspectErrorState" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api" url="https://api.example.com/fail" method="GET" />
  <q:dump var="{api_result.error}" when="{!api_result.success}" label="Error State" />

  <q:return value="Dumped" />
</q:component>
