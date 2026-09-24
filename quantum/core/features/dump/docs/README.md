# q:dump - Variable Inspection

Beautiful variable inspection for debugging - like ColdFusion's `<cfdump>` but better.

## Overview

`q:dump` provides instant visual inspection of variables during development. Unlike console.log, it offers:

- **Beautiful HTML output** - Rich formatting with syntax highlighting
- **Type information** - Clear indication of data types
- **Nested structure navigation** - Expandable trees for complex objects
- **Multiple formats** - HTML (default), JSON, or plain text
- **Depth control** - Limit output for deeply nested structures
- **Conditional dumping** - Only dump when conditions are met

## Basic Usage

### Dump Any Variable

```xml
<q:set var="message" value="Hello, World!" />
<q:dump var="{message}" />
```

### Dump with Label

```xml
<q:set var="user" value='{"id": 1, "name": "Alice"}' operation="json" />
<q:dump var="{user}" label="User Object" />
```

## Data Types

### Primitives

```xml
<q:set var="text" value="Hello" />
<q:dump var="{text}" label="String" />

<q:set var="count" value="42" />
<q:dump var="{count}" label="Integer" />

<q:set var="active" value="true" operation="json" />
<q:dump var="{active}" label="Boolean" />

<q:set var="nothing" value="null" operation="json" />
<q:dump var="{nothing}" label="Null Value" />
```

### Arrays

```xml
<q:set var="colors" value='["red", "green", "blue"]' operation="json" />
<q:dump var="{colors}" label="Colors Array" />
```

Output:
```
Colors Array (array[3]):
  [0] => "red" (string)
  [1] => "green" (string)
  [2] => "blue" (string)
```

### Objects

```xml
<q:set var="user" value='{"id": 1, "name": "Alice", "email": "alice@example.com"}' operation="json" />
<q:dump var="{user}" label="User Object" />
```

Output:
```
User Object (object):
  id => 1 (integer)
  name => "Alice" (string)
  email => "alice@example.com" (string)
```

### Nested Structures

```xml
<q:set var="nested" value='{"user": {"name": "Bob", "address": {"city": "NYC"}}}' operation="json" />
<q:dump var="{nested}" label="Nested Object" />
```

## Output Formats

### HTML Format (Default)

Rich, syntax-highlighted output with expandable sections:

```xml
<q:dump var="{data}" format="html" />
```

### JSON Format

Pretty-printed JSON:

```xml
<q:dump var="{data}" format="json" />
```

Output:
```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

### Text Format

Plain text tree structure:

```xml
<q:dump var="{data}" format="text" />
```

## Depth Control

Limit nesting depth for deeply nested structures:

```xml
<q:set var="deep" value='{"a": {"b": {"c": {"d": "value"}}}}' operation="json" />
<q:dump var="{deep}" depth="2" label="Depth Limited" />
```

Output only shows 2 levels deep, preventing information overload.

## Conditional Dumping

Use `when` to dump only when needed:

```xml
<q:invoke name="api" url="https://api.example.com/data" method="GET" />

<q:dump var="{api}"
        when="{!api_result.success}"
        label="API Error Debug" />
```

Only dumps if the API call failed.

## Integration with Features

### Dump Loop Variables

```xml
<q:set var="items" value='[{"id": 1, "value": 10}, {"id": 2, "value": 20}]' operation="json" />

<q:loop var="item" in="{items}">
  <q:dump var="{item}" label="Loop Item {item.id}" />
</q:loop>
```

### Dump API Responses

```xml
<q:invoke name="api" url="https://api.example.com/users/1" method="GET" />
<q:dump var="{api}" label="API Response" />
```

### Dump Data Import Results

```xml
<q:data name="users" source="data/users.csv" type="csv">
  <q:column name="id" type="integer" />
  <q:column name="name" type="string" />
</q:data>

<q:dump var="{users}" label="Imported Users" />
<q:dump var="{users_result}" label="Import Metadata" />
```

### Dump Function Results

```xml
<q:function name="add" params="a,b">
  <q:set var="result" value="{a + b}" operation="add" />
  <q:return value="{result}" />
</q:function>

<q:set var="sum" value="{add(5, 3)}" operation="function" />
<q:dump var="{sum}" label="Function Result" />
```

### Dump Validation State

```xml
<q:set var="email" value="test@example.com" validate="email" />
<q:dump var="{email_valid}" label="Email Valid?" />
```

## Real-World Debugging Patterns

### Debug API Response Structure

```xml
<q:invoke name="api" url="https://api.example.com/users/1" method="GET" />
<q:dump var="{api}" when="{!api_result.success}" label="API Error Debug" />
```

### Inspect Session State

```xml
<q:set var="session" value='{"userId": 123, "role": "admin", "permissions": ["read", "write"]}' operation="json" />
<q:dump var="{session}" label="Session State" />
```

### Troubleshoot Calculation

```xml
<q:set var="price" value="100" />
<q:set var="discount" value="0.2" />
<q:set var="final" value="{price - (price * discount)}" operation="subtract" />
<q:dump var="{final}" label="Final Price Calculation" />
```

### Debug Validation Failure

```xml
<q:set var="email" value="invalid-email" validate="email" />
<q:dump var="{email}" when="{!email_valid}" label="Failed Validation" />
```

### Inspect Transformed Data

```xml
<q:data name="raw" source="data/products.csv" type="csv">
  <q:column name="price" type="decimal" />
  <q:transform>
    <q:filter condition="{price > 50}" />
  </q:transform>
