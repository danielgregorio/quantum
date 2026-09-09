<!-- Test False Condition with Else -->
<q:component name="TestFalseCondition" xmlns:q="https://quantum.lang/ns">
  <q:if condition="1 > 5">
    <q:return value="This should NOT show" />
  <q:else>
    <q:return value="Else block should show!" />
  </q:else>
  </q:if>
</q:component>
