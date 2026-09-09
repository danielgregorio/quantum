<!-- Test Dump with Different Formats -->
<q:component name="TestDumpFormats" xmlns:q="https://quantum.lang/ns">
  <q:param name="data" type="object" default='{"name": "Test", "value": 123}' />

  <q:dump var="{data}" label="HTML Format" format="html" />
  <q:dump var="{data}" label="JSON Format" format="json" />
  <q:dump var="{data}" label="Text Format" format="text" />

  <q:return value="Dump formats test completed" />
</q:component>
