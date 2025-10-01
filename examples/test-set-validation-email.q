<!-- Test Set Validation Email -->
<q:component name="TestSetValidationEmail" xmlns:q="https://quantum.lang/ns">
  <!-- Valid email -->
  <q:set name="email" type="string" value="daniel@example.com" validate="email" />
  <q:return value="Email: {email}" />
</q:component>
