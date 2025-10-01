<!-- Test Set Validation Enum -->
<q:component name="TestSetValidationEnum" xmlns:q="https://quantum.lang/ns">
  <!-- Valid enum value -->
  <q:set name="status" type="string" value="active" enum="pending,active,inactive" />
  <q:return value="Status: {status}" />
</q:component>
