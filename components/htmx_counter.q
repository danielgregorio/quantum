<q:component name="HTMXCounter">
  <!-- Phase B: HTMX Partial - Auto-updating counter -->

  <q:set name="counter" value="{application.htmx_counter}" default="0" />
  <q:set name="application.htmx_counter" value="{counter + 1}" />

  <div>
    <p style="font-size: 3rem; color: #2ecc71; font-weight: bold;">{application.htmx_counter}</p>
    <p style="color: #7f8c8d; font-size: 0.9rem;">Updates every 2 seconds</p>
  </div>
</q:component>
