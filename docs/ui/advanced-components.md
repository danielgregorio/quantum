# Advanced Components

Rich UI components for complex use cases including cards, avatars, charts, and skeleton loaders.

## Card

`ui:card` is a flexible container for grouping related content.

### Basic Usage

```xml
<ui:card>
  <ui:cardheader>
    <ui:text weight="bold">Card Title</ui:text>
  </ui:cardheader>
  <ui:cardbody>
    <ui:text>Card content goes here.</ui:text>
  </ui:cardbody>
</ui:card>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "default" | Style (default, elevated, outlined) |
| `padding` | token | "md" | Content padding |
| `hoverable` | boolean | false | Hover effect |
| `clickable` | boolean | false | Click behavior |
| `on-click` | string | none | Click handler |

### Card Variants

```xml
<!-- Default card -->
<ui:card variant="default">
  <ui:cardbody>Default card with subtle shadow</ui:cardbody>
</ui:card>

<!-- Elevated card (more shadow) -->
<ui:card variant="elevated">
  <ui:cardbody>Elevated card with prominent shadow</ui:cardbody>
</ui:card>

<!-- Outlined card (border, no shadow) -->
<ui:card variant="outlined">
  <ui:cardbody>Outlined card with border</ui:cardbody>
</ui:card>
```

### Card with Image

```xml
<ui:card width="300px">
  <ui:cardimage src="/images/product.jpg" alt="Product" />
  <ui:cardbody>
    <ui:text weight="bold">Product Name</ui:text>
    <ui:text color="muted" size="sm">Product description goes here.</ui:text>
    <ui:text weight="bold" color="primary">$29.99</ui:text>
  </ui:cardbody>
  <ui:cardfooter>
    <ui:button variant="primary" width="fill">Add to Cart</ui:button>
  </ui:cardfooter>
</ui:card>
```

### Card with Header and Footer

```xml
<ui:card>
  <ui:cardheader>
    <ui:hbox justify="between" align="center">
      <ui:text weight="bold">Order #12345</ui:text>
      <ui:badge variant="success">Completed</ui:badge>
    </ui:hbox>
  </ui:cardheader>

  <ui:cardbody>
    <ui:vbox gap="sm">
      <ui:text>2x Widget Pro - $50.00</ui:text>
      <ui:text>1x Gadget Plus - $25.00</ui:text>
      <ui:divider />
      <ui:hbox justify="between">
        <ui:text weight="bold">Total:</ui:text>
        <ui:text weight="bold">$75.00</ui:text>
      </ui:hbox>
    </ui:vbox>
  </ui:cardbody>

  <ui:cardfooter>
    <ui:hbox gap="sm" justify="end">
      <ui:button variant="ghost">View Details</ui:button>
      <ui:button variant="primary">Track Order</ui:button>
    </ui:hbox>
  </ui:cardfooter>
</ui:card>
```

### Clickable Card

```xml
<ui:card hoverable="true" clickable="true" on-click="viewProduct(item.id)">
  <ui:cardimage src="{item.image}" />
  <ui:cardbody>
    <ui:text weight="bold">{item.name}</ui:text>
    <ui:text color="muted">{item.description}</ui:text>
  </ui:cardbody>
</ui:card>
```

### Card Grid

```xml
<ui:grid columns="3" gap="lg">
  <q:loop type="array" var="product" items="{products}">
    <ui:card hoverable="true">
      <ui:cardimage src="{product.image}" />
      <ui:cardbody>
        <ui:text weight="bold">{product.name}</ui:text>
        <ui:text color="primary" weight="bold">${product.price}</ui:text>
      </ui:cardbody>
      <ui:cardfooter>
        <ui:button variant="primary" width="fill" on-click="addToCart(product.id)">
          Add to Cart
        </ui:button>
      </ui:cardfooter>
    </ui:card>
  </q:loop>
