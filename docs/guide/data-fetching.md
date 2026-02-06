# Data Fetching (q:fetch)

`q:fetch` provides declarative HTTP data fetching with automatic state management, caching, loading/error/success states, and cross-target support.

## Overview

Instead of writing imperative fetch code, Quantum lets you declare what data you need and automatically handles loading states, caching, and error handling.

```xml
<q:fetch name="users" url="https://api.example.com/users">
  <q:loading>
    <ui:loading>Loading users...</ui:loading>
  </q:loading>
  <q:error>
    <ui:alert variant="danger">Failed to load users: {users.error}</ui:alert>
  </q:error>
  <q:success>
    <q:loop type="array" var="user" items="{users.data}">
      <ui:text>{user.name}</ui:text>
    </q:loop>
  </q:success>
</q:fetch>
```

## Basic Usage

### Simple GET Request

```xml
<q:component name="UserList" xmlns:q="https://quantum.lang/ns">
  <q:fetch name="users" url="https://api.example.com/users" />

  <q:if condition="users.loading">
    <q:return value="Loading..." />
  </q:if>

  <q:if condition="users.error">
    <q:return value="Error: {users.error}" />
  </q:if>

  <q:loop type="array" var="user" items="{users.data}">
    <q:return value="{user.name} - {user.email}" />
  </q:loop>
</q:component>
```

### With Declarative States

```xml
<q:fetch name="posts" url="/api/posts">
  <q:loading>
    <ui:skeleton type="text" lines="5" />
  </q:loading>
  <q:error>
    <ui:alert variant="danger" title="Error">
      {posts.error}
    </ui:alert>
  </q:error>
  <q:success>
    <q:loop type="array" var="post" items="{posts.data}">
      <ui:card title="{post.title}">
        <ui:text>{post.excerpt}</ui:text>
      </ui:card>
    </q:loop>
  </q:success>
</q:fetch>
```

## HTTP Methods

### GET Request (Default)

```xml
<q:fetch name="products" url="/api/products" method="GET" />
```

### POST Request

```xml
<q:fetch name="newUser" url="/api/users" method="POST">
  <q:body>
    {
      "name": "{form.name}",
      "email": "{form.email}"
    }
  </q:body>
</q:fetch>
```

### PUT Request

```xml
<q:fetch name="updateResult" url="/api/users/{userId}" method="PUT">
  <q:body>
    {
      "name": "{form.name}",
      "email": "{form.email}"
    }
  </q:body>
</q:fetch>
```

### DELETE Request

```xml
<q:fetch name="deleteResult" url="/api/users/{userId}" method="DELETE" />
```

## Request Configuration

### Adding Headers

```xml
<q:fetch name="data" url="/api/protected">
  <q:header name="Authorization" value="Bearer {session.token}" />
  <q:header name="Content-Type" value="application/json" />
  <q:header name="X-Custom-Header" value="custom-value" />
</q:fetch>
```

### Request Body

For POST, PUT, and PATCH requests:

```xml
<q:fetch name="result" url="/api/orders" method="POST">
  <q:body type="json">
    {
      "items": {cart.items},
      "shipping": {
        "address": "{form.address}",
        "city": "{form.city}"
      }
    }
  </q:body>
</q:fetch>
```

### Query Parameters

Include query parameters in the URL:

```xml
<q:fetch
  name="searchResults"
  url="/api/search?q={query}&page={currentPage}&limit=20"
/>
```

Or use the params attribute:

```xml
<q:fetch
  name="searchResults"
  url="/api/search"
  params='{"q": "{query}", "page": "{currentPage}", "limit": 20}'
/>
```

## Caching

### Enable Caching with TTL

```xml
<!-- Cache for 5 minutes -->
<q:fetch name="categories" url="/api/categories" cache="5m" />

<!-- Cache for 1 hour -->
<q:fetch name="config" url="/api/config" cache="1h" />

<!-- Cache for 30 seconds -->
<q:fetch name="liveData" url="/api/stats" cache="30s" />
```

### Cache Keys

By default, the cache key is based on the URL and method. Customize it:

```xml
<q:fetch
  name="userPosts"
  url="/api/posts?userId={userId}"
  cache="10m"
  cacheKey="user-posts-{userId}"
/>
```

### Invalidate Cache

Force a fresh fetch:

```xml
<q:fetch name="data" url="/api/data" cache="5m" forceRefresh="true" />
```

Or programmatically:

```xml
<ui:button on-click="data.refetch()">Refresh Data</ui:button>
```

## Polling

Automatically refetch data at intervals:

```xml
<!-- Poll every 5 seconds -->
<q:fetch name="notifications" url="/api/notifications" interval="5s" />

<!-- Poll every minute -->
<q:fetch name="stats" url="/api/dashboard/stats" interval="1m" />
```

### Conditional Polling

Only poll when a condition is met:

```xml
<q:fetch
  name="orderStatus"
  url="/api/orders/{orderId}/status"
  interval="10s"
  pollWhile="orderStatus.data.status == 'processing'"
/>
```

## Response Transformation

### Transform Response Data

```xml
<q:fetch
  name="users"
  url="/api/users"
  transform="response.data.users"
/>

<!-- Access transformed data -->
<q:loop type="array" var="user" items="{users.data}">
  ...
</q:loop>
```

### Complex Transformations

```xml
<q:fetch name="products" url="/api/products">
  <q:transform>
    {
      "items": response.data.products.map(p => ({
        "id": p.id,
        "name": p.title,
        "price": p.price.formatted
      })),
      "total": response.data.meta.total
    }
  </q:transform>
</q:fetch>
```

