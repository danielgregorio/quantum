# HTML Target

The HTML target generates standalone web pages from Quantum UI applications. It produces clean, semantic HTML5 with embedded CSS and JavaScript that works in any modern browser.

## Overview

When you build a Quantum UI application with `--target html`, the framework:

1. Parses your `.q` file and extracts UI components
2. Transforms `ui:*` elements into semantic HTML5
3. Generates CSS from design tokens and layout attributes
4. Adds JavaScript for interactivity (tabs, validation, animations)
5. Outputs a single self-contained HTML file

## Building for HTML

```bash
# Build UI application to HTML
python src/cli/runner.py run myapp.q --target html

# Output is saved as {app_id}.html in current directory
```

## Generated Output Structure

The HTML adapter produces a complete HTML5 document:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My App</title>
  <style>
    /* CSS Reset */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    /* Theme Variables */
    :root {
      --q-primary: #3b82f6;
      --q-secondary: #64748b;
      --q-success: #22c55e;
      /* ... more tokens */
    }

    /* Component Styles */
    .q-window { width: 100%; min-height: 100vh; }
    .q-btn { /* button styles */ }
    /* ... more components */
  </style>
</head>
<body>
  <!-- Generated UI -->
  <div class="q-window">
    <div style="display: flex; flex-direction: column; padding: 24px; gap: 16px;">
      <span style="font-size: 2rem; font-weight: bold;">Welcome!</span>
      <button class="q-btn q-btn-primary">Click Me</button>
    </div>
  </div>

  <script>
    /* Tab switching, form validation, animations */
  </script>
</body>
</html>
```

## Component Mapping

UI components are transformed to semantic HTML elements:

| Quantum Component | HTML Output |
|-------------------|-------------|
| `ui:window` | `<div class="q-window">` |
| `ui:hbox` | `<div style="display: flex; flex-direction: row">` |
| `ui:vbox` | `<div style="display: flex; flex-direction: column">` |
| `ui:text` | `<span>` |
| `ui:button` | `<button class="q-btn">` |
| `ui:input` | `<input class="q-input">` |
| `ui:form` | `<form class="q-form">` |
| `ui:table` | `<table class="q-table">` |
| `ui:panel` | `<div class="q-panel">` |
| `ui:tabs` | `<div class="q-tabs">` with tab JavaScript |
| `ui:modal` | `<div class="q-modal-overlay">` |
| `ui:card` | `<div class="q-card">` |
| `ui:alert` | `<div class="q-alert" role="alert">` |

## CSS Generation

### Design Token Translation

Design tokens are converted to CSS custom properties:

```xml
<ui:vbox padding="lg" gap="md">
```

Becomes:

```html
<div style="display: flex; flex-direction: column; padding: 24px; gap: 16px;">
```

Token mappings:

| Token | CSS Value |
|-------|-----------|
| `xs` | 4px |
| `sm` | 8px |
| `md` | 16px |
| `lg` | 24px |
| `xl` | 32px |
| `2xl` | 48px |

### Color Tokens

```xml
<ui:button variant="primary">Submit</ui:button>
<ui:alert variant="danger">Error occurred</ui:alert>
```

Colors use CSS variables:

```css
:root {
  --q-primary: #3b82f6;
  --q-secondary: #64748b;
  --q-success: #22c55e;
  --q-danger: #ef4444;
  --q-warning: #f59e0b;
  --q-info: #06b6d4;
}

.q-btn-primary { background: var(--q-primary); color: white; }
.q-alert-danger { background: var(--q-danger); color: white; }
```

### Typography

```xml
<ui:text size="2xl" weight="bold">Large Heading</ui:text>
<ui:text size="sm">Small text</ui:text>
```

Font sizes:

| Token | CSS Value |
|-------|-----------|
| `xs` | 0.75rem (12px) |
| `sm` | 0.875rem (14px) |
| `md` | 1rem (16px) |
| `lg` | 1.25rem (20px) |
| `xl` | 1.5rem (24px) |
| `2xl` | 2rem (32px) |

## JavaScript Features

### Tab Navigation

When using `ui:tabs`, the adapter generates JavaScript for tab switching:

```xml
<ui:tabs>
  <ui:tab title="Tab 1">Content 1</ui:tab>
  <ui:tab title="Tab 2">Content 2</ui:tab>
