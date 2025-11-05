<?xml version="1.0" encoding="UTF-8"?>
<q:component xmlns:q="https://quantum.lang/ns" name="test-invoke-function">

    <!-- Define a function that we'll invoke -->
    <q:function name="calculateSum">
        <q:param name="a" type="number" required="true" />
        <q:param name="b" type="number" required="true" />

        <q:set name="result" value="{a} + {b}" type="number" />

        <q:return value="{result}" />
    </q:function>

    <!-- Define another function with multiplication -->
    <q:function name="multiply">
        <q:param name="x" type="number" required="true" />
        <q:param name="y" type="number" required="true" />

        <q:set name="product" value="{x} * {y}" type="number" />

        <q:return value="{product}" />
    </q:function>

    <!-- Test 1: Invoke calculateSum function -->
    <q:invoke name="sum1" function="calculateSum">
        <q:param name="a" default="10" />
        <q:param name="b" default="20" />
    </q:invoke>

    <!-- Test 2: Invoke multiply function -->
    <q:invoke name="product1" function="multiply">
        <q:param name="x" default="5" />
        <q:param name="y" default="6" />
    </q:invoke>

    <!-- Test 3: Chain invocations - use result from sum1 -->
    <q:invoke name="product2" function="multiply">
        <q:param name="x" default="{sum1}" />
        <q:param name="y" default="2" />
    </q:invoke>

    <q:return value="sum={sum1}, product1={product1}, product2={product2}" />
</q:component>
