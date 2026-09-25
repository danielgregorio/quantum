<q:component name="Products">
  <q:query name="products" datasource="db">
    SELECT name, stock FROM products ORDER BY name
  </q:query>

  <ui:window title="Products">
    <ui:table source="{products}">
      <ui:column key="name" label="Name" />
      <ui:column key="stock" label="In stock" />
    </ui:table>
  </ui:window>
</q:component>
