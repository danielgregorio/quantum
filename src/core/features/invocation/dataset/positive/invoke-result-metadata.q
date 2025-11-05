<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Using result metadata
Tests: Accessing success, error, execution_time from result object
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-result-metadata">
    <q:invoke name="apiCall"
              url="https://jsonplaceholder.typicode.com/posts/1"
              method="GET"
              result="apiMeta" />

    <q:if condition="{apiCall_result.success}">
        <q:return value="Success! Took {apiCall_result.execution_time}ms - Status: {apiMeta.status_code}" />
    </q:if>
    <q:else>
        <q:return value="Error: {apiCall_result.error.message}" />
    </q:else>
</q:component>
