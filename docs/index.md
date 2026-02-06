---
layout: home
hero:
  name: Quantum Framework
  text: Build Web, Desktop & Mobile Apps
  tagline: Full-stack declarative framework using clean XML syntax. Write once, deploy anywhere.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/danielgregorio/quantum

features:
  - icon: "🎯"
    title: Declarative Syntax
    details: Write components using clean XML-based syntax. No JavaScript required for basic applications.
  - icon: "🖥️"
    title: Multi-Target Output
    details: Compile to HTML, Desktop (pywebview), Mobile (React Native), or Terminal (Textual) from a single codebase.
  - icon: "🔗"
    title: Data Binding
    details: Powerful {variable} expressions with automatic updates and computed values.
  - icon: "🗃️"
    title: Built-in Database
    details: SQL queries with q:query, transactions, caching, and query-of-queries support.
  - icon: "🎨"
    title: Rich UI Components
    details: 40+ UI components including cards, modals, charts, tables, and more.
  - icon: "⚡"
    title: Zero Configuration
    details: Start building immediately. Batteries included with sensible defaults.
---

# Welcome to Quantum

Quantum is a **full-stack declarative framework** for building web applications, desktop apps, and mobile apps using a clean XML-based syntax. Inspired by ColdFusion and Adobe Flex, it allows you to create powerful applications without writing JavaScript.

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

### UI Engine
- **40+ Components** - Forms, tables, cards, modals, charts, and more
- **Multi-Target** - HTML, Desktop, Mobile, and Terminal output
- **Design Tokens** - Consistent styling across all targets
- **Animations** - Built-in animation system with triggers

### Backend Features
- **Database Queries** - SQL with parameters, caching, and transactions
- **Authentication** - Session management and role-based access control
- **Data Import** - JSON, CSV, and XML data sources
- **Email** - Send emails with `q:mail`

## Philosophy

> **Simplicity over configuration**

Quantum prioritizes readability and ease of use while maintaining powerful capabilities. If you know XML and SQL, you can build full applications.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/danielgregorio/quantum.git
cd quantum

# Install dependencies
pip install flask

# Run your first component
python src/cli/runner.py run examples/hello.q
```

[Read the full Getting Started guide](/guide/getting-started)
