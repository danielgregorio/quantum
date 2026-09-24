<!-- Positive: Real-world GDPR compliance audit log -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldGDPRCompliance" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="dataAccess" value='{"userId": 789, "adminId": 101, "action": "view_personal_data", "reason": "customer_support_request"}' operation="json" />

  <q:log level="info"
         message="Personal data accessed by admin {dataAccess.adminId}"
         context="{dataAccess}" />

  <q:return value="GDPR audit logged" />
</q:component>
