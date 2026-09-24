<!-- Positive: XML import with XPath field mapping -->
<q:component name="XMLXPathImport" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
    <q:field name="id" xpath="@id" type="integer" />
    <q:field name="title" xpath="title/text()" type="string" />
    <q:field name="author" xpath="author/text()" type="string" />
    <q:field name="price" xpath="price/text()" type="decimal" />
  </q:data>

  <q:return value="{books}" />
</q:component>
