<!-- Test Recursive Function (Factorial) -->
<q:component name="TestFunctionRecursion" xmlns:q="https://quantum.lang/ns">
  <!-- Factorial function: factorial(n) = n * factorial(n-1), factorial(0) = 1 -->
  <q:function name="factorial" returnType="number">
    <q:param name="n" type="number" required="true" />

    <!-- Base case: factorial(0) = 1 -->
    <q:if condition="{n <= 0}">
      <q:return value="1" />
    </q:if>

    <!-- Recursive case: n * factorial(n-1) -->
    <q:set name="nMinus1" type="number" value="{n}" operation="decrement" />
    <q:set name="recursiveResult" value="{factorial(nMinus1)}" />
    <q:set name="result" type="number" value="{n * recursiveResult}" />

    <q:return value="{result}" />
  </q:function>

  <!-- Test: factorial(5) = 120 -->
  <q:set name="fact5" value="{factorial(5)}" />
  <q:return value="Factorial(5) = {fact5}" />
</q:component>
