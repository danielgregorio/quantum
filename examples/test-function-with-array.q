<!-- Test Function with Array Operations -->
<q:component name="TestFunctionWithArray" xmlns:q="https://quantum.lang/ns">
  <!-- Function that counts elements in an array -->
  <q:function name="countElements" returnType="number">
    <q:param name="items" type="array" required="true" />

    <q:set name="count" type="number" value="0" />

    <q:loop type="array" items="{items}" var="item">
      <q:set name="count" operation="increment" />
    </q:loop>

    <q:return value="{count}" />
  </q:function>

  <!-- Function that sums numbers in an array -->
  <q:function name="sumNumbers" returnType="number">
    <q:param name="numbers" type="array" required="true" />

    <q:set name="total" type="number" value="0" />

    <q:loop type="array" items="{numbers}" var="num">
      <q:set name="total" type="number" value="{total}" operation="add" operand="{num}" />
    </q:loop>

    <q:return value="{total}" />
  </q:function>

  <!-- Test with arrays -->
  <q:set name="myArray" type="array" value='["apple", "banana", "cherry"]' />
  <q:set name="myNumbers" type="array" value="[10, 20, 30, 40]" />

  <q:set name="itemCount" value="{countElements(myArray)}" />
  <q:set name="sum" value="{sumNumbers(myNumbers)}" />

  <q:return value="Count: {itemCount}, Sum: {sum}" />
</q:component>
