# Data Display Components

Components for displaying data in tables, lists, trees, and other structured formats.

## Table

`ui:table` displays tabular data with columns, sorting, and pagination.

### Basic Usage

```xml
<ui:table data="{users}">
  <ui:column field="name" header="Name" />
  <ui:column field="email" header="Email" />
  <ui:column field="role" header="Role" />
</ui:table>
```

### Attributes (ui:table)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | array | required | Array of row objects |
| `striped` | boolean | false | Alternate row colors |
| `bordered` | boolean | false | Add borders |
| `hoverable` | boolean | true | Highlight on hover |
| `compact` | boolean | false | Reduce padding |
| `selectable` | boolean | false | Enable row selection |
| `sortable` | boolean | false | Enable column sorting |
| `pagination` | boolean | false | Enable pagination |
| `pageSize` | number | 10 | Rows per page |

### Attributes (ui:column)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `field` | string | required | Data field name |
| `header` | string | field | Column header text |
| `width` | string | "auto" | Column width |
| `sortable` | boolean | false | Enable sorting |
| `align` | string | "left" | Text alignment |
| `format` | string | none | Format type (date, currency, number) |

### With Sorting

```xml
<ui:table data="{products}" sortable="true">
  <ui:column field="name" header="Product" sortable="true" />
  <ui:column field="price" header="Price" sortable="true" format="currency" />
  <ui:column field="stock" header="Stock" sortable="true" />
</ui:table>
```

### With Pagination

```xml
<ui:table data="{orders}" pagination="true" pageSize="20">
  <ui:column field="id" header="Order ID" />
  <ui:column field="customer" header="Customer" />
  <ui:column field="total" header="Total" format="currency" />
  <ui:column field="status" header="Status" />
</ui:table>
```

### Custom Cell Rendering

```xml
<ui:table data="{users}">
  <ui:column field="name" header="Name" />
  <ui:column field="status" header="Status">
    <ui:template>
      <ui:badge variant="{row.status == 'active' ? 'success' : 'secondary'}">
        {row.status}
      </ui:badge>
    </ui:template>
  </ui:column>
  <ui:column header="Actions">
    <ui:template>
      <ui:hbox gap="sm">
        <ui:button size="xs" on-click="editUser(row.id)">Edit</ui:button>
        <ui:button size="xs" variant="danger" on-click="deleteUser(row.id)">Delete</ui:button>
      </ui:hbox>
    </ui:template>
  </ui:column>
</ui:table>
```

### With Row Selection

```xml
<q:set name="selectedUsers" value='[]' type="array" />

<ui:table data="{users}" selectable="true" bind:selected="selectedUsers">
  <ui:column field="name" header="Name" />
  <ui:column field="email" header="Email" />
</ui:table>

<ui:text>{selectedUsers.length} users selected</ui:text>
<ui:button on-click="deleteSelected" disabled="{selectedUsers.length == 0}">
  Delete Selected
</ui:button>
```

### Expandable Rows

```xml
<ui:table data="{orders}" expandable="true">
  <ui:column field="id" header="Order ID" />
  <ui:column field="customer" header="Customer" />
  <ui:column field="total" header="Total" />

  <ui:expansion>
    <ui:vbox padding="md" gap="sm">
      <ui:text weight="bold">Order Items:</ui:text>
      <q:loop type="array" var="item" items="{row.items}">
        <ui:text>- {item.name} x {item.quantity}</ui:text>
      </q:loop>
    </ui:vbox>
  </ui:expansion>
</ui:table>
```

### Empty State

```xml
<ui:table data="{results}">
  <ui:column field="name" header="Name" />
  <ui:column field="value" header="Value" />

  <ui:empty>
    <ui:vbox align="center" padding="xl">
      <ui:icon name="inbox" size="xl" color="muted" />
      <ui:text color="muted">No results found</ui:text>
    </ui:vbox>
  </ui:empty>
</ui:table>
```

## List

`ui:list` displays items in a list format.

### Basic Usage

```xml
<ui:list>
  <ui:listitem>First item</ui:listitem>
  <ui:listitem>Second item</ui:listitem>
  <ui:listitem>Third item</ui:listitem>
</ui:list>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | "none" | Marker type (none, bullet, number, alpha) |
| `gap` | token | "sm" | Space between items |
| `dividers` | boolean | false | Show dividers between items |

### List Types

```xml
<!-- Bullet list -->
<ui:list type="bullet">
  <ui:listitem>Item one</ui:listitem>
  <ui:listitem>Item two</ui:listitem>
</ui:list>

<!-- Numbered list -->
<ui:list type="number">
  <ui:listitem>First step</ui:listitem>
  <ui:listitem>Second step</ui:listitem>
</ui:list>

<!-- Alphabetic list -->
<ui:list type="alpha">
  <ui:listitem>Option A</ui:listitem>
  <ui:listitem>Option B</ui:listitem>
