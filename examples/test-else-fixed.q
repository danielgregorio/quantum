<!-- Test Else Block -->
<q:component name="TestElseBlock" xmlns:q="https://quantum.lang/ns">
  <q:if condition="1 > 5">
    <q:return value="This should NOT show" />
    <q:else>
      <q:return value="Else block should show!" />
    </q:else>
  </q:if>
</q:component>
