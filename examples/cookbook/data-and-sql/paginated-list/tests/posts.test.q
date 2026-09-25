<q:test name="the first page" page="/">
  <test:visit />
  <test:expect text="1–10 of 23" />
  <test:expect text="Post 23" />
  <test:expect text="Post 14" />
  <test:expect no-text="Post 13" />
</q:test>

<q:test name="the last page" page="/">
  <test:visit page="3" />
  <test:expect text="21–23 of 23" />
  <test:expect text="Post 1" />
  <test:expect no-text="Post 4" />
</q:test>

<q:test name="a page that is not a number is page 1" page="/">
  <test:visit page="abc" />
  <test:expect text="1–10 of 23" />
</q:test>
