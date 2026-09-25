<q:test name="every book before a search" page="/">
  <test:visit />
  <test:expect text="4 books" />
</q:test>

<q:test name="a title or an author" page="/">
  <test:visit q="machado" />
  <test:expect text="2 books" />
  <test:expect text="Quincas Borba — Machado de Assis" />
  <test:expect no-text="Vidas Secas" />
</q:test>

<q:test name="nothing found" page="/">
  <test:visit q="tolstoy" />
  <test:expect text="0 books" />
</q:test>
