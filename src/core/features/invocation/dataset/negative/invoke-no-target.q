<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: No invocation target specified
Error: Invoke requires one of: function, component, url, endpoint, or service
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-no-target">
    <!-- ERROR: Must specify function, component, url, endpoint, or service -->
    <q:invoke name="result" method="GET" />

    <q:return value="This should fail" />
</q:component>
