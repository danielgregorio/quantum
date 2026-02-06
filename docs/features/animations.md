# Animation System

Quantum provides a declarative animation system with support for various animation types, triggers, and easing functions.

## Overview

The animation system allows you to add motion and transitions to UI components using the `ui:animate` component or animation attributes.

## Basic Usage

### Using Animation Attributes

Add animations directly to components:

```xml
<ui:card animate="fade" duration="300ms">
  <ui:text>This card fades in on load</ui:text>
</ui:card>
```

### Using ui:animate Wrapper

Wrap components for more control:

```xml
<ui:animate type="slide-up" duration="500ms" delay="100ms">
  <ui:panel title="Animated Panel">
    <ui:text>Content slides up</ui:text>
  </ui:panel>
</ui:animate>
```

## Animation Types

### Fade Animations

```xml
<!-- Fade in (default) -->
<ui:animate type="fade">
  <ui:text>Fades in</ui:text>
</ui:animate>

<!-- Fade out -->
<ui:animate type="fade-out">
  <ui:text>Fades out</ui:text>
</ui:animate>
```

### Slide Animations

```xml
<!-- Slide from left -->
<ui:animate type="slide-left">
  <ui:card>Slides from left</ui:card>
</ui:animate>

<!-- Slide from right -->
<ui:animate type="slide-right">
  <ui:card>Slides from right</ui:card>
</ui:animate>

<!-- Slide from top -->
<ui:animate type="slide-down">
  <ui:card>Slides from top</ui:card>
</ui:animate>

<!-- Slide from bottom -->
<ui:animate type="slide-up">
  <ui:card>Slides from bottom</ui:card>
</ui:animate>
```

### Scale Animations

```xml
<!-- Scale in (grow from center) -->
<ui:animate type="scale">
  <ui:card>Scales in</ui:card>
</ui:animate>

<!-- Scale out -->
<ui:animate type="scale-out">
  <ui:card>Scales out</ui:card>
</ui:animate>
```

### Rotate Animations

```xml
<!-- Rotate in -->
<ui:animate type="rotate">
  <ui:icon name="settings" size="xl" />
</ui:animate>

<!-- Continuous rotation -->
<ui:animate type="rotate" repeat="infinite">
  <ui:loading />
</ui:animate>
```

### Bounce Animation

```xml
<ui:animate type="bounce">
  <ui:badge variant="danger">New!</ui:badge>
</ui:animate>
```

### Pulse Animation

```xml
<ui:animate type="pulse">
  <ui:button variant="primary">Click Me</ui:button>
</ui:animate>
```

### Shake Animation

```xml
<ui:animate type="shake" trigger="on-error">
  <ui:input bind="email" />
</ui:animate>
```

## Animation Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | "fade" | Animation type |
| `duration` | string | "300ms" | Animation duration |
| `delay` | string | "0ms" | Start delay |
| `easing` | string | "ease" | Timing function |
| `repeat` | number/string | 1 | Repeat count or "infinite" |
| `direction` | string | "normal" | Direction (normal, reverse, alternate) |
| `trigger` | string | "on-load" | When to play |
| `fill` | string | "both" | Fill mode (none, forwards, backwards, both) |

## Animation Triggers

### On Load (Default)

Animation plays when element enters the DOM:

```xml
<ui:animate type="fade" trigger="on-load">
  <ui:text>Animates immediately</ui:text>
</ui:animate>
```

### On Hover

Animation plays on mouse hover:

```xml
<ui:animate type="scale" trigger="on-hover">
  <ui:card hoverable="true">
    <ui:text>Hover to scale</ui:text>
  </ui:card>
</ui:animate>
```

### On Click

Animation plays when clicked:

```xml
<ui:animate type="pulse" trigger="on-click">
  <ui:button>Click to pulse</ui:button>
</ui:animate>
```

### On Visible

Animation plays when element becomes visible (IntersectionObserver):

```xml
<ui:animate type="slide-up" trigger="on-visible">
  <ui:card>
    <ui:text>Animates when scrolled into view</ui:text>
  </ui:card>
</ui:animate>
```

### On State Change

Trigger animation based on state:

```xml
<q:set name="showContent" value="false" />

<ui:button on-click="toggleContent">Toggle</ui:button>

<q:if condition="showContent">
  <ui:animate type="fade" trigger="on-load">
    <ui:panel>Animated content</ui:panel>
  </ui:animate>
</q:if>
```

