<!-- Todo List -->
<q:component name="TodoList">
  <q:set name="todos" type="array" value="Learn Quantum,Build an app,Deploy to production" />
  <q:set name="title" value="My Todo List" />

  <style>
    .todo-app { max-width: 500px; margin: 0 auto; padding: 20px; font-family: sans-serif; }
    .todo-header { margin-bottom: 20px; }
    .todo-input { display: flex; gap: 8px; margin-bottom: 20px; }
    .todo-input input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }
    .todo-input button { padding: 12px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; }
    .todo-list { list-style: none; padding: 0; }
    .todo-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #f5f5f5; border-radius: 6px; margin-bottom: 8px; }
    .todo-item input[type="checkbox"] { width: 20px; height: 20px; }
    .todo-item span { flex: 1; }
    .todo-count { color: #666; font-size: 14px; margin-top: 16px; }
  </style>

  <div class="todo-app">
    <div class="todo-header">
      <h1>{title}</h1>
    </div>

    <div class="todo-input">
      <input type="text" placeholder="Add a new todo..." />
      <button>Add</button>
    </div>

    <ul class="todo-list">
      <q:loop type="list" var="todo" items="{todos}" index="i">
        <li class="todo-item">
          <input type="checkbox" />
          <span>{todo}</span>
          <button style="background: #ef4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">Delete</button>
        </li>
      </q:loop>
    </ul>

    <p class="todo-count">3 items in list</p>
  </div>
</q:component>
