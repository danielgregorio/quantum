# Attributes Reference

Complete reference for common attributes used across Quantum tags. This document covers layout, style, event, and binding attributes.

## Layout Attributes

Layout attributes control positioning, spacing, and sizing of elements.

### Spacing

#### gap

Space between child elements in flex/grid containers.

```xml
<ui:vbox gap="md">...</ui:vbox>
<ui:hbox gap="16px">...</ui:hbox>
<ui:grid gap="1rem">...</ui:grid>
```

| Value | Size |
|-------|------|
| `xs` | 4px |
| `sm` | 8px |
| `md` | 16px |
| `lg` | 24px |
| `xl` | 32px |
| `2xl` | 48px |
| Custom | `10px`, `1rem`, `2em` |

#### padding

Inner spacing (space between content and border).

```xml
<ui:panel padding="lg">...</ui:panel>
<ui:card padding="24px">...</ui:card>
```

Supports the same values as `gap`, plus shorthand:

```xml
<!-- All sides -->
<ui:panel padding="md" />

<!-- Vertical | Horizontal -->
<ui:panel padding="sm md" />

<!-- Top | Horizontal | Bottom -->
<ui:panel padding="sm md lg" />

<!-- Top | Right | Bottom | Left -->
<ui:panel padding="8px 16px 8px 16px" />
```

#### margin

Outer spacing (space outside the border).

```xml
<ui:card margin="lg">...</ui:card>
<ui:button margin="0 8px">Button</ui:button>
```

Supports the same values and shorthand as `padding`.

---

### Sizing

#### width

Element width.

```xml
<ui:panel width="300px">...</ui:panel>
<ui:input width="100%" />
<ui:button width="fill">Full Width</ui:button>
```

| Value | Description |
|-------|-------------|
| `auto` | Content-based width |
| `fill` | Fill available space |
| Pixels | `100px`, `250px` |
| Percentage | `50%`, `100%` |
| Rem/Em | `20rem`, `15em` |
| Viewport | `50vw`, `100vw` |

#### height

Element height.

```xml
<ui:panel height="200px">...</ui:panel>
<ui:image height="auto" />
```

Supports the same values as `width`.

#### min-width / max-width

Minimum and maximum width constraints.

```xml
<ui:panel min-width="200px" max-width="800px">...</ui:panel>
```

#### min-height / max-height

Minimum and maximum height constraints.

```xml
<ui:vbox min-height="100vh" max-height="500px">...</ui:vbox>
```

---

### Alignment

#### align

Cross-axis alignment (perpendicular to main axis).

```xml
<!-- Vertical alignment in hbox -->
<ui:hbox align="center">
  <ui:text>Vertically centered</ui:text>
</ui:hbox>

<!-- Horizontal alignment in vbox -->
<ui:vbox align="end">
  <ui:button>Right-aligned</ui:button>
</ui:vbox>
```

| Value | Description |
|-------|-------------|
| `start` | Align to start (top/left) |
| `center` | Center alignment |
| `end` | Align to end (bottom/right) |
| `stretch` | Stretch to fill |

#### justify

Main-axis alignment (direction of layout).

```xml
<!-- Horizontal distribution in hbox -->
<ui:hbox justify="between">
  <ui:text>Left</ui:text>
  <ui:text>Right</ui:text>
</ui:hbox>

<!-- Vertical distribution in vbox -->
<ui:vbox justify="center">
  <ui:text>Vertically centered</ui:text>
</ui:vbox>
```

| Value | Description |
|-------|-------------|
| `start` | Pack items at start |
| `center` | Pack items at center |
| `end` | Pack items at end |
| `between` | Distribute with space between |
| `around` | Distribute with space around |

---

## Style Attributes

### Colors

#### background

Background color of an element.

```xml
<ui:panel background="primary">...</ui:panel>
<ui:vbox background="#f5f5f5">...</ui:vbox>
<ui:card background="rgb(240, 240, 240)">...</ui:card>
```

| Token | Description |
|-------|-------------|
| `primary` | Primary brand color |
| `secondary` | Secondary color |
| `success` | Success/positive color |
| `danger` | Error/negative color |
| `warning` | Warning color |
| `info` | Information color |
| `muted` | Muted/subtle color |
| `surface` | Surface background |
| `background` | Page background |

Custom values:
- Named: `red`, `blue`, `white`
- Hex: `#ff0000`, `#333`
- RGB: `rgb(255, 0, 0)`
- RGBA: `rgba(0, 0, 0, 0.5)`
- HSL: `hsl(120, 100%, 50%)`

#### color

Text/foreground color.

