<q:test name="each card has its title and the page's content" page="/">
  <test:visit />
  <test:expect text="Open tickets 4 waiting for an answer." />
  <test:expect text="Warning The mail server is slow today." />
</q:test>

<q:test name="a component in a _ folder is not a page" page="/_shared/Card">
  <test:visit />
  <test:expect status="404" />
</q:test>
