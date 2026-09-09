<!-- Test Action Complete -->
<!-- Demonstrates all q:action patterns for form handling -->
<q:component name="TestActionComplete" xmlns:q="https://quantum.lang/ns">

  <!-- Simple form action -->
  <q:action name="simpleSubmit" method="POST">
    <q:set name="message" value="Form submitted!" />
    <q:return value="{message}" />
  </q:action>

  <!-- Action with validation -->
  <q:action name="validateUser" method="POST">
    <q:param name="username" required="true" minLength="3" maxLength="20" />
    <q:param name="email" required="true" pattern="^[^@]+@[^@]+\.[^@]+$" />
    <q:param name="age" type="number" required="true" min="18" max="120" />

    <q:set name="result" value="User {username} validated" />
    <q:return value="{result}" />
  </q:action>

  <!-- Action with redirect -->
  <q:action name="loginAction" method="POST">
    <q:param name="user" required="true" />
    <q:param name="pass" required="true" />

    <q:if condition="user == 'admin' and pass == 'secret'">
      <q:set name="session.loggedIn" value="true" />
      <q:redirect url="/dashboard" />
      <q:else>
        <q:flash type="error" message="Invalid credentials" />
        <q:redirect url="/login" />
      </q:else>
    </q:if>
  </q:action>

  <!-- Action with flash messages -->
  <q:action name="saveData" method="POST">
    <q:param name="data" required="true" />

    <q:set name="saved" value="true" />
    <q:flash type="success" message="Data saved successfully!" />
    <q:return value="Saved: {saved}" />
  </q:action>

  <q:return value="Actions defined: simpleSubmit, validateUser, loginAction, saveData" />
</q:component>