</q:data>

<q:dump var="{raw}" label="Filtered Products" />
```

### Debug Loop Iteration

```xml
<q:set var="items" value='[{"id": 1, "value": 10}, {"id": 2, "value": 20}]' operation="json" />

<q:loop var="item" in="{items}">
  <q:dump var="{item}" when="{item.value > 15}" label="High Value Item" />
</q:loop>
```

### Debug Type Conversion

```xml
<q:set var="stringNum" value="42" />
<q:set var="intNum" value="42" operation="json" />

<q:dump var="{stringNum}" label="String Number" />
<q:dump var="{intNum}" label="Integer Number" />
```

## Complex Scenarios

### Compare Before and After

```xml
<q:set var="before" value='[1, 2, 3, 4, 5]' operation="json" />
<q:dump var="{before}" label="Before Filter" />

<q:data name="after" source="{before}" type="transform">
  <q:transform>
    <q:filter condition="{value > 2}" />
  </q:transform>
</q:data>

<q:dump var="{after}" label="After Filter" />
```

### Multiple Format Dumps

```xml
<q:set var="data" value='{"key": "value", "count": 42}' operation="json" />

<q:dump var="{data}" format="html" label="HTML Format" />
<q:dump var="{data}" format="json" label="JSON Format" />
<q:dump var="{data}" format="text" label="Text Format" />
```

### Dump Chain Results

```xml
<q:set var="input" value="100" />
<q:dump var="{input}" label="Step 1: Input" />

<q:set var="doubled" value="{input * 2}" operation="multiply" />
<q:dump var="{doubled}" label="Step 2: Doubled" />

<q:set var="final" value="{doubled + 50}" operation="add" />
<q:dump var="{final}" label="Step 3: Final" />
```

### Dump Multi-API Responses

```xml
<q:invoke name="api1" url="https://api1.example.com/data" method="GET" />
<q:invoke name="api2" url="https://api2.example.com/data" method="GET" />

<q:dump var="{api1}" label="API 1 Response" />
<q:dump var="{api2}" label="API 2 Response" />
```

### Dump State Machine Transitions

```xml
<q:set var="state" value="pending" />
<q:dump var="{state}" label="Initial State" />

<q:set var="state" value="approved" />
<q:dump var="{state}" label="After Approval" />

<q:set var="state" value="completed" />
<q:dump var="{state}" label="Final State" />
```

## Attributes

### Required
- `var` - Variable to inspect

### Optional
- `label` - Identifying label (default: variable name)
- `format` - Output format: html, json, text (default: html)
- `depth` - Max depth for nesting (default: 10)
- `when` - Conditional expression (default: always)
- `expand` - Auto-expand depth (default: 2) - Phase 2
- `show_types` - Show type information (default: true) - Phase 2

## Best Practices

1. **Always use labels for clarity**
   ```xml
   <q:dump var="{user}" label="Current User" />
   ```

2. **Use conditional dumping to reduce noise**
   ```xml
   <q:dump var="{error}" when="{hasError}" label="Error State" />
   ```

3. **Limit depth for complex objects**
   ```xml
   <q:dump var="{complexObject}" depth="3" label="Limited Depth" />
   ```

4. **Use appropriate format for your needs**
   - `html` - Best for browser viewing (default)
   - `json` - Best for API responses
   - `text` - Best for logs

5. **Remove dumps before production**
   - Use `when="{environment == 'development'}"` for safety

## Edge Cases

### Empty Values

```xml
<q:set var="empty" value="" />
<q:dump var="{empty}" label="Empty String" />

<q:set var="emptyArr" value='[]' operation="json" />
<q:dump var="{emptyArr}" label="Empty Array" />

<q:set var="emptyObj" value='{}' operation="json" />
<q:dump var="{emptyObj}" label="Empty Object" />
```

### Undefined Variables

```xml
<q:dump var="{undefinedVariable}" label="Undefined Var" />
```

Shows: `Undefined Var => undefined`

### Special Characters

```xml
<q:set var="special" value="&lt;&gt;&amp;&quot;" />
<q:dump var="{special}" label="Special Chars" />
```

Properly escapes and displays special characters.

### Unicode

```xml
<q:set var="unicode" value="你好 🌍" />
<q:dump var="{unicode}" label="Unicode" />
```

Renders Unicode characters correctly.

## Performance Considerations

- Dumping is synchronous and blocks rendering
- Limit dumps in loops (use conditional `when`)
- Use `depth` to control output size
- Remove dumps in production

## Phase 2 Features (Planned)

- **Expandable/collapsible trees** - Interactive JavaScript UI
- **Search within dumps** - Filter displayed data
- **Side-by-side comparison** - Compare two variables
- **Export to file** - Save dump output
- **Custom themes** - Customize colors and styling
- **Performance metrics** - Show memory size and dump time

## See Also

- [q:log](../../logging/docs/README.md) - Structured logging for production
- [State Management](../../state_management/docs/README.md) - Variable scoping
- [Data Import](../../data_import/docs/README.md) - Dump imported data
