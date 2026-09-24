<!-- Test Set Validation Email Invalid -->
<q:component name="TestSetValidationEmailInvalid" xmlns:q="https://quantum.lang/ns">
  <!-- Invalid email - should fail -->
  <q:set name="email" type="string" value="not-an-email" validate="email" />
  <q:return value="Email: {email}" />
</q:component>
