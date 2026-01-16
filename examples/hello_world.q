<q:component name="HelloWorld">
  <q:set name="name" value="Quantum" />
  <q:set name="version" value="1.0" />

  <h1>Hello {name}!</h1>
  <p>Welcome to Quantum Framework v{version}</p>

  <q:set name="count" value="3" />
  <h2>Counting to {count}:</h2>
  <ul>
    <q:loop type="range" var="i" from="1" to="{count}">
      <li>Number {i}</li>
    </q:loop>
  </ul>
</q:component>
