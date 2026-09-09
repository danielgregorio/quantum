<!-- Test Multiple Functions in Same Component -->
<q:component name="TestFunctionMultiple" xmlns:q="https://quantum.lang/ns">
  <!-- String manipulation -->
  <q:function name="toUpperCase" returnType="string">
    <q:param name="text" type="string" required="true" />
    <q:set name="result" type="string" value="{text}" operation="uppercase" />
    <q:return value="{result}" />
  </q:function>

  <q:function name="toLowerCase" returnType="string">
    <q:param name="text" type="string" required="true" />
    <q:set name="result" type="string" value="{text}" operation="lowercase" />
    <q:return value="{result}" />
  </q:function>

  <!-- Math operations -->
  <q:function name="square" returnType="number">
    <q:param name="n" type="number" required="true" />
    <q:return value="{n * n}" />
  </q:function>

  <!-- Test all functions -->
  <q:set name="upper" value="{toUpperCase('hello')}" />
  <q:set name="lower" value="{toLowerCase('WORLD')}" />
  <q:set name="squared" value="{square(5)}" />

  <q:return value="{upper} {lower} {squared}" />
</q:component>
