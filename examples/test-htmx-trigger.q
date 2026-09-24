<q:component name="TestHtmxTrigger">
  <!-- Test: HTMX trigger mechanisms -->

  <q:set name="timestamp" value="2025-11-05 14:30:00" />

  <!-- Trigger on click -->
  <button hx-get="/_partial/TestHtmxTrigger"
          hx-trigger="click"
          hx-target="#result"
          hx-swap="innerHTML">
    Refresh
  </button>

  <!-- Trigger every 5 seconds -->
  <div hx-get="/_partial/TestHtmxTrigger"
       hx-trigger="every 5s"
       hx-swap="innerHTML">
    Last updated: {timestamp}
  </div>

  <div id="result">
    <!-- Result will be loaded here -->
  </div>
</q:component>
