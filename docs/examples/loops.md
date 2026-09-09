---
layout: doc
title: Loop Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/loops.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Loop Examples

Iteration with `q:loop` - arrays, ranges, and lists.

<div class="related-links">
  <a href="/guide/loops" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-loop" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Loop Types

### Range Loop

Iterate over a numeric range:

```xml
<q:loop type="range" var="i" from="1" to="5">
  <p>Number {i}</p>
</q:loop>
```

### Array Loop

Iterate over arrays:

```xml
<q:loop type="array" var="fruit" items='["apple", "banana", "orange"]'>
  <li>{fruit}</li>
</q:loop>
```

### Array with Index

Access the current index:

```xml
<q:loop type="array" var="item" index="idx" items="{myArray}">
  <p>{idx}: {item}</p>
</q:loop>
```

### List Loop

Iterate over delimited strings:

```xml
<q:loop type="list" var="city" items="NYC,London,Tokyo" delimiter=",">
  <span>{city}</span>
</q:loop>
```

### Range with Step

Control iteration step:

```xml
<q:loop type="range" var="i" from="0" to="10" step="2">
  <p>Even: {i}</p>
</q:loop>
```

## Related Categories

- [State Management](/examples/state-management) - Create data to iterate
- [Conditionals](/examples/conditionals) - Conditional logic inside loops
- [Database Queries](/examples/queries) - Loop over query results