</ui:grid>
```

## Avatar

`ui:avatar` displays user profile images or initials.

### Basic Usage

```xml
<ui:avatar src="/images/user.jpg" name="John Doe" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `src` | string | none | Image URL |
| `name` | string | none | Name for initials fallback |
| `size` | string | "md" | Size (xs, sm, md, lg, xl) |
| `shape` | string | "circle" | Shape (circle, square) |
| `status` | string | none | Status indicator (online, offline, away, busy) |
| `color` | string | "primary" | Background color for initials |

### Avatar Sizes

```xml
<ui:hbox gap="md" align="center">
  <ui:avatar src="{user.avatar}" size="xs" />
  <ui:avatar src="{user.avatar}" size="sm" />
  <ui:avatar src="{user.avatar}" size="md" />
  <ui:avatar src="{user.avatar}" size="lg" />
  <ui:avatar src="{user.avatar}" size="xl" />
</ui:hbox>
```

### Avatar with Initials

When no image is provided, initials are shown:

```xml
<ui:avatar name="John Doe" />
<!-- Shows "JD" -->

<ui:avatar name="Alice" color="success" />
<!-- Shows "A" with green background -->
```

### Avatar with Status

```xml
<ui:hbox gap="md">
  <ui:avatar src="{user.avatar}" status="online" />
  <ui:avatar src="{user.avatar}" status="away" />
  <ui:avatar src="{user.avatar}" status="busy" />
  <ui:avatar src="{user.avatar}" status="offline" />
</ui:hbox>
```

### Square Avatar

```xml
<ui:avatar src="{company.logo}" shape="square" />
```

### Avatar Group

```xml
<ui:avatargroup max="5">
  <q:loop type="array" var="member" items="{teamMembers}">
    <ui:avatar src="{member.avatar}" name="{member.name}" />
  </q:loop>
</ui:avatargroup>
<!-- Shows first 5 avatars + "+N" for remaining -->
```

### Avatar in Context

```xml
<!-- User profile header -->
<ui:hbox gap="md" align="center">
  <ui:avatar src="{user.avatar}" name="{user.name}" size="lg" status="online" />
  <ui:vbox gap="xs">
    <ui:text weight="bold">{user.name}</ui:text>
    <ui:text color="muted" size="sm">{user.role}</ui:text>
  </ui:vbox>
</ui:hbox>

<!-- Comment with avatar -->
<ui:hbox gap="sm">
  <ui:avatar src="{comment.author.avatar}" size="sm" />
  <ui:vbox gap="xs">
    <ui:text size="sm" weight="bold">{comment.author.name}</ui:text>
    <ui:text size="sm">{comment.text}</ui:text>
  </ui:vbox>
</ui:hbox>
```

## Chart

`ui:chart` displays data visualizations.

### Bar Chart

```xml
<ui:chart type="bar" title="Monthly Revenue">
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
| `type` | string | "bar" | Chart type |
| `title` | string | none | Chart title |
| `width` | string | "100%" | Chart width |
| `height` | string | "300px" | Chart height |
| `showValues` | boolean | true | Show data labels |
| `showLegend` | boolean | false | Show legend |
| `colors` | array | theme | Bar/segment colors |

### Chart with Dynamic Data

```xml
<q:fetch name="stats" url="/api/stats">
  <q:loading>
    <ui:skeleton type="rect" height="300px" />
  </q:loading>
  <q:success>
    <ui:chart type="bar" title="Sales by Region">
      <ui:data>{stats.data.regions}</ui:data>
    </ui:chart>
  </q:success>
</q:fetch>
```

### Colored Bars

```xml
<ui:chart type="bar" title="Task Status">
  <ui:data>
    [
      {"label": "Completed", "value": 45, "color": "success"},
      {"label": "In Progress", "value": 30, "color": "warning"},
      {"label": "Todo", "value": 25, "color": "secondary"}
    ]
  </ui:data>
</ui:chart>
```

### Horizontal Bar Chart

```xml
<ui:chart type="bar" direction="horizontal" title="Top Products">
  <ui:data>
    [
      {"label": "Product A", "value": 1200},
      {"label": "Product B", "value": 980},
      {"label": "Product C", "value": 750}
    ]
  </ui:data>
