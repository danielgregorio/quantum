<q:component name="ArrayDemo">
  <!--
    🔄 ARRAY LOOP DEMONSTRATION

    Shows q:loop type="array" working with real data
  -->

  <h1>🔄 Array Loop Demo</h1>

  <!-- Demo 1: Simple array -->
  <div class="section">
    <h2>Demo 1: Simple Array</h2>

    <ul>
      <q:loop type="array" var="fruit" items="fruits">
        <li>{fruit}</li>
      </q:loop>
    </ul>
  </div>

  <!-- Demo 2: Array with index -->
  <div class="section">
    <h2>Demo 2: Array with Index</h2>

    <ul>
      <q:loop type="array" var="color" items="colors">
        <li>#{color_count}: {color}</li>
      </q:loop>
    </ul>
  </div>

  <!-- Demo 3: Nested objects (simulated) -->
  <div class="section">
    <h2>Demo 3: Users List</h2>

    <div class="users">
      <q:loop type="array" var="user" items="users">
        <div class="user-card">
          <h3>User #{user_count}</h3>
          <p>Data: {user}</p>
        </div>
      </q:loop>
    </div>
  </div>

  <!-- Demo 4: Empty array handling -->
  <div class="section">
    <h2>Demo 4: Empty Array</h2>

    <q:loop type="array" var="item" items="emptyArray">
      <p>This should not appear</p>
    </q:loop>

    <p>✓ Empty array handled correctly (no output above)</p>
  </div>

  <!-- Styling -->
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 20px;
      background: #f0f0f0;
    }

    h1 {
      color: #667eea;
    }

    .section {
      background: white;
      padding: 20px;
      margin: 20px 0;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .user-card {
      padding: 15px;
      margin: 10px 0;
      background: #f8f9fa;
      border-radius: 6px;
      border-left: 4px solid #667eea;
    }

    ul {
      list-style: none;
      padding: 0;
    }

    li {
      padding: 10px;
      margin: 5px 0;
      background: #f8f9fa;
      border-radius: 4px;
    }
  </style>
</q:component>
