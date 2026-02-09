---
layout: doc
title: Function Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/functions.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Function Examples

Reusable logic with `q:function` and `q:invoke`.

<div class="related-links">
  <a href="/guide/functions" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-function" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Function Patterns

### Basic Function

```xml
<q:function name="greet">
  <q:param name="name" type="string" />
  <q:return value="Hello, {name}!" />
</q:function>

<p>{greet('World')}</p>
```

### Function with Logic

```xml
<q:function name="isEven">
  <q:param name="num" type="number" />
  <q:return value="{num % 2 == 0}" />
</q:function>
```

### Recursive Function

```xml
<q:function name="factorial">
  <q:param name="n" type="number" />
  <q:if condition="{n <= 1}">
    <q:return value="1" />
  <q:else>
    <q:return value="{n * factorial(n - 1)}" />
  </q:else>
  </q:if>
</q:function>
```

### HTTP Invocation

```xml
<q:invoke name="api" method="GET" url="https://api.example.com/data">
  <q:header name="Authorization" value="Bearer {token}" />
</q:invoke>

<p>Result: {api.data}</p>
```

### Function with Validation

```xml
<q:function name="validateEmail">
  <q:param name="email" type="string" />
  <q:set name="isValid" value="{email.includes('@')}" />
  <q:return value="{isValid}" />
</q:function>
```

## Related Categories

- [State Management](/examples/state-management) - Variables in functions
- [Database Queries](/examples/queries) - Functions with queries
- [Forms & Actions](/examples/forms-actions) - Form validation functions
