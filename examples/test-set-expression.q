<!-- Test Set Expression -->
<q:component name="TestSetExpression" xmlns:q="https://quantum.lang/ns">
  <!-- Teste: expressões aritméticas -->
  <q:set name="a" type="number" value="5" />
  <q:set name="b" type="number" value="3" />
  <q:set name="sum" type="number" value="{a + b}" />
  <q:return value="Sum: {sum}" />
</q:component>
