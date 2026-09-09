# Conditionals (q:if, q:elseif, q:else)

Quantum provides a comprehensive conditional system that allows you to control the flow of your components based on runtime conditions. The syntax is intuitive and closely mirrors traditional programming constructs.

## Basic Syntax

### Simple If Statement

The most basic conditional uses `q:if` with a `condition` attribute:

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:param name="age" type="number" required="true" />

  <q:if condition="age >= 18">
    <q:return value="You are an adult" />
  </q:if>
</q:component>
```

### If-Else Statement

Add an alternative branch with `q:else`:

```xml
<q:component name="AccessControl" xmlns:q="https://quantum.lang/ns">
  <q:param name="age" type="number" required="true" />

  <q:if condition="age >= 18">
    <q:return value="Access granted" />
  </q:if>
  <q:else>
    <q:return value="Access denied - must be 18 or older" />
  </q:else>
</q:component>
```

### If-ElseIf-Else Chain

For multiple conditions, use `q:elseif`:

```xml
<q:component name="GradeCalculator" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" required="true" />

  <q:if condition="score >= 90">
    <q:return value="Grade: A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="Grade: B" />
  </q:elseif>
  <q:elseif condition="score >= 70">
    <q:return value="Grade: C" />
  </q:elseif>
  <q:elseif condition="score >= 60">
    <q:return value="Grade: D" />
  </q:elseif>
  <q:else>
    <q:return value="Grade: F" />
  </q:else>
</q:component>
```

## Condition Expressions

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal to | `condition="status == 'active'"` |
| `!=` | Not equal to | `condition="role != 'guest'"` |
| `>` | Greater than | `condition="count > 0"` |
| `<` | Less than | `condition="age < 18"` |
| `>=` | Greater than or equal | `condition="score >= 60"` |
| `<=` | Less than or equal | `condition="quantity <= 100"` |

### Logical Operators

Combine conditions with logical operators:

```xml
<!-- AND operator -->
<q:if condition="age >= 18 && hasLicense == true">
  <q:return value="Can drive" />
</q:if>

<!-- OR operator -->
<q:if condition="role == 'admin' || role == 'moderator'">
  <q:return value="Has elevated permissions" />
</q:if>

<!-- NOT operator -->
<q:if condition="!isBlocked">
  <q:return value="User is not blocked" />
</q:if>

<!-- Combined -->
<q:if condition="(age >= 21 || hasParentConsent) && !isBanned">
  <q:return value="Access allowed" />
</q:if>
```

### Boolean Values

Check boolean variables directly:

```xml
<q:set name="isActive" type="boolean" value="true" />

<q:if condition="isActive">
  <q:return value="Active user" />
</q:if>

<q:if condition="!isActive">
  <q:return value="Inactive user" />
</q:if>
```

### String Comparisons

Compare string values:

```xml
<q:set name="status" value="pending" />

<q:if condition="status == 'pending'">
  <q:return value="Awaiting approval" />
</q:if>
<q:elseif condition="status == 'approved'">
  <q:return value="Request approved" />
</q:elseif>
<q:elseif condition="status == 'rejected'">
  <q:return value="Request denied" />
</q:elseif>
</q:component>
```

### Arithmetic in Conditions

Perform calculations within conditions:

```xml
<q:set name="price" value="100" />
<q:set name="discount" value="20" />

<q:if condition="price - discount > 50">
  <q:return value="Final price is above $50" />
</q:if>

<q:if condition="price * 0.9 <= 90">
  <q:return value="10% discount brings price to $90 or less" />
</q:if>
```

### Modulo Operations

Check for even/odd numbers or patterns:

```xml
<q:loop type="range" var="i" from="1" to="10">
  <q:if condition="i % 2 == 0">
    <q:return value="{i} is even" />
  </q:if>
  <q:else>
    <q:return value="{i} is odd" />
  </q:else>
</q:loop>
```

## Nested Conditionals

Conditionals can be nested for complex logic:

```xml
<q:component name="UserAccess" xmlns:q="https://quantum.lang/ns">
  <q:param name="userType" type="string" required="true" />
  <q:param name="subscriptionLevel" type="string" default="free" />
  <q:param name="age" type="number" required="true" />

  <q:if condition="userType == 'admin'">
    <q:return value="Full access granted" />
  </q:if>
  <q:elseif condition="userType == 'member'">
    <q:if condition="subscriptionLevel == 'premium'">
      <q:return value="Premium member access" />
    </q:if>
    <q:elseif condition="subscriptionLevel == 'basic'">
      <q:if condition="age >= 18">
        <q:return value="Basic adult member access" />
      </q:if>
      <q:else>
        <q:return value="Basic youth member access" />
      </q:else>
    </q:elseif>
    <q:else>
      <q:return value="Free member access" />
    </q:else>
  </q:elseif>
  <q:else>
    <q:return value="Guest access only" />
  </q:else>
