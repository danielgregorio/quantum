<!-- Test Conditionals Complete -->
<!-- Demonstrates all conditional patterns -->
<q:component name="TestConditionalsComplete" xmlns:q="https://quantum.lang/ns">

  <q:set name="score" type="number" value="85" />
  <q:set name="hasBonus" type="boolean" value="true" />
  <q:set name="result" value="" />

  <!-- Simple if -->
  <q:if condition="score >= 60">
    <q:set name="result" value="Passed" />
  </q:if>

  <!-- If with else -->
  <q:set name="status" value="" />
  <q:if condition="score >= 90">
    <q:set name="status" value="Excellent" />
    <q:else>
      <q:set name="status" value="Good" />
    </q:else>
  </q:if>

  <!-- If with elseif and else -->
  <q:set name="grade" value="" />
  <q:if condition="score >= 90">
    <q:set name="grade" value="A" />
    <q:elseif condition="score >= 80">
      <q:set name="grade" value="B" />
    </q:elseif>
    <q:elseif condition="score >= 70">
      <q:set name="grade" value="C" />
    </q:elseif>
    <q:elseif condition="score >= 60">
      <q:set name="grade" value="D" />
    </q:elseif>
    <q:else>
      <q:set name="grade" value="F" />
    </q:else>
  </q:if>

  <!-- Boolean conditions -->
  <q:set name="bonusText" value="" />
  <q:if condition="hasBonus == true">
    <q:set name="bonusText" value=" (with bonus)" />
  </q:if>

  <!-- Comparison operators -->
  <q:set name="comparison" value="" />
  <q:if condition="score > 80 and score &lt; 90">
    <q:set name="comparison" value="In 80s range" />
  </q:if>

  <q:return value="Result: {result}, Status: {status}, Grade: {grade}{bonusText}, Range: {comparison}" />
</q:component>
