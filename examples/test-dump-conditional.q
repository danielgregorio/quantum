<!-- Test Conditional Dump -->
<q:component name="TestDumpConditional" xmlns:q="https://quantum.lang/ns">
  <q:param name="debug" type="boolean" default="true" />
  <q:param name="data" type="object" default='{"test": "value"}' />

  <q:dump var="{data}" label="Debug Data" when="{debug}" />

  <q:return value="Conditional dump test completed" />
</q:component>
