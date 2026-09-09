<!-- Positive: Real-world security alert logging -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldSecurityAlert" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="loginAttempts" value="5" />
  <q:set var="userIP" value="192.168.1.100" />

  <q:log level="critical"
         message="Multiple failed login attempts from {userIP}"
         when="{loginAttempts >= 5}"
         context='{"ip": {userIP}, "attempts": {loginAttempts}, "action": "account_locked"}' />

  <q:return value="Security alert logged" />
</q:component>
