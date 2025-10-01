# Examples

This section contains practical examples demonstrating Quantum's features and capabilities. Each example includes complete code and expected output.

## Quick Start Examples

### Hello World

The simplest Quantum component:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

**Run:** `python quantum.py run hello.q`  
**Output:** `"Hello, World!"`

### Dynamic Greeting

Using loops for dynamic content:

```xml
<q:component name="Greetings" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="name" items="Alice,Bob,Charlie">
    <q:return value="Hello, {name}!" />
  </q:loop>
</q:component>
```

**Output:** `["Hello, Alice!", "Hello, Bob!", "Hello, Charlie!"]`

## Loop Examples

### Range Loops

#### Basic Range

```xml
<q:component name="BasicRange" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

#### Range with Step

```xml
<q:component name="RangeWithStep" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="0" to="10" step="2">
    <q:return value="Even number: {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Even number: 0", "Even number: 2", "Even number: 4", "Even number: 6", "Even number: 8", "Even number: 10"]`

### Array Loops

#### Simple Array

```xml
<q:component name="SimpleArray" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" items='["apple", "banana", "orange"]'>
    <q:return value="Fruit: {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["Fruit: apple", "Fruit: banana", "Fruit: orange"]`

#### Array with Index

```xml
<q:component name="ArrayWithIndex" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="color" index="idx" items='["red", "green", "blue"]'>
    <q:return value="Color {idx}: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color 0: red", "Color 1: green", "Color 2: blue"]`

### List Loops

#### Comma-Delimited List

```xml
<q:component name="CommaList" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="city" items="New York,London,Tokyo">
    <q:return value="City: {city}" />
  </q:loop>
</q:component>
```

**Output:** `["City: New York", "City: London", "City: Tokyo"]`

#### Custom Delimiter

```xml
<q:component name="CustomDelimiter" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="item" items="apple|banana|orange" delimiter="|">
    <q:return value="Item: {item}" />
  </q:loop>
</q:component>
```

**Output:** `["Item: apple", "Item: banana", "Item: orange"]`

## Databinding Examples

### Arithmetic Expressions

```xml
<q:component name="Arithmetic" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="3">
    <q:return value="Number: {i}, Square: {i * i}, Next: {i + 1}" />
  </q:loop>
</q:component>
```

**Output:** `["Number: 1, Square: 1, Next: 2", "Number: 2, Square: 4, Next: 3", "Number: 3, Square: 9, Next: 4"]`

### Complex Expressions

```xml
<q:component name="ComplexMath" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="x" from="1" to="3">
    <q:return value="x={x}, 2x+1={(2 * x) + 1}, x²-1={x * x - 1}" />
  </q:loop>
</q:component>
```

**Output:** `["x=1, 2x+1=3, x²-1=0", "x=2, 2x+1=5, x²-1=3", "x=3, 2x+1=7, x²-1=8"]`

## Conditional Logic Examples

### Basic If-Else

```xml
<q:component name="BasicConditional" xmlns:q="https://quantum.lang/ns">
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

### Multiple Conditions

```xml
<q:component name="MultipleConditions" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="score" from="85" to="100" step="5">
    <q:if condition="score >= 95">
      <q:return value="Score {score}: A+" />
    <q:elseif condition="score >= 90">
      <q:return value="Score {score}: A" />
    <q:elseif condition="score >= 85">
      <q:return value="Score {score}: B+" />
    <q:else>
      <q:return value="Score {score}: B" />
    </q:else>
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["Score 85: B+", "Score 90: A", "Score 95: A+", "Score 100: A+"]`

## Nested Structures

### Nested Loops

```xml
<q:component name="NestedLoops" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="x" from="1" to="2">
    <q:loop type="range" var="y" from="1" to="2">
      <q:return value="Point ({x}, {y})" />
    </q:loop>
  </q:loop>
