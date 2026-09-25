<q:component name="Import">
  <q:action name="load" method="POST">
    <q:data name="rows" source="import/products.csv" type="csv">
      <q:column name="price" type="integer" />
    </q:data>

    <!-- One transaction for the whole file: if one row is refused (a sku
         already there, a price that is not positive), none stays. -->
    <q:transaction datasource="db">
      <q:loop items="{rows}" var="row">
        <q:query name="inserted" datasource="db">
          INSERT INTO products (sku, name, price) VALUES (:sku, :name, :price)
          <q:param name="sku" value="{row.sku}" type="string" />
          <q:param name="name" value="{row.name}" type="string" />
          <q:param name="price" value="{row.price}" type="integer" />
        </q:query>
      </q:loop>
    </q:transaction>

    <q:redirect url="/" flash="Loaded {len(rows)} products." />
  </q:action>

  <q:query name="products" datasource="db">SELECT sku, name, price FROM products ORDER BY sku</q:query>

  <ui:window title="Products">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <ui:text>{products_result.recordCount} products</ui:text>
    <ui:table source="{products}" />
    <ui:form on-submit="load" submit="Load import/products.csv" />
  </ui:window>
</q:component>
