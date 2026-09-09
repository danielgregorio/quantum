# Components

Components are the fundamental building blocks of Quantum applications. They encapsulate logic, data processing, and output generation in reusable, modular units.

## Component Structure

Every Quantum component follows this basic structure:

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <!-- Component logic here -->
  <q:return value="component output" />
</q:component>
```

### Required Elements

- **Root Element**: `q:component`
- **Name Attribute**: Unique identifier for the component
- **Namespace**: `xmlns:q="https://quantum.lang/ns"`
- **Content**: The logic and output of your component

## Basic Components

### Simple Output

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

**Output:** `"Hello, World!"`

### Static Lists

```xml
<q:component name="StaticList" xmlns:q="https://quantum.lang/ns">
  <q:return value="Item 1" />
  <q:return value="Item 2" />
  <q:return value="Item 3" />
</q:component>
```

**Output:** `["Item 1", "Item 2", "Item 3"]`

## Dynamic Components

### Using Loops

```xml
<q:component name="NumberList" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

### Using Conditionals

```xml
<q:component name="ConditionalOutput" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:if condition="i % 2 == 0">
      <q:return value="{i} is even" />
    <q:else>
      <q:return value="{i} is odd" />
    </q:else>
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["1 is odd", "2 is even", "3 is odd", "4 is even", "5 is odd"]`

## Component Elements

### Return Statements (`q:return`)

The `q:return` element generates output from your component:

```xml
<!-- Simple value -->
<q:return value="Hello World" />

<!-- Dynamic value with databinding -->
<q:return value="User {userId}: {userName}" />

<!-- Complex expression -->
<q:return value="Total: {price * quantity}" />
```

### Conditional Logic (`q:if`, `q:else`, `q:elseif`)

Components support full conditional logic:

```xml
<q:if condition="score >= 90">
  <q:return value="Grade: A" />
<q:elseif condition="score >= 80">
  <q:return value="Grade: B" />
<q:elseif condition="score >= 70">
  <q:return value="Grade: C" />
<q:else>
  <q:return value="Grade: F" />
</q:else>
</q:if>
```

### Loop Structures (`q:loop`)

Components can use all loop types:

```xml
<!-- Range loop -->
<q:loop type="range" var="i" from="1" to="3">
  <q:return value="Item {i}" />
</q:loop>

<!-- Array loop -->
<q:loop type="array" var="item" items='["apple", "banana"]'>
  <q:return value="Fruit: {item}" />
</q:loop>

<!-- List loop -->
<q:loop type="list" var="color" items="red,green,blue">
  <q:return value="Color: {color}" />
</q:loop>
```

## Advanced Patterns

### Nested Structures

Components can contain deeply nested logic:

```xml
<q:component name="NestedExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="category" from="1" to="2">
    <q:return value="Category {category}:" />
    <q:loop type="range" var="item" from="1" to="3">
      <q:if condition="item % 2 == 0">
        <q:return value="  Even item: {item}" />
      <q:else>
        <q:return value="  Odd item: {item}" />
      </q:else>
      </q:if>
    </q:loop>
  </q:loop>
</q:component>
```

### Data Processing

Components can process complex data structures:

```xml
<q:component name="DataProcessor" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="user" items='[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'>
    <q:if condition="user.age >= 30">
      <q:return value="Senior: {user.name} ({user.age})" />
    <q:else>
      <q:return value="Junior: {user.name} ({user.age})" />
    </q:else>
    </q:if>
  </q:loop>
</q:component>
```

## Component Naming

### Naming Conventions

- Use **PascalCase** for component names
- Choose descriptive, meaningful names
- Avoid abbreviations when possible

```xml
<!-- Good -->
<q:component name="UserProfileList" xmlns:q="https://quantum.lang/ns">
<q:component name="ProductCatalog" xmlns:q="https://quantum.lang/ns">
<q:component name="OrderSummary" xmlns:q="https://quantum.lang/ns">

<!-- Less ideal -->
<q:component name="UPL" xmlns:q="https://quantum.lang/ns">
<q:component name="comp1" xmlns:q="https://quantum.lang/ns">
<q:component name="data" xmlns:q="https://quantum.lang/ns">
```

