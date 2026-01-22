<q:component name="SimpleTodo">
  <h1>📝 Simple TODO App</h1>

  <!-- Initialize state -->
  <q:set name="total" value="5" />
  <q:set name="completed" value="2" />

  <div class="container">
    <h2>Task Statistics</h2>

    <p>Total Tasks: {total}</p>
    <p>Completed: {completed}</p>

    <!-- Calculate remaining -->
    <q:set name="remaining" value="{total - completed}" />
    <p>Remaining: {remaining}</p>

    <!-- Loop demo -->
    <h3>Task List</h3>
    <ul>
      <q:loop type="range" var="i" from="1" to="{total}">
        <li>Task #{i}</li>
      </q:loop>
    </ul>
  </div>

  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 20px;
      background: #f0f0f0;
    }

    .container {
      background: white;
      padding: 30px;
      border-radius: 8px;
      max-width: 600px;
      margin: 0 auto;
    }

    h1 {
      color: #667eea;
    }

    ul {
      list-style: none;
      padding: 0;
    }

    li {
      padding: 10px;
      margin: 5px 0;
      background: #f5f5f5;
      border-radius: 4px;
    }
  </style>
</q:component>
