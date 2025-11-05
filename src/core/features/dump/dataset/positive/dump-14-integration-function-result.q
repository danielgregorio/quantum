<!-- Positive: Dump function result -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationFunctionResult" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" params="a,b">
    <q:set var="result" value="{a + b}" operation="add" />
    <q:return value="{result}" />
  </q:function>
  <q:set var="sum" value="{add(5, 3)}" operation="function" />
  <q:dump var="{sum}" label="Function Result" />

  <q:return value="Dumped" />
</q:component>
