<!-- Positive: Debug validation failure -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldDebugValidationFailure" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="email" value="invalid-email" validate="email" />
  <q:dump var="{email}" when="{!email_valid}" label="Failed Validation" />

  <q:return value="Dumped" />
</q:component>
