<q:component name="Stock">
  <!-- /?stock=3 -->
  <q:set name="stock" type="number" value="{query.stock}" default="0" />

  <html>
  <body>
    <q:if condition="stock == 0">
      <p class="out">Out of stock.</p>
    </q:if>
    <q:elseif condition="stock &lt; 5">
      <p class="low">Only {stock} left.</p>
    </q:elseif>
    <q:else>
      <p>In stock.</p>
    </q:else>

    <!-- A condition is an expression: and, or, not work as in Python. -->
    <q:if condition="stock > 0 and stock % 2 == 0">
      <p>Sold in pairs: {stock // 2} pairs.</p>
    </q:if>
  </body>
  </html>
</q:component>