</q:component>
```

**Output:** `["Point (1, 1)", "Point (1, 2)", "Point (2, 1)", "Point (2, 2)"]`

### Loops with Conditionals

```xml
<q:component name="LoopsWithConditions" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="4">
    <q:if condition="i % 2 == 0">
      <q:loop type="range" var="j" from="1" to="2">
        <q:return value="Even {i}, sub-item {j}" />
      </q:loop>
    <q:else>
      <q:return value="Odd {i}" />
    </q:else>
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["Odd 1", "Even 2, sub-item 1", "Even 2, sub-item 2", "Odd 3", "Even 4, sub-item 1", "Even 4, sub-item 2"]`

## Real-World Examples

### Product Catalog

```xml
<q:component name="ProductCatalog" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="product" items='[{"name": "Laptop", "price": 999.99}, {"name": "Mouse", "price": 25.99}]'>
    <q:return value="Product: {product.name}" />
    <q:return value="Price: ${product.price}" />
    <q:if condition="product.price > 100">
      <q:return value="Category: Premium" />
    <q:else>
      <q:return value="Category: Standard" />
    </q:else>
    </q:if>
    <q:return value="---" />
  </q:loop>
</q:component>
```

### User Statistics

```xml
<q:component name="UserStats" xmlns:q="https://quantum.lang/ns">
  <q:return value="User Activity Report" />
  <q:return value="===================" />
  
  <q:loop type="range" var="day" from="1" to="7">
    <q:return value="Day {day}:" />
    <q:loop type="range" var="hour" from="9" to="17" step="2">
      <q:return value="  {hour}:00 - Active users: {day * hour}" />
    </q:loop>
  </q:loop>
</q:component>
```

### Data Processing Pipeline

```xml
<q:component name="DataPipeline" xmlns:q="https://quantum.lang/ns">
  <q:return value="Starting data processing pipeline..." />
  
  <q:loop type="array" var="record" items='[{"id": 1, "status": "active"}, {"id": 2, "status": "inactive"}]'>
    <q:return value="Processing record {record.id}" />
    
    <q:if condition="record.status == 'active'">
      <q:return value="  Status: Active - Processing..." />
      <q:return value="  Result: Record {record.id} processed successfully" />
    <q:else>
      <q:return value="  Status: Inactive - Skipping..." />
    </q:else>
    </q:if>
  </q:loop>
  
  <q:return value="Pipeline completed!" />
</q:component>
```

## Web Application Examples

### Simple HTML Server

```xml
<q:application id="simple-web" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <q:return value="<!DOCTYPE html>" />
    <q:return value="<html><head><title>Quantum Web</title></head>" />
    <q:return value="<body>" />
    <q:return value="<h1>Welcome to Quantum Web!</h1>" />
    <q:return value="<p>This page is generated dynamically.</p>" />
    <q:return value="</body></html>" />
  </q:route>
</q:application>
```

### Dynamic API

```xml
<q:application id="number-api" type="api" xmlns:q="https://quantum.lang/ns">
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
    <q:return value='], "count": 5}' />
  </q:route>
</q:application>
```

## Running Examples

### Basic Components

```bash
# Save any example as a .q file and run:
python quantum.py run example.q

# With debug output:
python quantum.py run example.q --debug
```

### Web Applications

```bash
# Start web server:
python quantum.py run webapp.q

# Access at: http://localhost:5000
```

## Common Patterns

### Error Handling

```xml
<q:component name="SafeProcessing" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="item" items='["valid", "", "also_valid"]'>
    <q:if condition="item != ''">
      <q:return value="Processing: {item}" />
    <q:else>
      <q:return value="Skipping empty item" />
    </q:else>
    </q:if>
  </q:loop>
</q:component>
```

### Data Validation

```xml
<q:component name="DataValidation" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="age" items="[25, 17, 30, 16]">
    <q:if condition="age >= 18">
      <q:return value="Age {age}: Adult" />
    <q:else>
      <q:return value="Age {age}: Minor" />
    </q:else>
    </q:if>
  </q:loop>
</q:component>
```

### Report Generation

```xml
<q:component name="MonthlyReport" xmlns:q="https://quantum.lang/ns">
  <q:return value="MONTHLY SALES REPORT" />
  <q:return value="=====================" />
  
  <q:loop type="range" var="week" from="1" to="4">
    <q:return value="Week {week}:" />
    <q:loop type="range" var="day" from="1" to="7">
      <q:return value="  Day {day}: ${week * day * 100} in sales" />
    </q:loop>
    <q:return value="  Week {week} Total: ${week * 2800}" />
    <q:return value="" />
  </q:loop>
</q:component>
```

## Next Steps

- Explore [Loop Structures](/guide/loops) for detailed loop documentation
- Learn about [Variable Databinding](/guide/databinding) for dynamic content
- Check out [Applications](/guide/applications) for web development
- See [Components](/guide/components) for component fundamentals