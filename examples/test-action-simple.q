<q:component name="TestActionSimple">
  <!-- Test: Simple action execution -->

  <q:action name="createUser" method="POST">
    <q:param name="username" type="string" required="true" />
    <q:param name="email" type="email" required="true" />

    <q:set name="userCreated" value="true" />
    <q:set name="userId" value="123" />
  </q:action>

  <!-- Expected: Action defined successfully, params validated -->
  Action 'createUser' defined successfully
</q:component>
