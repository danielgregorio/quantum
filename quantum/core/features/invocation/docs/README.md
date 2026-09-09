# q:invoke - Universal Invocation Component

## Overview

`<q:invoke>` is Quantum's unified invocation system that provides a single, consistent interface for calling functions, components, external APIs, and remote services. It eliminates the need for separate tags (q:http, q:rpc, q:graphql, etc.) by using intelligent detection based on attributes.

## Philosophy

1. **Single Mental Model** - "Invoke something" works everywhere
2. **Progressive Complexity** - Start simple, grow as needed
3. **Protocol Agnostic** - Same syntax for local calls, HTTP, GraphQL, gRPC
4. **Service Mesh Ready** - Seamless transition from local to distributed
5. **Consistent Errors** - Unified error handling across all invocation types

## Key Innovation

**Before (Multiple Tags):**
```xml
<q:http url="..." />
<q:rpc service="..." />
<q:graphql endpoint="..." />
<q:grpc service="..." />
```

**After (One Tag):**
```xml
<q:invoke url="..." />              <!-- HTTP -->
<q:invoke service="..." />           <!-- RPC -->
<q:invoke url="..." type="graphql"/> <!-- GraphQL -->
<q:invoke url="..." type="grpc"/>    <!-- gRPC -->
```

## Basic Usage

### Local Function Call
```xml
<q:invoke name="result" function="calculateTotal">
    <q:arg name="items" value="{cart.items}" />
    <q:arg name="taxRate" value="0.08" />
</q:invoke>

<!-- Use result -->
<p>Total: ${result}</p>
```

### Local Component Call
```xml
<q:invoke name="userData" component="UserService.getUser">
    <q:arg name="userId" value="{id}" />
</q:invoke>

<!-- Use result -->
<h1>Welcome {userData.name}!</h1>
```

### HTTP REST API
```xml
<q:invoke name="weather"
          url="https://api.weather.com/forecast"
          method="GET">
    <q:header name="API-Key" value="{apiKey}" />
    <q:param name="city" value="{userCity}" />
    <q:param name="units" value="metric" />
</q:invoke>

<p>Temperature: {weather.temp}°C</p>
```

### POST Request with JSON Body
```xml
<q:invoke name="createUser"
          url="https://api.example.com/users"
          method="POST">
    <q:header name="Authorization" value="Bearer {token}" />
    <q:header name="Content-Type" value="application/json" />
    <q:body>
        {
            "name": "{userName}",
            "email": "{userEmail}",
            "role": "user"
        }
    </q:body>
</q:invoke>
```

## Attributes

### Core Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `name` | string | Variable name for result | `name="userData"` |
| `function` | string | Local q:function name | `function="calculateTotal"` |
| `component` | string | Local component path | `component="UserService.getUser"` |
| `url` | string | External HTTP/API URL | `url="https://api.com/data"` |
| `service` | string | Remote Quantum service | `service="order-service"` |
| `method` | string | HTTP method | `method="POST"` (default: GET) |
| `type` | string | Protocol type | `type="graphql"` |

### Optional Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | integer | 30000 | Timeout in milliseconds |
| `retry` | integer | 0 | Number of retry attempts |
| `cache` | boolean | false | Enable response caching |
| `ttl` | integer | 300 | Cache TTL in seconds |
| `async` | boolean | false | Async execution (future) |

## Detection Logic

`<q:invoke>` automatically detects the invocation type:

```
Has 'function' attribute?
  → Local function call

Has 'component' attribute?
  → Local component invocation

Has 'url' + no 'type'?
  → HTTP REST request

Has 'url' + 'type="graphql"'?
  → GraphQL query

Has 'service' attribute?
  → Remote Quantum service

Has 'url' + 'type="grpc"'?
  → gRPC call
```

## Child Elements

### `<q:arg>` - Function/Component Arguments
```xml
<q:invoke function="myFunction">
    <q:arg name="userId" value="{id}" type="integer" />
    <q:arg name="includeDetails" value="true" type="boolean" />
</q:invoke>
```

