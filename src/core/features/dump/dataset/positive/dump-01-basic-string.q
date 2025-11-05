<!-- Positive: Dump basic string variable -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicString" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="message" value="Hello, World!" />
  <q:dump var="{message}" />

  <q:return value="Dumped" />
</q:component>
