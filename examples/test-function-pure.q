<!-- Test Pure Function (no side effects) -->
<q:component name="TestFunctionPure" xmlns:q="https://quantum.lang/ns">
  <!-- Pure function - always returns same output for same input -->
  <q:function name="calculateDiscount" returnType="number" pure="true" memoize="true">
    <q:param name="price" type="number" required="true" />
    <q:param name="discountPercent" type="number" required="true" />

    <q:set name="discount" type="number" value="{price * discountPercent / 100}" />
    <q:set name="finalPrice" type="number" value="{price - discount}" />

    <q:return value="{finalPrice}" />
  </q:function>

  <!-- Test multiple calls with same arguments (should be memoized) -->
  <q:set name="price1" value="{calculateDiscount(100, 10)}" />
  <q:set name="price2" value="{calculateDiscount(200, 15)}" />
  <q:set name="price3" value="{calculateDiscount(100, 10)}" />

  <q:return value="{price1}, {price2}, {price3}" />
</q:component>
