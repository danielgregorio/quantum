<q:test name="an edit is recorded with who made it" page="/">
  <test:as user="ana" />
  <test:submit action="edit" title="Welcome!" body="Second draft." />
  <test:expect redirect="/" flash="Saved." />
  <test:expect history="pages" action="edit" op="update" user="ana" count="1" />
  <test:expect text="title: Welcome → Welcome!" />
  <test:expect text="body: First draft. → Second draft." />
</q:test>

<q:test name="a refused edit leaves no history" page="/">
  <test:as user="ana" />
  <test:submit action="edit" title="W" />
  <test:expect error="title" />
  <test:expect history="pages" count="0" />
</q:test>
