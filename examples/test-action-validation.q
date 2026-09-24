<q:component name="TestActionValidation">
  <!-- Test: Action parameter validation -->

  <q:action name="register" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" type="string" minlength="8" required="true" />
    <q:param name="age" type="integer" min="18" max="120" required="true" />

    <q:set name="registered" value="true" />
  </q:action>

  <!-- Expected: Validation rules defined correctly -->
  Validation rules: email, password (min 8 chars), age (18-120)
</q:component>
