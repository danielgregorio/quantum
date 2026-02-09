---
layout: doc
title: Advanced Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/advanced.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Advanced Examples

Complex examples combining multiple features - real-world applications.

<div class="related-links">
  <a href="/architecture/" class="related-link">Architecture Guide</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Application Types

### Web Application

A complete web app with routing, database, and authentication:

```xml
<q:application id="webapp" type="html" port="8080">
  <q:route path="/" method="GET">
    <q:if condition="{!session.userId}">
      <q:redirect url="/login" />
    </q:if>
    <!-- Dashboard content -->
  </q:route>

  <q:route path="/login" method="GET">
    <!-- Login form -->
  </q:route>

  <q:route path="/api/users" method="GET">
    <q:query name="users">SELECT * FROM users</q:query>
    <q:return type="json" value="{users}" />
  </q:route>
</q:application>
```

### REST API

Build a complete REST API:

```xml
<q:application id="api" type="api">
  <q:route path="/api/products" method="GET">
    <q:query name="products">SELECT * FROM products</q:query>
    <q:return type="json" value="{products}" />
  </q:route>

  <q:route path="/api/products/:id" method="GET">
    <q:query name="product">
      SELECT * FROM products WHERE id = :id
      <q:param name="id" value="{route.params.id}" />
    </q:query>
    <q:return type="json" value="{product[0]}" />
  </q:route>

  <q:route path="/api/products" method="POST">
    <q:query name="insert" type="insert">
      INSERT INTO products (name, price) VALUES (:name, :price)
      <q:param name="name" value="{body.name}" />
      <q:param name="price" value="{body.price}" />
    </q:query>
    <q:return type="json" value='{"id": {insert.insertId}}' />
  </q:route>
</q:application>
```

### Chat Application

Real-time chat with WebSockets:

```xml
<q:application id="chat" type="html">
  <q:websocket path="/ws/chat">
    <q:on event="message">
      <q:broadcast channel="chat" data="{message}" />
    </q:on>
  </q:websocket>

  <div id="messages"></div>

  <q:island type="htmx">
    <form hx-ws="send:message">
      <input name="text" placeholder="Type message..." />
      <button>Send</button>
    </form>
  </q:island>
</q:application>
```

### Desktop Application

Build cross-platform desktop apps:

```xml
<q:application id="desktop" type="desktop" width="1200" height="800">
  <q:window title="Task Manager" icon="/assets/icon.png">
    <q:menu>
      <q:menu-item label="File">
        <q:menu-item label="New" shortcut="Ctrl+N" action="newTask" />
        <q:menu-item label="Exit" action="exit" />
      </q:menu-item>
    </q:menu>

    <!-- App content -->
  </q:window>
</q:application>
```

### Job Queue

Background job processing:

```xml
<q:job-queue name="emails" workers="3">
  <q:job name="sendWelcome">
    <q:mail to="{job.data.email}" subject="Welcome!">
      <h1>Welcome, {job.data.name}!</h1>
    </q:mail>
  </q:job>
</q:job-queue>

<!-- Enqueue a job -->
<q:enqueue queue="emails" job="sendWelcome">
  <q:data email="{user.email}" name="{user.name}" />
</q:enqueue>
```

### Python Integration

Call Python code from Quantum:

```xml
<q:python name="analysis" script="/scripts/analyze.py">
  <q:arg name="data" value="{salesData}" />
</q:python>

<p>Analysis Result: {analysis.result}</p>
```

## Featured Applications

| Application | Description |
|-------------|-------------|
| [webapp.q](https://github.com/danielgregorio/quantum/blob/main/examples/webapp.q) | Full web application template |
| [api.q](https://github.com/danielgregorio/quantum/blob/main/examples/api.q) | REST API with CRUD operations |
| [chat.q](https://github.com/danielgregorio/quantum/blob/main/examples/chat.q) | Real-time chat application |
| [task-manager-desktop.q](https://github.com/danielgregorio/quantum/blob/main/examples/task-manager-desktop.q) | Desktop task management app |
| [filebrowser.q](https://github.com/danielgregorio/quantum/blob/main/examples/filebrowser.q) | File browser interface |

## Related Categories

All other categories build up to these advanced examples:

- [State Management](/examples/state-management)
- [Database Queries](/examples/queries)
- [Authentication](/examples/authentication)
- [AI Agents](/examples/agents)
