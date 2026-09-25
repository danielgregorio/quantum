<q:test name="the page still renders, and says why" page="/">
  <test:visit />
  <test:expect status="200" />
  <test:expect text="Returns are accepted within 30 days" />
  <test:expect text="No summary right now" />
  <test:expect text="127.0.0.1:9" />
  <test:expect no-text="In short:" />
</q:test>
