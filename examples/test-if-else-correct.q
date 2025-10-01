<!-- Test If-Else (Correct Structure) -->
<q:component name="TestIfElse" xmlns:q="https://quantum.lang/ns">
  <q:if condition="1 == 2">
    <q:return value="This should not execute" />
    <q:else>
      <q:return value="Else block executed!" />
    </q:else>
  </q:if>
</q:component>
