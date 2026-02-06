# Navigation Components

Components for navigating through applications, including tabs, breadcrumbs, pagination, and menus.

## Tabs

`ui:tabs` provides tabbed navigation between different views.

### Basic Usage

```xml
<ui:tabs>
  <ui:tab label="Overview">
    <ui:text>Overview content here</ui:text>
  </ui:tab>
  <ui:tab label="Details">
    <ui:text>Details content here</ui:text>
  </ui:tab>
  <ui:tab label="Settings">
    <ui:text>Settings content here</ui:text>
  </ui:tab>
</ui:tabs>
```

### Attributes (ui:tabs)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "default" | Style (default, pills, underline) |
| `position` | string | "top" | Tab position (top, bottom, left, right) |
| `bind` | string | none | Bind active tab to variable |
| `on-change` | string | none | Tab change handler |

### Attributes (ui:tab)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `label` | string | required | Tab label |
| `id` | string | auto | Tab identifier |
| `icon` | string | none | Icon name |
| `disabled` | boolean | false | Disable tab |
| `badge` | string | none | Badge content |

### Tab Variants

```xml
<!-- Default style -->
<ui:tabs variant="default">
  <ui:tab label="Tab 1">Content 1</ui:tab>
  <ui:tab label="Tab 2">Content 2</ui:tab>
</ui:tabs>

<!-- Pills style -->
<ui:tabs variant="pills">
  <ui:tab label="Tab 1">Content 1</ui:tab>
  <ui:tab label="Tab 2">Content 2</ui:tab>
</ui:tabs>

<!-- Underline style -->
<ui:tabs variant="underline">
  <ui:tab label="Tab 1">Content 1</ui:tab>
  <ui:tab label="Tab 2">Content 2</ui:tab>
</ui:tabs>
```

### Tabs with Icons

```xml
<ui:tabs>
  <ui:tab label="Home" icon="home">
    Home content
  </ui:tab>
  <ui:tab label="Profile" icon="user">
    Profile content
  </ui:tab>
  <ui:tab label="Settings" icon="settings">
    Settings content
  </ui:tab>
</ui:tabs>
```

### Tabs with Badges

```xml
<ui:tabs>
  <ui:tab label="Inbox" badge="5">
    Inbox content
  </ui:tab>
  <ui:tab label="Sent">
    Sent content
  </ui:tab>
  <ui:tab label="Drafts" badge="2">
    Drafts content
  </ui:tab>
</ui:tabs>
```

### Controlled Tabs

```xml
<q:set name="activeTab" value="overview" />

<ui:tabs bind="activeTab">
  <ui:tab id="overview" label="Overview">
    Overview content
  </ui:tab>
  <ui:tab id="analytics" label="Analytics">
    Analytics content
  </ui:tab>
  <ui:tab id="reports" label="Reports">
    Reports content
  </ui:tab>
</ui:tabs>

<ui:text>Current tab: {activeTab}</ui:text>
```

### Vertical Tabs

```xml
<ui:tabs position="left">
  <ui:tab label="General">General settings</ui:tab>
  <ui:tab label="Security">Security settings</ui:tab>
  <ui:tab label="Notifications">Notification settings</ui:tab>
</ui:tabs>
```

## Breadcrumb

`ui:breadcrumb` displays navigation path hierarchy.

### Basic Usage

```xml
<ui:breadcrumb>
  <ui:crumb href="/">Home</ui:crumb>
  <ui:crumb href="/products">Products</ui:crumb>
  <ui:crumb>Electronics</ui:crumb>
</ui:breadcrumb>
```

### Attributes (ui:breadcrumb)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `separator` | string | "/" | Separator character |

### Attributes (ui:crumb)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `href` | string | none | Link URL (omit for current page) |
| `icon` | string | none | Icon name |

### Custom Separator

```xml
<ui:breadcrumb separator=">">
  <ui:crumb href="/">Home</ui:crumb>
  <ui:crumb href="/docs">Documentation</ui:crumb>
  <ui:crumb>Getting Started</ui:crumb>
</ui:breadcrumb>
```

