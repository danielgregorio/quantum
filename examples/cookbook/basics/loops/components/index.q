<q:component name="Loops">
  <q:set name="fruits" type="array" value='["Apple", "Banana", "Cherry"]' />

  <html>
  <body>
    <h2>A list</h2>
    <ol>
      <!-- index= names the position, from 0 -->
      <q:loop type="array" var="fruit" index="i" items="{fruits}">
        <li>{i + 1}. {fruit}</li>
      </q:loop>
    </ol>

    <h2>A range</h2>
    <p>
      <!-- from and to are both included -->
      <q:loop type="range" var="n" from="2" to="10" step="2">
        <span>[{n}]</span>
      </q:loop>
    </p>

    <h2>Text split by commas</h2>
    <ul>
      <q:loop type="list" var="tag" items="red, green , blue">
        <li>({tag})</li>
      </q:loop>
    </ul>
  </body>
  </html>
</q:component>
