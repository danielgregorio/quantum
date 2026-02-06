# Theming System

Quantum provides a comprehensive theming system that supports dark/light modes, custom color themes, and runtime theme switching.

## Overview

The theming system is built on CSS custom properties (variables) and integrates with the design tokens system for consistent styling across all targets.

## Basic Usage

### Using Preset Themes

```xml
<q:application id="myapp" type="ui" theme="dark"
               xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">
  <!-- Application content -->
</q:application>
```

### Theme Attribute Values

| Value | Description |
|-------|-------------|
| `light` | Light theme (default) |
| `dark` | Dark theme |
| `system` | Follow system preference |
| `custom` | Use custom theme definition |

## Preset Themes

### Light Theme (Default)

The light theme provides a clean, professional appearance:

```xml
<q:application id="myapp" type="ui" theme="light">
  <ui:window title="Light Theme">
    <ui:vbox padding="lg" gap="md">
      <ui:text size="xl">Light Theme Example</ui:text>
      <ui:button variant="primary">Primary Button</ui:button>
      <ui:card>
        <ui:cardbody>Card content</ui:cardbody>
      </ui:card>
    </ui:vbox>
  </ui:window>
</q:application>
```

### Dark Theme

The dark theme reduces eye strain in low-light environments:

```xml
<q:application id="myapp" type="ui" theme="dark">
  <ui:window title="Dark Theme">
    <ui:vbox padding="lg" gap="md">
      <ui:text size="xl">Dark Theme Example</ui:text>
      <ui:button variant="primary">Primary Button</ui:button>
      <ui:card>
        <ui:cardbody>Card content</ui:cardbody>
      </ui:card>
    </ui:vbox>
  </ui:window>
</q:application>
```

### System Theme

Automatically matches the user's operating system preference:

```xml
<q:application id="myapp" type="ui" theme="system">
  <!-- Automatically uses light or dark based on OS setting -->
</q:application>
```

## Custom Themes

Define your own color schemes using `ui:theme`:

### Basic Custom Theme

```xml
<q:application id="myapp" type="ui">
  <ui:theme>
    <ui:colors>
      <ui:color name="primary" value="#8b5cf6" />
      <ui:color name="secondary" value="#6366f1" />
      <ui:color name="success" value="#10b981" />
      <ui:color name="danger" value="#ef4444" />
      <ui:color name="warning" value="#f59e0b" />
      <ui:color name="info" value="#3b82f6" />
    </ui:colors>
  </ui:theme>

  <ui:window title="Custom Theme">
    <ui:button variant="primary">Purple Primary</ui:button>
  </ui:window>
</q:application>
```

### Complete Custom Theme

```xml
<ui:theme name="corporate">
  <ui:colors>
    <!-- Brand colors -->
    <ui:color name="primary" value="#1e40af" />
    <ui:color name="secondary" value="#475569" />

    <!-- Semantic colors -->
    <ui:color name="success" value="#059669" />
    <ui:color name="danger" value="#dc2626" />
    <ui:color name="warning" value="#d97706" />
    <ui:color name="info" value="#0284c7" />

    <!-- Background/Surface -->
    <ui:color name="background" value="#ffffff" />
    <ui:color name="surface" value="#f8fafc" />

    <!-- Text colors -->
    <ui:color name="text" value="#0f172a" />
    <ui:color name="text-muted" value="#64748b" />

    <!-- Border -->
    <ui:color name="border" value="#e2e8f0" />
  </ui:colors>

  <ui:typography>
    <ui:font name="sans" value="Inter, system-ui, sans-serif" />
    <ui:font name="mono" value="JetBrains Mono, monospace" />
  </ui:typography>

  <ui:spacing>
    <ui:radius value="8px" />
    <ui:shadow value="0 2px 4px rgba(0,0,0,0.1)" />
  </ui:spacing>
</ui:theme>
```

### Dark Variant of Custom Theme

```xml
<ui:theme name="corporate-dark" extends="corporate">
  <ui:colors>
    <ui:color name="background" value="#0f172a" />
    <ui:color name="surface" value="#1e293b" />
    <ui:color name="text" value="#f8fafc" />
    <ui:color name="text-muted" value="#94a3b8" />
    <ui:color name="border" value="#334155" />
  </ui:colors>
</ui:theme>
```

## Runtime Theme Switching

### Toggle Between Themes

