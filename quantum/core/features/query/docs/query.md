# q:query - Database Query Component

## Overview

`q:query` is Quantum's declarative database component, inspired by ColdFusion's `<cfquery>` with modern enhancements. It provides secure, type-safe database access with automatic parameter binding and SQL injection protection.

## Philosophy

1. **Declarative over imperative** - Define what data you need, not how to get it
2. **Security first** - Automatic SQL injection protection via parameter binding
3. **Type-safe** - Strong typing for parameters and results
4. **Observable** - Reactive data binding with live updates
5. **Developer-friendly** - Clear syntax with intelligent defaults

## Basic Usage

```quantum
<q:query name="users" datasource="my-postgres-db">
    SELECT id, name, email, created_at
    FROM users
    WHERE status = :status
    ORDER BY created_at DESC
    LIMIT :limit

    <q:param name="status" value="active" type="string" />
    <q:param name="limit" value="10" type="integer" />
</q:query>

<!-- Use the results -->
<q:loop items="{users}" var="user">
    <div>
        <h2>{user.name}</h2>
        <p>{user.email}</p>
    </div>
</q:loop>
```

## Attributes

### q:query

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `name` | Yes | string | Variable name for query results |
| `datasource` | Yes | string | Datasource name from Quantum Admin |
| `source` | No | string | Query name for Query-of-Queries |
| `cache` | No | boolean | Enable query caching (default: false) |
| `ttl` | No | integer | Cache time-to-live in seconds |
| `reactive` | No | boolean | Auto-refresh query (default: false) |
| `interval` | No | integer | Refresh interval in milliseconds |
| `page` | No | integer | Current page number for pagination |
| `pageSize` | No | integer | Items per page (default: 20) |
| `timeout` | No | integer | Query timeout in seconds |
| `maxrows` | No | integer | Maximum rows to return |
| `result` | No | string | Variable name for query metadata |

### q:param

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `name` | Yes | string | Parameter name (matches :name in SQL) |
| `value` | Yes | any | Parameter value |
| `type` | Yes | string | Data type (see types below) |
| `null` | No | boolean | Allow null value (default: false) |
| `maxLength` | No | integer | Maximum string length |
| `scale` | No | integer | Decimal scale |

### Parameter Types

- `string` - Text data
- `integer` - Whole numbers
- `decimal` - Floating point numbers
- `boolean` - True/false values
- `datetime` - Date and time values
- `date` - Date only
- `time` - Time only
- `array` - Array of values (for IN clauses)
- `json` - JSON data

## Result Object Structure

Query results are returned as an object with the following structure:

```javascript
{
    data: [],              // Array of records (also accessible directly)
    recordCount: 10,       // Total records returned
    columnList: ["id", "name", "email"],  // Column names
    executionTime: 42,     // Query execution time in ms
    sql: "SELECT...",      // Executed SQL (debug mode only)
    page: 1,              // Current page (if paginated)
    totalPages: 5,        // Total pages (if paginated)
    hasMore: true,        // Has more pages
    cached: false         // Was served from cache
}
```

## Common Patterns

### INSERT with RETURNING

```quantum
<q:query name="newUser" datasource="db">
    INSERT INTO users (name, email, password_hash)
    VALUES (:name, :email, :password)
    RETURNING id, created_at

    <q:param name="name" value="{form.name}" type="string" />
    <q:param name="email" value="{form.email}" type="string" />
    <q:param name="password" value="{hashedPassword}" type="string" />
</q:query>

<p>User created with ID: {newUser.id}</p>
```

### UPDATE Operations

```quantum
<q:query name="updateUser" datasource="db">
    UPDATE users
    SET name = :name, updated_at = NOW()
    WHERE id = :userId

    <q:param name="name" value="{form.name}" type="string" />
    <q:param name="userId" value="{session.userId}" type="integer" />
</q:query>
```

### DELETE Operations

```quantum
<q:query name="deleteUser" datasource="db">
    DELETE FROM users WHERE id = :userId
    <q:param name="userId" value="{request.id}" type="integer" />
</q:query>
```

### Multiple Queries

```quantum
<q:query name="stats" datasource="db">
    SELECT COUNT(*) as total FROM articles;
    SELECT COUNT(*) as published FROM articles WHERE status = 'published';
    SELECT COUNT(*) as drafts FROM articles WHERE status = 'draft';
</q:query>

<p>Total: {stats[0].total}</p>
<p>Published: {stats[1].published}</p>
<p>Drafts: {stats[2].drafts}</p>
```

### Pagination

```quantum
<q:query name="articles" datasource="db"
         page="{request.page}"
         pageSize="20">
    SELECT * FROM articles
    WHERE published = true
    ORDER BY created_at DESC
</q:query>

<q:loop items="{articles.data}" var="article">
    <h2>{article.title}</h2>
</q:loop>

<div class="pagination">
    <q:if condition="{articles.page > 1}">
        <a href="?page={articles.page - 1}">Previous</a>
    </q:if>

    <span>Page {articles.page} of {articles.totalPages}</span>

    <q:if condition="{articles.hasMore}">
        <a href="?page={articles.page + 1}">Next</a>
    </q:if>
</div>
```

### Query Metadata

```quantum
<q:query name="users" datasource="db" result="usersMeta">
    SELECT * FROM users
</q:query>

<p>Found {usersMeta.recordCount} users</p>
<p>Query took {usersMeta.executionTime}ms</p>
<p>Columns: {usersMeta.columnList.join(', ')}</p>
```

## Advanced Features

### Query of Queries

Process query results in memory without hitting the database again:

