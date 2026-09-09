# UI Tags Reference (ui:)

Complete reference for all `ui:` namespace tags in the Quantum Framework. These tags are used to build user interfaces that compile to HTML, Desktop (pywebview), or Terminal (Textual) targets.

## Layout Containers

### ui:window

Top-level window container for UI applications.

```xml
<ui:window title="My Application">
  <ui:vbox padding="lg">
    <ui:text>Hello World</ui:text>
  </ui:vbox>
</ui:window>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | - | Window title |
| + [Layout Attributes](#layout-attributes) |

---

### ui:vbox

Vertical flex container. Children are stacked vertically.

```xml
<ui:vbox gap="md" padding="lg" align="center">
  <ui:text>Item 1</ui:text>
  <ui:text>Item 2</ui:text>
  <ui:text>Item 3</ui:text>
</ui:vbox>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

---

### ui:hbox

Horizontal flex container. Children are arranged horizontally.

```xml
<ui:hbox gap="md" justify="between">
  <ui:button>Left</ui:button>
  <ui:spacer />
  <ui:button>Right</ui:button>
</ui:hbox>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

---

### ui:grid

CSS grid container for complex layouts.

```xml
<ui:grid columns="3" gap="md">
  <ui:card>1</ui:card>
  <ui:card>2</ui:card>
  <ui:card>3</ui:card>
</ui:grid>

<!-- Custom column template -->
<ui:grid columns="1fr 2fr 1fr" gap="lg">
  <ui:panel>Sidebar</ui:panel>
  <ui:panel>Main</ui:panel>
  <ui:panel>Sidebar</ui:panel>
