<q:component name="Products">
  <!-- ?name=mouse from the URL; empty when it is not there. -->
  <q:set name="term" value="{query.name}" default="" />

  <!-- :pattern is bound to the q:param: the value is sent to the database
       apart from the SQL, so it can never change what the SQL does. -->
  <q:query name="products" datasource="db">
    SELECT name, price FROM products WHERE name LIKE :pattern ORDER BY price
    <q:param name="pattern" value="%{term}%" type="string" />
  </q:query>

  <ui:window title="Products">
    <ui:text>{products_result.recordCount} products</ui:text>
    <ui:table source="{products}">
      <ui:column key="name" label="Name" />
      <ui:column key="price" label="Price" />
    </ui:table>
  </ui:window>
</q:component>
