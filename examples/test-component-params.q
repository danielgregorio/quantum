<!-- Test Component Params -->
<!-- Demonstrates component parameter declaration patterns -->
<q:component name="TestComponentParams" xmlns:q="https://quantum.lang/ns">

  <!-- String parameter with default -->
  <q:param name="title" type="string" default="My Title" />

  <!-- Number parameter with default -->
  <q:param name="count" type="number" default="10" />

  <!-- Boolean parameter -->
  <q:param name="enabled" type="boolean" default="true" />

  <!-- Array parameter -->
  <q:param name="items" type="array" default='["a", "b", "c"]' />

  <!-- Object parameter -->
  <q:param name="config" type="object" default='{"debug": false}' />

  <!-- Use local variables to show results -->
  <q:set name="msg" value="Component has 5 parameters defined" />

  <q:return value="{msg}" />
</q:component>