</q:component>
```

## Conditionals with Loops

Combine conditionals with loops for powerful data processing:

```xml
<q:component name="FilteredList" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='[
    {"name": "Apple", "type": "fruit", "price": 1.50},
    {"name": "Carrot", "type": "vegetable", "price": 0.75},
    {"name": "Banana", "type": "fruit", "price": 0.50}
  ]' />

  <q:return value="Fruits under $1.00:" />

  <q:loop type="array" var="item" items="{items}">
    <q:if condition="item.type == 'fruit' && item.price < 1.00">
      <q:return value="- {item.name}: ${item.price}" />
    </q:if>
  </q:loop>
</q:component>
```

**Output:**
```
["Fruits under $1.00:", "- Banana: $0.50"]
```

## Conditionals in Functions

Use conditionals to implement function logic:

```xml
<q:component name="DiscountCalculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="calculateDiscount" returnType="number">
    <q:param name="total" type="number" required="true" />
    <q:param name="customerType" type="string" default="regular" />

    <q:if condition="customerType == 'vip'">
      <q:return value="{total * 0.20}" />
    </q:if>
    <q:elseif condition="customerType == 'member'">
      <q:return value="{total * 0.10}" />
    </q:elseif>
    <q:elseif condition="total > 100">
      <q:return value="{total * 0.05}" />
    </q:elseif>
    <q:else>
      <q:return value="0" />
    </q:else>
  </q:function>

  <q:set name="discount" value="{calculateDiscount(150, 'vip')}" />
  <q:return value="Your discount: ${discount}" />
</q:component>
```

## Conditionals with Database Queries

Check query results conditionally:

```xml
<q:component name="UserDashboard" xmlns:q="https://quantum.lang/ns">
  <q:query name="user" datasource="db">
    SELECT * FROM users WHERE id = :userId
    <q:param name="userId" value="{session.userId}" type="integer" />
  </q:query>

  <q:if condition="user_result.recordCount == 0">
    <q:return value="User not found" />
  </q:if>
  <q:else>
    <q:if condition="user.role == 'admin'">
      <q:return value="Welcome, Administrator {user.name}!" />
    </q:if>
    <q:else>
      <q:return value="Welcome, {user.name}!" />
    </q:else>
  </q:else>
</q:component>
```

## Conditionals in HTML Output

Use conditionals within HTML templates:

```xml
<q:application id="myapp" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/" method="GET">
    <q:set name="isLoggedIn" value="true" />
    <q:set name="userName" value="Alice" />

    <html>
    <body>
      <nav>
        <q:if condition="isLoggedIn">
          <span>Welcome, {userName}!</span>
          <a href="/logout">Logout</a>
        </q:if>
        <q:else>
          <a href="/login">Login</a>
          <a href="/register">Register</a>
        </q:else>
      </nav>
    </body>
    </html>
  </q:route>
</q:application>
```

## Best Practices

### 1. Keep Conditions Simple

Break complex conditions into multiple checks or use variables:

```xml
<!-- Good: Clear and readable -->
<q:set name="isEligible" value="{age >= 18 && hasConsent}" />
<q:if condition="isEligible">
  ...
</q:if>

<!-- Avoid: Overly complex inline conditions -->
<q:if condition="((age >= 18 || (age >= 16 && hasParentConsent)) && !isBanned && (country == 'US' || country == 'CA'))">
  ...
</q:if>
```

### 2. Use Early Returns

For validation, use early returns to reduce nesting:

```xml
<q:function name="processOrder">
  <q:param name="orderId" type="string" required="true" />

  <q:if condition="!orderId">
    <q:return value="Error: Order ID required" />
  </q:if>

  <q:if condition="!session.authenticated">
    <q:return value="Error: Must be logged in" />
  </q:if>

  <!-- Main logic here with less nesting -->
  <q:return value="Order processed" />
</q:function>
```

### 3. Consider Readability

Use meaningful variable names for conditions:

```xml
<q:set name="canPurchaseAlcohol" value="{age >= 21}" />
<q:set name="hasValidId" value="{idStatus == 'verified'}" />

<q:if condition="canPurchaseAlcohol && hasValidId">
  <q:return value="Purchase approved" />
</q:if>
```

### 4. Handle All Cases

Always consider the else case:

```xml
<q:if condition="status == 'active'">
  <q:return value="Active" />
</q:if>
<q:elseif condition="status == 'pending'">
  <q:return value="Pending" />
</q:elseif>
<q:else>
  <!-- Handle unknown status -->
  <q:return value="Unknown status: {status}" />
</q:else>
```

## Error Handling

### Invalid Condition Syntax

Quantum provides clear error messages for invalid conditions:

```
[ERROR] Component 'MyComponent' at line 5:
  Invalid condition syntax: 'age >'
  Expected value after operator '>'
```

### Undefined Variables

Referencing undefined variables in conditions produces errors:

```xml
<!-- Error: 'unknownVar' is not defined -->
<q:if condition="unknownVar == true">
  ...
</q:if>
```

## Related Documentation

- [State Management (q:set)](/guide/state-management) - Variable declarations
- [Loops (q:loop)](/guide/loops) - Iteration patterns
- [Functions (q:function)](/guide/functions) - Reusable logic blocks
- [Databinding](/guide/databinding) - Expression syntax