### With Icons

```xml
<ui:breadcrumb>
  <ui:crumb href="/" icon="home" />
  <ui:crumb href="/settings" icon="settings">Settings</ui:crumb>
  <ui:crumb>Profile</ui:crumb>
</ui:breadcrumb>
```

### Dynamic Breadcrumbs

```xml
<q:set name="breadcrumbs" value='[
  {"label": "Home", "href": "/"},
  {"label": "Category", "href": "/category/electronics"},
  {"label": "Product", "href": null}
]' />

<ui:breadcrumb>
  <q:loop type="array" var="crumb" items="{breadcrumbs}">
    <q:if condition="crumb.href">
      <ui:crumb href="{crumb.href}">{crumb.label}</ui:crumb>
    </q:if>
    <q:else>
      <ui:crumb>{crumb.label}</ui:crumb>
    </q:else>
  </q:loop>
</ui:breadcrumb>
```

## Pagination

`ui:pagination` provides page navigation for paginated content.

### Basic Usage

```xml
<ui:pagination
  current="{currentPage}"
  total="{totalPages}"
  on-change="handlePageChange"
/>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `current` | number | 1 | Current page number |
| `total` | number | required | Total number of pages |
| `on-change` | string | none | Page change handler |
| `showTotal` | boolean | true | Show total count |
| `pageSize` | number | 10 | Items per page |
| `totalItems` | number | none | Total item count |
| `siblings` | number | 1 | Visible page siblings |
| `showFirst` | boolean | true | Show first page button |
| `showLast` | boolean | true | Show last page button |

### With Item Count

```xml
<ui:pagination
  current="{page}"
  total="{totalPages}"
  totalItems="{totalRecords}"
  pageSize="20"
  on-change="loadPage"
/>
<!-- Displays: "Showing 1-20 of 150" -->
```

### Simple Pagination

```xml
<ui:pagination
  current="{page}"
  total="{totalPages}"
  showFirst="false"
  showLast="false"
  showTotal="false"
/>
```

### With Page Size Selector

```xml
<ui:hbox align="center" gap="lg">
  <ui:pagination
    current="{page}"
    total="{totalPages}"
    on-change="loadPage"
  />

  <ui:hbox align="center" gap="sm">
    <ui:text size="sm">Items per page:</ui:text>
    <ui:select bind="pageSize" on-change="updatePageSize">
      <ui:option value="10">10</ui:option>
      <ui:option value="20">20</ui:option>
      <ui:option value="50">50</ui:option>
      <ui:option value="100">100</ui:option>
    </ui:select>
  </ui:hbox>
</ui:hbox>
```

### Complete Pagination Example

```xml
<q:set name="page" value="1" />
<q:set name="pageSize" value="20" />

<q:fetch name="items" url="/api/items?page={page}&limit={pageSize}">
  <q:success>
    <ui:table data="{items.data.records}" />

    <ui:pagination
      current="{page}"
      total="{items.data.pagination.totalPages}"
      totalItems="{items.data.pagination.totalRecords}"
      pageSize="{pageSize}"
      on-change="handlePageChange"
    />
  </q:success>
</q:fetch>

<q:function name="handlePageChange">
  <q:param name="newPage" type="number" />
  <q:set name="page" value="{newPage}" />
</q:function>
```

## Menu

`ui:menu` provides navigation menu.

### Basic Usage

```xml
<ui:menu>
  <ui:menuitem href="/" active="true">Home</ui:menuitem>
  <ui:menuitem href="/about">About</ui:menuitem>
  <ui:menuitem href="/contact">Contact</ui:menuitem>
</ui:menu>
```

### Attributes (ui:menu)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `orientation` | string | "horizontal" | Menu direction |
| `variant` | string | "default" | Style variant |

### Attributes (ui:menuitem)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `href` | string | none | Link URL |
| `icon` | string | none | Icon name |
| `active` | boolean | false | Active state |
| `disabled` | boolean | false | Disabled state |
| `on-click` | string | none | Click handler |

### Vertical Menu

```xml
<ui:menu orientation="vertical">
  <ui:menuitem icon="home" active="true">Dashboard</ui:menuitem>
  <ui:menuitem icon="users">Users</ui:menuitem>
  <ui:menuitem icon="settings">Settings</ui:menuitem>
  <ui:menuitem icon="help">Help</ui:menuitem>
