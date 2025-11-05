<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Invalid authentication type
Error: Invalid auth_type: custom. Must be bearer, apikey, basic, or oauth2
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-invalid-auth-type">
    <!-- ERROR: 'custom' is not a valid auth type -->
    <q:invoke name="result"
              url="https://api.example.com/data"
              method="GET"
              authType="custom"
              authToken="token123" />

    <q:return value="This should fail" />
</q:component>