</ui:chart>
```

## Skeleton

`ui:skeleton` displays loading placeholders.

### Text Skeleton

```xml
<ui:skeleton type="text" lines="3" />
```

### Card Skeleton

```xml
<ui:skeleton type="card">
  <ui:skeleton type="rect" height="150px" />
  <ui:vbox gap="sm" padding="md">
    <ui:skeleton type="text" width="70%" />
    <ui:skeleton type="text" width="90%" />
    <ui:skeleton type="text" width="50%" />
  </ui:vbox>
</ui:skeleton>
```

### List Skeleton

```xml
<ui:vbox gap="md">
  <q:loop type="range" var="i" from="1" to="5">
    <ui:hbox gap="md" align="center">
      <ui:skeleton type="circle" width="40px" height="40px" />
      <ui:vbox gap="xs" width="fill">
        <ui:skeleton type="text" width="150px" />
        <ui:skeleton type="text" width="200px" />
      </ui:vbox>
    </ui:hbox>
  </q:loop>
</ui:vbox>
```

### Table Skeleton

```xml
<ui:skeleton type="table" rows="5" columns="4" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | "text" | Shape (text, rect, circle, card, table) |
| `width` | string | "100%" | Width |
| `height` | string | varies | Height |
| `lines` | number | 1 | Text lines |
| `animated` | boolean | true | Shimmer animation |

## Icon

`ui:icon` displays vector icons.

### Basic Usage

```xml
<ui:icon name="home" />
<ui:icon name="user" />
<ui:icon name="settings" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Icon name |
| `size` | string | "md" | Size (xs, sm, md, lg, xl) |
| `color` | string | "inherit" | Icon color |

### Icon Sizes

```xml
<ui:hbox gap="md" align="center">
  <ui:icon name="star" size="xs" />
  <ui:icon name="star" size="sm" />
  <ui:icon name="star" size="md" />
  <ui:icon name="star" size="lg" />
  <ui:icon name="star" size="xl" />
</ui:hbox>
```

### Icon Colors

```xml
<ui:icon name="check" color="success" />
<ui:icon name="x" color="danger" />
<ui:icon name="alert" color="warning" />
<ui:icon name="info" color="info" />
```

### Icons in Buttons

```xml
<ui:button variant="primary">
  <ui:icon name="save" /> Save
</ui:button>

<ui:button variant="danger">
  <ui:icon name="trash" /> Delete
</ui:button>
```

## Image

`ui:image` displays images with loading states.

### Basic Usage

```xml
<ui:image src="/images/photo.jpg" alt="Description" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `src` | string | required | Image URL |
| `alt` | string | "" | Alt text |
| `width` | string | "auto" | Image width |
| `height` | string | "auto" | Image height |
| `fit` | string | "cover" | Object-fit (cover, contain, fill) |
| `lazy` | boolean | true | Lazy loading |
| `fallback` | string | none | Fallback image URL |

### Responsive Image

```xml
<ui:image
  src="/images/hero.jpg"
  alt="Hero image"
  width="100%"
  height="300px"
  fit="cover"
/>
```

### Image with Fallback

```xml
<ui:image
  src="{user.avatar}"
  fallback="/images/default-avatar.png"
  alt="{user.name}"
/>
```

## Complete Advanced Components Example

