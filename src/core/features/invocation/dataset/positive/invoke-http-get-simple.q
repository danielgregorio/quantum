<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Simple HTTP GET request
Tests: Basic REST API invocation without auth
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-http-get-simple">
    <q:invoke name="user"
              url="https://jsonplaceholder.typicode.com/users/1"
              method="GET"
              timeout="5000" />

    <q:return value="{user.name}" />
</q:component>
