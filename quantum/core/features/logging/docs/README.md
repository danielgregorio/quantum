# q:log - Structured Logging

Declarative structured logging with async output, multiple severity levels, and external service integration.

## Overview

`q:log` provides production-ready logging capabilities for Quantum applications. Unlike traditional console.log, it offers:

- **Structured logging** - JSON format with context data
- **Multiple severity levels** - trace, debug, info, warning, error, critical
- **Conditional logging** - Log only when conditions are met
- **Async non-blocking** - No performance impact
- **External integrations** - Sentry, Datadog, webhooks (Phase 2)

## Basic Usage

### Simple Logging

```xml
<q:log level="info" message="User logged in successfully" />
```

### Log Levels

```xml
<q:log level="trace" message="Entering function processPayment" />
<q:log level="debug" message="Processing user authentication" />
<q:log level="info" message="Application started" />
<q:log level="warning" message="Database connection slow" />
<q:log level="error" message="Failed to process request" />
<q:log level="critical" message="Database connection lost" />
```

### Databinding in Messages

```xml
<q:set var="userName" value="Alice" />
<q:log level="info" message="User {userName} logged in" />
```

## Structured Context Data

Add structured JSON context to logs for better debugging:

```xml
<q:set var="user" value='{"id": 123, "email": "alice@example.com"}' operation="json" />
<q:log level="info"
       message="User login successful"
       context="{user}" />
```

Output:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "info",
  "message": "User login successful",
  "context": {
    "id": 123,
    "email": "alice@example.com"
  }
}
```

## Conditional Logging

Use the `when` attribute to log only when specific conditions are met:

```xml
<q:invoke name="api" url="https://api.example.com/data" method="GET" />

<q:log level="error"
       message="API call failed: {api_result.error.message}"
       when="{!api_result.success}"
       context="{api_result.error}" />

<q:log level="info"
       message="API call succeeded"
       when="{api_result.success}" />
```

## Integration with Features

### Logging in Loops

```xml
<q:loop var="user" in="{users}">
  <q:log level="debug" message="Processing user {user.id}" />
</q:loop>
```

### Logging with Conditionals

```xml
<q:if condition="{status == 'error'}">
  <q:log level="error" message="Error status detected" />
<q:else>
  <q:log level="info" message="Status OK" />
</q:if>
```

### Logging Data Import Results

```xml
<q:data name="users" source="data/users.csv" type="csv">
  <q:column name="id" type="integer" />
  <q:column name="name" type="string" />
</q:data>

<q:log level="info"
       message="Loaded {users_result.recordCount} users in {users_result.loadTime}ms"
       when="{users_result.success}" />

<q:log level="error"
       message="Failed to load users: {users_result.error.message}"
       when="{!users_result.success}" />
```

## Real-World Patterns

### User Authentication Tracking

```xml
<q:set var="user" value='{"id": 123, "email": "alice@example.com", "ip": "192.168.1.1"}' operation="json" />

<q:log level="info"
       message="User login: {user.email}"
       context='{"userId": {user.id}, "ip": {user.ip}}' />
```

### Payment Processing Audit

```xml
<q:set var="payment" value='{"orderId": "ORD-123", "amount": 99.99, "status": "completed"}' operation="json" />

<q:log level="info"
       message="Payment processed: {payment.orderId} - ${payment.amount}"
       context="{payment}" />
```

### API Performance Monitoring

```xml
<q:invoke name="api" url="https://api.example.com/data" method="GET" />

<q:log level="warning"
       message="Slow API response: {api_result.loadTime}ms"
       when="{api_result.loadTime > 1000}"
       context='{"url": "https://api.example.com/data", "duration": {api_result.loadTime}}' />
```

### Security Alerts

```xml
<q:set var="loginAttempts" value="5" />
<q:set var="userIP" value="192.168.1.100" />

<q:log level="critical"
       message="Multiple failed login attempts from {userIP}"
       when="{loginAttempts >= 5}"
       context='{"ip": {userIP}, "attempts": {loginAttempts}}' />
```

### GDPR Compliance Audit

```xml
<q:set var="dataAccess" value='{"userId": 789, "adminId": 101, "action": "view_personal_data"}' operation="json" />

