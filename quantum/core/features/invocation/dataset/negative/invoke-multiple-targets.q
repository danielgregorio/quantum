<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Multiple targets specified
Error: Invoke can only specify one target (function, component, url, endpoint, or service)
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-multiple-targets">
    <!-- ERROR: Cannot specify both function and url -->
    <q:invoke name="result"
              function="myFunction"
              url="https://api.example.com/data" />

    <q:return value="This should fail" />
</q:component>
