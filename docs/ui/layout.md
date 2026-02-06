# Layout Components

Layout components control the structure and arrangement of UI elements in Quantum applications.

## Window

`ui:window` is the root container for UI applications. It represents the main application window.

### Basic Usage

```xml
<ui:window title="My Application">
  <!-- Content here -->
</ui:window>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | "Quantum UI" | Window title |
| `width` | string | "100%" | Window width |
| `height` | string | "100vh" | Window height |
| `theme` | string | "light" | Theme preset (light, dark) |

### With Header and Footer

```xml
<ui:window title="Dashboard">
  <ui:header>
    <ui:text size="xl" weight="bold">Dashboard</ui:text>
  </ui:header>

  <ui:vbox padding="lg">
    <!-- Main content -->
  </ui:vbox>

  <ui:footer>
    <ui:text color="muted">Copyright 2025</ui:text>
  </ui:footer>
</ui:window>
```

## HBox

`ui:hbox` arranges children horizontally (row layout).

### Basic Usage

```xml
<ui:hbox gap="md">
  <ui:button>First</ui:button>
  <ui:button>Second</ui:button>
  <ui:button>Third</ui:button>
</ui:hbox>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `gap` | token | none | Space between children (xs, sm, md, lg, xl) |
| `padding` | token | none | Inner padding |
| `align` | string | "start" | Cross-axis alignment (start, center, end, stretch) |
| `justify` | string | "start" | Main-axis alignment (start, center, end, between, around) |
| `wrap` | boolean | false | Allow wrapping to next line |

### Alignment Examples

```xml
<!-- Center items vertically and spread horizontally -->
<ui:hbox align="center" justify="between">
  <ui:text>Left</ui:text>
  <ui:text>Right</ui:text>
</ui:hbox>

<!-- Center everything -->
<ui:hbox align="center" justify="center" gap="lg">
  <ui:button>Button 1</ui:button>
  <ui:button>Button 2</ui:button>
</ui:hbox>

<!-- Stretch items to fill height -->
<ui:hbox align="stretch" gap="md" height="200px">
  <ui:panel width="1/3">Sidebar</ui:panel>
  <ui:panel width="2/3">Content</ui:panel>
</ui:hbox>
```

### With Spacer

Use `ui:spacer` to push items apart:

```xml
<ui:hbox padding="md">
  <ui:text size="lg">Logo</ui:text>
  <ui:spacer />
  <ui:button>Login</ui:button>
  <ui:button variant="primary">Sign Up</ui:button>
</ui:hbox>
```

## VBox

`ui:vbox` arranges children vertically (column layout).

### Basic Usage

```xml
<ui:vbox gap="md">
  <ui:text>First line</ui:text>
  <ui:text>Second line</ui:text>
  <ui:text>Third line</ui:text>
</ui:vbox>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `gap` | token | none | Space between children |
| `padding` | token | none | Inner padding |
| `align` | string | "stretch" | Cross-axis alignment |
| `justify` | string | "start" | Main-axis alignment |

### Common Patterns

```xml
<!-- Centered content -->
<ui:vbox align="center" justify="center" height="100vh">
  <ui:text size="2xl">Welcome</ui:text>
  <ui:button variant="primary">Get Started</ui:button>
</ui:vbox>

<!-- Form layout -->
<ui:vbox gap="md" padding="lg">
  <ui:formitem label="Email">
    <ui:input type="email" bind="email" />
  </ui:formitem>
  <ui:formitem label="Password">
    <ui:input type="password" bind="password" />
  </ui:formitem>
  <ui:button variant="primary" width="fill">Login</ui:button>
</ui:vbox>
```

## Grid

`ui:grid` creates CSS Grid-based layouts.

### Basic Usage

```xml
<ui:grid columns="3" gap="md">
  <ui:card>Card 1</ui:card>
  <ui:card>Card 2</ui:card>
  <ui:card>Card 3</ui:card>
  <ui:card>Card 4</ui:card>
  <ui:card>Card 5</ui:card>
  <ui:card>Card 6</ui:card>
</ui:grid>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `columns` | number/string | 1 | Number of columns or template |
| `rows` | string | "auto" | Row template |
| `gap` | token | none | Gap between cells |
| `rowGap` | token | gap | Vertical gap |
| `colGap` | token | gap | Horizontal gap |

### Responsive Grid

```xml
<ui:grid columns="1 md:2 lg:3" gap="lg">
  <!-- 1 column on mobile, 2 on tablet, 3 on desktop -->
  <ui:card>Item 1</ui:card>
  <ui:card>Item 2</ui:card>
  <ui:card>Item 3</ui:card>
</ui:grid>
```

### Custom Column Templates

