<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: HTTP with caching enabled
Tests: Result caching with TTL
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-http-with-cache">
    <q:invoke name="cachedUsers"
              url="https://jsonplaceholder.typicode.com/users"
              method="GET"
              cache="true"
              ttl="300000" />

    <q:return value="Users cached for 5 minutes: {cachedUsers[0].name}" />
</q:component>
