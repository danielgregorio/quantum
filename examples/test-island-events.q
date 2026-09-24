<q:component name="TestIslandEvents" interactive="true">
  <!-- Test: Event handlers in interactive islands -->

  <q:set name="defaultText" value="Type something..." />

  <input type="text"
         id="textInput"
         placeholder="{defaultText}"
         oninput="handleInput(event)"
         onkeypress="handleKeyPress(event)" />

  <div id="output">Character count: 0</div>
  <div id="lastKey"></div>

  <script>
    function handleInput(event) {
      const text = event.target.value;
      const charCount = text.length;
      document.getElementById('output').textContent = 'Character count: ' + charCount;
    }

    function handleKeyPress(event) {
      document.getElementById('lastKey').textContent = 'Last key: ' + event.key;
    }
  </script>

  <!-- Expected: Multiple event handlers work correctly -->
</q:component>
