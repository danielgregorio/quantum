<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Invalid HTTP method
Error: Invalid HTTP method: INVALID
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-invalid-method">
    <!-- ERROR: INVALID is not a valid HTTP method -->
    <q:invoke name="result"
              url="https://api.example.com/data"
              method="INVALID" />

    <q:return value="This should fail" />
</q:component>
