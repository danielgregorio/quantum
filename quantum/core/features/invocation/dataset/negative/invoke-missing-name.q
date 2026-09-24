<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Missing required 'name' attribute
Error: Invoke requires 'name' attribute
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-missing-name">
    <!-- ERROR: Missing name attribute -->
    <q:invoke url="https://api.example.com/data" method="GET" />

    <q:return value="This should fail" />
</q:component>
