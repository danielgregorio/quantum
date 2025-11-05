<!-- Negative: Field missing required 'name' attribute -->
<!-- Expected error: Field requires 'name' attribute -->
<q:component name="DataFieldMissingName" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
    <q:field xpath="title/text()" type="string" />
  </q:data>

  <q:return value="Error" />
</q:component>
