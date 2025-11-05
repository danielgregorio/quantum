<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Basic function invocation
Tests: Simple function call with parameters
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-function-basic">
    <q:function name="greet">
        <q:param name="name" type="string" required="true" />
        <q:return value="Hello, {name}!" />
    </q:function>

    <q:invoke name="greeting" function="greet">
        <q:param name="name" default="World" />
    </q:invoke>

    <q:return value="{greeting}" />
</q:component>
