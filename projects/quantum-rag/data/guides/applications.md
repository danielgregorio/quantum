# Applications

Quantum applications are deployable services that can serve web pages, APIs, or handle background jobs. They extend the component system to create fully functional applications.

## Application Types

Quantum supports three main application types:

### HTML Applications (`type="html"`)

Serve web pages and HTML content:

```xml
<q:application id="webapp" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <q:return value="<h1>Welcome to Quantum!</h1>" />
  </q:route>
</q:application>
```

### API Applications (`type="api"`)

Serve JSON data and REST endpoints:

```xml
<q:application id="api" type="api" xmlns:q="https://quantum.lang/ns">
  <q:route path="/users" method="GET">
    <q:loop type="array" var="user" items='[{"id": 1, "name": "Alice"}]'>
      <q:return value='{"id": {user.id}, "name": "{user.name}"}' />
    </q:loop>
  </q:route>
</q:application>
```

### Job Applications (`type="job"`)

Background processes and scheduled tasks:

```xml
<q:job id="data-processor" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="100">
    <q:return value="Processing item {i}" />
  </q:loop>
</q:job>
```

## Application Structure

### Required Elements

- **Root Element**: `q:application` or `q:job`
- **ID Attribute**: Unique identifier for the application
- **Type Attribute**: Application type (`html`, `api`, or omitted for jobs)
- **Namespace**: `xmlns:q="https://quantum.lang/ns"`

### Routes (`q:route`)

Define endpoints for web applications:

```xml
<q:route path="/endpoint" method="HTTP_METHOD">
  <!-- Route logic here -->
</q:route>
```

#### Supported HTTP Methods

- `GET` - Retrieve data
- `POST` - Create/submit data
- `PUT` - Update data
- `DELETE` - Remove data

## HTML Applications

### Basic Web Server

```xml
<q:application id="simple-web" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <q:return value="<!DOCTYPE html>" />
    <q:return value="<html><head><title>Quantum App</title></head>" />
    <q:return value="<body><h1>Hello from Quantum!</h1></body></html>" />
  </q:route>
</q:application>
```

### Dynamic Content

```xml
<q:application id="dynamic-web" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/users" method="GET">
    <q:return value="<html><body><h1>User List</h1><ul>" />
    <q:loop type="list" var="user" items="Alice,Bob,Charlie">
      <q:return value="<li>User: {user}</li>" />
    </q:loop>
    <q:return value="</ul></body></html>" />
  </q:route>
</q:application>
```

### Multiple Pages

```xml
<q:application id="multi-page" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <q:return value="<h1>Home Page</h1>" />
    <q:return value="<a href='/about'>About</a>" />
  </q:route>
  
  <q:route path="/about" method="GET">
    <q:return value="<h1>About Us</h1>" />
    <q:return value="<p>This is a Quantum application</p>" />
    <q:return value="<a href='/'>Home</a>" />
  </q:route>
</q:application>
```

## API Applications

### RESTful API

```xml
<q:application id="rest-api" type="api" xmlns:q="https://quantum.lang/ns">
  <!-- Get all users -->
  <q:route path="/api/users" method="GET">
    <q:loop type="array" var="user" items='[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'>
      <q:return value='{"id": {user.id}, "name": "{user.name}"}' />
    </q:loop>
  </q:route>
  
  <!-- Get user by ID -->
  <q:route path="/api/users/1" method="GET">
    <q:return value='{"id": 1, "name": "Alice", "email": "alice@example.com"}' />
  </q:route>
  
  <!-- API status -->
  <q:route path="/api/status" method="GET">
    <q:return value='{"status": "online", "version": "1.0"}' />
  </q:route>
</q:application>
```

### Dynamic JSON Responses

```xml
<q:application id="dynamic-api" type="api" xmlns:q="https://quantum.lang/ns">
  <q:route path="/api/numbers" method="GET">
    <q:return value='{"numbers": [' />
    <q:loop type="range" var="i" from="1" to="5">
      <q:if condition="i == 5">
        <q:return value='{i}' />
      <q:else>
        <q:return value='{i},' />
      </q:else>
      </q:if>
    </q:loop>
    <q:return value=']}' />
  </q:route>
</q:application>
```

## Job Applications

### Data Processing Job

```xml
<q:job id="data-processor" xmlns:q="https://quantum.lang/ns">
  <q:return value="Starting data processing..." />
  
  <q:loop type="array" var="record" items='[{"id": 1}, {"id": 2}, {"id": 3}]'>
    <q:return value="Processing record {record.id}" />
  </q:loop>
  
  <q:return value="Data processing complete!" />
</q:job>
```

