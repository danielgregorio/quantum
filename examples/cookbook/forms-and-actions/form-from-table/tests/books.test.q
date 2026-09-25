<q:test name="the form draws a field per column, labelled from its name" page="/">
  <test:visit />
  <test:expect text="Title" />
  <test:expect text="Author" />
  <test:expect text="Machado de Assis" />
  <test:expect text="Add book" />
</q:test>

<q:test name="a book is added" page="/">
  <test:submit action="add" title="Dom Casmurro" author_id="2" genre="novel" pages="256" />
  <test:expect redirect="/" flash="Added: Dom Casmurro" />
  <test:expect table="books" count="1" where="title = 'Dom Casmurro' AND pages = 256 AND lent = 0" />
</q:test>

<q:test name="the rules come from the schema" page="/">
  <test:submit action="add" title="" author_id="9" genre="comic" pages="many" />
  <test:expect error="title" message="Required" />
  <test:expect error="author_id" message="Must name an existing row of authors (no id = 9)" />
  <test:expect error="genre" message="Must be one of: novel, poetry, essay" />
  <test:expect error="pages" message="Must be an integer, got 'many'" />
  <test:expect table="books" count="0" />
</q:test>

<q:test name="a blank optional column is stored as NULL" page="/">
  <test:submit action="add" title="A hora da estrela" author_id="1" genre="novel" pages="" />
  <test:expect table="books" count="1" where="pages IS NULL" />
</q:test>
