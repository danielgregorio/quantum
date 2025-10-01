<!-- Test Databinding with List Loop -->
<q:component name="TestDatabindingList" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>