### Report Generation

```xml
<q:job id="report-generator" xmlns:q="https://quantum.lang/ns">
  <q:return value="Generating monthly report..." />
  
  <q:loop type="range" var="day" from="1" to="30">
    <q:if condition="day % 7 == 0">
      <q:return value="Week {day / 7} summary generated" />
    </q:if>
  </q:loop>
  
  <q:return value="Report generation complete" />
</q:job>
```

## Running Applications

### Web Applications

Start an HTML or API application:

```bash
# Run HTML application
python quantum.py run webapp.q

# Access at http://localhost:5000
```

### Job Applications

Execute a job application:

```bash
# Run job
python quantum.py run data-job.q
```

### Debug Mode

Run with detailed debugging:

```bash
python quantum.py run webapp.q --debug
```

## Advanced Features

### Conditional Routes

```xml
<q:application id="conditional-app" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/status" method="GET">
    <q:if condition="server.healthy">
      <q:return value="<h1>Server Status: Healthy</h1>" />
    <q:else>
      <q:return value="<h1>Server Status: Down</h1>" />
    </q:else>
    </q:if>
  </q:route>
</q:application>
```

### Complex Data Processing

```xml
<q:application id="data-app" type="api" xmlns:q="https://quantum.lang/ns">
  <q:route path="/api/analytics" method="GET">
    <q:return value='{"analytics": {' />
    <q:return value='"total_users": ' />
    
    <q:loop type="array" var="user" items="{users}">
      <!-- Count users -->
    </q:loop>
    
    <q:return value=', "active_sessions": 42' />
    <q:return value='}}' />
  </q:route>
</q:application>
```

## Error Handling

### Invalid Routes

```xml
<!-- Missing method attribute -->
<q:route path="/invalid">
  <q:return value="This will cause an error" />
</q:route>
```
**Error:** `Route requires 'method' attribute`

### Runtime Errors

Applications handle runtime errors gracefully:

```xml
<q:route path="/error-prone" method="GET">
  <q:return value="Value: {undefined_variable}" />
</q:route>
```

The application will continue running and log the error.

## Application Configuration

### Port Configuration

Default port is 5000, but can be configured:

```bash
# Custom port (future feature)
python quantum.py run webapp.q --port 8080
```

### Debug Configuration

Enable detailed logging:

```bash
python quantum.py run webapp.q --debug
```

## Best Practices

### Organize Routes Logically

```xml
<q:application id="organized-app" type="api" xmlns:q="https://quantum.lang/ns">
  <!-- Public routes -->
  <q:route path="/" method="GET">
    <q:return value='{"message": "Welcome to API"}' />
  </q:route>
  
  <!-- User routes -->
  <q:route path="/api/users" method="GET">
    <!-- User list logic -->
  </q:route>
  
  <!-- Admin routes -->
  <q:route path="/api/admin/stats" method="GET">
    <!-- Admin statistics -->
  </q:route>
</q:application>
```

### Use Consistent Response Formats

```xml
<!-- API responses should follow consistent structure -->
<q:route path="/api/success" method="GET">
  <q:return value='{"success": true, "data": "result"}' />
</q:route>

<q:route path="/api/error" method="GET">
  <q:return value='{"success": false, "error": "message"}' />
</q:route>
```

### Handle Different HTTP Methods

```xml
<q:application id="crud-api" type="api" xmlns:q="https://quantum.lang/ns">
  <!-- Read -->
  <q:route path="/api/items" method="GET">
    <q:return value='{"items": []}' />
  </q:route>
  
  <!-- Create -->
  <q:route path="/api/items" method="POST">
    <q:return value='{"message": "Item created"}' />
  </q:route>
  
  <!-- Update -->
  <q:route path="/api/items/1" method="PUT">
    <q:return value='{"message": "Item updated"}' />
  </q:route>
  
  <!-- Delete -->
  <q:route path="/api/items/1" method="DELETE">
    <q:return value='{"message": "Item deleted"}' />
  </q:route>
</q:application>
```

## Deployment Considerations

### Production Readiness

- Applications run on Flask development server
- Consider production WSGI server for deployment
- Implement proper error handling and logging

### Security

- Validate all input data
- Implement authentication for protected routes
- Use HTTPS in production

### Performance

- Optimize loop operations for large datasets
- Consider caching for frequently accessed data
- Monitor application performance

## Coming Soon

Future application enhancements:

- **Middleware**: Request/response processing
- **Authentication**: Built-in auth system
- **Database Integration**: Direct database queries
- **Static File Serving**: CSS, JS, images
- **Template System**: HTML template support
- **WebSocket Support**: Real-time communication