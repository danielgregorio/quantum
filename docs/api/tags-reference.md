# Tags Reference (q:)

Complete reference for all `q:` namespace tags in the Quantum Framework. These are the core tags for logic, data, and component definition.

## Core Tags

### q:component

Defines a reusable Quantum component. Components are the building blocks of Quantum applications.

```xml
<q:component name="UserProfile" type="pure">
  <q:param name="userId" type="integer" required="true" />
  <!-- Component content -->
</q:component>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Component name (PascalCase recommended) |
| `type` | enum | `pure` | Component type: `pure`, `microservice`, `event-driven`, `worker`, `websocket`, `graphql`, `grpc`, `serverless` |
| `port` | integer | - | Port number for microservice components |
| `basePath` | string | - | Base URL path for REST endpoints |
| `health` | string | - | Health check endpoint path |
| `metrics` | string | - | Metrics provider (prometheus, datadog) |
| `trace` | string | - | Tracing provider (jaeger, zipkin) |
| `require_auth` | boolean | `false` | Require authentication |
| `require_role` | string | - | Required role(s) (comma-separated) |
| `require_permission` | string | - | Required permission(s) |
| `interactive` | boolean | `false` | Enable client-side hydration |

**See also:** [q:application](#qapplication), [q:function](#qfunction), [q:param](#qparam)

---

### q:application

Defines a Quantum application with routing and configuration.

```xml
<q:application id="myApp" type="html">
  <q:route path="/" method="GET" />
</q:application>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | string | **required** | Unique application identifier |
| `type` | enum | `html` | Application type: `html`, `game`, `terminal`, `testing`, `ui` |
| `engine` | string | - | Engine variant (e.g., '2d' for game type) |
| `theme` | string | - | Theme preset for UI applications |

