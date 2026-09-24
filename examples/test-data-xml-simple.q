<q:component name="TestDataXML" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import XML file with XPath -->
  <q:data name="books" source="examples/test-data-books.xml" type="xml" xpath=".//book">
    <q:field name="id" xpath="@id" type="integer" />
    <q:field name="title" xpath="title/text()" type="string" />
    <q:field name="author" xpath="author/text()" type="string" />
    <q:field name="year" xpath="year/text()" type="integer" />
    <q:field name="price" xpath="price/text()" type="decimal" />
  </q:data>

  <!-- Loop through books and print -->
  <q:loop items="{books}" var="book">
    Book {book.id}: {book.title} by {book.author} ({book.year}) - ${book.price}
  </q:loop>

  <q:return value="{books}" />
</q:component>
