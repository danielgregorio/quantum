---
layout: doc
title: Authentication Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/authentication.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Authentication Examples

Login, logout, roles, and protected routes.

<div class="related-links">
  <a href="/guide/authentication" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-auth" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Authentication Patterns

### Login Action

```xml
<q:action name="login" method="POST">
  <q:query name="user" datasource="mydb">
    SELECT id, name, role, password_hash
    FROM users WHERE email = :email
    <q:param name="email" value="{form.email}" />
  </q:query>

  <q:if condition="{user.recordCount > 0 && verifyPassword(form.password, user.password_hash)}">
    <q:set scope="session" name="userId" value="{user.id}" />
    <q:set scope="session" name="userRole" value="{user.role}" />
    <q:redirect url="/dashboard" />
  <q:else>
    <q:flash type="error" message="Invalid credentials" />
    <q:redirect url="/login" />
  </q:else>
  </q:if>
</q:action>
```

### Protected Route

```xml
<q:if condition="{!session.userId}">
  <q:redirect url="/login" />
</q:if>

<!-- Protected content -->
<h1>Welcome, {session.userName}!</h1>
```

### Role-Based Access

```xml
<q:if condition="{session.userRole != 'admin'}">
  <q:redirect url="/unauthorized" />
</q:if>

<!-- Admin-only content -->
<h1>Admin Dashboard</h1>
```

### Logout

```xml
<q:action name="logout" method="POST">
  <q:set scope="session" name="userId" value="" />
  <q:set scope="session" name="userRole" value="" />
  <q:flash type="info" message="You have been logged out" />
  <q:redirect url="/login" />
</q:action>
```

### Remember Me

```xml
<q:action name="login" method="POST">
  <!-- After successful login -->
  <q:if condition="{form.remember}">
    <q:set scope="cookie" name="rememberToken"
           value="{generateToken()}"
           expires="30 days" />
  </q:if>
</q:action>
```

## Related Categories

- [Forms & Actions](/examples/forms-actions) - Login form handling
- [Database Queries](/examples/queries) - User authentication queries
- [State Management](/examples/state-management) - Session state
