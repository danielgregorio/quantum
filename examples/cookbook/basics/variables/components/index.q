<q:component name="Receipt">
  <q:set name="item" value="Coffee beans" />
  <q:set name="price" type="number" value="12.5" />
  <q:set name="quantity" type="number" value="3" />
  <!-- A value that is one expression keeps its type: total is a number. -->
  <q:set name="total" value="{price * quantity}" />
  <!-- default is stored when the value is empty or missing. -->
  <q:set name="note" value="{query.note}" default="no note" />
  <q:set name="quantity" operation="increment" />

  <html>
  <body>
    <h1>{upper(item)}</h1>
    <p>{quantity} bags at {price} = {total}</p>
    <p>With the extra bag: {price * quantity}</p>
    <p>Note: {note}</p>
  </body>
  </html>
</q:component>
