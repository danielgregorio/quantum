<!-- Test Conditional Logic -->
<q:component name="TestConditionals" xmlns:q="https://quantum.lang/ns">
  <q:param name="age" type="number" required="true" />
  <q:param name="hasParentConsent" type="boolean" default="false" />
  
  <q:if condition="age >= 18">
    <q:return value="Adult content available" />
  </q:if>
</q:component>
