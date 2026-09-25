<q:test name="a function called from q:set and from the HTML" page="/">
  <test:visit />
  <test:expect var="book" value="22.0" />
  <test:expect text="Book: $22.0" />
</q:test>

<q:test name="an argument by position replaces the default" page="/">
  <test:visit />
  <test:expect text="Food: $10.5" />
</q:test>

<q:test name="functions compose" page="/">
  <test:visit />
  <test:expect text="Sample: free" />
</q:test>
