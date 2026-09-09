<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: HTTP with retry logic
Tests: Retry on failure with configurable delay
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-http-retry">
    <q:invoke name="unreliableApi"
              url="https://api.example.com/unstable-endpoint"
              method="GET"
              retry="3"
              retryDelay="1000"
              timeout="5000" />

    <q:if condition="{unreliableApi_result.success}">
        <q:return value="{unreliableApi}" />
    </q:if>
    <q:else>
        <q:return value="Failed after retries: {unreliableApi_result.error.message}" />
    </q:else>
</q:component>
