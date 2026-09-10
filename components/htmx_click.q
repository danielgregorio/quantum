<q:component name="HTMXClick">
  <!-- Phase B: HTMX Partial - Click counter -->

  <q:set name="session.click_count" operation="increment" />

  {session.click_count}
</q:component>