```xml
<ui:text color="primary">Primary text</ui:text>
<ui:text color="muted">Subtle text</ui:text>
<ui:text color="#666">Gray text</ui:text>
```

Supports the same values as `background`.

---

### Borders

#### border

Border style shorthand.

```xml
<ui:panel border="1px solid #ccc">...</ui:panel>
<ui:card border="2px solid primary">...</ui:card>
```

Format: `[width] [style] [color]`

Styles: `solid`, `dashed`, `dotted`, `double`, `none`

#### border-radius

Corner rounding.

```xml
<ui:card border-radius="8px">...</ui:card>
<ui:avatar border-radius="50%">...</ui:avatar>
```

| Token | Size |
|-------|------|
| `sm` | 4px |
| `md` | 8px |
| `lg` | 12px |
| `xl` | 16px |
| `full` | 9999px (pill shape) |

---

### Shadows

#### shadow

Box shadow effect.

```xml
<ui:card shadow="md">...</ui:card>
<ui:panel shadow="lg">...</ui:panel>
```

| Token | Description |
|-------|-------------|
| `none` | No shadow |
| `sm` | Small subtle shadow |
| `md` | Medium shadow |
| `lg` | Large shadow |
| `xl` | Extra large shadow |

---

## Event Attributes

Event attributes bind user interactions to handlers.

### Mouse Events

#### on-click

Triggered when element is clicked.

```xml
<ui:button on-click="handleClick">Click Me</ui:button>
<ui:button on-click="saveItem(item.id)">Save</ui:button>
```

#### on-double-click

Triggered on double-click.

```xml
<ui:item on-double-click="openEditor">Double-click to edit</ui:item>
```

#### on-hover / on-mouse-enter / on-mouse-leave

Mouse hover events.

```xml
<ui:card on-mouse-enter="showPreview" on-mouse-leave="hidePreview">
  Hover for preview
</ui:card>
```

---

### Form Events

#### on-submit

Triggered when form is submitted.

```xml
<ui:form on-submit="handleSubmit">
  <ui:button type="submit">Submit</ui:button>
</ui:form>
```

#### on-change

Triggered when input value changes (on blur).

```xml
<ui:input bind="email" on-change="validateEmail" />
<ui:select bind="country" on-change="loadCities" />
```

#### on-input

Triggered on every input keystroke (real-time).

```xml
<ui:input bind="search" on-input="performSearch" />
```

#### on-focus / on-blur

Focus and blur events.

```xml
<ui:input
  on-focus="showSuggestions"
  on-blur="hideSuggestions"
/>
```

---

### Keyboard Events

#### on-keydown / on-keyup / on-keypress

Keyboard events.

```xml
<ui:input on-keydown="handleKeyDown" />
<ui:input on-keyup="handleKeyUp" />
```

#### on-enter

Triggered when Enter key is pressed.

```xml
<ui:input bind="message" on-enter="sendMessage" />
```

#### on-escape

Triggered when Escape key is pressed.

```xml
<ui:modal on-escape="closeModal">...</ui:modal>
```

---

### Custom Events

#### on-{eventName}

Listen to custom events.

```xml
<ui:panel on-resize="handleResize">...</ui:panel>
<CustomComponent on-itemSelected="handleSelection" />
```

---

## Binding Attributes

### bind

Two-way data binding between a variable and an input.

```xml
<q:set name="username" value="" />
<ui:input bind="username" />

<!-- Nested binding -->
<q:set name="user" type="struct" value='{"name": "", "email": ""}' />
<ui:input bind="user.name" />
<ui:input bind="user.email" />
```

Changes in the input automatically update the variable, and changes to the variable update the input.

### value

One-way binding (read-only).

```xml
<ui:text value="{user.name}" />
<ui:progress value="{downloadProgress}" />
```

### visible

Conditional visibility.

```xml
<ui:panel visible="{isLoggedIn}">
  Welcome back!
</ui:panel>

<ui:alert visible="{errors.length > 0}" variant="danger">
  There are errors
</ui:alert>
```

### disabled

Disable interactive elements.

```xml
<ui:button disabled="{isSubmitting}">Submit</ui:button>
<ui:input disabled="{!canEdit}" />
```

---

## Identification Attributes

### id

Unique element identifier.

```xml
<ui:panel id="settings-panel">...</ui:panel>
<ui:modal id="confirm-dialog">...</ui:modal>
```

Used for:
- Targeting modals: `openModal('confirm-dialog')`
- Form labels: `for="field-id"`
- JavaScript access
- CSS styling

### class

CSS class names.

```xml
<ui:card class="product-card featured">...</ui:card>
<ui:text class="highlight">Important</ui:text>
```