**See also:** [q:component](#qcomponent), [q:route](#qroute)

---

### q:set

Declares or modifies a variable with type safety and validation.

```xml
<!-- Basic assignment -->
<q:set name="counter" type="integer" value="0" />

<!-- With validation -->
<q:set name="email" type="string" validate="email" required="true" />

<!-- Operations -->
<q:set name="counter" operation="increment" />

<!-- Persistence -->
<q:set name="theme" value="dark" persist="local" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Variable name |
| `value` | expression | - | Value to assign (supports databinding) |
| `type` | enum | `string` | Data type: `string`, `integer`, `decimal`, `boolean`, `array`, `struct`, `date`, `datetime` |
| `default` | any | - | Default value if not set |
| `scope` | enum | `local` | Variable scope: `local`, `component`, `session`, `application`, `request` |
| `operation` | enum | `assign` | Operation: `assign`, `increment`, `decrement`, `add`, `remove`, `append`, `prepend`, `toggle`, `clear` |
| `required` | boolean | `false` | Whether the variable is required |
| `validate` | string | - | Validation rule (email, url, cpf, etc.) |
| `pattern` | regex | - | Regex pattern for validation |
| `min` | number | - | Minimum value |
| `max` | number | - | Maximum value |
| `minlength` | integer | - | Minimum string length |
| `maxlength` | integer | - | Maximum string length |
| `enum` | string | - | Allowed values (comma-separated) |
| `persist` | enum | - | Persistence mode: `local`, `session`, `sync` |
| `persistKey` | string | - | Custom key for persistent storage |
| `persistEncrypt` | boolean | `false` | Encrypt persisted value |

**See also:** [q:param](#qparam), [q:loop](#qloop), [State Management](/guide/state-management)

---

## Control Flow

### q:if

Conditional execution with optional elseif and else branches.

```xml
<q:if condition="{user.isAdmin}">
  <p>Admin content</p>
<q:elseif condition="{user.isModerator}">
  <p>Moderator content</p>
<q:else>
  <p>Regular user content</p>
</q:else>
</q:if>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `condition` | expression | **required** | Boolean expression to evaluate |

**Children:** `q:elseif`, `q:else`, `q:set`, `q:loop`, `q:query`, `q:return`

---

### q:elseif

Else-if branch within a `q:if` block.

```xml
<q:elseif condition="{age >= 13}">
  <p>Teen content</p>
</q:elseif>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `condition` | expression | **required** | Boolean expression to evaluate |

**Parent:** `q:if`

---

### q:else

Else branch within a `q:if` block. Executed when all conditions are false.

```xml
<q:else>
  <p>Default content</p>
</q:else>
```

**Parent:** `q:if`

---

### q:loop

Iterates over ranges, arrays, lists, or query results.

```xml
<!-- Range loop -->
<q:loop var="i" type="range" from="1" to="10">
  <p>Item {i}</p>
</q:loop>

<!-- Array loop -->
<q:loop var="user" type="array" items="{users}" index="idx">
  <p>{idx}: {user.name}</p>
</q:loop>

<!-- Query loop -->
<q:loop query="users">
  <tr><td>{users.name}</td></tr>
</q:loop>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `var` | string | **required** | Loop variable name |
| `type` | enum | `range` | Iteration type: `range`, `array`, `list`, `query`, `object` |
| `from` | integer | - | Start value for range loops |
| `to` | integer | - | End value for range loops |
| `step` | integer | `1` | Step value for range loops |
| `items` | expression | - | Array or list to iterate |
| `query` | string | - | Query result to iterate |
| `index` | string | - | Variable name for current index |
| `delimiter` | string | `,` | Delimiter for list loops |

**See also:** [q:if](#qif), [q:query](#qquery)

---

## Functions

### q:function

Defines a function within a component. Can be exposed as REST endpoint.

```xml
<q:function name="greet" returnType="string">
  <q:param name="name" type="string" />
  <q:return value="Hello, {name}!" />
</q:function>

<!-- REST endpoint -->
<q:function name="getUsers" endpoint="/users" method="GET" roles="admin">
  <q:query name="users" datasource="db">SELECT * FROM users</q:query>
  <q:return value="{users}" />
</q:function>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Function name |
| `returnType` | enum | `any` | Return type: `any`, `void`, `string`, `integer`, `decimal`, `boolean`, `array`, `struct`, `query` |
| `scope` | enum | `component` | Visibility: `component`, `public`, `private` |
| `access` | enum | `public` | Access modifier: `public`, `private`, `protected` |
| `description` | string | - | Function documentation |
| `cache` | boolean | - | Cache function results |
| `memoize` | boolean | `false` | Memoize function calls |
| `pure` | boolean | `false` | Mark as pure function (no side effects) |
| `async` | boolean | `false` | Async function execution |
| `timeout` | string | - | Execution timeout (e.g., '30s') |
| `retry` | integer | - | Number of retries on failure |
| `endpoint` | string | - | REST endpoint path |
| `method` | enum | - | HTTP method: `GET`, `POST`, `PUT`, `DELETE`, `PATCH` |
| `produces` | string | `application/json` | Response content type |
| `consumes` | string | `application/json` | Request content type |
| `auth` | string | - | Authentication requirement |
| `roles` | string | - | Required roles (comma-separated) |
| `rateLimit` | string | - | Rate limit (e.g., '100/minute') |
| `cors` | boolean | - | Enable CORS |

**Children:** `q:param`, `q:return`, `q:set`, `q:if`, `q:loop`, `q:query`

---

### q:param

Declares a parameter for components, functions, queries, or actions.

```xml
<q:param name="userId" type="integer" required="true" />
<q:param name="status" type="string" enum="active,inactive" default="active" />
<q:param name="avatar" type="binary" accept="image/*" maxsize="5MB" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Parameter name |
| `type` | enum | `string` | Data type: `string`, `integer`, `decimal`, `boolean`, `array`, `struct`, `date`, `datetime`, `binary`, `email`, `url` |
| `required` | boolean | `false` | Whether required |
| `default` | any | - | Default value |
| `value` | expression | - | Value expression (for query params) |
| `description` | string | - | Documentation |
| `source` | enum | `auto` | Parameter source: `auto`, `path`, `query`, `body`, `header`, `cookie` |
| `validate` | string | - | Validation rule |
| `pattern` | regex | - | Regex pattern |
| `min` | number | - | Minimum value |
| `max` | number | - | Maximum value |
| `minlength` | integer | - | Minimum length |
| `maxlength` | integer | - | Maximum length |
| `enum` | string | - | Allowed values (comma-separated) |
| `accept` | string | - | Accepted file types for binary |
| `maxsize` | string | - | Maximum file size |

---

### q:return

Returns a value from a function or route.

```xml
<q:return value="{result}" />
<q:return value="Success" type="string" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `value` | expression | **required** | Value to return |
| `type` | enum | `string` | Return type: `string`, `integer`, `decimal`, `boolean`, `array`, `struct`, `query`, `json` |
| `name` | string | - | Named return for multiple values |

---

## Data

### q:query

Executes a database query with automatic parameter binding.

```xml
<q:query name="users" datasource="db">
  SELECT * FROM users WHERE active = true
</q:query>

<q:query name="user" datasource="db" cache="true" ttl="300">
  SELECT * FROM users WHERE id = :userId
  <q:param name="userId" value="{userId}" type="integer" />
</q:query>

<!-- Paginated query -->
<q:query name="products" datasource="db" paginate="true" pageSize="20">
  SELECT * FROM products ORDER BY name
</q:query>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Query result variable name |
| `datasource` | string | - | Database connection name |
| `source` | string | - | Source query for Query-of-Queries |
| `cache` | boolean | `false` | Cache query results |
| `ttl` | integer | - | Cache TTL in seconds |
| `reactive` | boolean | `false` | Enable reactive updates |
| `interval` | integer | - | Polling interval in ms |
| `paginate` | boolean | `false` | Enable automatic pagination |
| `page` | integer | `1` | Current page number |
| `pageSize` | integer | `20` | Items per page |
| `timeout` | integer | - | Query timeout in ms |
| `maxrows` | integer | - | Maximum rows to return |
| `result` | string | - | Variable for query metadata |
| `mode` | enum | - | Query mode (`rag` for RAG pipeline) |
| `model` | string | - | LLM model for RAG queries |

**Children:** `q:param`

---

### q:invoke

Invokes a function, component method, or external HTTP endpoint.

```xml
<!-- Call a function -->
<q:invoke name="result" function="calculateTotal" />

<!-- Call external API -->
<q:invoke name="data" url="https://api.example.com/users" method="GET">
  <q:header name="Authorization" value="Bearer {token}" />
</q:invoke>

<!-- Call a microservice -->
<q:invoke name="response" service="user-service" endpoint="/users/{id}" method="GET" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Result variable name |
| `function` | string | - | Function name to call |
| `component` | string | - | Component containing the function |
| `url` | url | - | External URL to call |
| `endpoint` | string | - | REST endpoint path |
| `service` | string | - | Service name for discovery |
| `method` | enum | `GET` | HTTP method: `GET`, `POST`, `PUT`, `DELETE`, `PATCH` |
| `contentType` | string | `application/json` | Request content type |
| `authType` | enum | - | Auth type: `none`, `basic`, `bearer`, `api-key` |
| `authToken` | string | - | Auth token value |
| `timeout` | integer | - | Request timeout in ms |
| `retry` | integer | - | Retry count |
| `retryDelay` | integer | - | Delay between retries in ms |
| `responseFormat` | enum | `auto` | Response format: `auto`, `json`, `xml`, `text`, `binary` |
| `cache` | boolean | `false` | Cache response |
| `ttl` | integer | - | Cache TTL in seconds |

**Children:** `q:header`, `q:param`, `q:body`

---

### q:data

Imports and transforms data from external sources.

```xml
<q:data name="products" source="./data/products.csv" type="csv" />

<q:data name="config" source="./config.json" type="json" cache="true" ttl="3600" />

<q:data name="feed" source="https://api.example.com/feed.xml" type="xml" xpath="//item" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Result variable name |
| `source` | url | **required** | Data source URL or path |
| `type` | enum | `csv` | Data format: `csv`, `xml`, `json`, `excel` |
| `cache` | boolean | `true` | Cache imported data |
| `ttl` | integer | - | Cache TTL in seconds |
| `delimiter` | string | `,` | CSV delimiter |
| `header` | boolean | `true` | CSV has header row |
| `encoding` | string | `utf-8` | File encoding |
| `xpath` | string | - | XPath for XML extraction |

---

### q:transaction

Wraps queries in a database transaction for atomic operations.

```xml
<q:transaction>
  <q:query datasource="db">
    UPDATE accounts SET balance = balance - :amount WHERE id = :from
    <q:param name="from" value="{fromAccount}" />
    <q:param name="amount" value="{amount}" />
  </q:query>
  <q:query datasource="db">
    UPDATE accounts SET balance = balance + :amount WHERE id = :to
    <q:param name="to" value="{toAccount}" />
    <q:param name="amount" value="{amount}" />
  </q:query>
</q:transaction>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `isolationLevel` | enum | `READ_COMMITTED` | Isolation: `READ_UNCOMMITTED`, `READ_COMMITTED`, `REPEATABLE_READ`, `SERIALIZABLE` |

**Children:** `q:query`, `q:set`, `q:if`

---

## Components

### q:import

Imports a component for use within the current component.

```xml
<q:import component="Header" />
<q:import component="Button" from="./components/ui" />
<q:import component="AdminLayout" as="Layout" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `component` | string | **required** | Component name to import |
| `from` | path | - | Path to component file |
| `as` | string | - | Alias name |

---

### q:slot

Defines a content projection slot for component composition.

```xml
<!-- Default slot -->
<q:slot />

<!-- Named slot -->
<q:slot name="header" />

<!-- Slot with default content -->
<q:slot name="footer">
  <p>Default footer content</p>
</q:slot>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | `default` | Slot name |

---

## Actions & Forms

### q:action

Defines a form action handler with validation and CSRF protection.

```xml
<q:action name="createUser" method="POST" csrf="true">
  <q:param name="email" type="email" required="true" />
  <q:param name="password" type="string" required="true" minlength="8" />

  <q:query datasource="db">
    INSERT INTO users (email, password_hash)
    VALUES (:email, :passwordHash)
    <q:param name="email" value="{email}" />
    <q:param name="passwordHash" value="{hashPassword(password)}" />
  </q:query>

  <q:redirect url="/users" flash="User created!" />
</q:action>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Action name |
| `method` | enum | `POST` | HTTP method: `POST`, `PUT`, `DELETE`, `PATCH` |
| `csrf` | boolean | `true` | Enable CSRF protection |
| `rate_limit` | string | - | Rate limit (e.g., '10/minute') |
| `require_auth` | boolean | `false` | Require authentication |

**Children:** `q:param`, `q:query`, `q:set`, `q:redirect`, `q:flash`

---

### q:redirect

Redirects to another URL, optionally with a flash message.

```xml
<q:redirect url="/thank-you" />
<q:redirect url="/products" flash="Product created!" status="303" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | url | **required** | Target URL |
| `flash` | string | - | Flash message to display |
| `status` | integer | `302` | HTTP status code (301, 302, 303, 307, 308) |

---

### q:flash

Sets a flash message to be displayed once after redirect.

```xml
<q:flash type="success" message="Operation completed!" />
<q:flash type="error">An error occurred</q:flash>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | enum | `info` | Message type: `info`, `success`, `warning`, `error` |
| `message` | string | - | Message text (or use tag content) |

---

## LLM Integration

### q:llm

Invokes an LLM (Large Language Model) via Ollama or compatible API.

```xml
<q:llm name="response" model="phi3">
  <q:prompt>Summarize this text: {text}</q:prompt>
</q:llm>

<q:llm name="chat" model="mistral" responseFormat="json">
  <q:message role="system">You are a helpful assistant</q:message>
  <q:message role="user">{question}</q:message>
</q:llm>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Result variable name |
| `model` | string | - | Model name (phi3, mistral, llama3) |
| `endpoint` | url | - | Custom API endpoint |
| `system` | string | - | System prompt |
| `responseFormat` | enum | - | Response format: `text`, `json` |
| `temperature` | decimal | - | Temperature (0.0-2.0) |
| `maxTokens` | integer | - | Max tokens in response |
| `timeout` | integer | `30` | Request timeout in seconds |
| `cache` | boolean | `false` | Cache LLM responses |

**Children:** `q:prompt`, `q:message`

---

### q:prompt

Defines the prompt text for an LLM invocation.

```xml
<q:prompt>Translate to French: {text}</q:prompt>
```

**Parent:** `q:llm`

---

### q:message

Defines a chat message for LLM conversation mode.

```xml
<q:message role="system">You are a helpful assistant</q:message>
<q:message role="user">{userQuestion}</q:message>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `role` | enum | `user` | Message role: `system`, `user`, `assistant` |

**Parent:** `q:llm`

---

### q:knowledge

Defines a knowledge base for RAG (Retrieval Augmented Generation).

```xml
<q:knowledge name="docs" model="nomic-embed-text">
  <q:source type="file" path="./docs/" />
  <q:source type="url" url="https://docs.example.com" />
</q:knowledge>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | **required** | Knowledge base name |
| `model` | string | - | Embedding model |
| `chunkSize` | integer | `500` | Text chunk size |
| `chunkOverlap` | integer | `50` | Overlap between chunks |

**Children:** `q:source`

---

## Utilities

### q:mail

Sends an email (ColdFusion cfmail-inspired).

```xml
<q:mail to="{user.email}" from="noreply@app.com" subject="Welcome!">
  <h1>Welcome, {user.name}!</h1>
  <p>Thank you for signing up.</p>
</q:mail>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `to` | string | **required** | Recipient email address(es) |
| `subject` | string | **required** | Email subject |
| `from` | string | - | Sender email address |
| `cc` | string | - | CC recipients |
| `bcc` | string | - | BCC recipients |
| `replyTo` | string | - | Reply-To address |
| `type` | enum | `html` | Content type: `html`, `text` |
| `charset` | string | `UTF-8` | Character encoding |

---

### q:file

Handles file operations (upload, delete, move, copy).

```xml
<q:file action="upload" file="{avatar}" destination="./uploads/avatars/" />
<q:file action="delete" file="{filePath}" />
<q:file action="move" file="{source}" destination="{target}" nameConflict="makeUnique" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | enum | `upload` | Operation: `upload`, `delete`, `move`, `copy` |
| `file` | string | **required** | File variable or path |
| `destination` | path | `./uploads/` | Destination path |
| `nameConflict` | enum | `error` | Conflict handling: `error`, `overwrite`, `skip`, `makeUnique` |
| `result` | string | - | Variable to store result |

---

### q:log

Logs a message for debugging or monitoring.

```xml
<q:log message="Processing user {userId}" level="debug" />
<q:log var="userData" level="info" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | expression | - | Log message (supports databinding) |
| `level` | enum | `info` | Log level: `debug`, `info`, `warn`, `error` |
| `var` | string | - | Variable to dump |

---

### q:dump

Dumps a variable's contents for debugging.

```xml
<q:dump var="users" />
<q:dump var="config" label="Configuration" format="json" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `var` | string | **required** | Variable to dump |
| `label` | string | - | Label for the output |
| `format` | enum | `auto` | Output format: `auto`, `json`, `table`, `tree` |

---

## Events

### q:onEvent

Subscribes to and handles events.

```xml
<q:onEvent event="user.created" maxRetries="3" retryDelay="30s">
  <q:mail to="{event.data.email}" subject="Welcome!">
    Welcome to our platform!
  </q:mail>
</q:onEvent>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | string | **required** | Event pattern (supports wildcards) |
| `queue` | string | - | Queue name for message broker |
| `maxRetries` | integer | `0` | Maximum retry attempts |
| `retryDelay` | string | - | Delay between retries (e.g., '30s') |
| `deadLetter` | string | - | Dead letter queue name |
| `filter` | expression | - | Filter expression |
| `concurrent` | integer | `1` | Concurrent handler count |
| `timeout` | string | - | Handler timeout |

**Children:** `q:set`, `q:if`, `q:query`, `q:invoke`

---

### q:dispatchEvent

Publishes an event to the event bus.

```xml
<q:dispatchEvent event="user.created" data="{userData}" />
<q:dispatchEvent event="order.placed" data="{order}" priority="high" delay="5s" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | string | **required** | Event name |
| `data` | expression | - | Event payload |
| `queue` | string | - | Target queue |
| `exchange` | string | - | Exchange name |
| `routingKey` | string | - | Routing key |
| `priority` | enum | `normal` | Priority: `low`, `normal`, `high` |
| `delay` | string | - | Delay before delivery (e.g., '5s') |
| `ttl` | string | - | Time-to-live (e.g., '60s') |

---

## Persistence

### q:persist

Configures state persistence for variables.

```xml
<q:persist scope="local" prefix="myapp_">
  <q:var name="theme" />
  <q:var name="locale" />
</q:persist>

<q:persist scope="session" encrypt="true" ttl="3600">
  <q:var name="tempToken" />
</q:persist>
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | enum | `local` | Storage scope: `local`, `session`, `sync` |
| `prefix` | string | - | Key prefix in storage |
| `key` | string | - | Custom storage key |
| `encrypt` | boolean | `false` | Encrypt stored values |
| `ttl` | integer | - | TTL in seconds |

**Children:** `q:var`

**See also:** [State Persistence](/features/state-persistence)

---

### q:route

Defines a route in an application.

```xml
<q:route path="/" method="GET" />
<q:route path="/users/:id" method="GET" />
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | **required** | URL path pattern |
| `method` | enum | `GET` | HTTP method: `GET`, `POST`, `PUT`, `DELETE`, `PATCH` |

**Parent:** `q:application`

---

### q:script

Embeds custom script code within a component.

```xml
<q:script>
  // Custom JavaScript or Python code
  function customHelper(value) {
    return value.toUpperCase();
  }
</q:script>
```

---

## Related Documentation

- [UI Tags Reference](/api/ui-reference) - UI component tags
- [Attributes Reference](/api/attributes-reference) - Common attributes
- [State Management](/guide/state-management) - Variable management
- [Query Guide](/guide/query) - Database queries
