<!-- Positive: Troubleshoot calculation error -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldTroubleshootCalculation" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="price" value="100" />
  <q:set var="discount" value="0.2" />
  <q:set var="final" value="{price - (price * discount)}" operation="subtract" />
  <q:dump var="{final}" label="Final Price Calculation" />

  <q:return value="Dumped" />
</q:component>
