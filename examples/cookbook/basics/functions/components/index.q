<q:component name="Prices">
  <!-- Arguments are checked against the q:params on every call. -->
  <q:function name="withTax" returnType="number">
    <q:param name="amount" type="number" required="true" min="0" />
    <q:param name="rate" type="number" default="0.1" />
    <q:return value="{round(amount * (1 + rate), 2)}" />
  </q:function>

  <q:function name="label">
    <q:param name="amount" type="number" required="true" />
    <q:return value="{'free' if amount == 0 else '$' + str(amount)}" />
  </q:function>

  <q:set name="book" value="{withTax(20)}" />

  <html>
  <body>
    <p>Book: {label(book)}</p>
    <p>Food: {label(withTax(10, 0.05))}</p>
    <p>Sample: {label(withTax(0))}</p>
  </body>
  </html>
</q:component>
