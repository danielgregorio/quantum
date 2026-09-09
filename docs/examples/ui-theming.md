---
layout: doc
title: UI & Theming Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/ui-theming.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# UI & Theming Examples

UI components, themes, and animations.

<div class="related-links">
  <a href="/ui/overview" class="related-link">UI Documentation</a>
  <a href="/features/theming" class="related-link">Theming Guide</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## UI Patterns

### Theme Configuration

```xml
<q:application id="myapp" theme="dark">
  <q:theme>
    <q:colors>
      <primary>#6366f1</primary>
      <secondary>#8b5cf6</secondary>
      <background>#0f172a</background>
    </q:colors>
    <q:fonts>
      <heading>Inter, sans-serif</heading>
      <body>system-ui, sans-serif</body>
    </q:fonts>
  </q:theme>

  <!-- App content -->
</q:application>
```

### UI Components

```xml
<ui:card>
  <ui:card-header>
    <ui:card-title>User Profile</ui:card-title>
  </ui:card-header>
  <ui:card-body>
    <ui:avatar src="{user.avatar}" size="lg" />
    <ui:text variant="h2">{user.name}</ui:text>
    <ui:badge color="success">Active</ui:badge>
  </ui:card-body>
  <ui:card-footer>
    <ui:button variant="primary">Edit Profile</ui:button>
  </ui:card-footer>
</ui:card>
```

### Animations

```xml
<ui:animate type="fadeIn" duration="0.3s">
  <div class="content">Animated content</div>
</ui:animate>

<ui:animate type="slideUp" delay="0.1s" on="hover">
  <ui:card>Hover me!</ui:card>
</ui:animate>
```

### Responsive Layout

```xml
<ui:grid cols="1" md:cols="2" lg:cols="3" gap="4">
  <ui:card v-for="item in items">
    {item.title}
  </ui:card>
</ui:grid>
```

### Dark Mode Toggle

```xml
<q:set name="theme" value="light" scope="session" />

<q:action name="toggleTheme">
  <q:if condition="{session.theme == 'light'}">
    <q:set name="theme" value="dark" scope="session" />
  <q:else>
    <q:set name="theme" value="light" scope="session" />
  </q:else>
  </q:if>
</q:action>

<button onclick="toggleTheme()">
  {session.theme == 'light' ? 'Dark Mode' : 'Light Mode'}
</button>
```

## Related Categories

- [State Management](/examples/state-management) - Theme state
- [Forms & Actions](/examples/forms-actions) - UI form components
- [Advanced](/examples/advanced) - Complete UI applications
