<!-- Positive: Complex conditional branching with detailed logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexConditionalBranching" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="userRole" value="admin" />
  <q:set var="accountStatus" value="active" />
  <q:set var="permissionLevel" value="3" />

  <q:if condition="{userRole == 'admin' AND accountStatus == 'active'}">
    <q:log level="info"
           message="Admin access granted"
           context='{"role": {userRole}, "status": {accountStatus}, "permission": {permissionLevel}}' />
    <q:if condition="{permissionLevel >= 3}">
      <q:log level="debug" message="Full admin privileges enabled" />
    <q:else>
      <q:log level="warning" message="Limited admin access" />
    </q:if>
  <q:else>
    <q:if condition="{userRole == 'user'}">
      <q:log level="info" message="Standard user access" />
    <q:else>
      <q:log level="warning" message="Unknown role: {userRole}" />
    </q:if>
  </q:if>

  <q:return value="Access evaluated" />
</q:component>
