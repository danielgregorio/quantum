---
layout: doc
title: Database Query Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/queries.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Database Query Examples

Database operations with `q:query` and transactions.

<div class="related-links">
  <a href="/guide/query" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-query" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Query Patterns

### Basic Select

```xml
<q:query name="users" datasource="mydb">
  SELECT id, name, email FROM users
</q:query>

<q:loop items="{users}" var="user">
  <p>{user.name} - {user.email}</p>
</q:loop>
```

### Parameterized Query

```xml
<q:query name="user" datasource="mydb">
  SELECT * FROM users WHERE id = :userId
  <q:param name="userId" value="{requestedId}" />
</q:query>
```

### Insert with Return

```xml
<q:query name="newUser" datasource="mydb" type="insert">
  INSERT INTO users (name, email) VALUES (:name, :email)
  <q:param name="name" value="{form.name}" />
  <q:param name="email" value="{form.email}" />
</q:query>

<p>Created user ID: {newUser.insertId}</p>
```

### Transaction

```xml
<q:transaction datasource="mydb">
  <q:query name="debit">
    UPDATE accounts SET balance = balance - :amount WHERE id = :fromId
    <q:param name="amount" value="{transferAmount}" />
    <q:param name="fromId" value="{fromAccountId}" />
  </q:query>

  <q:query name="credit">
    UPDATE accounts SET balance = balance + :amount WHERE id = :toId
    <q:param name="amount" value="{transferAmount}" />
    <q:param name="toId" value="{toAccountId}" />
  </q:query>
</q:transaction>
```

### Query with Cache

```xml
<q:query name="products" datasource="mydb" cache="300">
  SELECT * FROM products WHERE active = 1
</q:query>
```

## Related Categories

- [Loops](/examples/loops) - Iterate over query results
- [Forms & Actions](/examples/forms-actions) - Form submissions to database
- [Advanced](/examples/advanced) - Complex data applications
