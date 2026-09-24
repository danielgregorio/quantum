---
layout: home
hero:
  name: Quantum
  text: Web applications from declarative pages
  tagline: Database, forms, sessions and AI in the language. No build chain, no JavaScript, no front-end framework.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: Why Quantum
      link: /guide/why-quantum
    - theme: alt
      text: View on GitHub
      link: https://github.com/danielgregorio/quantum

features:
  - icon: "🎯"
    title: One page, top to bottom
    details: Guards, actions, queries and the screen in the order they run. No JavaScript to write.
  - icon: "🖥️"
    title: Browser, terminal, desktop
    details: The same page runs in a browser (quantum start), a terminal (quantum console) and a desktop window (quantum desktop).
  - icon: "🧾"
    title: Forms that know their rules
    details: A form takes required, lengths, types and choices from its action's q:param — checked in the browser and on the server.
  - icon: "🗃️"
    title: SQL you can trust
    details: Parameterized queries, a declarative schema plan, change history and quantum check against your database.
  - icon: "🤖"
    title: AI in the language
    details: q:llm answers from your documents with sources and streams; q:agent calls tools you write in Quantum.
  - icon: "✅"
    title: Specified and tested
    details: Every rule of the SPEC has a test; the example apps run end to end in CI.
---

# Welcome to Quantum

Quantum builds **web applications from declarative XML pages** — the same page also runs in a terminal and in a desktop window. Inspired by ColdFusion and Adobe Flex, it lets you build internal tools, dashboards and AI applications without writing JavaScript. [Why Quantum?](/guide/why-quantum)

## Quick Example

```xml
<q:component name="UserList" xmlns:q="https://quantum.lang/ns">
  <!-- Query the database -->
  <q:query name="users" datasource="mydb">
    SELECT id, name, email FROM users WHERE active = 1
  </q:query>

  <!-- Display results -->
  <q:loop query="users">
    <q:return value="User: {users.name} ({users.email})" />
  </q:loop>
</q:component>
```

## Key Features

### Core Language
- **Components** - Reusable .q files with parameters and return values
- **State Management** - `q:set` for variables with validation and type checking
- **Loops** - Range, array, list, and query iterations with `q:loop`
- **Conditionals** - Full `q:if`/`q:elseif`/`q:else` support
- **Functions** - Define reusable logic with `q:function`

### Screens (`ui:*`)
- **A core set** - windows, boxes, panels, tables, lists, forms and fields ([UI](/guide/ui))
- **Three renderers** - browser, terminal and desktop window, from the same page
- **Forms from actions** - fields, rules and errors come from the action's `q:param`
- **Tables from queries** - pagination, search as you type, sortable and editable cells

### Backend Features
- **Database Queries** - SQL with parameters, schema plans, change history, `quantum check`
- **Authentication** - Session management and role-based access control
- **Data Import** - JSON, CSV, and XML data sources
- **Files and Mail** - Uploads, protected downloads and `q:mail` ([guide](/guide/files-and-mail))
- **AI** - `q:llm` with sources and streaming, `q:knowledge`, `q:agent` ([guide](/guide/ai))

## Philosophy

> **Simplicity over configuration**

Quantum prioritizes readability and ease of use while maintaining powerful capabilities. If you know XML and SQL, you can build full applications.

## Getting Started

```bash
pip install quantum-framework
quantum start          # in an application folder; the guide builds one step by step
```

[Read the full Getting Started guide](/guide/getting-started)
