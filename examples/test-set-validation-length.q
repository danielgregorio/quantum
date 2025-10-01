<!-- Test Set Validation Length -->
<q:component name="TestSetValidationLength" xmlns:q="https://quantum.lang/ns">
  <!-- Valid length -->
  <q:set name="username" type="string" value="daniel" minlength="3" maxlength="20" />
  <q:return value="Username: {username}" />
</q:component>
