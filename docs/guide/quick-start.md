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
quantum run counter.q
```

## Step 2: Add a Loop

Create `todo-list.q`:

```xml
<q:component name="TodoList" xmlns:q="https://quantum.lang/ns">
  <!-- Define tasks as an array -->
  <q:set name="tasks" value='["Buy groceries", "Walk the dog", "Write code"]' />

  <!-- Loop through tasks: each q:return adds one item to the result -->
  <q:loop type="array" var="task" items="{tasks}">
    <q:return value="- {task}" />
  </q:loop>
</q:component>
```

Output:
```
["- Buy groceries", "- Walk the dog", "- Write code"]
```

A `q:return` inside a loop does not stop the loop: every value is collected,
and when the loop ends the component returns the list — the same way a
`q:return` inside `q:if` ends the component. A loop that runs no `q:return`
lets execution continue to what comes after it.

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

## Step 4: Serve a Web Page

Pages live in a `components/` folder; the file name is the URL. Create
`components/index.q`:

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["Apple", "Banana", "Cherry"]' />
  <q:set name="a" value="10" type="number" />
  <q:set name="b" value="5" type="number" />

  <html>
  <head><title>My Quantum App</title></head>
  <body>
    <h1>Welcome to Quantum</h1>
    <ul>
      <q:loop type="array" var="item" items="{items}">
        <li>{item}</li>
      </q:loop>
    </ul>
    <p>{a} + {b} = {a + b}</p>
  </body>
  </html>
</q:component>
```

Start the server from the folder that contains `components/`:

```bash
quantum start
```

Open `http://localhost:8080`. `components/about.q` would be served at
`/about`. Stop the server with `quantum stop`.

> No `<!DOCTYPE html>` in the file: a `.q` is XML, and a DOCTYPE is only valid
> before the root element. The server adds it to the response.

## Step 5: Read from a Database

Create a SQLite database with one table (any Python works — Quantum already
needs it):

```bash
python -c "import sqlite3, os; os.makedirs('data', exist_ok=True); c = sqlite3.connect('data/app.db'); c.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)'); c.executemany('INSERT INTO users (name, email) VALUES (?, ?)', [('Ana', 'ana@example.com'), ('Bruno', 'bruno@example.com')]); c.commit()"
```

Declare it in `quantum.config.yaml`, next to `components/`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Create `components/users.q`:

```xml
<q:component name="users" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">
    SELECT id, name, email FROM users ORDER BY name
  </q:query>

  <html><body>
    <h1>{users_result.recordCount} users</h1>
    <table>
      <q:loop query="users">
        <tr><td>{users.name}</td><td>{users.email}</td></tr>
      </q:loop>
    </table>
  </body></html>
</q:component>
```

Restart the server and open `http://localhost:8080/users`.

## Step 6: Handle a Form

Add a form and a `q:action` that inserts a row — the parameter is declared, so
the SQL never sees raw input. Replace `components/users.q` with:

```xml
<q:component name="users" xmlns:q="https://quantum.lang/ns">
  <q:action name="add" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="email" type="email" required="true" />
    <q:query name="inserted" datasource="db">
      INSERT INTO users (name, email) VALUES (:name, :email)
      <q:param name="name" value="{name}" type="string" />
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:redirect url="/users" flash="Added {name}" />
  </q:action>

  <q:query name="users" datasource="db">
    SELECT id, name, email FROM users ORDER BY name
  </q:query>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <table>
      <q:loop query="users">
        <tr><td>{users.name}</td><td>{users.email}</td></tr>
      </q:loop>
    </table>
    <form method="POST" action="/users">
      <input name="name" /> <input name="email" type="email" />
      <button>Add</button>
    </form>
  </body></html>
</q:component>
```

## What's Next?

You've learned the basics! Now explore:

- [Actions & Forms](/guide/actions) - Validation, redirects, several actions
- [Authentication](/guide/authentication) - Login with password checks
- [Components](/guide/components) - Deep dive into the component system
- [State Management](/guide/state-management) - Advanced variable handling
- [AI](/guide/ai) - LLM calls, RAG and agents as tags
- [Database Queries](/guide/query) - SQL and data operations
- [Examples](/examples/) - More real-world examples
