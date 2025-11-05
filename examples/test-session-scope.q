<q:component name="TestSessionScope">
  <!-- Test: Session-scoped variables (user-specific) -->

  <q:set name="session.visitCount" value="{session.visitCount + 1}" />
  <q:set name="session.userName" value="John Doe" />
  <q:set name="session.lastVisit" value="2025-11-05" />

  <!-- Expected: Session variables persist across requests for this user -->
  Session visit count: {session.visitCount}
  User: {session.userName}
  Last visit: {session.lastVisit}
</q:component>
