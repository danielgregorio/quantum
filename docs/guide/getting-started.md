# Getting Started

Welcome to Quantum! This guide will help you get up and running with the Quantum framework in just a few minutes.

## What is Quantum?

Quantum is a **full-stack declarative framework** that uses XML syntax to create web applications, desktop apps, and mobile apps. It's designed with the philosophy of "simplicity over configuration" - making complex tasks simple while keeping the language clean and readable.

### Key Benefits

- **No JavaScript Required** - Build interactive apps using only XML and SQL
- **Multi-Target** - Write once, deploy to HTML, Desktop, Mobile, or Terminal
- **Full-Stack** - Database queries, authentication, email, and more built-in
- **Type Safe** - Optional type checking and validation

## Prerequisites

- **Python 3.8+** - Required for the runtime
- **pip** - Python package manager
- **Git** - For cloning the repository

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install flask

# Optional: For desktop apps
pip install pywebview

# Optional: For terminal apps
pip install textual

# Optional: For database support
pip install sqlalchemy
```

### 3. Verify Installation

```bash
python src/cli/runner.py run examples/hello.q
```

You should see:

```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

## Your First Component

Create a file called `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

Run it:

```bash
python src/cli/runner.py run hello.q
```

## Adding Dynamic Content

Let's make it more interesting with variables and loops:

```xml
<q:component name="Greetings" xmlns:q="https://quantum.lang/ns">
  <!-- Define a variable -->
  <q:set name="greeting" value="Hello" />

  <!-- Loop through a list -->
  <q:loop type="list" var="name" items="Alice,Bob,Charlie">
    <q:return value="{greeting} {name}!" />
  </q:loop>
</q:component>
```

**Output:**
```
["Hello Alice!", "Hello Bob!", "Hello Charlie!"]
```

## Using Conditionals

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="25" />

  <q:if condition="age >= 18">
    <q:return value="You are an adult" />
  </q:if>
  <q:else>
    <q:return value="You are a minor" />
  </q:else>
</q:component>
```

## Creating Functions

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:return value="5 + 3 = {sum}" />
</q:component>
```

## Web Applications

Create a web server with routes:

```xml
<q:application id="myapp" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <h1>Welcome to My App</h1>
    <p>Current time: {now()}</p>
  </q:route>

  <q:route path="/users" method="GET">
    <q:query name="users" datasource="mydb">
      SELECT name, email FROM users
    </q:query>
    <ul>
      <q:loop query="users">
        <li>{users.name} - {users.email}</li>
      </q:loop>
    </ul>
  </q:route>
</q:application>
```

Start the server:

```bash
python src/cli/runner.py start myapp.q
```

## UI Applications

Build cross-platform UI with the UI engine:

```xml
<q:application id="myui" type="ui" xmlns:q="https://quantum.lang/ns">
  <ui:window title="My App">
    <ui:vbox padding="md" gap="sm">
      <ui:text size="xl" weight="bold">Welcome!</ui:text>

      <ui:form on-submit="handleSubmit">
        <ui:formitem label="Name">
          <ui:input bind="userName" placeholder="Enter your name" />
        </ui:formitem>
        <ui:button variant="primary">Submit</ui:button>
      </ui:form>

      <ui:text>Hello, {userName}!</ui:text>
    </ui:vbox>
  </ui:window>
</q:application>
```

Build for different targets:

```bash
# HTML output
python src/cli/runner.py build myui.q --target html

# Desktop app
python src/cli/runner.py build myui.q --target desktop

# Terminal app
python src/cli/runner.py build myui.q --target textual
```

## Debug Mode

For detailed execution information:

```bash
python src/cli/runner.py run examples/hello.q --debug
```

This shows:
- File parsing details
- AST generation info
- Validation steps
- Execution flow

## Next Steps

- [Installation Details](/guide/installation) - Complete setup guide
- [Project Structure](/guide/project-structure) - How to organize your code
- [Components](/guide/components) - Deep dive into components
- [UI Engine](/ui-engine/overview) - Build cross-platform UIs
- [Examples](/examples/) - Real-world examples
