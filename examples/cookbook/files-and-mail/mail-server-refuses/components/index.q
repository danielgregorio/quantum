<q:component name="Order">
  <q:action name="order" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="item" required="true" />
    <q:query name="saved" datasource="db">
      INSERT INTO orders (email, item) VALUES (:email, :item)
      <q:param name="email" value="{email}" type="string" />
      <q:param name="item" value="{item}" type="string" />
    </q:query>

    <!-- onerror="continue": a refused message does not undo the order -->
    <q:mail name="confirmation" to="{email}" subject="Your order: {item}"
            type="text" onerror="continue">We received your order for {item}.</q:mail>

    <q:if condition="confirmation_result.success">
      <q:redirect url="/" flash="Ordered {item}. A confirmation is on its way." />
    </q:if>
    <q:redirect url="/" flash="Ordered {item}. We could not send the confirmation e-mail." />
  </q:action>

  <h1>Order</h1>
  <q:if condition="flash"><p class="flash">{flash}</p></q:if>
  <form method="POST" action="/?action=order">
    <input name="email" type="email" />
    <input name="item" />
    <button>Order</button>
  </form>
</q:component>
