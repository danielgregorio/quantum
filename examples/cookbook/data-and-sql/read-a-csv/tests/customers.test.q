<q:test name="the active customers, oldest first" page="/">
  <test:visit />
  <test:expect text="Bruno 35 Ana 28 Davi 19" />
  <test:expect no-text="Carla" />
</q:test>
