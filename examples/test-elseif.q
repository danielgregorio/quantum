<!-- Test ElseIf -->
<q:component name="TestElseIf" xmlns:q="https://quantum.lang/ns">
  <q:if condition="1 == 2">
    <q:return value="First condition false" />
    <q:elseif condition="2 == 2">
      <q:return value="ElseIf condition is true!" />
    </q:elseif>
    <q:else>
      <q:return value="Else block" />
    </q:else>
  </q:if>
</q:component>