</ui:grid>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `columns` | string | - | Column definition (number or CSS template) |
| + [Layout Attributes](#layout-attributes) |

---

### ui:panel

Bordered container with optional title.

```xml
<ui:panel title="Settings" collapsible="true">
  <ui:input bind="name" />
  <ui:input bind="email" />
</ui:panel>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | - | Panel title |
| `collapsible` | boolean | `false` | Allow collapsing |
| + [Layout Attributes](#layout-attributes) |

---

### ui:tabpanel

Tabbed content container.

```xml
<ui:tabpanel>
  <ui:tab title="General">
    <ui:text>General settings</ui:text>
  </ui:tab>
  <ui:tab title="Advanced">
    <ui:text>Advanced settings</ui:text>
  </ui:tab>
</ui:tabpanel>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:tab`

---

### ui:tab

Individual tab inside a tabpanel.

```xml
<ui:tab title="Settings">
  <ui:form>...</ui:form>
</ui:tab>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | **required** | Tab title |
| + [Layout Attributes](#layout-attributes) |

**Parent:** `ui:tabpanel`

---

### ui:accordion

Collapsible sections container.

```xml
<ui:accordion>
  <ui:section title="Section 1" expanded="true">
    Content for section 1
  </ui:section>
  <ui:section title="Section 2">
    Content for section 2
  </ui:section>
</ui:accordion>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:section`

---

### ui:section

Collapsible section inside an accordion.

```xml
<ui:section title="Details" expanded="true">
  <ui:text>Section content here</ui:text>
</ui:section>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | **required** | Section title |
| `expanded` | boolean | `false` | Initial expanded state |
| + [Layout Attributes](#layout-attributes) |

**Parent:** `ui:accordion`

---

### ui:spacer

Flexible space filler.

```xml
<ui:hbox>
  <ui:text>Left</ui:text>
  <ui:spacer />
  <ui:text>Right</ui:text>
</ui:hbox>

<!-- Fixed size spacer -->
<ui:spacer size="20px" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `size` | css-size | - | Fixed size (flexible if not set) |
| + [Layout Attributes](#layout-attributes) |

---

### ui:rule

Horizontal rule/separator.

```xml
<ui:vbox>
  <ui:text>Above</ui:text>
  <ui:rule />
  <ui:text>Below</ui:text>
</ui:vbox>
```

---

## Form Components

### ui:form

Form container with validation support.

```xml
<ui:form on-submit="handleSubmit" validation="both" error-display="inline">
  <ui:formitem label="Email">
    <ui:input bind="email" type="email" required="true" />
  </ui:formitem>
  <ui:button type="submit" variant="primary">Submit</ui:button>
</ui:form>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `on-submit` | expression | - | Submit handler |
| `validationMode` | enum | `both` | Validation: `client`, `server`, `both` |
| `errorDisplay` | enum | `inline` | Error display: `inline`, `summary`, `both` |
| `novalidate` | boolean | `false` | Disable HTML5 validation |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:formitem`, `ui:input`, `ui:select`, `ui:button`, `ui:validator`

---

### ui:formitem

Form item wrapper with label.

```xml
<ui:formitem label="Username" required="true">
  <ui:input bind="username" placeholder="Enter username" />
</ui:formitem>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `label` | string | - | Field label |
| + [Layout Attributes](#layout-attributes) |

---

### ui:validator

Custom validation rule for forms.

```xml
<ui:validator name="passwordStrength"
              pattern="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$"
              message="Password must have uppercase, lowercase, and number" />

<ui:validator name="passwordMatch"
              match="password"
              message="Passwords must match" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | - | Validator name |
| `pattern` | regex | - | Regex pattern |
| `match` | string | - | Field name to match against |
| `min` | number | - | Minimum value |
| `max` | number | - | Maximum value |
| `minlength` | integer | - | Minimum length |
| `maxlength` | integer | - | Maximum length |
| `message` | string | - | Error message |
| `field` | string | - | Target field |
| `trigger` | enum | `submit` | When to validate: `blur`, `change`, `input`, `submit` |
| `expression` | string | - | Custom JS expression |

---

### ui:input

Text input widget with validation support.

```xml
<ui:input bind="email" type="email" placeholder="Enter email" required="true" />
<ui:input bind="age" type="number" min="0" max="120" />
<ui:input bind="password" type="password" minlength="8" pattern="(?=.*\d)" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | expression | - | Two-way binding variable |
| `type` | enum | `text` | Input type: `text`, `password`, `email`, `number`, `tel`, `url`, `search`, `date`, `time`, `datetime-local` |
| `placeholder` | string | - | Placeholder text |
| `on-change` | expression | - | Change handler |
| `on-submit` | expression | - | Submit handler |
| `required` | boolean | `false` | Field is required |
| `min` | number | - | Minimum value |
| `max` | number | - | Maximum value |
| `minlength` | integer | - | Minimum length |
| `maxlength` | integer | - | Maximum length |
| `pattern` | regex | - | Validation pattern |
| `errorMessage` | string | - | Custom error message |
| + [Layout Attributes](#layout-attributes) |

---

### ui:select

Dropdown select widget.

```xml
<ui:select bind="country">
  <ui:option value="">Select country</ui:option>
  <ui:option value="us">United States</ui:option>
  <ui:option value="uk">United Kingdom</ui:option>
</ui:select>

<!-- From data source -->
<ui:select bind="user" source="{users}">
  <ui:option value="{item.id}" label="{item.name}" />
</ui:select>

<!-- Simple options -->
<ui:select bind="size" options="S,M,L,XL" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | expression | - | Binding variable |
| `options` | string | - | Comma-separated options |
| `source` | expression | - | Data source for options |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:option`

---

### ui:option

Option for select, menu, or dropdown.

```xml
<ui:option value="1" label="Option 1" />
<ui:option value="delete" label="Delete" on-click="handleDelete" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `value` | string | - | Option value |
| `label` | string | - | Display label |
| `on-click` | expression | - | Click handler |

---

### ui:checkbox

Checkbox widget for boolean values.

```xml
<ui:checkbox bind="agreeToTerms" label="I agree to the terms" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | expression | - | Boolean variable to bind |
| `label` | string | - | Checkbox label |
| + [Layout Attributes](#layout-attributes) |

---

### ui:switch

Toggle switch widget (on/off).

```xml
<ui:switch bind="darkMode" label="Dark Mode" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | expression | - | Boolean variable to bind |
| `label` | string | - | Switch label |
| + [Layout Attributes](#layout-attributes) |

---

### ui:radio

Radio button group.

```xml
<ui:radio bind="size" options="S,M,L,XL" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | expression | - | Binding variable |
| `options` | string | - | Comma-separated options |
| + [Layout Attributes](#layout-attributes) |

---

### ui:button

Clickable button widget.

```xml
<ui:button on-click="handleSave" variant="primary">Save</ui:button>
<ui:button type="submit" variant="success">Submit</ui:button>
<ui:button disabled="{!isValid}" variant="danger">Delete</ui:button>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `on-click` | expression | - | Click handler |
| `variant` | enum | - | Style: `primary`, `secondary`, `danger`, `success` |
| `disabled` | boolean | `false` | Disable the button |
| + [Layout Attributes](#layout-attributes) |

---

## Data Display

### ui:text

Text display widget.

```xml
<ui:text size="xl" weight="bold">Title</ui:text>
<ui:text color="muted">Subtitle</ui:text>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `size` | enum | - | Size: `xs`, `sm`, `md`, `lg`, `xl`, `2xl` |
| `weight` | enum | - | Weight: `normal`, `bold`, `light` |
| + [Layout Attributes](#layout-attributes) |

---

### ui:table

Data table widget.

```xml
<ui:table source="{users}">
  <ui:column key="name" label="Name" />
  <ui:column key="email" label="Email" />
  <ui:column key="role" label="Role" align="center" />
</ui:table>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | expression | **required** | Data source binding |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:column`

---

### ui:column

Table column definition.

```xml
<ui:column key="name" label="Name" width="200px" />
<ui:column key="price" label="Price" align="right" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | string | **required** | Data field key |
| `label` | string | - | Column header label |
| `width` | css-size | - | Column width |
| `align` | enum | - | Alignment: `left`, `center`, `right` |

**Parent:** `ui:table`

---

### ui:list

Repeating list widget.

```xml
<ui:list source="{items}" as="item">
  <ui:item>
    <ui:text>{item.name}</ui:text>
  </ui:item>
</ui:list>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | expression | - | Data source binding |
| `as` | string | - | Loop variable name |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:item`

---

### ui:item

List item container.

```xml
<ui:item>
  <ui:hbox justify="between">
    <ui:text>{item.name}</ui:text>
    <ui:badge>{item.status}</ui:badge>
  </ui:hbox>
</ui:item>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

**Parent:** `ui:list`

---

### ui:card

Card container with header, body, and footer sections.

```xml
<ui:card title="Product" subtitle="Electronics" image="/product.jpg">
  <ui:card-body>
    <ui:text>Product description</ui:text>
  </ui:card-body>
  <ui:card-footer>
    <ui:button variant="primary">Buy Now</ui:button>
  </ui:card-footer>
</ui:card>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | - | Card title |
| `subtitle` | string | - | Card subtitle |
| `image` | url | - | Header image |
| `variant` | enum | - | Style: `default`, `elevated`, `outlined` |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:card-header`, `ui:card-body`, `ui:card-footer`

---

### ui:image

Image display widget.

```xml
<ui:image src="/images/logo.png" alt="Logo" width="200px" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `src` | url | **required** | Image source URL |
| `alt` | string | - | Alternative text |
| + [Layout Attributes](#layout-attributes) |

---

### ui:avatar

User avatar with image or initials.

```xml
<ui:avatar src="/user.jpg" name="John Doe" size="lg" status="online" />
<ui:avatar name="Jane Smith" size="md" shape="circle" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `src` | url | - | Image URL |
| `name` | string | - | Name for initials fallback |
| `size` | enum | - | Size: `xs`, `sm`, `md`, `lg`, `xl` |
| `shape` | enum | `circle` | Shape: `circle`, `square` |
| `status` | enum | - | Status indicator: `online`, `offline`, `away`, `busy` |
| + [Layout Attributes](#layout-attributes) |

---

### ui:badge

Small status badge.

```xml
<ui:badge variant="success">Active</ui:badge>
<ui:badge variant="danger">3</ui:badge>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | enum | - | Style: `primary`, `secondary`, `danger`, `success`, `warning` |
| `color` | css-color | - | Custom color |
| + [Layout Attributes](#layout-attributes) |

---

### ui:chart

Simple charts (bar, line, pie).

```xml
<ui:chart type="bar" labels="Jan,Feb,Mar" values="10,20,30" title="Sales" />
<ui:chart type="pie" source="{distributionData}" colors="red,blue,green" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | enum | `bar` | Chart type: `bar`, `line`, `pie`, `doughnut` |
| `source` | expression | - | Data source |
| `labels` | string | - | Comma-separated labels |
| `values` | string | - | Comma-separated values |
| `title` | string | - | Chart title |
| `colors` | string | - | Comma-separated colors |
| + [Layout Attributes](#layout-attributes) |

---

### ui:markdown

Markdown rendered content.

```xml
<ui:markdown>
# Heading

This is **bold** and *italic* text.

- List item 1
- List item 2
</ui:markdown>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

---

## Feedback Components

### ui:alert

Alert/notification box.

```xml
<ui:alert variant="success" dismissible="true">
  Operation completed successfully!
</ui:alert>

<ui:alert variant="danger" title="Error">
  An error occurred while processing your request.
</ui:alert>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | - | Alert title |
| `variant` | enum | `info` | Style: `info`, `success`, `warning`, `danger` |
| `dismissible` | boolean | `false` | Allow dismissing |
| `icon` | string | - | Icon name |
| + [Layout Attributes](#layout-attributes) |

---

### ui:modal

Modal/dialog container.

```xml
<ui:modal title="Confirm" id="confirmModal" size="md">
  <ui:text>Are you sure you want to delete this item?</ui:text>
  <ui:hbox gap="md" justify="end">
    <ui:button on-click="closeModal">Cancel</ui:button>
    <ui:button on-click="confirmDelete" variant="danger">Delete</ui:button>
  </ui:hbox>
</ui:modal>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | - | Modal title |
| `id` | string | - | Modal ID for targeting |
| `open` | boolean | `false` | Initial open state |
| `closable` | boolean | `true` | Show close button |
| `size` | enum | - | Size: `sm`, `md`, `lg`, `xl`, `full` |
| + [Layout Attributes](#layout-attributes) |

---

### ui:tooltip

Tooltip on hover.

```xml
<ui:tooltip content="Click to save" position="bottom">
  <ui:button>Save</ui:button>
</ui:tooltip>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | string | **required** | Tooltip text |
| `position` | enum | `top` | Position: `top`, `bottom`, `left`, `right` |
| + [Layout Attributes](#layout-attributes) |

---

### ui:dropdown

Dropdown menu.

```xml
<ui:dropdown label="Actions" trigger="click" align="left">
  <ui:option label="Edit" on-click="handleEdit" />
  <ui:option label="Duplicate" on-click="handleDuplicate" />
  <ui:option label="Delete" on-click="handleDelete" />
</ui:dropdown>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `label` | string | - | Trigger button label |
| `trigger` | enum | `click` | Trigger mode: `click`, `hover` |
| `align` | enum | `left` | Menu alignment: `left`, `right` |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:option`

---

### ui:progress

Progress bar widget.

```xml
<ui:progress value="{progress}" max="100" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `value` | expression | - | Current value binding |
| `max` | number | `100` | Maximum value |
| + [Layout Attributes](#layout-attributes) |

---

### ui:loading

Loading indicator widget.

```xml
<ui:loading text="Loading data..." />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | - | Loading text |
| + [Layout Attributes](#layout-attributes) |

---

### ui:skeleton

Loading skeleton placeholder.

```xml
<ui:skeleton variant="text" lines="3" />
<ui:skeleton variant="circle" width="48px" height="48px" />
<ui:skeleton variant="card" width="300px" height="200px" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | enum | `text` | Shape: `text`, `circle`, `rect`, `card` |
| `lines` | integer | `1` | Number of lines for text variant |
| `animated` | boolean | `true` | Animate the skeleton |
| + [Layout Attributes](#layout-attributes) |

---

## Navigation

### ui:link

Hyperlink widget.

```xml
<ui:link to="/about">About Us</ui:link>
<ui:link to="https://example.com" external="true">External Site</ui:link>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `to` | url | **required** | Target URL |
| `external` | boolean | `false` | Open in new tab |
| + [Layout Attributes](#layout-attributes) |

---

### ui:breadcrumb

Navigation breadcrumbs.

```xml
<ui:breadcrumb separator="/">
  <ui:breadcrumb-item label="Home" to="/" />
  <ui:breadcrumb-item label="Products" to="/products" />
  <ui:breadcrumb-item label="Details" />
</ui:breadcrumb>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `separator` | string | `/` | Separator character |
| + [Layout Attributes](#layout-attributes) |

**Children:** `ui:breadcrumb-item`

---

### ui:pagination

Pagination controls.

```xml
<ui:pagination total="{totalItems}" pageSize="20" bind="currentPage" on-change="loadPage" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `total` | expression | - | Total items |
| `pageSize` | number | `10` | Items per page |
| `current` | number | `1` | Current page |
| `bind` | expression | - | Binding for current page |
| `on-change` | expression | - | Page change handler |
| `showTotal` | boolean | `false` | Show total count |
| + [Layout Attributes](#layout-attributes) |

---

### ui:header

Page/window header.

```xml
<ui:header title="Dashboard" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | - | Header title |
| + [Layout Attributes](#layout-attributes) |

---

### ui:footer

Page/window footer.

```xml
<ui:footer>
  <ui:text>Copyright 2024</ui:text>
</ui:footer>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| + [Layout Attributes](#layout-attributes) |

---

## Animation

### ui:animate

Animation wrapper container.

```xml
<ui:animate type="fade" duration="300ms" trigger="on-load">
  <ui:panel>Animated content</ui:panel>
</ui:animate>

<ui:animate type="slide-up" delay="200ms" easing="ease-out">
  <ui:card>Slides in from bottom</ui:card>
</ui:animate>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | enum | - | Animation type (see below) |
| `duration` | string | `300ms` | Animation duration |
| `delay` | string | `0ms` | Start delay |
| `easing` | enum | `ease` | Easing: `ease`, `ease-in`, `ease-out`, `ease-in-out`, `linear`, `spring`, `bounce` |
| `repeat` | string | `1` | Repeat count or `infinite` |
| `trigger` | enum | `on-load` | Trigger: `on-load`, `on-hover`, `on-click`, `on-visible`, `none` |
| + [Layout Attributes](#layout-attributes) |

**Animation Types:**
- `fade`, `fade-in`, `fade-out`
- `slide`, `slide-left`, `slide-right`, `slide-up`, `slide-down`
- `scale`, `scale-in`, `scale-out`
- `rotate`
- `bounce`, `pulse`, `shake`

---

## Layout Attributes

These attributes are available on most UI components:

| Attribute | Type | Description |
|-----------|------|-------------|
| `gap` | css-size | Gap between children |
| `padding` | css-size | Inner padding |
| `margin` | css-size | Outer margin |
| `align` | enum | Cross-axis alignment: `start`, `center`, `end`, `stretch` |
| `justify` | enum | Main-axis alignment: `start`, `center`, `end`, `between`, `around` |
| `width` | css-size | Width |
| `height` | css-size | Height |
| `background` | css-color | Background color |
| `color` | css-color | Text color |
| `border` | string | Border style |
| `id` | string | Element ID |
| `class` | string | CSS class(es) |
| `visible` | expression | Visibility binding |

### Size Values

Size attributes accept:
- Pixels: `10px`, `100px`
- Rem: `1rem`, `2rem`
- Percentage: `50%`, `100%`
- Keywords: `auto`, `fill`
- Design tokens: `sm`, `md`, `lg`, `xl`

### Color Values

Color attributes accept:
- Named colors: `red`, `blue`, `green`
- Hex: `#ff0000`, `#00ff00`
- RGB: `rgb(255, 0, 0)`
- Design tokens: `primary`, `secondary`, `danger`, `success`, `warning`, `muted`

---

## Related Documentation

- [Tags Reference (q:)](/api/tags-reference) - Core tags
- [Attributes Reference](/api/attributes-reference) - Common attributes
- [Form Validation](/features/form-validation) - Form validation
- [Animation System](/features/animations) - Animation details
