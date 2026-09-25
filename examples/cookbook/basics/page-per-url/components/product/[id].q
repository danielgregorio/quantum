<q:component name="Product">
  <!-- components/product/[id].q answers /product/7 with id = "7". -->
  <q:set name="products" type="array"
         value='[{"name": "Kettle", "price": 35}, {"name": "Teapot", "price": 22}]' />
  <q:set name="n" type="integer" value="{id}" />

  <html>
  <body>
    <q:if condition="n >= 1 and n &lt;= len(products)">
      <h1>{products[n - 1].name}</h1>
      <p>Product {id}: ${products[n - 1].price}</p>
    </q:if>
    <q:else>
      <h1>No product {id}</h1>
    </q:else>
  </body>
  </html>
</q:component>
