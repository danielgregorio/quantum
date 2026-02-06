# UI Engine Overview

The Quantum UI Engine is a cross-platform UI framework that allows you to build rich user interfaces using declarative XML syntax. Write once, deploy to HTML, Desktop, Mobile, or Terminal.

## Key Features

- **40+ UI Components** - Forms, tables, cards, modals, charts, and more
- **Multi-Target Rendering** - Single codebase compiles to multiple platforms
- **Design Tokens** - Consistent styling across all targets
- **Reactive State** - Automatic UI updates when state changes
- **Built-in Theming** - Dark/light modes and custom themes
- **Animation System** - Declarative animations with triggers

## Getting Started

### Basic UI Application

```xml
<q:application id="myapp" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <ui:window title="My First App">
    <ui:vbox padding="lg" gap="md">
      <ui:text size="2xl" weight="bold">Welcome to Quantum UI!</ui:text>
      <ui:button variant="primary">Click Me</ui:button>
    </ui:vbox>
  </ui:window>

</q:application>
```

### Build Commands

```bash
# Build for HTML (web browser)
python src/cli/runner.py build myapp.q --target html -o myapp.html

# Build for Desktop (pywebview)
python src/cli/runner.py build myapp.q --target desktop -o myapp.py

# Build for Mobile (React Native)
python src/cli/runner.py build myapp.q --target mobile -o App.js

# Build for Terminal (Textual TUI)
python src/cli/runner.py build myapp.q --target terminal -o app.py
```

## Component Categories

### Layout Components

Control the structure and arrangement of UI elements.

