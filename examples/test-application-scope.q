<q:component name="TestApplicationScope">
  <!-- Test: Application-scoped variables (shared across all users) -->

  <q:set name="application.totalVisits" value="{application.totalVisits + 1}" />
  <q:set name="application.startTime" value="2025-11-05 10:00:00" />
  <q:set name="application.version" value="1.0.0" />

  <!-- Expected: Application variables shared by all users -->
  Total visits (all users): {application.totalVisits}
  App version: {application.version}
  Started: {application.startTime}
</q:component>
