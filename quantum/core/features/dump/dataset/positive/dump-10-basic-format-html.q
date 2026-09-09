<!-- Positive: Dump with HTML format -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicFormatHtml" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value='{"key": "value"}' operation="json" />
  <q:dump var="{data}" format="html" />

  <q:return value="Dumped" />
</q:component>
