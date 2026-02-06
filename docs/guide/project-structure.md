# Project Structure

Understanding how to organize your Quantum projects.

## Basic Structure

A typical Quantum project looks like this:

```
my-project/
├── quantum.yaml          # Configuration file
├── src/
│   ├── components/       # Reusable .q components
│   │   ├── user-card.q
│   │   └── nav-menu.q
│   ├── pages/            # Page components
│   │   ├── home.q
│   │   └── about.q
│   └── app.q             # Main application
├── data/
│   └── app.db            # SQLite database
├── static/
│   ├── css/
│   └── images/
└── dist/                 # Build output
```

## File Types

### Component Files (.q)

Components are self-contained units of functionality:

```xml
<!-- src/components/greeting.q -->
<q:component name="Greeting" xmlns:q="https://quantum.lang/ns">
  <q:param name="name" type="string" default="World" />
  <q:return value="Hello, {name}!" />
</q:component>
```

### Application Files (.q)

Applications define web servers or UI apps:

```xml
<!-- src/app.q -->
<q:application id="myapp" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <h1>Welcome</h1>
  </q:route>
</q:application>
```

### Configuration (quantum.yaml)

```yaml
# quantum.yaml
app:
  name: My Quantum App
  version: 1.0.0

server:
  host: 0.0.0.0
  port: 5000
  debug: false

datasources:
  default:
    driver: sqlite
    database: ./data/app.db

  postgres:
    driver: postgresql
    host: ${DB_HOST}
    port: 5432
    database: ${DB_NAME}
    username: ${DB_USER}
    password: ${DB_PASS}

paths:
  components: ./src/components
  static: ./static
  output: ./dist
```

## Component Organization

### By Feature

Organize components by feature or domain:

```
src/
├── auth/
│   ├── login-form.q
│   ├── register-form.q
│   └── auth-guard.q
├── users/
│   ├── user-list.q
│   ├── user-card.q
│   └── user-profile.q
└── products/
    ├── product-grid.q
    ├── product-card.q
    └── cart.q
```

### By Type

Organize by component type:

```
src/
├── layouts/
│   ├── main-layout.q
│   └── sidebar-layout.q
├── forms/
│   ├── contact-form.q
│   └── search-form.q
├── widgets/
│   ├── stat-card.q
│   └── chart-widget.q
└── pages/
    ├── home.q
    └── dashboard.q
```

## Importing Components

### Basic Import

```xml
<q:component name="Dashboard" xmlns:q="https://quantum.lang/ns">
  <!-- Import a component -->
  <q:import component="UserCard" from="./components/user-card.q" />

  <!-- Use the imported component -->
  <UserCard name="John" email="john@example.com" />
</q:component>
```

### Multiple Imports

```xml
<q:component name="App" xmlns:q="https://quantum.lang/ns">
  <q:import component="Header" from="./layouts/header.q" />
  <q:import component="Sidebar" from="./layouts/sidebar.q" />
  <q:import component="Footer" from="./layouts/footer.q" />

  <Header title="My App" />
  <Sidebar />
  <Footer copyright="2024" />
</q:component>
```

## Feature Modules

For advanced features, Quantum uses the feature module system:

```
src/core/features/{feature_name}/
├── manifest.yaml          # Feature metadata
├── src/
│   ├── __init__.py
│   └── ast_node.py        # AST node class
├── intentions/
│   └── primary.intent     # Semantic specification
└── dataset/
    ├── metadata.json
    ├── positive/          # Valid examples
    └── negative/          # Invalid examples
```

### Feature Manifest

```yaml
# manifest.yaml
name: my_feature
version: 1.0.0
description: My custom feature

dependencies:
  - state_management
  - conditionals

tags:
  - my:feature

provides:
  ast_node: MyFeatureNode
  runtime_method: _execute_my_feature
```

## Build Output

### HTML Target

```
dist/
├── index.html
├── styles.css
└── app.js
```

### Desktop Target

```
dist/
├── app.py              # Main pywebview app
└── requirements.txt
```

### Mobile Target

```
dist/
├── App.js              # React Native entry
├── package.json
└── app.json
```

### Terminal Target

```
dist/
├── app.py              # Textual TUI app
└── requirements.txt
```

## Best Practices

### 1. Keep Components Small

Each component should do one thing well:

```xml
<!-- Good: Focused component -->
<q:component name="UserAvatar" xmlns:q="https://quantum.lang/ns">
  <q:param name="src" type="string" required="true" />
  <q:param name="size" type="string" default="md" />
  <!-- Just renders an avatar -->
</q:component>
```

### 2. Use Clear Naming

- **Components**: PascalCase (`UserCard`, `NavMenu`)
- **Variables**: camelCase (`userName`, `isActive`)
- **Files**: kebab-case (`user-card.q`, `nav-menu.q`)

### 3. Organize by Domain

Group related components together:

```
src/
├── auth/           # Authentication related
├── dashboard/      # Dashboard features
├── settings/       # Settings pages
└── shared/         # Shared utilities
```

### 4. Separate Concerns

- **Components** - Reusable UI pieces
- **Pages** - Full page layouts
- **Layouts** - Page structure templates
- **Services** - Data fetching logic

### 5. Document Your Components

```xml
<!--
  UserCard Component

  Displays a user's information in a card format.

  @param name - User's display name (required)
  @param email - User's email address
  @param avatar - URL to avatar image

  @example
  <UserCard name="John" email="john@example.com" />
-->
<q:component name="UserCard" xmlns:q="https://quantum.lang/ns">
  ...
</q:component>
```

## Next Steps

- [Components](/guide/components) - Deep dive into components
- [State Management](/guide/state-management) - Managing application state
- [UI Engine](/ui-engine/overview) - Building user interfaces