## Easing Functions

### Built-in Easing

```xml
<ui:animate easing="linear">...</ui:animate>
<ui:animate easing="ease">...</ui:animate>
<ui:animate easing="ease-in">...</ui:animate>
<ui:animate easing="ease-out">...</ui:animate>
<ui:animate easing="ease-in-out">...</ui:animate>
```

### Special Easing

```xml
<!-- Spring effect -->
<ui:animate easing="spring">
  <ui:card>Bouncy spring</ui:card>
</ui:animate>

<!-- Bounce effect -->
<ui:animate easing="bounce">
  <ui:badge>Bouncy badge</ui:badge>
</ui:animate>
```

### Custom Cubic Bezier

```xml
<ui:animate easing="cubic-bezier(0.68, -0.55, 0.265, 1.55)">
  <ui:card>Custom easing</ui:card>
</ui:animate>
```

## Staggered Animations

Animate list items with delay:

```xml
<ui:vbox gap="sm">
  <q:loop type="array" var="item" index="i" items="{items}">
    <ui:animate type="slide-up" delay="{i * 100}ms">
      <ui:card>
        <ui:text>{item.name}</ui:text>
      </ui:card>
    </ui:animate>
  </q:loop>
</ui:vbox>
```

## Transition Effects

For hover/active state transitions:

### Button Transitions

```xml
<ui:button transition="scale:1.05:150ms">
  Scales on hover
</ui:button>

<ui:button transition="lift:-2px:150ms">
  Lifts on hover
</ui:button>
```

### Card Transitions

```xml
<ui:card transition="scale:1.02:200ms">
  <ui:text>Card scales slightly on hover</ui:text>
</ui:card>
```

### Transition Types

| Type | Description | Example |
|------|-------------|---------|
| `scale` | Scale transform | `scale:1.05:150ms` |
| `lift` | Y translation | `lift:-4px:200ms` |
| `fade` | Opacity change | `fade:0.8:150ms` |

## Combining Animations

### Sequential Animations

```xml
<ui:animate type="fade" duration="300ms">
  <ui:animate type="slide-up" duration="300ms" delay="300ms">
    <ui:card>Fades then slides</ui:card>
  </ui:animate>
</ui:animate>
```

### Multiple Properties

```xml
<ui:animate type="fade,scale" duration="400ms">
  <ui:card>Fades and scales together</ui:card>
</ui:animate>
```

## Controlling Animations

### Play/Pause with State

```xml
<q:set name="isPlaying" value="true" />

<ui:animate type="rotate" repeat="infinite" playing="{isPlaying}">
  <ui:icon name="loading" />
</ui:animate>

<ui:button on-click="toggleAnimation">
  {isPlaying ? 'Pause' : 'Play'}
</ui:button>
```

### Programmatic Control

```xml
<q:set name="animationKey" value="0" />

<q:function name="replayAnimation">
  <q:set name="animationKey" value="{animationKey + 1}" />
</q:function>

<ui:animate type="bounce" key="{animationKey}">
  <ui:badge>Animates</ui:badge>
</ui:animate>

<ui:button on-click="replayAnimation">Replay</ui:button>
```

## Page Transitions

### Route Transitions

```xml
<q:application id="myapp" type="ui">
  <ui:router>
    <ui:route path="/" transition="fade">
      <HomePage />
    </ui:route>
    <ui:route path="/about" transition="slide-left">
      <AboutPage />
    </ui:route>
  </ui:router>
</q:application>
```

## Accessibility

### Respecting Motion Preferences

Animations automatically respect `prefers-reduced-motion`:

```xml
<!-- Animation is disabled for users who prefer reduced motion -->
<ui:animate type="bounce">
  <ui:badge>Badge</ui:badge>
</ui:animate>
```

### Manual Motion Control

```xml
<ui:animate type="slide-up" reducedMotion="fade">
  <!-- Uses fade instead of slide for reduced motion preference -->
  <ui:card>Content</ui:card>
</ui:animate>
```

## Complete Animation Example

