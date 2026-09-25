---
layout: doc
title: Conditional Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/conditionals.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Conditional Examples

::: danger Under review
The examples on this page have not been checked against the language, and some
of them use tags or attributes that do not exist. The page is being replaced by
tested examples. Until then, trust the [Guide](/guide/getting-started) and the
[Reference](/reference/), whose examples are checked on every change.
:::

Conditional logic with `q:if`, `q:else`, and `q:elseif`.

<div class="related-links">
  <a href="../guide/conditionals" class="related-link">Documentation</a>
  <a href="../reference/tags#q-if" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Conditional Patterns

### Basic If

```xml
<q:if condition="{isLoggedIn}">
  <p>Welcome back!</p>
</q:if>
```

### If-Else

```xml
<q:if condition="{age >= 18}">
  <p>Adult content</p>
<q:else>
  <p>Content for minors</p>
</q:else>
</q:if>
```

### Multiple Conditions

```xml
<q:if condition="{score >= 90}">
  <p>Grade: A</p>
<q:elseif condition="{score >= 80}">
  <p>Grade: B</p>
<q:elseif condition="{score >= 70}">
  <p>Grade: C</p>
<q:else>
  <p>Grade: F</p>
</q:else>
</q:if>
```

### Comparison Operators

```xml
<!-- Equality -->
<q:if condition="{status == 'active'}">...</q:if>

<!-- Numeric comparison -->
<q:if condition="{count > 0}">...</q:if>

<!-- Boolean -->
<q:if condition="{isEnabled}">...</q:if>
<q:if condition="{!isDisabled}">...</q:if>
```

## Related Categories

- [State Management](/examples/state-management) - Variables to test
- [Loops](/examples/loops) - Conditionals inside loops
- [Authentication](/examples/authentication) - Auth-based conditionals
