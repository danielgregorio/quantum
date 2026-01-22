# 🚀 Quantum Framework - Quick Start Guide

## What is Quantum?

Quantum is a declarative XML-based framework for building web applications with server-side rendering, inspired by ColdFusion but modernized for 2025.

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd quantum

# Install dependencies
pip install -r requirements.txt
```

## Your First Component

Create a file `components/hello.q`:

```xml
<q:component name="Hello">
  <q:set name="message" value="Hello Quantum!" />

  <h1>{message}</h1>
  <p>Welcome to the future of web development!</p>

  <style>
    h1 { color: #667eea; }
  </style>
</q:component>
```

## Starting the Server

```bash
# Option 1: Using the CLI
python quantum_cli.py dev --port 8000

# Option 2: Using quantum.py
python quantum.py

# Option 3: Direct server start
python -m src.web.quantum_server --dir components --port 8000
```

Visit: http://localhost:8000/hello

## Core Features

### 1. Variables with `q:set`

```xml
<q:set name="username" value="Alice" />
<q:set name="age" value="25" />
<q:set name="score" value="100" />

<p>Hello {username}, you are {age} years old!</p>
<p>Your score: {score}</p>
```

### 2. Conditional Rendering with `q:if`

```xml
<q:set name="isLoggedIn" value="true" />

<q:if condition="{isLoggedIn}">
  <p>Welcome back!</p>
</q:if>

<q:if condition="{!isLoggedIn}">
  <p>Please log in</p>
</q:if>
```

### 3. Loops with `q:loop`

**Range Loop:**
```xml
<q:set name="count" value="5" />

<ul>
  <q:loop type="range" var="i" from="1" to="{count}">
    <li>Item {i}</li>
  </q:loop>
</ul>
```

**Array Loop** (coming soon):
```xml
<q:loop type="array" var="item" array="{items}">
  <div>{item.name}: ${item.price}</div>
</q:loop>
```

### 4. Functions with `q:function`

**Define a function:**
```xml
<q:function name="greet">
  <q:param name="name" type="string" required="true" />
  <q:param name="greeting" type="string" default="Hello" />

  <q:return value="{greeting}, {name}!" />
</q:function>
```

**Call the function:**
```xml
<q:call function="greet" name="Alice" result="message" />
<p>{message}</p>
```

### 5. Functions with Caching

```xml
<q:function name="fetchData" cache="true" cache_ttl="3600">
  <q:param name="userId" type="number" required="true" />

  <!-- Expensive operation - will be cached for 1 hour -->
  <q:query name="user" datasource="db">
    SELECT * FROM users WHERE id = {userId}
  </q:query>

  <q:return value="{user}" />
</q:function>
```

### 6. REST API Auto-Generation

```xml
<q:function name="getUser"
            rest="/api/users/{id}"
            method="GET"
            return="object">
  <q:param name="id" type="number" required="true" />

  <q:query name="user" datasource="db">
    SELECT id, name, email FROM users WHERE id = {id}
  </q:query>

  <q:return value="{user.records[0]}" />
</q:function>
```

This automatically creates a REST endpoint at `GET /api/users/:id`!

### 7. Event System

**Dispatch events:**
```xml
<q:dispatch event="orderCreated" data="{order}" />
```

**Handle events:**
```xml
<q:on event="orderCreated" function="sendConfirmation" />

<q:function name="sendConfirmation">
  <q:param name="eventData" type="object" />
  <q:log message="Order {eventData.id} created!" />
</q:function>
```

## Databinding Expressions

Quantum supports powerful databinding expressions:

```xml
<!-- Simple variables -->
<p>{name}</p>

<!-- Math operations -->
<p>Total: {price * quantity}</p>

<!-- Comparisons -->
<q:if condition="{age >= 18}">
  <p>Adult</p>
</q:if>

<!-- Object properties (coming soon) -->
<p>{user.name}</p>

<!-- Array access (coming soon) -->
<p>{items[0]}</p>
```

## Complete Example: TODO App

See `components/todo_app.q` for a complete example that demonstrates:
- State management with `q:set`
- List rendering with `q:loop`
- Conditional rendering with `q:if`
- Functions with `q:function`
- Function calls with `q:call`
- Databinding expressions

## Project Structure

```
quantum/
├── components/          # Your .q component files
│   ├── index.q         # Default homepage
│   ├── hello.q         # Example component
│   └── todo_app.q      # TODO app example
├── src/
│   ├── core/           # Parser & AST
│   ├── runtime/        # Renderer & databinding
│   └── web/            # Web server
├── tests/              # Unit tests
├── quantum.py          # CLI entry point
├── quantum_cli.py      # Advanced CLI
└── QUICKSTART.md       # This file!
```

## CLI Commands

```bash
# Start development server
python quantum_cli.py dev --port 8000

# Create a new component
python quantum_cli.py create component MyComponent

# Create a component with template
python quantum_cli.py create component ContactForm --template form

# Initialize a new project
python quantum_cli.py init

# Inspect a component
python quantum_cli.py inspect todo_app

# Build for production
python quantum_cli.py build --production
```

## What's Working Now

✅ **Parser** - Converts .q files to AST
✅ **Renderer** - Renders AST to HTML
✅ **Databinding** - Resolves {variable} expressions
✅ **q:set** - Variable assignment
✅ **q:if/q:else** - Conditional rendering
✅ **q:loop** - Range loops
✅ **q:function** - Function definitions with parameters
✅ **q:call** - Function invocation
✅ **Caching** - Function result caching with TTL
✅ **REST API** - Auto-generation from functions
✅ **Event System** - q:on / q:dispatch
✅ **Web Server** - Flask-based component server
✅ **CLI Tool** - Development server and utilities

## What's Coming Next

🔄 **Array Loops** - Loop over arrays/lists
🔄 **Database Integration** - Real q:query support
🔄 **Form Handling** - q:action with POST support
🔄 **Session Management** - User sessions
🔄 **File Uploads** - q:upload support
🔄 **Email Sending** - q:email integration
🔄 **Hot Module Reload** - Auto-refresh on changes
🔄 **Production Build** - Optimized output

## Examples

### 1. Hello World

```xml
<q:component name="HelloWorld">
  <h1>Hello Quantum!</h1>
</q:component>
```

### 2. Counter with State

```xml
<q:component name="Counter">
  <q:set name="count" value="0" />

  <h2>Count: {count}</h2>

  <q:set name="count" operation="add" value="1" />
  <p>After increment: {count}</p>
</q:component>
```

### 3. User Profile

```xml
<q:component name="UserProfile">
  <q:set name="name" value="Alice" />
  <q:set name="age" value="25" />
  <q:set name="isAdmin" value="true" />

  <div class="profile">
    <h1>{name}</h1>
    <p>Age: {age}</p>

    <q:if condition="{isAdmin}">
      <span class="badge">Admin</span>
    </q:if>
  </div>
</q:component>
```

### 4. Shopping Cart Total

```xml
<q:component name="Cart">
  <q:function name="calculateTotal">
    <q:param name="price" type="number" required="true" />
    <q:param name="quantity" type="number" default="1" />
    <q:param name="tax" type="number" default="0.1" />

    <q:set name="subtotal" value="{price * quantity}" />
    <q:set name="taxAmount" value="{subtotal * tax}" />
    <q:set name="total" value="{subtotal + taxAmount}" />

    <q:return value="{total}" />
  </q:function>

  <h2>Shopping Cart</h2>

  <q:call function="calculateTotal"
          price="99.99"
          quantity="2"
          result="cartTotal" />

  <p class="total">Total: ${cartTotal}</p>
</q:component>
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/test_parser.py -v
```

## Getting Help

- 📖 **Documentation**: See `/docs` folder
- 💡 **Examples**: Check `components/` and `examples/` directories
- 🐛 **Issues**: Report bugs on GitHub
- 💬 **Community**: Join our Discord

## Next Steps

1. **Explore Examples**: Check out `components/todo_app.q` and `components/complete_demo.q`
2. **Build Something**: Create your own component
3. **Read the Docs**: Deep dive into advanced features
4. **Contribute**: Help us build the future of web development!

---

**Made with ❤️ by the Quantum Team**

*Quantum - Declarative web development, simplified.*
