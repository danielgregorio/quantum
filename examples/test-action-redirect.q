<q:component name="TestActionRedirect">
  <!-- Test: Redirect with flash message -->

  <q:action name="deleteItem" method="POST">
    <q:param name="itemId" type="integer" required="true" />

    <q:set name="deleted" value="true" />
    <q:redirect url="/items" flash="Item {itemId} deleted successfully" />
  </q:action>

  <!-- Expected: Redirect defined with flash message -->
  Redirect with flash message configured
</q:component>