```xml
<q:application id="advanced-demo" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:fetch name="users" url="/api/users" />
  <q:fetch name="stats" url="/api/dashboard/stats" />

  <ui:window title="Advanced Components Demo">
    <ui:vbox padding="lg" gap="lg">

      <!-- Stats Cards -->
      <ui:grid columns="4" gap="md">
        <ui:card>
          <ui:cardbody>
            <ui:hbox justify="between" align="start">
              <ui:vbox gap="xs">
                <ui:text color="muted" size="sm">Total Users</ui:text>
                <ui:text size="2xl" weight="bold">1,234</ui:text>
              </ui:vbox>
              <ui:avatar name="U" color="primary" shape="square" />
            </ui:hbox>
          </ui:cardbody>
        </ui:card>

        <ui:card>
          <ui:cardbody>
            <ui:hbox justify="between" align="start">
              <ui:vbox gap="xs">
                <ui:text color="muted" size="sm">Revenue</ui:text>
                <ui:text size="2xl" weight="bold">$56.7k</ui:text>
              </ui:vbox>
              <ui:avatar name="$" color="success" shape="square" />
            </ui:hbox>
          </ui:cardbody>
        </ui:card>

        <ui:card>
          <ui:cardbody>
            <ui:hbox justify="between" align="start">
              <ui:vbox gap="xs">
                <ui:text color="muted" size="sm">Orders</ui:text>
                <ui:text size="2xl" weight="bold">89</ui:text>
              </ui:vbox>
              <ui:avatar name="O" color="warning" shape="square" />
            </ui:hbox>
          </ui:cardbody>
        </ui:card>

        <ui:card>
          <ui:cardbody>
            <ui:hbox justify="between" align="start">
              <ui:vbox gap="xs">
                <ui:text color="muted" size="sm">Growth</ui:text>
                <ui:text size="2xl" weight="bold" color="success">+12%</ui:text>
              </ui:vbox>
              <ui:icon name="trending-up" size="xl" color="success" />
            </ui:hbox>
          </ui:cardbody>
        </ui:card>
      </ui:grid>

      <!-- Chart Section -->
      <ui:card>
        <ui:cardheader>
          <ui:text weight="bold">Monthly Performance</ui:text>
        </ui:cardheader>
        <ui:cardbody>
          <q:if condition="stats.loading">
            <ui:skeleton type="rect" height="300px" />
          </q:if>
          <q:if condition="!stats.loading && stats.data">
            <ui:chart type="bar" height="300px">
              <ui:data>{stats.data.monthly}</ui:data>
            </ui:chart>
          </q:if>
        </ui:cardbody>
      </ui:card>

      <!-- User List -->
      <ui:card>
        <ui:cardheader>
          <ui:hbox justify="between" align="center">
            <ui:text weight="bold">Team Members</ui:text>
            <ui:avatargroup max="4">
              <q:if condition="!users.loading">
                <q:loop type="array" var="user" items="{users.data}">
                  <ui:avatar src="{user.avatar}" name="{user.name}" />
                </q:loop>
              </q:if>
            </ui:avatargroup>
          </ui:hbox>
        </ui:cardheader>
        <ui:cardbody>
          <q:if condition="users.loading">
            <ui:vbox gap="md">
              <q:loop type="range" var="i" from="1" to="3">
                <ui:hbox gap="md" align="center">
                  <ui:skeleton type="circle" width="48px" height="48px" />
                  <ui:vbox gap="xs" width="fill">
                    <ui:skeleton type="text" width="150px" />
                    <ui:skeleton type="text" width="200px" />
                  </ui:vbox>
                </ui:hbox>
              </q:loop>
            </ui:vbox>
          </q:if>
          <q:if condition="!users.loading">
            <ui:vbox gap="md">
              <q:loop type="array" var="user" items="{users.data}">
                <ui:hbox gap="md" align="center">
                  <ui:avatar src="{user.avatar}" name="{user.name}" status="{user.status}" />
                  <ui:vbox gap="xs">
                    <ui:text weight="bold">{user.name}</ui:text>
                    <ui:text color="muted" size="sm">{user.email}</ui:text>
                  </ui:vbox>
                  <ui:spacer />
                  <ui:badge variant="{user.role == 'admin' ? 'primary' : 'secondary'}">
                    {user.role}
                  </ui:badge>
                </ui:hbox>
              </q:loop>
            </ui:vbox>
          </q:if>
        </ui:cardbody>
      </ui:card>

    </ui:vbox>
  </ui:window>

</q:application>
```

## Related Documentation

- [Layout Components](/ui/layout) - Container components
- [Data Display](/ui/data-display) - Tables and lists
- [Feedback Components](/ui/feedback) - Loading states
