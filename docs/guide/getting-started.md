# Getting Started

Welcome to Quantum! This guide will help you get up and running with the Quantum framework in just a few minutes.

## What is Quantum?

Quantum is a **full-stack declarative framework** for web applications written in XML. It's designed with the philosophy of "simplicity over configuration" - making complex tasks simple while keeping the language clean and readable.

### Key Benefits

- **No JavaScript Required** - Build interactive apps using only XML and SQL
- **AI as tags** - Model calls, RAG and agents with tools, without Python glue
- **Full-Stack** - Database queries, forms, sessions and authentication built in
- **Validated input** - Declared parameters are type-checked before your code runs

## Prerequisites

- **Python 3.12+**
- **pip**

## Installation

```bash
pip install quantum-framework
quantum --version
```

Optional extras (PostgreSQL/MySQL, RAG, jobs, websockets) and the desktop
target's extra dependency are listed in [Installation](/guide/installation).

## Your First Component

Create a file called `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

Run it:

```bash
quantum run hello.q
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

Pages are components in a `components/` folder, and the file name is the URL.
Create `components/index.q`:

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <html><body>
    <h1>Welcome to My App</h1>
    <p>Now: {dateFormat(now(), '%H:%M')}</p>
  </body></html>
</q:component>
```

Start the server from the folder that contains `components/`:

```bash
quantum start
```

Open `http://localhost:8080`. The [Quick Start](/guide/quick-start) continues
with a database and a form.

::: warning `q:application type="html"`
Older pages describe web apps as a `q:application type="html"` with `q:route`
blocks. That form never ran its routes and was removed in 0.11 — use
`components/` as above. See [q:application](/guide/applications).
:::

## Debug Mode

For detailed execution information:

```bash
quantum run hello.q --debug
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
- [AI](/guide/ai) - LLM calls, RAG and agents as tags
- [Examples](/examples/) - Real-world examples