### `<q:header>` - HTTP Headers
```xml
<q:invoke url="https://api.com/data">
    <q:header name="Authorization" value="Bearer {token}" />
    <q:header name="Accept" value="application/json" />
</q:invoke>
```

### `<q:param>` - Query Parameters (GET)
```xml
<q:invoke url="https://api.com/search" method="GET">
    <q:param name="q" value="{searchTerm}" />
    <q:param name="limit" value="10" type="integer" />
</q:invoke>
```

### `<q:body>` - Request Body (POST/PUT/PATCH)
```xml
<q:invoke url="https://api.com/users" method="POST">
    <q:body>{
        "name": "{userName}",
        "email": "{userEmail}"
    }</q:body>
</q:invoke>
```

## Result Object

All invocations return a result object accessible via `{name_result}`:

```xml
<q:invoke name="data" url="https://api.com/users" />

<!-- Access result metadata -->
<q:if condition="{data_result.success}">
    <p>Loaded {data_result.recordCount} users in {data_result.executionTime}ms</p>
    <q:loop items="{data}" var="user">
        <p>{user.name}</p>
    </q:loop>
<q:else>
    <p>Error: {data_result.error.message}</p>
    <q:log level="error">Failed to load users: {data_result.error}</q:log>
</q:else>
</q:if>
```

### Result Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether invocation succeeded |
| `data` | any | Response data (varies by type) |
| `error` | object | Error object (if failed) |
| `statusCode` | integer | HTTP status code (HTTP only) |
| `headers` | object | Response headers (HTTP only) |
| `executionTime` | decimal | Execution time in milliseconds |
| `cached` | boolean | Whether result was cached |

## Implementation Phases

### Phase 1: Foundation (MVP) ✅ Planned
- Local function calls (`function="..."`)
- Local component calls (`component="..."`)
- HTTP REST (GET, POST, PUT, DELETE, PATCH)
- Headers, query params, JSON body
- Basic auth (Bearer, API Key)
- Error handling with result objects

### Phase 2: Advanced Protocols
- GraphQL (`type="graphql"`)
- SOAP (`type="soap"`)
- Remote Quantum services (`service="..."`)
- OAuth 2.0 authentication
- File uploads (multipart/form-data)

### Phase 3: Real-time & Messaging
- WebSockets (`type="websocket"`)
- gRPC (`type="grpc"`)
- Message queues (`type="amqp"`)
- Streaming responses

## Examples

### Example 1: Weather API
```xml
<q:component name="weather-widget">
    <q:param name="city" type="string" default="London" />

    <q:invoke name="weather"
              url="https://api.openweathermap.org/data/2.5/weather"
              method="GET">
        <q:param name="q" value="{city}" />
        <q:param name="appid" value="{env.WEATHER_API_KEY}" />
        <q:param name="units" value="metric" />
    </q:invoke>

    <q:if condition="{weather_result.success}">
        <div class="weather-card">
            <h2>{weather.name}</h2>
            <p class="temp">{weather.main.temp}°C</p>
            <p>{weather.weather[0].description}</p>
        </div>
    <q:else>
        <p>Unable to load weather data</p>
    </q:else>
    </q:if>
</q:component>
```

### Example 2: User Authentication
```xml
<q:invoke name="login"
          url="https://api.myapp.com/auth/login"
          method="POST">
    <q:header name="Content-Type" value="application/json" />
    <q:body>{
        "email": "{email}",
        "password": "{password}"
    }</q:body>
</q:invoke>

<q:if condition="{login_result.success}">
    <q:set name="authToken" value="{login.token}" scope="session" />
    <q:set name="currentUser" value="{login.user}" scope="session" />
    <q:return value="redirect:/dashboard" />
<q:else>
    <p class="error">{login_result.error.message}</p>
</q:else>
</q:if>
```

### Example 3: Microservice Call
```xml
<!-- Local development - calls local component -->
<q:invoke name="order" component="OrderService.createOrder">
    <q:arg name="customerId" value="{customerId}" />
    <q:arg name="items" value="{cart.items}" />
</q:invoke>

<!-- Production - calls remote service (same syntax!) -->
<q:invoke name="order"
          service="order-service"
          component="OrderService.createOrder">
    <q:arg name="customerId" value="{customerId}" />
    <q:arg name="items" value="{cart.items}" />
</q:invoke>
```

