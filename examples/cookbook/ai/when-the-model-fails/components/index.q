<q:component name="Summary">
  <q:set name="text" value="Returns are accepted within 30 days of delivery, with the receipt." />

  <!-- endpoint= sends this one call to another server — here one that is not
       running, to show the failure. onerror="continue": instead of stopping
       the page, the failure is in summary_result and the value is empty. -->
  <q:llm name="summary" endpoint="http://127.0.0.1:9" timeout="5" onerror="continue">
    <q:prompt>Summarize in five words: {text}</q:prompt>
  </q:llm>

  <ui:window title="Policy">
    <ui:text>{text}</ui:text>
    <q:if condition="summary_result.success">
      <ui:text>In short: {summary}</ui:text>
      <q:else>
        <ui:alert variant="info">No summary right now — the assistant is unavailable.</ui:alert>
        <ui:text>Why: {summary_result.error.message}</ui:text>
      </q:else>
    </q:if>
  </ui:window>
</q:component>
