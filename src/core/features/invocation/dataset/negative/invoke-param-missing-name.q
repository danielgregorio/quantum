<?xml version="1.0" encoding="UTF-8"?>
<!--
Negative Example: Parameter missing name attribute
Error: Param name is required
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-param-missing-name">
    <q:function name="testFunc">
        <q:param name="arg1" type="string" required="true" />
        <q:return value="{arg1}" />
    </q:function>

    <q:invoke name="result" function="testFunc">
        <!-- ERROR: Param must have name attribute -->
        <q:param default="value" />
    </q:invoke>

    <q:return value="This should fail" />
</q:component>