## Error Handling

### Basic Error Handling

```xml
<q:fetch name="data" url="/api/data">
  <q:error>
    <q:if condition="data.status == 404">
      <ui:alert variant="warning">Resource not found</ui:alert>
    </q:if>
    <q:elseif condition="data.status == 401">
      <ui:alert variant="danger">Please log in to continue</ui:alert>
    </q:elseif>
    <q:else>
      <ui:alert variant="danger">Error: {data.error}</ui:alert>
    </q:else>
  </q:error>
</q:fetch>
```

### Retry on Failure

```xml
<q:fetch
  name="data"
  url="/api/unreliable-endpoint"
  retry="3"
  retryDelay="1s"
/>
```

### Timeout

```xml
<q:fetch name="data" url="/api/slow-endpoint" timeout="10s" />
```

## Result Object

The fetch result object contains:

| Property | Type | Description |
|----------|------|-------------|
| `data` | any | Response data (after transformation) |
| `loading` | boolean | True while request is in progress |
| `error` | string | Error message if request failed |
| `status` | number | HTTP status code |
| `refetch()` | function | Manually trigger a refetch |
| `abort()` | function | Cancel the current request |

### Using Result Properties

```xml
<q:fetch name="users" url="/api/users" />

<ui:text>Status: {users.status}</ui:text>
<ui:text>Loading: {users.loading}</ui:text>
<ui:text>Error: {users.error}</ui:text>
<ui:text>Count: {users.data.length}</ui:text>

<ui:button on-click="users.refetch()">Refresh</ui:button>
```

## Dependent Fetches

Fetch data that depends on other fetched data:

```xml
<!-- First fetch: Get user -->
<q:fetch name="user" url="/api/users/{userId}" />

<!-- Second fetch: Depends on user.data -->
<q:if condition="!user.loading && user.data">
  <q:fetch
    name="userPosts"
    url="/api/users/{user.data.id}/posts"
  />
</q:if>
```

## Events and Callbacks

### Success Callback

```xml
<q:fetch
  name="result"
  url="/api/action"
  method="POST"
  on-success="handleSuccess"
>
  <q:body>{form.data}</q:body>
</q:fetch>

<q:function name="handleSuccess">
  <q:set name="message" value="Action completed successfully!" />
</q:function>
```

### Error Callback

```xml
<q:fetch
  name="result"
  url="/api/action"
  on-error="handleError"
/>

<q:function name="handleError">
  <q:set name="errorMessage" value="{result.error}" />
</q:function>
```

## Cross-Target Support

`q:fetch` works across all Quantum targets:

### HTML Target

Uses the browser's `fetch()` API with automatic state management.

### Desktop Target (pywebview)

Uses Python's `requests` library with threading for non-blocking requests.

### Mobile Target (React Native)

Compiles to React Native's `fetch()` with hooks for state management.

## Complete Example

```xml
<q:application id="blog" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="currentPage" value="1" />

  <q:function name="loadPage">
    <q:param name="page" type="number" />
    <q:set name="currentPage" value="{page}" />
  </q:function>

  <ui:window title="Blog Posts">
    <ui:vbox padding="lg" gap="md">
      <ui:header>
        <ui:text size="2xl" weight="bold">Latest Posts</ui:text>
      </ui:header>

      <q:fetch
        name="posts"
        url="/api/posts?page={currentPage}&limit=10"
        cache="5m"
      >
        <q:loading>
          <ui:vbox gap="sm">
            <ui:skeleton type="card" count="3" />
          </ui:vbox>
        </q:loading>

        <q:error>
          <ui:alert variant="danger" dismissible="true">
            <ui:text weight="bold">Failed to load posts</ui:text>
            <ui:text>{posts.error}</ui:text>
          </ui:alert>
          <ui:button on-click="posts.refetch()">Try Again</ui:button>
        </q:error>

        <q:success>
          <q:loop type="array" var="post" items="{posts.data.items}">
            <ui:card>
              <ui:text size="lg" weight="bold">{post.title}</ui:text>
              <ui:text color="muted">{post.author} - {post.date}</ui:text>
              <ui:text>{post.excerpt}</ui:text>
            </ui:card>
          </q:loop>

          <ui:pagination
            current="{currentPage}"
            total="{posts.data.totalPages}"
            on-change="loadPage"
          />
        </q:success>
      </q:fetch>
    </ui:vbox>
  </ui:window>
</q:application>
```

## Best Practices

### 1. Always Handle Loading and Error States

```xml
<q:fetch name="data" url="/api/data">
  <q:loading>...</q:loading>
  <q:error>...</q:error>
  <q:success>...</q:success>
</q:fetch>
```

### 2. Use Caching for Static Data

```xml
<q:fetch name="countries" url="/api/countries" cache="1h" />
```

### 3. Set Appropriate Timeouts

```xml
<q:fetch name="data" url="/api/slow" timeout="30s" />
```

### 4. Transform Data at Fetch Time

```xml
<q:fetch name="data" url="/api/data" transform="response.data.items" />
```

### 5. Use Meaningful Names

```xml
<!-- Good -->
<q:fetch name="activeUsers" url="/api/users?status=active" />

<!-- Avoid -->
<q:fetch name="data1" url="/api/users?status=active" />
```

## Related Documentation

- [Database Queries (q:query)](/guide/query) - Server-side data fetching
- [State Management (q:set)](/guide/state-management) - Managing fetched data
- [Loops (q:loop)](/guide/loops) - Iterating over fetched data
- [UI Components](/ui/overview) - Displaying fetched data
