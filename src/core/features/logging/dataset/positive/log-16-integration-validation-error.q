<!-- Positive: Logging validation errors -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationValidationError" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="email" value="invalid-email" validate="email" />

  <q:log level="warning"
         message="Invalid email: {email}"
         when="{!email_valid}" />

  <q:return value="{email_valid}" />
</q:component>
