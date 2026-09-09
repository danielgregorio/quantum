<!-- Negative: Dump tag with child elements -->
<!-- Expected error: Dump tag must be self-closing -->
<q:component name="DumpNegChildElements" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="{data}">
  <!-- Should not have children -->
</q:dump>

  <q:return value="Error" />
</q:component>
