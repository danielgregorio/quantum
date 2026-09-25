<q:test name="the form opens on the row's page" page="/book/2">
  <test:visit />
  <test:expect text="Edit a book" />
  <test:expect text="Save" />
  <test:expect no-text="There is no book" />
</q:test>

<q:test name="saving changes only that row" page="/book/2">
  <test:submit action="save" title="Libertinagem (1930)" genre="poetry" />
  <test:expect redirect="/" flash="Saved: Libertinagem (1930)" />
  <test:expect table="books" count="1" where="id = 2 AND title = 'Libertinagem (1930)'" />
  <test:expect table="books" count="1" where="id = 1 AND title = 'Dom Casmurro'" />
  <test:expect text="Libertinagem (1930) (poetry)" />
</q:test>

<q:test name="the table's rules still apply" page="/book/2">
  <test:submit action="save" title="Libertinagem" genre="comic" />
  <test:expect error="genre" message="Must be one of: novel, poetry, essay" />
  <test:expect table="books" count="1" where="id = 2 AND genre = 'poetry'" />
</q:test>

<q:test name="a book that does not exist says so" page="/book/99">
  <test:visit />
  <test:expect text="There is no book 99." />
  <test:expect no-text="Save" />
</q:test>
