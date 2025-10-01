<!-- Test Function with If Logic -->
<q:component name="TestFunctionIfLogic" xmlns:q="https://quantum.lang/ns">
  <!-- Function that checks if number is positive, negative, or zero -->
  <q:function name="checkNumber" returnType="string">
    <q:param name="num" type="number" required="true" />

    <q:if condition="{num > 0}">
      <q:return value="positive" />
    </q:if>

    <q:if condition="{num &lt; 0}">
      <q:return value="negative" />
    </q:if>

    <q:return value="zero" />
  </q:function>

  <!-- Test with different numbers -->
  <q:set name="result1" value="{checkNumber(5)}" />
  <q:set name="result2" value="{checkNumber(-3)}" />
  <q:set name="result3" value="{checkNumber(0)}" />

  <q:return value="{result1}, {result2}, {result3}" />
</q:component>
