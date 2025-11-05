<q:component name="HTMXClick">
  <!-- Phase B: HTMX Partial - Click counter -->

  <q:set name="clicks" value="{session.click_count}" default="0" />
  <q:set name="session.click_count" value="{clicks + 1}" />

  {session.click_count}
</q:component>
