<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Header missing name attribute
Error: Header name is required
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-header-missing-name">
    <q:invoke name="result"
              url="https://api.example.com/data"
              method="GET">
        <!-- ERROR: Header must have name attribute -->
        <q:header value="application/json" />
    </q:invoke>

    <q:return value="This should fail" />
</q:component>
