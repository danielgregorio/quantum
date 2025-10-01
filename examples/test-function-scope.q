<!-- Test Function Scopes (component, global) -->
<q:component name="TestFunctionScope" xmlns:q="https://quantum.lang/ns">
  <!-- Component-scoped function (default) -->
  <q:function name="privateHelper" returnType="string" access="private">
    <q:param name="text" type="string" required="true" />
    <q:return value="[PRIVATE] {text}" />
  </q:function>

  <!-- Public component function -->
  <q:function name="publicAPI" returnType="string" access="public">
    <q:param name="input" type="string" required="true" />

    <!-- Can call private function within same component -->
    <q:set name="processed" value="{privateHelper(input)}" />
    <q:return value="[PUBLIC] {processed}" />
  </q:function>

  <!-- Global-scoped function (accessible from other components) -->
  <q:function name="utilityFunction" returnType="string" scope="global">
    <q:param name="data" type="string" required="true" />
    <q:return value="[UTILITY] {data}" />
  </q:function>

  <!-- Test function calls -->
  <q:set name="result1" value="{publicAPI('test')}" />
  <q:set name="result2" value="{utilityFunction('global')}" />

  <q:return value="{result1} | {result2}" />
</q:component>
