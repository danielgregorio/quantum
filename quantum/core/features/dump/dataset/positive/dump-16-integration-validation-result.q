<!-- Positive: Dump validation result -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationValidationResult" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="email" value="test@example.com" validate="email" />
  <q:dump var="{email_valid}" label="Email Valid" />

  <q:return value="Dumped" />
</q:component>