</ui:menu>
```

### Menu with Submenus

```xml
<ui:menu>
  <ui:menuitem href="/">Home</ui:menuitem>
  <ui:menuitem>
    Products
    <ui:submenu>
      <ui:menuitem href="/products/electronics">Electronics</ui:menuitem>
      <ui:menuitem href="/products/clothing">Clothing</ui:menuitem>
      <ui:menuitem href="/products/books">Books</ui:menuitem>
    </ui:submenu>
  </ui:menuitem>
  <ui:menuitem href="/about">About</ui:menuitem>
</ui:menu>
```

### Menu with Sections

```xml
<ui:menu orientation="vertical">
  <ui:menusection title="Main">
    <ui:menuitem icon="home">Dashboard</ui:menuitem>
    <ui:menuitem icon="chart">Analytics</ui:menuitem>
  </ui:menusection>

  <ui:menusection title="Management">
    <ui:menuitem icon="users">Users</ui:menuitem>
    <ui:menuitem icon="folder">Projects</ui:menuitem>
    <ui:menuitem icon="file">Reports</ui:menuitem>
  </ui:menusection>

  <ui:menusection title="Settings">
    <ui:menuitem icon="settings">Preferences</ui:menuitem>
    <ui:menuitem icon="shield">Security</ui:menuitem>
  </ui:menusection>
</ui:menu>
```

### Dynamic Menu from Data

```xml
<q:set name="menuItems" value='[
  {"id": "dashboard", "label": "Dashboard", "icon": "home", "href": "/"},
  {"id": "users", "label": "Users", "icon": "users", "href": "/users"},
  {"id": "settings", "label": "Settings", "icon": "settings", "href": "/settings"}
]' />

<q:set name="activeItem" value="dashboard" />

<ui:menu orientation="vertical">
  <q:loop type="array" var="item" items="{menuItems}">
    <ui:menuitem
      href="{item.href}"
      icon="{item.icon}"
      active="{activeItem == item.id}"
    >
      {item.label}
    </ui:menuitem>
  </q:loop>
</ui:menu>
```

## Navbar

`ui:navbar` provides a top navigation bar.

### Basic Usage

```xml
<ui:navbar>
  <ui:navbrand href="/">
    <ui:text size="lg" weight="bold">MyApp</ui:text>
  </ui:navbrand>

  <ui:navlinks>
    <ui:navlink href="/" active="true">Home</ui:navlink>
    <ui:navlink href="/features">Features</ui:navlink>
    <ui:navlink href="/pricing">Pricing</ui:navlink>
  </ui:navlinks>

  <ui:navactions>
    <ui:button variant="ghost">Login</ui:button>
    <ui:button variant="primary">Sign Up</ui:button>
  </ui:navactions>
</ui:navbar>
```

### Responsive Navbar

```xml
<ui:navbar>
  <ui:navbrand href="/">
    <ui:text size="lg" weight="bold">Logo</ui:text>
  </ui:navbrand>

  <!-- Mobile menu toggle -->
  <ui:navtoggle target="main-nav" />

  <!-- Collapsible section -->
  <ui:navcollapse id="main-nav">
    <ui:navlinks>
      <ui:navlink href="/">Home</ui:navlink>
      <ui:navlink href="/about">About</ui:navlink>
      <ui:navlink href="/contact">Contact</ui:navlink>
    </ui:navlinks>
  </ui:navcollapse>