### Example 4: Function Call with Caching
```xml
<q:invoke name="expensiveCalc"
          function="calculateComplexMetrics"
          cache="true"
          ttl="600">
    <q:arg name="dataset" value="{largeDataset}" />
</q:invoke>

<!-- Subsequent calls within 10 minutes use cached result -->
```

## Error Handling

### Result-Based Pattern (Recommended)
```xml
<q:invoke name="data" url="https://api.com/users" />

<q:if condition="{data_result.success}">
    <!-- Handle success -->
    <q:loop items="{data}" var="user">
        <p>{user.name}</p>
    </q:loop>
<q:else>
    <!-- Handle error -->
    <q:log level="error">API Error: {data_result.error.message}</q:log>
    <q:set name="data" value="[]" type="array" />
</q:else>
</q:if>
```

### Fallback Data
```xml
<q:invoke name="products"
          url="https://api.com/products"
          timeout="5000">
    <q:header name="API-Key" value="{apiKey}" />
</q:invoke>

<q:if condition="{products_result.error}">
    <!-- Use static fallback data -->
    <q:data name="products" source="fallback/products.json" type="json" />
</q:if>
```

## Authentication Patterns

### Bearer Token
```xml
<q:invoke url="https://api.com/protected" method="GET">
    <q:header name="Authorization" value="Bearer {session.authToken}" />
</q:invoke>
```

### API Key
```xml
<q:invoke url="https://api.com/data" method="GET">
    <q:header name="X-API-Key" value="{env.API_KEY}" />
</q:invoke>
```

### Basic Auth
```xml
<q:invoke url="https://api.com/data" method="GET">
    <q:header name="Authorization" value="Basic {base64(username + ':' + password)}" />
</q:invoke>
```

## Benefits Over Multiple Tags

| Aspect | Multiple Tags | q:invoke |
|--------|---------------|----------|
| **Learning Curve** | 6+ tags to learn | 1 tag to learn |
| **Consistency** | Different error handling per tag | Unified error handling |
| **Scalability** | Rewrite code when moving to microservices | Change 1 attribute |
| **Future-proof** | New protocol = new tag | New protocol = new type value |
| **Documentation** | 6+ separate pages | 1 comprehensive page |

## Integration with Other Features

### With q:data (Transform API responses)
```xml
<q:invoke name="apiUsers" url="https://api.com/users" />

<q:data name="activeUsers" source="{apiUsers}" type="transform">
    <q:filter condition="{status == 'active'}" />
    <q:sort by="name" />
</q:data>
```

### With q:loop (Iterate results)
```xml
<q:invoke name="products" url="https://api.com/products" />

<q:loop items="{products}" var="product">
    <div class="product-card">
        <h3>{product.name}</h3>
        <p>${product.price}</p>
    </div>
</q:loop>
```

### With q:function (Wrap invocation)
```xml
<q:function name="getUser" access="public">
    <q:param name="userId" type="integer" required="true" />

    <q:invoke name="user" url="https://api.com/users/{userId}" method="GET">
        <q:header name="API-Key" value="{env.API_KEY}" />
    </q:invoke>

    <q:return value="{user}" />
</q:function>
```

## Migration Path

### From Separate Tags (Future)
If you currently use hypothetical separate tags:
```xml
<!-- OLD -->
<q:http url="..." method="GET" />
<q:rpc service="..." function="..." />

<!-- NEW -->
<q:invoke url="..." method="GET" />
<q:invoke service="..." component="..." />
```

### Local to Remote
```xml
<!-- Development -->
<q:invoke component="PaymentService.charge" ... />

<!-- Production (just change one attribute!) -->
<q:invoke service="payment-service" component="PaymentService.charge" ... />
```

## See Also

- [q:data - Data Import & Transform](../../data_import/docs/README.md)
- [q:function - Function Definitions](../../functions/src/README.md)
- [Error Handling Guide](../../../../docs/guide/error-handling.md)
