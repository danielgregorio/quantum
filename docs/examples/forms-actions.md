---
layout: doc
title: Forms & Actions Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/forms-actions.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Forms & Actions Examples

Form handling, validation, and user actions.

<div class="related-links">
  <a href="/guide/actions" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-action" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Form Patterns

### Basic Form Action

```xml
<q:action name="submitForm" method="POST">
  <q:set name="message" value="Form submitted: {form.name}" />
</q:action>

<form action="/submitForm" method="POST">
  <input type="text" name="name" />
  <button type="submit">Submit</button>
</form>
```

### Form Validation

```xml
<q:action name="register" method="POST">
  <q:validate field="email" rule="email" message="Invalid email" />
  <q:validate field="password" rule="min:8" message="Password too short" />

  <q:if condition="{validation.valid}">
    <q:query name="createUser">...</q:query>
    <q:redirect url="/dashboard" />
  </q:if>
</q:action>
```

### Flash Messages

```xml
<q:action name="save" method="POST">
  <q:flash type="success" message="Changes saved successfully!" />
  <q:redirect url="/settings" />
</q:action>

<!-- Display flash -->
<q:if condition="{flash.success}">
  <div class="alert success">{flash.success}</div>
</q:if>
```

### File Upload

```xml
<q:action name="upload" method="POST" enctype="multipart/form-data">
  <q:file name="document"
          allowed="pdf,doc,docx"
          maxSize="5MB"
          destination="/uploads/{timestamp}-{filename}" />

  <q:flash type="success" message="File uploaded!" />
</q:action>
```

### Redirect After Action

```xml
<q:action name="logout" method="POST">
  <q:set scope="session" name="user" value="" />
  <q:redirect url="/login" />
</q:action>
```

## Related Categories

- [Database Queries](/examples/queries) - Save form data
- [Authentication](/examples/authentication) - Login forms
- [State Management](/examples/state-management) - Form state handling
