<q:component name="Cart">
  <!-- Three actions on one page. Each form (and each button) sends the name
       of its action in the field "action"; the page runs that one only. -->
  <q:action name="add" method="POST">
    <q:param name="item" required="true" maxlength="60" />
    <q:param name="quantity" type="integer" min="1" max="99" default="1" />
    <q:query name="added" datasource="db">
      INSERT INTO cart (item, quantity) VALUES (:item, :quantity)
      <q:param name="item" value="{item}" type="string" />
      <q:param name="quantity" value="{quantity}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Added {quantity} × {item}." />
  </q:action>

  <q:action name="remove" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM cart WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Removed." />
  </q:action>

  <q:action name="empty" method="POST">
    <q:query name="emptied" datasource="db">DELETE FROM cart</q:query>
    <q:redirect url="/" flash="The cart is empty." />
  </q:action>

  <q:query name="cart" datasource="db">
    SELECT id, item, quantity FROM cart ORDER BY id
  </q:query>

  <ui:window title="Cart">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="add">
      <ui:hbox gap="sm">
        <ui:input bind="item" placeholder="Item" grow="true" />
        <ui:input bind="quantity" width="80" />
        <ui:button variant="primary">Add</ui:button>
      </ui:hbox>
    </ui:form>
    <q:loop query="cart">
      <ui:hbox gap="sm" align="center">
        <ui:text>{cart.quantity} × {cart.item}</ui:text>
        <!-- with= sends the row's id along with the action's name. -->
        <ui:button on-click="remove" with="id={cart.id}">Remove</ui:button>
      </ui:hbox>
    </q:loop>
    <ui:button on-click="empty" variant="danger">Empty the cart</ui:button>
  </ui:window>
</q:component>
