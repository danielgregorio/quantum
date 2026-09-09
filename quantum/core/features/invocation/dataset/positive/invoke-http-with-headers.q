<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: HTTP with custom headers
Tests: Adding custom headers to request
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-http-with-headers">
    <q:invoke name="data"
              url="https://jsonplaceholder.typicode.com/posts/1"
              method="GET">
        <q:header name="Accept" value="application/json" />
        <q:header name="User-Agent" value="Quantum/1.0" />
        <q:header name="X-Custom-Header" value="test-value" />
    </q:invoke>

    <q:return value="{data.title}" />
</q:component>
