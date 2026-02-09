<!-- Test Function Complete -->
<!-- Demonstrates all function patterns -->
<q:component name="TestFunctionComplete" xmlns:q="https://quantum.lang/ns">

  <!-- Simple function with parameters -->
  <q:function name="greet" returnType="string">
    <q:param name="name" type="string" required="true" />
    <q:param name="greeting" type="string" default="Hello" />
    <q:return value="{greeting}, {name}!" />
  </q:function>

  <!-- Function with number operations -->
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" type="number" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <q:function name="subtract" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" type="number" value="{a - b}" />
    <q:return value="{result}" />
  </q:function>

  <q:function name="multiply" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" type="number" value="{a * b}" />
    <q:return value="{result}" />
  </q:function>

  <!-- Function with array parameter -->
  <q:function name="sumArray" returnType="number">
    <q:param name="numbers" type="array" required="true" />

    <q:set name="total" type="number" value="0" />
    <q:loop type="array" var="num" items="{numbers}">
      <q:set name="total" value="{total + num}" />
    </q:loop>

    <q:return value="{total}" />
  </q:function>

  <!-- Call functions -->
  <q:set name="msg1" value="{greet('World')}" />
  <q:set name="msg2" value="{greet('John', 'Welcome')}" />
  <q:set name="sum" value="{add(10, 5)}" />
  <q:set name="diff" value="{subtract(10, 5)}" />
  <q:set name="product" value="{multiply(10, 5)}" />

  <q:return value="{msg1} | {msg2} | Sum: {sum} | Diff: {diff} | Product: {product}" />
</q:component>
