<q:component name="TestIslandInteractive" interactive="true">
  <!-- Test: Interactive island with client-side JavaScript -->

  <q:set name="initialCount" value="0" />

  <div id="counter">{initialCount}</div>
  <button onclick="increment()">Increment</button>
  <button onclick="decrement()">Decrement</button>
  <button onclick="reset()">Reset</button>

  <script>
    let count = {initialCount};

    function increment() {
      count++;
      document.getElementById('counter').textContent = count;
    }

    function decrement() {
      count--;
      document.getElementById('counter').textContent = count;
    }

    function reset() {
      count = 0;
      document.getElementById('counter').textContent = count;
    }
  </script>

  <!-- Expected: Client-side interactivity without server round-trips -->
</q:component>