</ui:list>
```

### Dynamic List

```xml
<q:set name="tasks" value='[
  {"id": 1, "name": "Buy groceries", "done": false},
  {"id": 2, "name": "Walk the dog", "done": true},
  {"id": 3, "name": "Write code", "done": false}
]' />

<ui:list dividers="true">
  <q:loop type="array" var="task" items="{tasks}">
    <ui:listitem>
      <ui:hbox align="center" gap="md">
        <ui:checkbox checked="{task.done}" on-change="toggleTask(task.id)" />
        <ui:text decoration="{task.done ? 'line-through' : 'none'}">
          {task.name}
        </ui:text>
      </ui:hbox>
    </ui:listitem>
  </q:loop>
</ui:list>
```

### List with Avatars

```xml
<ui:list dividers="true">
  <q:loop type="array" var="user" items="{users}">
    <ui:listitem>
      <ui:hbox align="center" gap="md">
        <ui:avatar src="{user.avatar}" name="{user.name}" />
        <ui:vbox gap="none">
          <ui:text weight="bold">{user.name}</ui:text>
          <ui:text color="muted" size="sm">{user.email}</ui:text>
        </ui:vbox>
        <ui:spacer />
        <ui:badge variant="{user.role == 'admin' ? 'primary' : 'secondary'}">
          {user.role}
        </ui:badge>
      </ui:hbox>
    </ui:listitem>
  </q:loop>
</ui:list>
```

## Tree

`ui:tree` displays hierarchical data.

### Basic Usage

```xml
<ui:tree data="{fileSystem}">
  <ui:treetemplate>
    <ui:hbox gap="sm">
      <ui:icon name="{node.type == 'folder' ? 'folder' : 'file'}" />
      <ui:text>{node.name}</ui:text>
    </ui:hbox>
  </ui:treetemplate>
</ui:tree>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | array | required | Tree data structure |
| `childKey` | string | "children" | Key for child nodes |
| `labelKey` | string | "name" | Key for node label |
| `expandedKeys` | array | [] | Initially expanded nodes |
| `selectable` | boolean | false | Enable selection |
| `multiSelect` | boolean | false | Allow multiple selections |
| `checkable` | boolean | false | Show checkboxes |
| `on-select` | string | none | Selection handler |

### Tree Data Structure

```xml
<q:set name="categories" value='[
  {
    "id": 1,
    "name": "Electronics",
    "children": [
      {
        "id": 2,
        "name": "Phones",
        "children": [
          {"id": 3, "name": "iPhone"},
          {"id": 4, "name": "Android"}
        ]
      },
      {"id": 5, "name": "Laptops"}
    ]
  },
  {
    "id": 6,
    "name": "Clothing",
    "children": [
      {"id": 7, "name": "Shirts"},
      {"id": 8, "name": "Pants"}
    ]
  }
]' />

<ui:tree data="{categories}" />
```

### Checkable Tree

```xml
<q:set name="checkedNodes" value='[]' type="array" />

<ui:tree
  data="{permissions}"
  checkable="true"
  bind:checked="checkedNodes"
  on-check="handlePermissionChange"
/>

<ui:text>Selected: {checkedNodes.join(', ')}</ui:text>
```

### Custom Node Template

```xml
<ui:tree data="{fileSystem}">
  <ui:treetemplate>
    <ui:hbox align="center" gap="sm" padding="xs">
      <ui:icon
        name="{node.type == 'folder' ? 'folder' : 'file-text'}"
        color="{node.type == 'folder' ? 'warning' : 'muted'}"
      />
      <ui:text>{node.name}</ui:text>
      <ui:spacer />
      <q:if condition="node.size">
        <ui:text color="muted" size="xs">{formatSize(node.size)}</ui:text>
      </q:if>
    </ui:hbox>
  </ui:treetemplate>
</ui:tree>
```

## Chart

`ui:chart` displays data visualizations. Currently supports bar charts.

### Bar Chart

```xml
<ui:chart type="bar" title="Monthly Sales">
  <ui:data>
    [
      {"label": "Jan", "value": 4500},
      {"label": "Feb", "value": 3200},
      {"label": "Mar", "value": 5100},
      {"label": "Apr", "value": 4800}
    ]
  </ui:data>
</ui:chart>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | "bar" | Chart type (bar, line, pie) |
| `title` | string | none | Chart title |
| `width` | string | "100%" | Chart width |
| `height` | string | "300px" | Chart height |
| `colors` | array | theme colors | Bar/segment colors |
| `showValues` | boolean | true | Show value labels |
| `showLegend` | boolean | false | Show legend |

### Dynamic Chart Data

```xml
<q:fetch name="stats" url="/api/stats">
  <q:success>
    <ui:chart type="bar" title="Revenue by Region">
      <ui:data>{stats.data.regions}</ui:data>
    </ui:chart>
  </q:success>