```xml
<q:application id="animation-demo" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="showModal" value="false" />
  <q:set name="items" value='["Item 1", "Item 2", "Item 3", "Item 4"]' />

  <ui:window title="Animation Demo">
    <ui:vbox padding="lg" gap="lg">

      <!-- Header with fade animation -->
      <ui:animate type="fade" duration="500ms">
        <ui:text size="2xl" weight="bold">Animation Examples</ui:text>
      </ui:animate>

      <!-- Cards with staggered slide animation -->
      <ui:grid columns="2" gap="md">
        <q:loop type="array" var="item" index="i" items="{items}">
          <ui:animate type="slide-up" delay="{i * 100}ms" trigger="on-visible">
            <ui:card hoverable="true" transition="lift:-4px:200ms">
              <ui:cardbody>
                <ui:text weight="bold">{item}</ui:text>
                <ui:text color="muted">Card {i + 1}</ui:text>
              </ui:cardbody>
            </ui:card>
          </ui:animate>
        </q:loop>
      </ui:grid>

      <!-- Interactive animations -->
      <ui:panel title="Interactive">
        <ui:hbox gap="md">
          <!-- Hover animation -->
          <ui:animate type="scale" trigger="on-hover">
            <ui:button variant="primary">Hover to Scale</ui:button>
          </ui:animate>

          <!-- Click animation -->
          <ui:animate type="pulse" trigger="on-click">
            <ui:button variant="secondary">Click to Pulse</ui:button>
          </ui:animate>

          <!-- Shake on error simulation -->
          <ui:animate type="shake" trigger="on-click">
            <ui:button variant="danger">Click to Shake</ui:button>
          </ui:animate>
        </ui:hbox>
      </ui:panel>

      <!-- Loading spinner with continuous animation -->
      <ui:panel title="Continuous Animations">
        <ui:hbox gap="xl" align="center">
          <ui:vbox align="center" gap="sm">
            <ui:animate type="rotate" repeat="infinite" duration="1s" easing="linear">
              <ui:icon name="loader" size="xl" />
            </ui:animate>
            <ui:text size="sm">Spinning</ui:text>
          </ui:vbox>

          <ui:vbox align="center" gap="sm">
            <ui:animate type="pulse" repeat="infinite" duration="1s">
              <ui:badge variant="success" size="lg">Live</ui:badge>
            </ui:animate>
            <ui:text size="sm">Pulsing</ui:text>
          </ui:vbox>

          <ui:vbox align="center" gap="sm">
            <ui:animate type="bounce" repeat="infinite" duration="1s">
              <ui:icon name="arrow-down" size="xl" />
            </ui:animate>
            <ui:text size="sm">Bouncing</ui:text>
          </ui:vbox>
        </ui:hbox>
      </ui:panel>

      <!-- Modal with animation -->
      <ui:button variant="primary" on-click="openModal">
        Open Animated Modal
      </ui:button>

      <ui:modal open="{showModal}" on-close="closeModal" title="Animated Modal">
        <ui:animate type="scale" duration="300ms">
          <ui:vbox gap="md">
            <ui:text>This modal has an entrance animation!</ui:text>
            <ui:animate type="slide-up" delay="200ms">
              <ui:text color="muted">Content animates in after the modal.</ui:text>
            </ui:animate>
          </ui:vbox>
        </ui:animate>
      </ui:modal>

    </ui:vbox>
  </ui:window>

  <q:function name="openModal">
    <q:set name="showModal" value="true" />
  </q:function>

  <q:function name="closeModal">
    <q:set name="showModal" value="false" />
  </q:function>

</q:application>
```

## Cross-Target Support

### HTML Target

Animations compile to CSS animations and keyframes with JavaScript triggers.

### Desktop Target

pywebview applications include the same CSS animations.

### Terminal Target

Limited animation support in Textual TUI:
- Basic fade (opacity simulation)
- No complex animations

::: warning Terminal Limitations
Complex animations like slide, rotate, and scale are not available in terminal mode. Use `reducedMotion` attribute to provide fallbacks.
:::

## Best Practices

1. **Keep animations subtle** - Avoid excessive motion
2. **Use appropriate durations** - 150-300ms for micro-interactions, 300-500ms for larger changes
3. **Respect user preferences** - Always support `prefers-reduced-motion`
4. **Provide fallbacks** - Use `reducedMotion` attribute for terminal/accessibility
5. **Stagger list items** - Use delay for natural-feeling list animations
6. **Match content importance** - Use attention-grabbing animations sparingly

## Related Documentation

- [UI Engine Overview](/ui/overview) - Component basics
- [Theming](/features/theming) - Visual customization
- [State Management](/guide/state-management) - Animation triggers