```quantum
<q:query name="allUsers" datasource="db">
    SELECT * FROM users
</q:query>

<q:query name="activeUsers" source="{allUsers}">
    SELECT * FROM query WHERE status = 'active'
</q:query>

<q:query name="premiumUsers" source="{allUsers}">
    SELECT * FROM query WHERE subscription = 'premium'
</q:query>
```

### Transactions

```quantum
<q:transaction datasource="db">
    <q:query name="createOrder">
        INSERT INTO orders (user_id, total)
        VALUES (:userId, :total)
        RETURNING id
        <q:param name="userId" value="{session.userId}" type="integer" />
        <q:param name="total" value="{cart.total}" type="decimal" />
    </q:query>

    <q:query name="updateInventory">
        UPDATE products
        SET stock = stock - :quantity
        WHERE id = :productId
        <q:param name="quantity" value="{item.quantity}" type="integer" />
        <q:param name="productId" value="{item.id}" type="integer" />
    </q:query>

    <q:query name="clearCart">
        DELETE FROM cart_items WHERE user_id = :userId
        <q:param name="userId" value="{session.userId}" type="integer" />
    </q:query>
</q:transaction>
```

### Cached Queries

```quantum
<q:query name="categories" datasource="db" cache="true" ttl="3600">
    SELECT id, name, slug FROM categories ORDER BY name
</q:query>

<!-- Subsequent requests within 1 hour will use cached data -->
```

### Reactive Queries

```quantum
<q:query name="liveStats" datasource="db" reactive="true" interval="5000">
    SELECT COUNT(*) as online_users
    FROM sessions
    WHERE last_seen > NOW() - INTERVAL '5 minutes'
</q:query>

<!-- Auto-updates every 5 seconds -->
<div>Online Users: {liveStats.online_users}</div>
```

### Stored Procedures

```quantum
<q:storedproc name="getUserStats" datasource="db" procedure="sp_get_user_stats">
    <q:param name="user_id" value="{session.userId}" type="integer" direction="in" />
    <q:param name="total_posts" type="integer" direction="out" />
    <q:param name="total_comments" type="integer" direction="out" />
</q:storedproc>

<p>Posts: {getUserStats.total_posts}</p>
<p>Comments: {getUserStats.total_comments}</p>
```

### Batch Operations

```quantum
<q:query name="bulkInsert" datasource="db" batch="true">
    INSERT INTO logs (user_id, action, timestamp)
    VALUES (:userId, :action, :timestamp)
    <q:param name="batch" value="{logEntries}" type="array" />
</q:query>
```

## Error Handling

```quantum
<q:try>
    <q:query name="users" datasource="db">
        SELECT * FROM users WHERE id = :id
        <q:param name="id" value="{request.id}" type="integer" />
    </q:query>

    <q:catch type="database">
        <p>Database error: {error.message}</p>
        <p>SQL State: {error.sqlState}</p>
    </q:catch>
</q:try>
```

## Security Best Practices

### ✅ DO: Use Parameter Binding

```quantum
<q:query name="user" datasource="db">
    SELECT * FROM users WHERE email = :email
    <q:param name="email" value="{form.email}" type="string" />
</q:query>
```

### ❌ DON'T: Concatenate SQL

```quantum
<!-- VULNERABLE TO SQL INJECTION! -->
<q:query name="user" datasource="db">
    SELECT * FROM users WHERE email = '{form.email}'
</q:query>
```

### ✅ DO: Validate Input Types

```quantum
<q:param name="age" value="{form.age}" type="integer" />
<!-- Automatically validates that age is an integer -->
```

### ✅ DO: Use maxLength for Strings

```quantum
<q:param name="bio" value="{form.bio}" type="string" maxLength="500" />
<!-- Prevents buffer overflow attacks -->
```

## Performance Tips

1. **Use LIMIT** - Don't fetch more rows than you need
2. **Index your WHERE clauses** - Query performance depends on database indexes
3. **Use pagination** - For large datasets, paginate results
4. **Cache static data** - Categories, tags, etc. rarely change
5. **Avoid SELECT *** - Only fetch columns you need
6. **Use Query of Queries** - Process data in memory when possible

## Implementation Phases

### Phase 1 (MVP) ✅ Current Implementation
- Basic SELECT queries with parameter binding
- INSERT/UPDATE/DELETE operations
- Query results accessible in loops and databinding
- Connection to datasources from Quantum Admin
- Error handling
- Query metadata (recordCount, columnList, executionTime)

### Phase 2 (Planned)
- Multiple queries in one component
- Pagination support
- Query of Queries
- Result metadata enhancements

### Phase 3 (Future)
- Transactions
- Query caching
- Stored procedures
- Batch operations

### Phase 4 (Advanced)
- Reactive queries
- GraphQL-style field selection
- JSON path queries
- Advanced monitoring and profiling

## Architecture Evolution

Quantum supports a natural evolution from monolith to microservices:

### Stage 1: Monolith (q:query only)
```quantum
<q:query name="articles" datasource="db">
    SELECT * FROM articles WHERE published = true
</q:query>
```

### Stage 2: Modular (q:function + q:query)
```quantum
<q:function name="getPublishedArticles" access="public">
    <q:query name="articles" datasource="db">
        SELECT * FROM articles WHERE published = true
    </q:query>
    <q:return value="{articles}" />
</q:function>
```

### Stage 3: Service-Oriented (q:rpc + q:function)
```quantum
<q:rpc component="article-service" function="getPublishedArticles" result="articles" />
```

### Stage 4: Microservices (q:rpc remote)
```quantum
<q:rpc service="article-service" function="getPublishedArticles" result="articles" />
```

## See Also

- [State Management (q:set)](./state-management.md)
- [Functions (q:function)](./functions.md)
- [Loops (q:loop)](./loops.md)
- [Quantum Admin - Datasource Management](../admin/datasources.md)
