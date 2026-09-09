<!-- Test Validation Complete -->
<!-- Demonstrates all q:set validation patterns -->
<q:component name="TestValidationComplete" xmlns:q="https://quantum.lang/ns">

  <!-- String length validation -->
  <q:set name="username" value="john_doe"
         validation="length"
         minLength="3"
         maxLength="20" />

  <!-- Numeric range validation -->
  <q:set name="age" type="number" value="25"
         validation="range"
         min="18"
         max="120" />

  <!-- Email pattern validation -->
  <q:set name="email" value="john@example.com"
         validation="email" />

  <!-- Enum validation -->
  <q:set name="status" value="active"
         validation="enum"
         allowedValues="active,inactive,pending" />

  <!-- CPF validation (Brazilian ID) -->
  <q:set name="cpf" value="123.456.789-09"
         validation="cpf" />

  <!-- Custom pattern validation -->
  <q:set name="phone" value="555-1234"
         validation="pattern"
         pattern="^\d{3}-\d{4}$" />

  <!-- Required field -->
  <q:set name="required_field" value="must have value"
         required="true" />

  <q:return value="Username: {username}, Age: {age}, Email: {email}, Status: {status}" />
</q:component>