| Component | Description |
|-----------|-------------|
| [`ui:window`](/ui/layout#window) | Root container for UI applications |
| [`ui:hbox`](/ui/layout#hbox) | Horizontal layout container |
| [`ui:vbox`](/ui/layout#vbox) | Vertical layout container |
| [`ui:grid`](/ui/layout#grid) | CSS Grid-based layout |
| [`ui:panel`](/ui/layout#panel) | Bordered container with optional title |
| [`ui:tabs`](/ui/layout#tabs) | Tabbed navigation container |
| [`ui:accordion`](/ui/layout#accordion) | Collapsible sections |

### Form Components

User input and form controls.

| Component | Description |
|-----------|-------------|
| [`ui:form`](/ui/forms#form) | Form container with validation |
| [`ui:formitem`](/ui/forms#formitem) | Label and input wrapper |
| [`ui:input`](/ui/forms#input) | Text input field |
| [`ui:button`](/ui/forms#button) | Clickable button |
| [`ui:checkbox`](/ui/forms#checkbox) | Checkbox input |
| [`ui:switch`](/ui/forms#switch) | Toggle switch |
| [`ui:select`](/ui/forms#select) | Dropdown select |
| [`ui:radio`](/ui/forms#radio) | Radio button group |

### Data Display Components

Display and visualize data.

| Component | Description |
|-----------|-------------|
| [`ui:table`](/ui/data-display#table) | Data table with columns |
| [`ui:list`](/ui/data-display#list) | Ordered/unordered lists |
| [`ui:tree`](/ui/data-display#tree) | Hierarchical tree view |
| [`ui:chart`](/ui/data-display#chart) | Data visualization charts |

### Feedback Components

User feedback and notifications.

| Component | Description |
|-----------|-------------|
| [`ui:alert`](/ui/feedback#alert) | Alert messages |
| [`ui:loading`](/ui/feedback#loading) | Loading spinners |
| [`ui:progress`](/ui/feedback#progress) | Progress bars |
| [`ui:badge`](/ui/feedback#badge) | Status badges |
| [`ui:skeleton`](/ui/feedback#skeleton) | Loading placeholders |

### Navigation Components

Navigation and wayfinding.

| Component | Description |
|-----------|-------------|
| [`ui:tabs`](/ui/navigation#tabs) | Tab navigation |
| [`ui:breadcrumb`](/ui/navigation#breadcrumb) | Breadcrumb trail |
| [`ui:pagination`](/ui/navigation#pagination) | Page navigation |
| [`ui:menu`](/ui/navigation#menu) | Navigation menu |

### Overlay Components

Modals, tooltips, and dropdowns.

| Component | Description |
|-----------|-------------|
| [`ui:modal`](/ui/overlays#modal) | Modal dialogs |
| [`ui:tooltip`](/ui/overlays#tooltip) | Hover tooltips |
| [`ui:dropdown`](/ui/overlays#dropdown) | Dropdown menus |

### Advanced Components

Rich UI components for complex use cases.

| Component | Description |
|-----------|-------------|
| [`ui:card`](/ui/advanced-components#card) | Card containers |
| [`ui:avatar`](/ui/advanced-components#avatar) | User avatars |
| [`ui:chart`](/ui/advanced-components#chart) | Data charts |

## Design Tokens

Design tokens ensure consistent styling across all targets. Tokens are normalized values that translate to platform-specific implementations.

### Spacing Tokens

| Token | HTML Value | Terminal Value |
|-------|------------|----------------|
| `xs` | 4px | 1 char |
| `sm` | 8px | 1 char |
| `md` | 16px | 2 chars |
| `lg` | 24px | 3 chars |
| `xl` | 32px | 4 chars |

```xml
<ui:vbox padding="lg" gap="md">
  <!-- Content with large padding and medium gap -->
</ui:vbox>
```

### Size Tokens

| Token | Description |
|-------|-------------|
| `auto` | Automatic sizing |
| `fill` | Fill available space |
| `1/2` | 50% width |
| `1/3` | 33.3% width |
| `1/4` | 25% width |
| `2/3` | 66.6% width |
| `3/4` | 75% width |

```xml
<ui:hbox>
  <ui:panel width="1/3">Sidebar</ui:panel>
  <ui:panel width="2/3">Main Content</ui:panel>
</ui:hbox>
```

### Color Tokens

| Token | Description |
|-------|-------------|
| `primary` | Primary brand color |
| `secondary` | Secondary color |
| `success` | Success/positive state |
| `danger` | Error/negative state |
| `warning` | Warning state |
| `info` | Informational state |
| `light` | Light background |
| `dark` | Dark background |

```xml
<ui:button variant="primary">Submit</ui:button>
<ui:alert variant="success">Operation completed!</ui:alert>
<ui:badge variant="danger">Error</ui:badge>
```

### Typography Tokens

| Token | Description |
|-------|-------------|
| `xs` | Extra small (12px) |
| `sm` | Small (14px) |
| `md` | Medium (16px) |
| `lg` | Large (20px) |
| `xl` | Extra large (24px) |
| `2xl` | 2x large (32px) |

```xml
<ui:text size="2xl" weight="bold">Large Heading</ui:text>
<ui:text size="sm" color="muted">Small helper text</ui:text>
```

## Reactive State Binding

Bind UI components to state variables for automatic updates:

```xml
<q:application id="counter" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="count" value="0" type="number" />

  <q:function name="increment">
    <q:set name="count" value="{count + 1}" />
  </q:function>

  <q:function name="decrement">
    <q:set name="count" value="{count - 1}" />
  </q:function>

  <ui:window title="Counter">
    <ui:vbox padding="lg" gap="md" align="center">
      <ui:text size="2xl">{count}</ui:text>
      <ui:hbox gap="sm">
        <ui:button on-click="decrement">-</ui:button>
        <ui:button on-click="increment">+</ui:button>
      </ui:hbox>
    </ui:vbox>
  </ui:window>

</q:application>
```

## Event Handling

### Click Events

```xml
<ui:button on-click="handleClick">Click Me</ui:button>

<q:function name="handleClick">
  <q:set name="message" value="Button clicked!" />
</q:function>
```

### Form Events

```xml
<ui:form on-submit="handleSubmit">
  <ui:formitem label="Name">
    <ui:input bind="userName" />
  </ui:formitem>
  <ui:button type="submit">Submit</ui:button>
</ui:form>
```

### Change Events

```xml
<ui:input bind="searchQuery" on-change="handleSearch" />
<ui:select bind="selectedOption" on-change="handleSelection" />
```

## Targets

### HTML Target

Generates standalone HTML with CSS and JavaScript. Suitable for web applications.

```bash
python src/cli/runner.py build app.q --target html
```

### Desktop Target

Generates a Python pywebview application for native desktop apps.

```bash
python src/cli/runner.py build app.q --target desktop
python output.py  # Run the desktop app
```

### Mobile Target

Generates React Native code for iOS and Android apps.

```bash
python src/cli/runner.py build app.q --target mobile
cd output && npm install && npx react-native run-ios
```

### Terminal Target

Generates a Textual TUI application for terminal interfaces.

```bash
python src/cli/runner.py build app.q --target terminal
python output.py  # Run in terminal
```

## Complete Example

```xml
<q:application id="taskmanager" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="tasks" value='[]' type="array" />
  <q:set name="newTaskName" value="" />
  <q:set name="filter" value="all" />

  <q:function name="addTask">
    <q:if condition="newTaskName != ''">
      <q:set name="tasks" operation="append" value='{
        "id": "{Date.now()}",
        "name": "{newTaskName}",
        "completed": false
      }' />
      <q:set name="newTaskName" value="" />
    </q:if>
  </q:function>

  <q:function name="toggleTask">
    <q:param name="taskId" type="string" />
    <!-- Toggle task completion -->
  </q:function>

  <ui:window title="Task Manager">
    <ui:vbox padding="lg" gap="md">

      <ui:header>
        <ui:text size="2xl" weight="bold">My Tasks</ui:text>
      </ui:header>

      <ui:form on-submit="addTask">
        <ui:hbox gap="sm">
          <ui:input
            bind="newTaskName"
            placeholder="Enter a new task..."
            width="fill"
          />
          <ui:button type="submit" variant="primary">Add</ui:button>
        </ui:hbox>
      </ui:form>

      <ui:tabs>
        <ui:tab label="All" active="{filter == 'all'}" on-click="setFilter('all')">
          <q:loop type="array" var="task" items="{tasks}">
            <ui:hbox gap="sm" padding="sm">
              <ui:checkbox
                checked="{task.completed}"
                on-change="toggleTask(task.id)"
              />
              <ui:text>{task.name}</ui:text>
            </ui:hbox>
          </q:loop>
        </ui:tab>
        <ui:tab label="Active">
          <!-- Active tasks -->
        </ui:tab>
        <ui:tab label="Completed">
          <!-- Completed tasks -->
        </ui:tab>
      </ui:tabs>

      <ui:footer>
        <ui:text color="muted">{tasks.length} tasks total</ui:text>
      </ui:footer>

    </ui:vbox>
  </ui:window>

</q:application>
```

## Next Steps

- [Layout Components](/ui/layout) - Structure your UI
- [Form Components](/ui/forms) - User input handling
- [Data Display](/ui/data-display) - Tables, lists, and trees
- [Theming](/features/theming) - Customize appearance
- [Animations](/features/animations) - Add motion