</ui:tabs>
```

Generated JavaScript handles:
- Active tab state
- Click event listeners
- Showing/hiding tab content

### Form Validation

Client-side validation is added automatically when using validation attributes:

```xml
<ui:form on-submit="handleSubmit" validation-mode="client">
  <ui:input bind="email" required="true" validate="email" />
  <ui:input bind="password" minlength="8" />
  <ui:button type="submit">Submit</ui:button>
</ui:form>
```

The adapter generates:
- HTML5 validation attributes
- Custom JavaScript validators
- Error message display

### Animations

When using `ui:animate` or animation attributes:

```xml
<ui:animate type="fade" trigger="on-load" duration="300">
  <ui:card>Animated content</ui:card>
</ui:animate>
```

CSS animations are generated:

```css
.q-animate { animation-duration: var(--q-anim-duration); }
.q-anim-fade { animation-name: q-fade; }

@keyframes q-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

### State Persistence

Variables with `persist` attribute are saved to localStorage:

```xml
<q:set name="theme" value="dark" persist="local" />
```

JavaScript handles:
- Saving state to localStorage
- Restoring state on page load
- TTL expiration

## Responsive Design

### Viewport Meta Tag

The generated HTML includes a responsive viewport:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

### Flexible Layouts

Flexbox layouts adapt to screen size:

```xml
<ui:hbox gap="md">
  <ui:panel width="1/3">Sidebar</ui:panel>
  <ui:panel width="2/3">Main</ui:panel>
</ui:hbox>
```

Fractional widths use percentages for responsiveness.

### CSS Grid

```xml
<ui:grid columns="3" gap="md">
  <ui:card>Item 1</ui:card>
  <ui:card>Item 2</ui:card>
  <ui:card>Item 3</ui:card>
</ui:grid>
```

Generates CSS Grid for responsive layouts.

## SEO Considerations

### Semantic HTML

The adapter generates semantic elements:
- `<header>` for `ui:header`
- `<footer>` for `ui:footer`
- `<nav>` for `ui:menu` and `ui:breadcrumb`
- `<table>` for `ui:table`
- Proper heading hierarchy

### Accessibility

- ARIA roles on interactive elements
- `role="alert"` on `ui:alert`
- `role="dialog"` on `ui:modal`
- Proper button types
- Label associations

### Document Structure

```html
<title>App Title</title>
<!-- Generated from ui:window title attribute -->
```

## Theming

### Theme Configuration

```xml
<ui:theme preset="dark" auto-switch="true">
  <ui:color name="primary" value="#8b5cf6" />
</ui:theme>
```

Generates theme CSS with color overrides and optional auto-switching based on system preferences.

### Theme Presets

- `light` - Default light theme
- `dark` - Dark mode
- `system` - Follows OS preference

## Example

### Input

```xml
<q:application id="myapp" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <ui:window title="My App">
    <ui:vbox padding="lg" gap="md">
      <ui:text size="2xl" weight="bold">Welcome!</ui:text>

      <ui:form on-submit="handleSubmit">
        <ui:formitem label="Email">
          <ui:input bind="email" type="email" required="true" />
        </ui:formitem>
        <ui:button variant="primary">Submit</ui:button>
      </ui:form>
    </ui:vbox>
  </ui:window>

</q:application>
```

### Output

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My App</title>
  <style>
    /* Reset + Theme + Components */
  </style>
</head>
<body>
  <div class="q-window">
    <div style="display: flex; flex-direction: column; padding: 24px; gap: 16px;">
      <span style="font-size: 2rem; font-weight: bold;">Welcome!</span>
      <form class="q-form" novalidate data-validation="client">
        <div class="q-formitem">
          <label class="q-formitem-label">Email</label>
          <input class="q-input" type="email" name="email" required />
        </div>
        <button class="q-btn q-btn-primary">Submit</button>
      </form>
    </div>
  </div>
</body>
</html>
```

## Best Practices

1. **Use semantic components** - Choose `ui:header`, `ui:footer`, `ui:nav` for better SEO
2. **Design tokens over inline styles** - Use `padding="lg"` not `padding="24px"`
3. **Leverage validation** - Use built-in form validation for better UX
4. **Test responsiveness** - Check layouts on different screen sizes
5. **Consider bundle size** - Keep components minimal for faster loading

## Related

- [Desktop Target](/targets/desktop) - Native desktop apps
- [Mobile Target](/targets/mobile) - React Native apps
- [Terminal Target](/targets/terminal) - TUI applications
- [Design Tokens](/ui-engine/design-tokens) - Token reference
