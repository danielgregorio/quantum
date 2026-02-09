---
layout: doc
title: State Management Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])
const metadata = ref({})

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/state-management.json')
    examples.value = data.examples || []
    metadata.value = data
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# State Management Examples

Learn how to manage state with `q:set`, data binding, and variable operations.

<div class="related-links">
  <a href="/guide/state-management" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-set" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Featured Example

The simplest way to create and display a variable:

```xml
<!-- test-set-simple.q -->
<q:component name="TestSetSimple" xmlns:q="https://quantum.lang/ns">
  <q:set name="x" value="10" />
  <q:return value="x = {x}" />
</q:component>
```

## Key Concepts

### Basic Variable Assignment

```xml
<q:set name="message" value="Hello, World!" />
<p>{message}</p>
```

### Expressions and Calculations

```xml
<q:set name="price" value="100" type="number" />
<q:set name="tax" value="{price * 0.1}" type="number" />
<p>Total: {price + tax}</p>
```

### Arrays and Objects

```xml
<q:set name="colors" value='["red", "green", "blue"]' type="array" />
<q:loop items="{colors}" var="color">
  <span>{color}</span>
</q:loop>
```

### Variable Validation

```xml
<q:set name="email" value="user@example.com" validate="email" />
<q:set name="age" value="25" type="number" validate="min:18,max:120" />
```

## Related Categories

- [Loops](/examples/loops) - Iterate over data
- [Conditionals](/examples/conditionals) - Conditional display based on state
- [Data Import](/examples/data-import) - Load external data into variables
