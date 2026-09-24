<!-- Test If-Else -->
<q:component name="TestIfElse" xmlns:q="https://quantum.lang/ns">
  <q:if condition="2 > 5">
    <q:return value="This should not execute" />
  <q:else>
    <q:return value="Else block executed successfully!" />
  </q:else>
  </q:if>
</q:component>