</ui:navbar>
```

## Sidebar

`ui:sidebar` provides a side navigation panel.

### Basic Usage

```xml
<ui:hbox>
  <ui:sidebar width="250px">
    <ui:sidebarheader>
      <ui:text size="lg" weight="bold">Admin Panel</ui:text>
    </ui:sidebarheader>

    <ui:sidebarcontent>
      <ui:menu orientation="vertical">
        <ui:menuitem icon="home" active="true">Dashboard</ui:menuitem>
        <ui:menuitem icon="users">Users</ui:menuitem>
        <ui:menuitem icon="settings">Settings</ui:menuitem>
      </ui:menu>
    </ui:sidebarcontent>

    <ui:sidebarfooter>
      <ui:text size="sm" color="muted">v1.0.0</ui:text>
    </ui:sidebarfooter>
  </ui:sidebar>

  <ui:main padding="lg">
    <!-- Main content -->
  </ui:main>
</ui:hbox>
```

### Collapsible Sidebar

```xml
<q:set name="sidebarCollapsed" value="false" />

<ui:sidebar collapsed="{sidebarCollapsed}" collapsedWidth="64px">
  <ui:sidebarheader>
    <ui:button
      variant="ghost"
      on-click="toggleSidebar"
      icon="{sidebarCollapsed ? 'menu' : 'x'}"
    />
  </ui:sidebarheader>

  <ui:menu orientation="vertical">
    <ui:menuitem icon="home">
      <q:if condition="!sidebarCollapsed">Dashboard</q:if>
    </ui:menuitem>
    <ui:menuitem icon="users">
      <q:if condition="!sidebarCollapsed">Users</q:if>
    </ui:menuitem>
  </ui:menu>
</ui:sidebar>
```

## Complete Navigation Example

```xml
<q:application id="nav-demo" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="currentPage" value="dashboard" />
  <q:set name="currentTab" value="overview" />

  <ui:window title="Navigation Demo">
    <!-- Top navbar -->
    <ui:navbar>
      <ui:navbrand href="/">
        <ui:text size="lg" weight="bold">Quantum App</ui:text>
      </ui:navbrand>
      <ui:navlinks>
        <ui:navlink href="/dashboard" active="{currentPage == 'dashboard'}">
          Dashboard
        </ui:navlink>
        <ui:navlink href="/users" active="{currentPage == 'users'}">
          Users
        </ui:navlink>
        <ui:navlink href="/settings" active="{currentPage == 'settings'}">
          Settings
        </ui:navlink>
      </ui:navlinks>
      <ui:navactions>
        <ui:avatar src="{user.avatar}" name="{user.name}" size="sm" />
      </ui:navactions>
    </ui:navbar>

    <ui:hbox height="fill">
      <!-- Sidebar -->
      <ui:sidebar width="220px">
        <ui:menu orientation="vertical">
          <ui:menusection title="Quick Links">
            <ui:menuitem icon="chart">Analytics</ui:menuitem>
            <ui:menuitem icon="file">Reports</ui:menuitem>
          </ui:menusection>
        </ui:menu>
      </ui:sidebar>

      <!-- Main content -->
      <ui:vbox padding="lg" width="fill">
        <!-- Breadcrumb -->
        <ui:breadcrumb>
          <ui:crumb href="/" icon="home" />
          <ui:crumb href="/dashboard">Dashboard</ui:crumb>
          <ui:crumb>Overview</ui:crumb>
        </ui:breadcrumb>

        <!-- Tabs -->
        <ui:tabs bind="currentTab" variant="underline">
          <ui:tab id="overview" label="Overview">
            <ui:text>Overview content</ui:text>
          </ui:tab>
          <ui:tab id="analytics" label="Analytics" badge="New">
            <ui:text>Analytics content</ui:text>
          </ui:tab>
          <ui:tab id="reports" label="Reports">
            <ui:text>Reports content</ui:text>
          </ui:tab>
        </ui:tabs>

        <!-- Content with pagination -->
        <ui:panel title="Recent Items">
          <ui:table data="{items}" />
          <ui:pagination
            current="{page}"
            total="{totalPages}"
            on-change="loadPage"
          />
        </ui:panel>
      </ui:vbox>
    </ui:hbox>
  </ui:window>

</q:application>
```

## Related Documentation

- [Layout Components](/ui/layout) - Container components
- [Form Components](/ui/forms) - Button and input components
- [Overlays](/ui/overlays) - Dropdown menus