```xml
<!-- Sidebar + Content layout -->
<ui:grid columns="250px 1fr" gap="lg">
  <ui:panel>Sidebar</ui:panel>
  <ui:panel>Main Content</ui:panel>
</ui:grid>

<!-- Dashboard layout -->
<ui:grid columns="repeat(4, 1fr)" gap="md">
  <ui:card>Stat 1</ui:card>
  <ui:card>Stat 2</ui:card>
  <ui:card>Stat 3</ui:card>
  <ui:card>Stat 4</ui:card>
</ui:grid>
```

### Grid Item Spanning

```xml
<ui:grid columns="3" gap="md">
  <ui:card colspan="2">Wide Card (2 columns)</ui:card>
  <ui:card>Normal</ui:card>
  <ui:card>Normal</ui:card>
  <ui:card colspan="2" rowspan="2">Large Card</ui:card>
</ui:grid>
```

## Panel

`ui:panel` is a bordered container with optional title.

### Basic Usage

```xml
<ui:panel title="User Information">
  <ui:text>Name: John Doe</ui:text>
  <ui:text>Email: john@example.com</ui:text>
</ui:panel>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | none | Panel header text |
| `padding` | token | "md" | Inner padding |
| `variant` | string | "default" | Style variant |
| `collapsible` | boolean | false | Allow collapsing |
| `collapsed` | boolean | false | Initial collapsed state |

### Variants

```xml
<!-- Default panel -->
<ui:panel title="Default">Content</ui:panel>

<!-- Elevated panel (more shadow) -->
<ui:panel title="Elevated" variant="elevated">Content</ui:panel>

<!-- Outlined panel (no shadow, thicker border) -->
<ui:panel title="Outlined" variant="outlined">Content</ui:panel>
```

### Collapsible Panel

```xml
<ui:panel title="Advanced Options" collapsible="true" collapsed="true">
  <ui:formitem label="Debug Mode">
    <ui:switch bind="debugMode" />
  </ui:formitem>
</ui:panel>
```

## Tabs

`ui:tabs` creates tabbed navigation.

### Basic Usage

```xml
<ui:tabs>
  <ui:tab label="Profile">
    <ui:text>Profile content here</ui:text>
  </ui:tab>
  <ui:tab label="Settings">
    <ui:text>Settings content here</ui:text>
  </ui:tab>
  <ui:tab label="Notifications">
    <ui:text>Notifications content here</ui:text>
  </ui:tab>
</ui:tabs>
```

### Attributes (ui:tabs)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "default" | Style variant (default, pills, underline) |
| `position` | string | "top" | Tab position (top, bottom, left, right) |

### Attributes (ui:tab)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `label` | string | required | Tab label text |
| `icon` | string | none | Icon name |
| `disabled` | boolean | false | Disable the tab |
| `active` | boolean | false | Set as active tab |

### Tab Variants

```xml
<!-- Pills style -->
<ui:tabs variant="pills">
  <ui:tab label="All">...</ui:tab>
  <ui:tab label="Active">...</ui:tab>
  <ui:tab label="Completed">...</ui:tab>
</ui:tabs>

<!-- Underline style -->
<ui:tabs variant="underline">
  <ui:tab label="Overview">...</ui:tab>
  <ui:tab label="Analytics">...</ui:tab>
</ui:tabs>
```

### Controlled Tabs

```xml
<q:set name="activeTab" value="profile" />

<ui:tabs bind="activeTab">
  <ui:tab id="profile" label="Profile">...</ui:tab>
  <ui:tab id="settings" label="Settings">...</ui:tab>
</ui:tabs>
```

## Accordion

`ui:accordion` creates collapsible sections.

### Basic Usage

```xml
<ui:accordion>
  <ui:section title="Section 1">
    <ui:text>Content for section 1</ui:text>
  </ui:section>
  <ui:section title="Section 2">
    <ui:text>Content for section 2</ui:text>
  </ui:section>
  <ui:section title="Section 3">
    <ui:text>Content for section 3</ui:text>
  </ui:section>
</ui:accordion>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `multiple` | boolean | false | Allow multiple sections open |
| `variant` | string | "default" | Style variant |

### Single Selection (Default)

Only one section can be open at a time:

```xml
<ui:accordion>
  <ui:section title="FAQ 1" expanded="true">
    Answer 1
  </ui:section>
  <ui:section title="FAQ 2">
    Answer 2
  </ui:section>
</ui:accordion>
```

### Multiple Selection

```xml
<ui:accordion multiple="true">
  <ui:section title="General Settings">...</ui:section>
  <ui:section title="Advanced Settings">...</ui:section>
  <ui:section title="Developer Options">...</ui:section>
</ui:accordion>
```

## Header and Footer

