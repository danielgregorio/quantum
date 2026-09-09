<!-- Negative: Field missing required 'xpath' attribute -->
<!-- Expected error: Field requires 'xpath' attribute -->
<q:component name="DataFieldMissingXPath" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
    <q:field name="title" type="string" />
  </q:data>

  <q:return value="Error" />
</q:component>