### Unique Names

Each component must have a unique name within your application:

```xml
<!-- This will work -->
<q:component name="ProductList" xmlns:q="https://quantum.lang/ns">
  <!-- ... -->
</q:component>

<!-- This will cause conflicts if both exist -->
<q:component name="ProductList" xmlns:q="https://quantum.lang/ns">
  <!-- ... -->
</q:component>
```

## Output Behavior

### Single Return

Components with one `q:return` produce a single value:

```xml
<q:component name="SingleValue" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World" />
</q:component>
```
**Result:** `"Hello World"`

### Multiple Returns

Components with multiple `q:return` statements produce arrays:

```xml
<q:component name="MultipleValues" xmlns:q="https://quantum.lang/ns">
  <q:return value="First" />
  <q:return value="Second" />
</q:component>
```
**Result:** `["First", "Second"]`

### No Returns

Components without `q:return` statements produce empty results:

```xml
<q:component name="NoOutput" xmlns:q="https://quantum.lang/ns">
  <q:if condition="false">
    <q:return value="This won't execute" />
  </q:if>
</q:component>
```
**Result:** `[]`

## Error Handling

### Validation Errors

Quantum validates component structure:

```xml
<!-- Missing name attribute -->
<q:component xmlns:q="https://quantum.lang/ns">
  <q:return value="Error!" />
</q:component>
```
**Error:** `Component requires 'name' attribute`

### Runtime Errors

Components can encounter runtime errors:

```xml
<q:component name="ErrorExample" xmlns:q="https://quantum.lang/ns">
  <q:return value="Value: {undefined_variable}" />
</q:component>
```
**Error:** `NameError: name 'undefined_variable' is not defined`

## Best Practices

### Keep Components Focused

Each component should have a single, clear responsibility:

```xml
<!-- Good - focused on user display -->
<q:component name="UserCard" xmlns:q="https://quantum.lang/ns">
  <q:return value="Name: {user.name}" />
  <q:return value="Email: {user.email}" />
</q:component>

<!-- Less ideal - mixing concerns -->
<q:component name="UserAndProducts" xmlns:q="https://quantum.lang/ns">
  <q:return value="User: {user.name}" />
  <q:loop type="array" var="product" items="{products}">
    <q:return value="Product: {product.name}" />
  </q:loop>
</q:component>
```

### Use Meaningful Structure

Organize your component logic clearly:

```xml
<q:component name="OrderProcessor" xmlns:q="https://quantum.lang/ns">
  <!-- Process order items -->
  <q:loop type="array" var="item" items="{order.items}">
    <q:return value="Item: {item.name} - ${item.price}" />
  </q:loop>
  
  <!-- Calculate total -->
  <q:return value="Total: ${order.total}" />
  
  <!-- Add status -->
  <q:if condition="order.total > 100">
    <q:return value="Status: Premium Order" />
  <q:else>
    <q:return value="Status: Standard Order" />
  </q:else>
  </q:if>
</q:component>
```

### Handle Edge Cases

Consider empty data and error conditions:

```xml
<q:component name="SafeUserList" xmlns:q="https://quantum.lang/ns">
  <q:if condition="users.length > 0">
    <q:loop type="array" var="user" items="{users}">
      <q:return value="User: {user.name}" />
    </q:loop>
  <q:else>
    <q:return value="No users found" />
  </q:else>
  </q:if>
</q:component>
```

## Integration with Applications

Components are designed to integrate seamlessly with Quantum applications:

```xml
<!-- This component can be used in web applications -->
<q:component name="ApiResponse" xmlns:q="https://quantum.lang/ns">
  <q:return value="API Version: 1.0" />
  <q:return value="Status: Online" />
  <q:loop type="array" var="endpoint" items="{api.endpoints}">
    <q:return value="Endpoint: {endpoint.path}" />
  </q:loop>
</q:component>
```

## Coming Soon

Future component enhancements:

- **Parameters**: `q:param` for component input
- **Local Variables**: `q:set` for internal state
- **Function Calls**: `q:function` definitions and calls
- **Component Composition**: Calling components from other components
- **Lifecycle Hooks**: Initialization and cleanup logic