```xml
<q:application id="myapp" type="ui">
  <q:set name="currentTheme" value="light" />

  <q:function name="toggleTheme">
    <q:if condition="currentTheme == 'light'">
      <q:set name="currentTheme" value="dark" />
    </q:if>
    <q:else>
      <q:set name="currentTheme" value="light" />
    </q:else>
  </q:function>

  <ui:window theme="{currentTheme}">
    <ui:header>
      <ui:hbox justify="between" padding="md">
        <ui:text weight="bold">My App</ui:text>
        <ui:button variant="ghost" on-click="toggleTheme">
          <ui:icon name="{currentTheme == 'light' ? 'moon' : 'sun'}" />
        </ui:button>
      </ui:hbox>
    </ui:header>

    <ui:vbox padding="lg">
      <ui:text>Current theme: {currentTheme}</ui:text>
    </ui:vbox>
  </ui:window>
</q:application>
```

### Theme Selector

```xml
<q:set name="theme" value="light" persist="local" />

<ui:formitem label="Theme">
  <ui:select bind="theme" on-change="applyTheme">
    <ui:option value="light">Light</ui:option>
    <ui:option value="dark">Dark</ui:option>
    <ui:option value="system">System</ui:option>
  </ui:select>
</ui:formitem>
```

### Persist Theme Preference

```xml
<q:set name="theme" value="light" persist="local" key="user-theme" />

<!-- Theme is automatically saved and restored -->
<ui:window theme="{theme}">
  ...
</ui:window>
```

## CSS Variables Reference

### Color Variables

| Variable | Light Value | Dark Value |
|----------|-------------|------------|
| `--q-primary` | #3b82f6 | #60a5fa |
| `--q-secondary` | #64748b | #94a3b8 |
| `--q-success` | #22c55e | #4ade80 |
| `--q-danger` | #ef4444 | #f87171 |
| `--q-warning` | #f59e0b | #fbbf24 |
| `--q-info` | #06b6d4 | #22d3ee |
| `--q-bg` | #ffffff | #0f172a |
| `--q-text` | #1e293b | #f8fafc |
| `--q-border` | #e2e8f0 | #334155 |

### Typography Variables

| Variable | Description |
|----------|-------------|
| `--q-font-xs` | 0.75rem (12px) |
| `--q-font-sm` | 0.875rem (14px) |
| `--q-font-md` | 1rem (16px) |
| `--q-font-lg` | 1.25rem (20px) |
| `--q-font-xl` | 1.5rem (24px) |
| `--q-font-2xl` | 2rem (32px) |

### Spacing Variables

| Variable | Description |
|----------|-------------|
| `--q-radius` | Border radius (6px) |
| `--q-shadow` | Box shadow |

## Using Theme in Components

### Accessing Theme Colors

Components automatically use theme colors through semantic variants:

```xml
<ui:button variant="primary">Uses --q-primary</ui:button>
<ui:button variant="secondary">Uses --q-secondary</ui:button>
<ui:button variant="success">Uses --q-success</ui:button>
<ui:button variant="danger">Uses --q-danger</ui:button>
```

### Inline Color Overrides

```xml
<ui:text color="primary">Primary colored text</ui:text>
<ui:text color="danger">Danger colored text</ui:text>
<ui:text color="#custom">Custom hex color</ui:text>
```

### Component-Level Theming

Some components accept theme-aware props:

```xml
<ui:card variant="elevated">
  <!-- Automatically adjusts shadow based on theme -->
</ui:card>

<ui:badge variant="success">
  <!-- Uses theme's success color -->
</ui:badge>
```

## Theme-Aware Styling

### Conditional Styles Based on Theme

```xml
<q:set name="isDark" value="{theme == 'dark'}" />

<ui:panel
  background="{isDark ? '#1e293b' : '#ffffff'}"
  border="{isDark ? '#334155' : '#e2e8f0'}"
>
  Content adapts to theme
</ui:panel>
```

### Images for Different Themes

```xml
<ui:image
  src="{theme == 'dark' ? '/logo-dark.svg' : '/logo-light.svg'}"
  alt="Logo"
/>
```

## Cross-Target Theming

### HTML Target

Themes compile to CSS custom properties:

```css
:root {
  --q-primary: #3b82f6;
  --q-bg: #ffffff;
  /* ... */
}

[data-theme="dark"] {
  --q-primary: #60a5fa;
  --q-bg: #0f172a;
  /* ... */
}
```

### Desktop Target

pywebview applications receive the same CSS theming:

