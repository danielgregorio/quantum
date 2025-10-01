<!-- Test Function with Local Variables -->
<q:component name="TestFunctionLocalVars" xmlns:q="https://quantum.lang/ns">
  <!-- Function that uses local variables for computation -->
  <q:function name="calculateTotal" returnType="number">
    <q:param name="price" type="number" required="true" />
    <q:param name="quantity" type="number" required="true" />
    <q:param name="taxRate" type="number" default="0.1" />

    <!-- Local computation -->
    <q:set name="subtotal" type="number" value="{price * quantity}" />
    <q:set name="tax" type="number" value="{subtotal * taxRate}" />
    <q:set name="total" type="number" value="{subtotal + tax}" />

    <q:return value="{total}" />
  </q:function>

  <!-- Test function call -->
  <q:set name="orderTotal" value="{calculateTotal(100, 3, 0.15)}" />
  <q:return value="Total: {orderTotal}" />
</q:component>