<q:log level="info"
       message="Personal data accessed by admin {dataAccess.adminId}"
       context="{dataAccess}" />
```

## Complex Scenarios

### Multi-Condition Logging

```xml
<q:invoke name="api" url="https://api.example.com/data" method="GET" />

<q:log level="critical"
       message="API failure with slow response"
       when="{!api_result.success AND api_result.loadTime > 2000}" />

<q:log level="warning"
       message="API slow but successful"
       when="{api_result.success AND api_result.loadTime > 1000}" />

<q:log level="info"
       message="API fast and successful"
       when="{api_result.success AND api_result.loadTime <= 1000}" />
```

### Distributed Tracing

```xml
<q:set var="correlationId" value="CORR-ABC-123" />

<q:log level="trace"
       message="[{correlationId}] Request started"
       context='{"correlationId": {correlationId}}' />

<q:invoke name="userService" url="https://api.example.com/users/123" method="GET" />
<q:log level="trace"
       message="[{correlationId}] User service called"
       context='{"correlationId": {correlationId}, "duration": {userService_result.loadTime}}' />

<q:invoke name="orderService" url="https://api.example.com/orders" method="GET" />
<q:log level="trace"
       message="[{correlationId}] Order service called"
       context='{"correlationId": {correlationId}, "duration": {orderService_result.loadTime}}' />
```

### Retry Logic with Logging

```xml
<q:set var="maxRetries" value="3" />
<q:set var="attempt" value="0" />

<q:loop var="retry" in='[1, 2, 3]'>
  <q:set var="attempt" value="{attempt + 1}" operation="increment" />
  <q:log level="debug" message="Attempt {attempt} of {maxRetries}" />

  <q:invoke name="api" url="https://api.example.com/unreliable" method="GET" />

  <q:log level="warning"
         message="Attempt {attempt} failed, retrying..."
         when="{!api_result.success AND attempt < maxRetries}" />

  <q:log level="error"
         message="All {maxRetries} attempts failed"
         when="{!api_result.success AND attempt == maxRetries}" />
</q:loop>
```

## Attributes

### Required
- `level` - Log severity: trace, debug, info, warning, error, critical
- `message` - Log message (supports databinding)

### Optional
- `context` - Structured JSON data object
- `when` - Conditional expression (logs only if true)
- `provider` - Output destination (default: file+console) - Phase 2
- `async` - Async mode (default: true) - Phase 2
- `correlation_id` - Request tracking ID - Phase 2

## Output

Logs are written to:
- **Console** (development) - Beautiful formatted output
- **File** (production) - `quantum_{date}.log` with rotation
- **External services** (Phase 2) - Sentry, Datadog, webhooks

## Best Practices

1. **Use appropriate log levels**
   - `trace` - Very detailed debugging (function entry/exit)
   - `debug` - Debugging information
   - `info` - Important events (user actions, state changes)
   - `warning` - Unexpected but handled situations
   - `error` - Errors that need attention
   - `critical` - System-critical failures

2. **Always add context for errors**
   ```xml
   <q:log level="error"
          message="Payment failed"
          context="{payment_result.error}" />
   ```

3. **Use conditional logging to reduce noise**
   ```xml
   <q:log level="warning"
          message="Slow query"
          when="{query_result.loadTime > 1000}" />
   ```

4. **Include correlation IDs for distributed systems**
   ```xml
   <q:log level="info"
          message="[{correlationId}] Processing request"
          context='{"correlationId": {correlationId}}' />
   ```

5. **Don't log sensitive data**
   - Never log passwords, tokens, credit card numbers
   - Redact PII when logging user data

## Phase 2 Features (Planned)

- **Sentry integration** - Automatic error tracking
- **Datadog integration** - APM and monitoring
- **Custom webhooks** - Send logs to external endpoints
- **Database audit logging** - Store compliance logs
- **Correlation IDs** - Automatic request tracking
- **Sampling** - Reduce log volume in high-traffic scenarios

## Error Handling

Logging uses the result-based pattern. Logs are written asynchronously and won't block execution. If logging fails, the error is silently captured.

## See Also

- [q:dump](../../dump/docs/README.md) - Variable inspection for debugging
- [State Management](../../state_management/docs/README.md) - Variable scoping
- [Data Import](../../data_import/docs/README.md) - Logging import results
