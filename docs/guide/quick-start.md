# Quick Start

Build your first Quantum application in 5 minutes.

## Step 1: Create a Component

Create a file called `counter.q`:

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <!-- Initialize state -->
  <q:set name="count" value="0" type="number" />

  <!-- Function to increment -->
  <q:function name="increment">
    <q:set name="count" value="{count + 1}" />
  </q:function>

  <!-- Function to decrement -->
  <q:function name="decrement">
    <q:set name="count" value="{count - 1}" />
  </q:function>

  <!-- Return current count -->
  <q:return value="Count: {count}" />
</q:component>
```

Run it:
```bash
python src/cli/runner.py run counter.q
```

## Step 2: Add a Loop

Create `todo-list.q`:

```xml
<q:component name="TodoList" xmlns:q="https://quantum.lang/ns">
  <!-- Define tasks as an array -->
  <q:set name="tasks" value='["Buy groceries", "Walk the dog", "Write code"]' />

  <q:return value="My Todo List:" />

  <!-- Loop through tasks -->
  <q:loop type="array" var="task" items="{tasks}">
    <q:return value="- {task}" />
  </q:loop>

  <q:return value="Total: {tasks.length} tasks" />
</q:component>
```

Output:
```
["My Todo List:", "- Buy groceries", "- Walk the dog", "- Write code", "Total: 3 tasks"]
```

## Step 3: Add Conditionals

Create `weather.q`:

```xml
<q:component name="Weather" xmlns:q="https://quantum.lang/ns">
  <q:set name="temperature" value="25" type="number" />

  <q:if condition="temperature > 30">
    <q:return value="It's hot! Stay hydrated." />
  </q:if>
  <q:elseif condition="temperature > 20">
    <q:return value="Nice weather for a walk." />
  </q:elseif>
  <q:elseif condition="temperature > 10">
    <q:return value="Bring a jacket." />
  </q:elseif>
  <q:else>
    <q:return value="Bundle up, it's cold!" />
  </q:else>
</q:component>
```

## Step 4: Create a Web Application

Create `webapp.q`:

```xml
<q:application id="webapp" type="html" xmlns:q="https://quantum.lang/ns">

  <q:route path="/" method="GET">
    <!DOCTYPE html>
    <html>
    <head>
      <title>My Quantum App</title>
      <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 8px; }
      </style>
    </head>
    <body>
      <h1>Welcome to Quantum</h1>

      <div class="card">
        <h2>Quick Stats</h2>
        <q:set name="items" value='["Apple", "Banana", "Cherry"]' />
        <ul>
          <q:loop type="array" var="item" items="{items}">
            <li>{item}</li>
          </q:loop>
        </ul>
      </div>

      <div class="card">
        <h2>Calculator</h2>
        <q:set name="a" value="10" />
        <q:set name="b" value="5" />
        <p>{a} + {b} = {a + b}</p>
        <p>{a} - {b} = {a - b}</p>
        <p>{a} * {b} = {a * b}</p>
      </div>
    </body>
    </html>
  </q:route>

</q:application>
```

Start the server:
```bash
python src/cli/runner.py start webapp.q
```

Visit `http://localhost:5000` in your browser.

## Step 5: Build a UI Application

Create `myapp.q`:

```xml
<q:application id="myapp" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="userName" value="" />
  <q:set name="greeting" value="Welcome!" />

  <q:function name="updateGreeting">
    <q:set name="greeting" value="Hello, {userName}!" />
  </q:function>

  <ui:window title="My First App">
    <ui:vbox padding="lg" gap="md">

      <ui:header>
        <ui:text size="2xl" weight="bold">Quantum UI Demo</ui:text>
      </ui:header>

      <ui:panel title="User Form">
        <ui:form>
          <ui:formitem label="Your Name">
            <ui:input bind="userName" placeholder="Enter your name" />
          </ui:formitem>
          <ui:button variant="primary" on-click="updateGreeting">
            Say Hello
          </ui:button>
        </ui:form>
      </ui:panel>

      <ui:card>
        <ui:text size="lg">{greeting}</ui:text>
      </ui:card>

      <ui:hbox gap="sm">
        <ui:badge variant="success">Online</ui:badge>
        <ui:badge variant="primary">v1.0</ui:badge>
      </ui:hbox>

    </ui:vbox>
  </ui:window>

</q:application>
```

Build for HTML:
```bash
python src/cli/runner.py build myapp.q --target html -o myapp.html
```

Build for Desktop:
```bash
python src/cli/runner.py build myapp.q --target desktop -o myapp.py
python myapp.py  # Run the desktop app
```

## Step 6: Add Database

Create `users.q`:

```xml
<q:component name="UserManager" xmlns:q="https://quantum.lang/ns">
  <!-- Query users from database -->
  <q:query name="users" datasource="mydb">
    SELECT id, name, email, created_at
    FROM users
    WHERE active = 1
    ORDER BY created_at DESC
    LIMIT 10
  </q:query>

  <q:return value="Active Users:" />

  <!-- Loop through query results -->
  <q:loop query="users">
    <q:return value="- {users.name} ({users.email})" />
  </q:loop>

  <q:return value="Found {users_result.recordCount} users" />
</q:component>
```

## What's Next?

You've learned the basics! Now explore:

- [Components](/guide/components) - Deep dive into the component system
- [State Management](/guide/state-management) - Advanced variable handling
- [UI Engine](/ui-engine/overview) - Build rich user interfaces
- [Database Queries](/guide/query) - SQL and data operations
- [Examples](/examples/) - More real-world examples
