<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: HTTP with Bearer token authentication
Tests: Bearer token auth in Authorization header
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-http-bearer-auth">
    <q:invoke name="protectedData"
              url="https://api.example.com/data"
              method="GET"
              authType="bearer"
              authToken="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." />

    <q:return value="{protectedData}" />
</q:component>
