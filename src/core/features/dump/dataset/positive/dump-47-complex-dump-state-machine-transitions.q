<!-- Positive: Dump state machine transitions -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpStateMachineTransitions" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="state" value="pending" />
  <q:dump var="{state}" label="Initial State" />
  <q:set var="state" value="approved" />
  <q:dump var="{state}" label="After Approval" />
  <q:set var="state" value="completed" />
  <q:dump var="{state}" label="Final State" />

  <q:return value="Dumped" />
</q:component>
