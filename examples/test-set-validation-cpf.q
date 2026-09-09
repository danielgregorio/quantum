<!-- Test Set Validation CPF -->
<q:component name="TestSetValidationCPF" xmlns:q="https://quantum.lang/ns">
  <!-- Valid CPF -->
  <q:set name="cpf" type="string" value="123.456.789-09" validate="cpf" />
  <q:return value="CPF: {cpf}" />
</q:component>
