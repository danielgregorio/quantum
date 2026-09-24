<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Local component invocation
Tests: Calling another component within same application
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-component-call">
    <q:invoke name="userResult"
              component="UserService"
              method="getUser">
        <q:param name="userId" default="123" />
    </q:invoke>

    <q:return value="{userResult}" />
</q:component>
