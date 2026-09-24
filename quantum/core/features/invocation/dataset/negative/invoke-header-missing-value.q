<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Header missing value attribute
Error: Header 'Content-Type' value is required
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-header-missing-value">
    <q:invoke name="result"
              url="https://api.example.com/data"
              method="GET">
        <!-- ERROR: Header must have value attribute -->
        <q:header name="Content-Type" />
    </q:invoke>

    <q:return value="This should fail" />
</q:component>
