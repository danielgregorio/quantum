<!-- Test List Loop with Custom Delimiter -->
<q:component name="TestListLoopDelimiter" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="name" items="João|Maria|Pedro" delimiter="|">
    <q:return value="Name" />
  </q:loop>
</q:component>