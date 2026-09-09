<!-- Test Function Parameter Validation -->
<q:component name="TestFunctionValidation" xmlns:q="https://quantum.lang/ns">
  <!-- Function with parameter validation -->
  <q:function name="registerUser" returnType="string" validate="true">
    <q:param name="email" type="string" required="true" validate="email" />
    <q:param name="age" type="number" required="true" min="18" max="100" />
    <q:param name="role" type="string" required="true" enum="admin,user,guest" />

    <q:return value="User {email} registered as {role}" />
  </q:function>

  <!-- Test with valid data -->
  <q:set name="result" value="{registerUser('john@example.com', 25, 'user')}" />
  <q:return value="{result}" />
</q:component>
