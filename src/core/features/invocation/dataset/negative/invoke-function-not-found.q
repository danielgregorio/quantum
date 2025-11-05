<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Invoking non-existent function
Error: Function 'nonExistentFunc' not found
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-function-not-found">
    <!-- ERROR: Function does not exist -->
    <q:invoke name="result" function="nonExistentFunc">
        <q:param name="arg1" default="value" />
    </q:invoke>

    <q:return value="This should fail" />
</q:component>