</q:fetch>
```

### Multiple Data Series

```xml
<ui:chart type="bar" title="Comparison" showLegend="true">
  <ui:series name="2024" color="primary">
    [
      {"label": "Q1", "value": 100},
      {"label": "Q2", "value": 150},
      {"label": "Q3", "value": 120}
    ]
  </ui:series>
  <ui:series name="2025" color="success">
    [
      {"label": "Q1", "value": 130},
      {"label": "Q2", "value": 180},
      {"label": "Q3", "value": 160}
    ]
  </ui:series>
</ui:chart>
```

## Text

`ui:text` displays formatted text content.

### Basic Usage

```xml
<ui:text>Regular text</ui:text>
<ui:text weight="bold">Bold text</ui:text>
<ui:text size="xl">Large text</ui:text>
<ui:text color="primary">Colored text</ui:text>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `size` | string | "md" | Font size token |
| `weight` | string | "normal" | Font weight (normal, bold) |
| `color` | string | "text" | Color token or value |
| `align` | string | "left" | Text alignment |
| `decoration` | string | "none" | Text decoration |
| `truncate` | boolean | false | Truncate with ellipsis |
| `lines` | number | none | Max lines before truncate |

### Text Variants

```xml
<!-- Heading sizes -->
<ui:text size="2xl" weight="bold">Heading 1</ui:text>
<ui:text size="xl" weight="bold">Heading 2</ui:text>
<ui:text size="lg" weight="bold">Heading 3</ui:text>

<!-- Body text -->
<ui:text>Normal paragraph text</ui:text>
<ui:text color="muted">Secondary text</ui:text>
<ui:text size="sm" color="muted">Caption text</ui:text>

<!-- Semantic colors -->
<ui:text color="success">Success message</ui:text>
<ui:text color="danger">Error message</ui:text>
<ui:text color="warning">Warning message</ui:text>
```

### Truncation

```xml
<!-- Single line truncate -->
<ui:text truncate="true" width="200px">
  This is a very long text that will be truncated with an ellipsis
</ui:text>

<!-- Multi-line clamp -->
<ui:text lines="3">
  This paragraph will be clamped to a maximum of three lines.
  Any text beyond that will be hidden and shown with an ellipsis.
</ui:text>
```

## Complete Data Display Example

```xml
<q:application id="dashboard" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:fetch name="users" url="/api/users" />

  <ui:window title="User Management">
    <ui:vbox padding="lg" gap="lg">

      <ui:header>
        <ui:hbox justify="between" align="center">
          <ui:text size="2xl" weight="bold">Users</ui:text>
          <ui:button variant="primary">Add User</ui:button>
        </ui:hbox>
      </ui:header>

      <q:if condition="users.loading">
        <ui:skeleton type="table" rows="5" />
      </q:if>

      <q:if condition="users.error">
        <ui:alert variant="danger">Failed to load users</ui:alert>
      </q:if>

      <q:if condition="!users.loading && !users.error">
        <ui:table
          data="{users.data}"
          sortable="true"
          pagination="true"
          pageSize="10"
          striped="true"
        >
          <ui:column field="id" header="ID" width="60px" />
          <ui:column field="name" header="Name" sortable="true" />
          <ui:column field="email" header="Email" sortable="true" />
          <ui:column field="role" header="Role">
            <ui:template>
              <ui:badge variant="{row.role == 'admin' ? 'primary' : 'secondary'}">
                {row.role}
              </ui:badge>
            </ui:template>
          </ui:column>
          <ui:column field="status" header="Status">
            <ui:template>
              <ui:badge variant="{row.status == 'active' ? 'success' : 'danger'}">
                {row.status}
              </ui:badge>
            </ui:template>
          </ui:column>
          <ui:column field="createdAt" header="Created" format="date" sortable="true" />
          <ui:column header="Actions" width="150px">
            <ui:template>
              <ui:hbox gap="xs">
                <ui:button size="xs" variant="ghost" on-click="editUser(row.id)">
                  Edit
                </ui:button>
                <ui:button size="xs" variant="ghost" color="danger" on-click="deleteUser(row.id)">
                  Delete
                </ui:button>
              </ui:hbox>
            </ui:template>
          </ui:column>

          <ui:empty>
            <ui:vbox align="center" padding="xl">
              <ui:text color="muted">No users found</ui:text>
              <ui:button variant="primary" on-click="addUser">Add First User</ui:button>
            </ui:vbox>
          </ui:empty>
        </ui:table>
      </q:if>

    </ui:vbox>
  </ui:window>

</q:application>
```

## Related Documentation

- [Layout Components](/ui/layout) - Container components
- [Form Components](/ui/forms) - Input components
- [Feedback Components](/ui/feedback) - Loading states