### Header

```xml
<ui:header>
  <ui:hbox align="center" justify="between" padding="md">
    <ui:text size="lg" weight="bold">My App</ui:text>
    <ui:hbox gap="sm">
      <ui:button variant="ghost">Help</ui:button>
      <ui:button variant="primary">Login</ui:button>
    </ui:hbox>
  </ui:hbox>
</ui:header>
```

### Footer

```xml
<ui:footer>
  <ui:hbox justify="between" padding="md">
    <ui:text color="muted">Copyright 2025 My Company</ui:text>
    <ui:hbox gap="md">
      <ui:link href="/privacy">Privacy</ui:link>
      <ui:link href="/terms">Terms</ui:link>
    </ui:hbox>
  </ui:hbox>
</ui:footer>
```

## Scroll Container

`ui:scrollbox` creates a scrollable container.

```xml
<ui:scrollbox height="400px">
  <ui:vbox gap="sm">
    <q:loop type="range" var="i" from="1" to="50">
      <ui:text>Item {i}</ui:text>
    </q:loop>
  </ui:vbox>
</ui:scrollbox>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `height` | string | "auto" | Container height |
| `maxHeight` | string | none | Maximum height |
| `horizontal` | boolean | false | Enable horizontal scrolling |

## Spacer

`ui:spacer` fills available space in flex layouts.

```xml
<ui:hbox>
  <ui:text>Left</ui:text>
  <ui:spacer />
  <ui:text>Right</ui:text>
</ui:hbox>
```

## Divider

`ui:divider` creates a visual separator.

```xml
<ui:vbox gap="md">
  <ui:text>Section 1</ui:text>
  <ui:divider />
  <ui:text>Section 2</ui:text>
</ui:vbox>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `orientation` | string | "horizontal" | horizontal or vertical |
| `variant` | string | "solid" | solid, dashed, dotted |

## Complete Layout Example

```xml
<ui:window title="Dashboard">
  <!-- Fixed header -->
  <ui:header>
    <ui:hbox padding="md" align="center" justify="between">
      <ui:text size="lg" weight="bold">Dashboard</ui:text>
      <ui:hbox gap="sm">
        <ui:badge variant="success">Online</ui:badge>
        <ui:avatar src="{user.avatar}" size="sm" />
      </ui:hbox>
    </ui:hbox>
  </ui:header>

  <!-- Main content area -->
  <ui:hbox height="fill">
    <!-- Sidebar -->
    <ui:vbox width="250px" padding="md" gap="sm">
      <ui:menu>
        <ui:menuitem icon="home" active="true">Dashboard</ui:menuitem>
        <ui:menuitem icon="users">Users</ui:menuitem>
        <ui:menuitem icon="settings">Settings</ui:menuitem>
      </ui:menu>
    </ui:vbox>

    <!-- Content -->
    <ui:scrollbox width="fill" padding="lg">
      <!-- Stats grid -->
      <ui:grid columns="4" gap="md">
        <ui:card>
          <ui:text color="muted" size="sm">Total Users</ui:text>
          <ui:text size="2xl" weight="bold">1,234</ui:text>
        </ui:card>
        <ui:card>
          <ui:text color="muted" size="sm">Revenue</ui:text>
          <ui:text size="2xl" weight="bold">$5,678</ui:text>
        </ui:card>
        <ui:card>
          <ui:text color="muted" size="sm">Orders</ui:text>
          <ui:text size="2xl" weight="bold">89</ui:text>
        </ui:card>
        <ui:card>
          <ui:text color="muted" size="sm">Growth</ui:text>
          <ui:text size="2xl" weight="bold" color="success">+12%</ui:text>
        </ui:card>
      </ui:grid>

      <!-- Content panels -->
      <ui:hbox gap="lg" padding="lg 0">
        <ui:panel title="Recent Activity" width="2/3">
          <ui:table data="{activities}" />
        </ui:panel>
        <ui:panel title="Quick Actions" width="1/3">
          <ui:vbox gap="sm">
            <ui:button width="fill">New User</ui:button>
            <ui:button width="fill">New Order</ui:button>
            <ui:button width="fill">Generate Report</ui:button>
          </ui:vbox>
        </ui:panel>
      </ui:hbox>
    </ui:scrollbox>
  </ui:hbox>

  <!-- Fixed footer -->
  <ui:footer>
    <ui:text color="muted" align="center">
      Version 1.0.0 | Built with Quantum
    </ui:text>
  </ui:footer>
</ui:window>
```

## Related Documentation

- [Form Components](/ui/forms) - Input controls
- [Data Display](/ui/data-display) - Tables and lists
- [Design Tokens](/ui/overview#design-tokens) - Spacing and sizing