Multiple classes separated by spaces.

### data-*

Custom data attributes.

```xml
<ui:button data-action="delete" data-id="{item.id}">
  Delete
</ui:button>
```

---

## Accessibility Attributes

### aria-label

Accessible label for screen readers.

```xml
<ui:button aria-label="Close dialog" on-click="closeModal">
  X
</ui:button>
```

### aria-describedby

Reference to element with description.

```xml
<ui:input bind="password" aria-describedby="password-hint" />
<ui:text id="password-hint">Must be at least 8 characters</ui:text>
```

### role

ARIA role for semantics.

```xml
<ui:panel role="navigation">...</ui:panel>
<ui:vbox role="main">...</ui:vbox>
```

### tabindex

Keyboard navigation order.

```xml
<ui:panel tabindex="0">Focusable panel</ui:panel>
<ui:button tabindex="-1">Skip in tab order</ui:button>
```

---

## Responsive Attributes

### Breakpoint Modifiers

Apply different values at different screen sizes.

```xml
<ui:grid columns="1" columns-md="2" columns-lg="3">
  <!-- 1 column on mobile, 2 on tablet, 3 on desktop -->
</ui:grid>

<ui:panel padding="sm" padding-lg="xl">
  <!-- Small padding on mobile, extra large on desktop -->
</ui:panel>
```

| Breakpoint | Min Width |
|------------|-----------|
| (default) | 0px |
| `-sm` | 640px |
| `-md` | 768px |
| `-lg` | 1024px |
| `-xl` | 1280px |
| `-2xl` | 1536px |

---

## Animation Attributes

### animate

Apply entrance animation.

```xml
<ui:card animate="fade">Fades in</ui:card>
<ui:panel animate="slide-up">Slides up</ui:panel>
```

### transition

Apply hover/state transitions.

```xml
<ui:button transition="scale:1.05:150ms">
  Scales on hover
</ui:button>

<ui:card transition="lift:-4px:200ms">
  Lifts on hover
</ui:card>
```

Format: `type:value:duration`

---

## Expression Syntax

Attributes that accept expressions use curly braces for databinding:

### Simple Variables

```xml
<ui:text>{username}</ui:text>
<ui:input value="{email}" />
```

### Object Properties

```xml
<ui:text>{user.name}</ui:text>
<ui:text>{order.items[0].name}</ui:text>
```

### Expressions

```xml
<ui:text>{firstName + ' ' + lastName}</ui:text>
<ui:text>{price * quantity}</ui:text>
<ui:text>{items.length}</ui:text>
```

### Ternary Conditions

```xml
<ui:text>{isAdmin ? 'Admin' : 'User'}</ui:text>
<ui:badge variant="{status == 'active' ? 'success' : 'danger'}">{status}</ui:badge>
```

### Function Calls

```xml
<ui:text>{formatDate(createdAt)}</ui:text>
<ui:text>{price.toFixed(2)}</ui:text>
<ui:text>{name.toUpperCase()}</ui:text>
```

---

## Attribute Type Reference

### css-size

CSS size values:
- Pixels: `10px`, `100px`
- Rem: `1rem`, `2rem`
- Em: `1em`, `2em`
- Percentage: `50%`, `100%`
- Viewport: `100vw`, `50vh`
- Tokens: `xs`, `sm`, `md`, `lg`, `xl`, `2xl`
- Keywords: `auto`, `fill`

### css-color

CSS color values:
- Named: `red`, `blue`, `white`
- Hex: `#ff0000`, `#333`
- RGB: `rgb(255, 0, 0)`
- RGBA: `rgba(0, 0, 0, 0.5)`
- HSL: `hsl(120, 100%, 50%)`
- Tokens: `primary`, `secondary`, `success`, `danger`, `warning`, `muted`

### expression

Databinding expression:
- Variables: `{myVar}`
- Properties: `{obj.prop}`
- Computed: `{a + b}`
- Functions: `{fn()}`

### enum

Fixed set of allowed values (specified per attribute).

### boolean

Boolean values: `true`, `false`

### string

Plain text string.

### integer

Whole number: `0`, `1`, `100`

### number

Number with decimals: `0.5`, `3.14`

### url

URL or path: `https://example.com`, `/images/logo.png`

### regex

Regular expression pattern: `^[a-z]+$`, `\d{3}-\d{4}`

---

## Related Documentation

- [Tags Reference (q:)](/api/tags-reference) - Core tags
- [UI Tags Reference (ui:)](/api/ui-reference) - UI component tags
- [State Management](/guide/state-management) - Variable binding
- [Databinding](/guide/databinding) - Expression syntax
