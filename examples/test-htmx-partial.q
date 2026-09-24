<q:component name="TestHtmxPartial">
  <!-- Test: HTMX partial rendering -->

  <q:set name="counter" value="0" />

  <div hx-get="/_partial/TestHtmxPartial"
       hx-trigger="load"
       hx-swap="innerHTML">
    Loading counter...
  </div>

  <!-- Expected: Partial can be loaded via /_partial/ endpoint -->
  Counter: {counter}
</q:component>
