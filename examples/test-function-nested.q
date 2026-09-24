<!-- Test Nested Function Calls -->
<q:component name="TestFunctionNested" xmlns:q="https://quantum.lang/ns">
  <!-- Simple arithmetic functions -->
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:function name="multiply" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a * b}" />
  </q:function>

  <!-- Test nested calls: multiply(add(2, 3), 4) = multiply(5, 4) = 20 -->
  <q:set name="result" value="{multiply(add(2, 3), 4)}" />
  <q:return value="Result: {result}" />
</q:component>