```python
# Theme is injected into the HTML
webview.create_window(title, html=themed_html)
```

### Terminal Target

Textual TUI uses theme-mapped colors:

```python
# Quantum themes map to Textual themes
app.theme = "dark"  # Uses Textual dark theme
```

## Complete Theming Example

```xml
<q:application id="themed-app" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <!-- Persisted theme preference -->
  <q:set name="theme" value="light" persist="local" key="app-theme" />
  <q:set name="accentColor" value="blue" persist="local" key="app-accent" />

  <!-- Custom theme with configurable accent -->
  <ui:theme name="custom">
    <ui:colors>
      <ui:color name="primary" value="{getAccentColor(accentColor)}" />
    </ui:colors>
  </ui:theme>

  <q:function name="getAccentColor">
    <q:param name="color" />
    <q:if condition="color == 'blue'">
      <q:return value="#3b82f6" />
    </q:if>
    <q:elseif condition="color == 'purple'">
      <q:return value="#8b5cf6" />
    </q:elseif>
    <q:elseif condition="color == 'green'">
      <q:return value="#22c55e" />
    </q:elseif>
    <q:else>
      <q:return value="#3b82f6" />
    </q:else>
  </q:function>

  <q:function name="setTheme">
    <q:param name="newTheme" />
    <q:set name="theme" value="{newTheme}" />
  </q:function>

  <ui:window theme="{theme}" title="Themed Application">
    <ui:vbox padding="lg" gap="lg">

      <ui:panel title="Theme Settings">
        <ui:vbox gap="md">

          <ui:formitem label="Color Scheme">
            <ui:hbox gap="sm">
              <ui:button
                variant="{theme == 'light' ? 'primary' : 'ghost'}"
                on-click="setTheme('light')"
              >
                <ui:icon name="sun" /> Light
              </ui:button>
              <ui:button
                variant="{theme == 'dark' ? 'primary' : 'ghost'}"
                on-click="setTheme('dark')"
              >
                <ui:icon name="moon" /> Dark
              </ui:button>
              <ui:button
                variant="{theme == 'system' ? 'primary' : 'ghost'}"
                on-click="setTheme('system')"
              >
                <ui:icon name="monitor" /> System
              </ui:button>
            </ui:hbox>
          </ui:formitem>

          <ui:formitem label="Accent Color">
            <ui:hbox gap="sm">
              <ui:button
                variant="{accentColor == 'blue' ? 'primary' : 'ghost'}"
                on-click="setAccent('blue')"
              >
                Blue
              </ui:button>
              <ui:button
                variant="{accentColor == 'purple' ? 'primary' : 'ghost'}"
                on-click="setAccent('purple')"
              >
                Purple
              </ui:button>
              <ui:button
                variant="{accentColor == 'green' ? 'primary' : 'ghost'}"
                on-click="setAccent('green')"
              >
                Green
              </ui:button>
            </ui:hbox>
          </ui:formitem>

        </ui:vbox>
      </ui:panel>

      <ui:panel title="Preview">
        <ui:vbox gap="md">
          <ui:hbox gap="sm">
            <ui:button variant="primary">Primary</ui:button>
            <ui:button variant="secondary">Secondary</ui:button>
            <ui:button variant="success">Success</ui:button>
            <ui:button variant="danger">Danger</ui:button>
          </ui:hbox>

          <ui:hbox gap="sm">
            <ui:badge variant="primary">Badge</ui:badge>
            <ui:badge variant="success">Active</ui:badge>
            <ui:badge variant="warning">Pending</ui:badge>
          </ui:hbox>

          <ui:alert variant="info">
            This is how alerts look with the current theme.
          </ui:alert>
        </ui:vbox>
      </ui:panel>

    </ui:vbox>
  </ui:window>

</q:application>
```

## Best Practices

1. **Use semantic color names** - Prefer `variant="primary"` over `color="#3b82f6"`
2. **Test both themes** - Always verify your UI in light and dark modes
3. **Persist user preference** - Save theme choice with `persist="local"`
4. **Support system preference** - Offer `theme="system"` option
5. **Ensure contrast** - Verify text readability in both themes
6. **Use theme-aware images** - Provide light/dark versions of logos

## Related Documentation

- [UI Engine Overview](/ui/overview) - Component styling
- [Design Tokens](/ui/overview#design-tokens) - Spacing and sizing
- [State Persistence](/features/state-persistence) - Saving preferences
