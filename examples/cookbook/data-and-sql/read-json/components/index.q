<q:component name="Cart">
  <!-- A JSON array is the list as it is; each object is a record. -->
  <q:data name="items" source="import/products.json" type="json">
    <q:transform>
      <q:compute field="subtotal" expression="{price} * {qty}" type="integer" />
      <q:sort by="subtotal" order="desc" />
    </q:transform>
  </q:data>

  <ui:window title="Cart">
    <ui:table source="{items}">
      <ui:column key="name" label="Item" />
      <ui:column key="qty" label="Qty" />
      <ui:column key="subtotal" label="Subtotal" />
    </ui:table>
  </ui:window>
</q:component>
