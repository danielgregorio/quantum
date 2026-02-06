# Form Validation

Quantum provides a comprehensive declarative form validation system that works on both client and server side. Validation can be configured using HTML5 attributes, the `ui:validator` tag, or custom expressions.

## Overview

Form validation in Quantum supports:

- HTML5 validation attributes (`required`, `min`, `max`, `pattern`, etc.)
- Custom validators with `ui:validator`
- Client-side and server-side validation
- Multiple error display modes
- Custom error messages
- Field matching (password confirmation)
- Async validation

## HTML5 Validation Attributes

The simplest way to add validation is using HTML5 attributes on input elements.

### Required Fields

```xml
<ui:input bind="email" required="true" />
```

### Length Constraints

```xml
<!-- Minimum and maximum length -->
<ui:input bind="username" minlength="3" maxlength="20" />

<!-- Combined with required -->
<ui:input bind="password" required="true" minlength="8" />
```

### Numeric Constraints

```xml
<!-- Min/max values for number inputs -->
<ui:input bind="age" type="number" min="18" max="120" />

<!-- Step values -->
<ui:input bind="price" type="number" min="0" step="0.01" />
```

### Pattern Validation

```xml
<!-- Regex pattern -->
<ui:input bind="username"
          pattern="[a-zA-Z0-9_]+"
          error-message="Only letters, numbers, and underscores allowed" />

<!-- Phone number pattern -->
<ui:input bind="phone"
          type="tel"
          pattern="\d{10,11}"
          error-message="Enter 10-11 digit phone number" />
```

### Built-in Type Validation

```xml
<!-- Email validation -->
<ui:input bind="email" type="email" required="true" />

<!-- URL validation -->
<ui:input bind="website" type="url" />

<!-- Date validation -->
<ui:input bind="birthdate" type="date" min="1900-01-01" max="2010-12-31" />
```

## Custom Validators with `ui:validator`

For complex validation rules, use the `ui:validator` tag inside a form.

### Basic Syntax

```xml
<ui:form>
  <!-- Define validators at form level -->
  <ui:validator name="validatorName"
                pattern="regex"
                message="Error message" />

  <!-- Apply to inputs -->
  <ui:input bind="field" validators="validatorName" />
</ui:form>
```

### Validator Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | string | Unique validator name (required) |
| `pattern` | regex | Regex pattern to match |
| `match` | string | Field name to match against |
| `min` | number | Minimum value |
| `max` | number | Maximum value |
| `minlength` | number | Minimum string length |
| `maxlength` | number | Maximum string length |
| `message` | string | Error message to display |
| `field` | string | Target field (for form-level validators) |
| `trigger` | string | When to validate: `blur`, `change`, `input`, `submit` |
| `expression` | string | Custom JavaScript validation expression |
| `server-expression` | string | Custom server-side validation expression |

### Password Strength Validator

```xml
<ui:form>
  <ui:validator name="passwordStrength"
                pattern="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$"
                message="Password must have at least 8 characters with uppercase, lowercase, and number" />

  <ui:formitem label="Password">
    <ui:input bind="password"
              type="password"
              required="true"
              validators="passwordStrength" />
  </ui:formitem>
</ui:form>
```

### Password Match Validator

```xml
<ui:form>
  <ui:validator name="passwordMatch"
                match="password"
                message="Passwords must match" />

  <ui:formitem label="Password">
    <ui:input bind="password" type="password" required="true" />
  </ui:formitem>

  <ui:formitem label="Confirm Password">
    <ui:input bind="confirmPassword"
              type="password"
              required="true"
              validators="passwordMatch" />
  </ui:formitem>
</ui:form>
```

### Range Validator

```xml
<ui:form>
  <ui:validator name="ageRange"
                field="age"
                min="18"
                max="120"
                message="Age must be between 18 and 120" />

  <ui:formitem label="Age">
    <ui:input bind="age" type="number" validators="ageRange" />
  </ui:formitem>
</ui:form>
```

### Multiple Validators

Apply multiple validators to a single field:

```xml
<ui:form>
  <ui:validator name="noSpaces"
                pattern="^\S+$"
                message="Username cannot contain spaces" />

  <ui:validator name="alphanumeric"
                pattern="^[a-zA-Z0-9_]+$"
                message="Only letters, numbers, and underscores" />

  <ui:formitem label="Username">
    <ui:input bind="username"
              required="true"
              minlength="3"
              maxlength="20"
              validators="noSpaces,alphanumeric" />
  </ui:formitem>
</ui:form>
```

## Validation Modes

Control when and where validation occurs with the `validation` attribute on forms.

### Client-Side Only

```xml
<ui:form validation="client">
  <!-- Validates in browser only -->
</ui:form>
```

### Server-Side Only

```xml
<ui:form validation="server">
  <!-- Validates on form submission -->
</ui:form>
```

### Both (Default)

```xml
<ui:form validation="both">
  <!-- Validates on client and server -->
</ui:form>
```

## Error Display Modes

Control how validation errors are displayed with the `error-display` attribute.

### Inline Errors (Default)

Errors appear next to each field:

```xml
<ui:form error-display="inline">
  <ui:formitem label="Email" error="{errors.email}">
    <ui:input bind="email" type="email" required="true" />
  </ui:formitem>
</ui:form>
```

### Summary Errors

All errors displayed in a summary at the top:

```xml
<ui:form error-display="summary">
  <q:if condition="{hasErrors}">
    <ui:alert variant="danger" title="Please fix the following errors:">
      <ul>
        <q:loop var="error" items="{errors}">
          <li>{error}</li>
        </q:loop>
      </ul>
    </ui:alert>
  </q:if>

  <!-- Form fields -->
</ui:form>
```

### Both Inline and Summary

```xml
<ui:form error-display="both">
  <!-- Shows errors inline AND in summary -->
</ui:form>
```

## Custom Error Messages

Customize error messages for each validation rule:

```xml
<ui:formitem label="Email">
  <ui:input bind="email"
            type="email"
            required="true"
            error-message="Please enter a valid email address" />
</ui:formitem>

<ui:formitem label="Age">
  <ui:input bind="age"
            type="number"
            min="18"
            max="120"
            error-message="You must be between 18 and 120 years old" />
</ui:formitem>
```

### Per-Constraint Messages

Use data attributes for specific constraint messages:

```xml
<ui:input bind="password"
          required="true"
          minlength="8"
          pattern="(?=.*\d)(?=.*[A-Z])"
          data-error-required="Password is required"
          data-error-minlength="Password must be at least 8 characters"
          data-error-pattern="Password must contain a number and uppercase letter" />
```

## Validation Triggers

Control when validation fires:

### On Submit (Default)

```xml
<ui:validator name="myValidator" trigger="submit" ... />
```

### On Blur (Field Loses Focus)

```xml
<ui:validator name="myValidator" trigger="blur" ... />
```

### On Change (Value Changes)

```xml
<ui:validator name="myValidator" trigger="change" ... />
```

### On Input (Real-Time)

```xml
<ui:validator name="myValidator" trigger="input" ... />
```

## Custom Validation Expressions

For complex validation logic, use expressions:

### Client-Side Expression

```xml
<ui:validator name="checkStartDate"
              expression="new Date(value) >= new Date()"
              message="Start date must be in the future" />
```

### Server-Side Expression

```xml
<ui:validator name="uniqueEmail"
              server-expression="not EmailService.exists(value)"
              message="This email is already registered" />
```

## Disabling HTML5 Validation

To use only custom validation (no browser popups):

```xml
<ui:form novalidate="true">
  <!-- Uses Quantum validation only -->
</ui:form>
```

## Complete Example

Here's a comprehensive registration form with validation:

```xml
<q:application id="registration" type="ui">
  <q:set name="form" type="struct" value='{
    "email": "",
    "username": "",
    "password": "",
    "confirmPassword": "",
    "age": "",
    "phone": "",
    "website": ""
  }' />

  <ui:window title="User Registration">
    <ui:panel title="Create Account">
      <ui:form validation="both" error-display="both" on-submit="handleSubmit">

        <!-- Custom validators -->
        <ui:validator name="passwordStrength"
                      pattern="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$"
                      message="Password must have 8+ chars with uppercase, lowercase, and number" />

        <ui:validator name="passwordMatch"
                      match="password"
                      message="Passwords must match" />

        <ui:validator name="ageRange"
                      field="age"
                      min="18"
                      max="120"
                      message="Age must be between 18 and 120" />

        <!-- Email -->
        <ui:formitem label="Email">
          <ui:input bind="form.email"
                    type="email"
                    required="true"
                    placeholder="user@example.com"
                    error-message="Please enter a valid email address" />
        </ui:formitem>

        <!-- Username -->
        <ui:formitem label="Username">
          <ui:input bind="form.username"
                    required="true"
                    minlength="3"
                    maxlength="20"
                    pattern="[a-zA-Z0-9_]+"
                    placeholder="alphanumeric_only"
                    error-message="Username must be 3-20 alphanumeric characters" />
        </ui:formitem>

        <!-- Password -->
        <ui:formitem label="Password">
          <ui:input bind="form.password"
                    type="password"
                    required="true"
                    validators="passwordStrength"
                    placeholder="8+ characters, mixed case + number" />
        </ui:formitem>

        <!-- Confirm Password -->
        <ui:formitem label="Confirm Password">
          <ui:input bind="form.confirmPassword"
                    type="password"
                    required="true"
                    validators="passwordMatch" />
        </ui:formitem>

        <!-- Age -->
        <ui:formitem label="Age">
          <ui:input bind="form.age"
                    type="number"
                    min="18"
                    max="120"
                    placeholder="18-120" />
        </ui:formitem>

        <!-- Phone (optional) -->
        <ui:formitem label="Phone (Optional)">
          <ui:input bind="form.phone"
                    type="tel"
                    pattern="\d{10,11}"
                    placeholder="10-11 digits" />
        </ui:formitem>

        <!-- Website (optional) -->
        <ui:formitem label="Website (Optional)">
          <ui:input bind="form.website"
                    type="url"
                    placeholder="https://example.com" />
        </ui:formitem>

        <!-- Submit -->
        <ui:hbox gap="12" justify="end">
          <ui:button variant="secondary">Cancel</ui:button>
          <ui:button variant="primary" type="submit">Register</ui:button>
        </ui:hbox>

      </ui:form>
    </ui:panel>
  </ui:window>

  <q:function name="handleSubmit">
    <q:log message="Form submitted with: {form}" />
    <!-- Process registration -->
  </q:function>
</q:application>
```

## Server-Side Validation with `q:set`

For server-side validation, use `q:set` with validation attributes:

```xml
<q:action name="register" method="POST">
  <!-- Validate email format -->
  <q:set name="email"
         type="string"
         value="{form.email}"
         required="true"
         validate="email" />

  <!-- Validate age range -->
  <q:set name="age"
         type="integer"
         value="{form.age}"
         min="18"
         max="120" />

  <!-- Validate with pattern -->
  <q:set name="username"
         type="string"
         value="{form.username}"
         required="true"
         minlength="3"
         maxlength="20"
         pattern="^[a-zA-Z0-9_]+$" />

  <!-- Validate against enum -->
  <q:set name="plan"
         type="string"
         value="{form.plan}"
         enum="free,basic,premium,enterprise"
         default="free" />

  <!-- Process if all validations pass -->
  <q:query datasource="db">
    INSERT INTO users (email, username, age, plan)
    VALUES (:email, :username, :age, :plan)
    <q:param name="email" value="{email}" />
    <q:param name="username" value="{username}" />
    <q:param name="age" value="{age}" />
    <q:param name="plan" value="{plan}" />
  </q:query>

  <q:redirect url="/welcome" flash="Registration successful!" />
</q:action>
```

## Built-in Validators

Quantum includes these built-in validators for `q:set`:

| Validator | Description |
|-----------|-------------|
| `email` | Valid email address |
| `url` | Valid URL |
| `phone` | Phone number format |
| `cpf` | Brazilian CPF with digit verification |
| `cnpj` | Brazilian CNPJ with digit verification |
| `cep` | Brazilian CEP format |
| `uuid` | UUID format |
| `creditcard` | Credit card number (Luhn check) |
| `ipv4` | IPv4 address |
| `ipv6` | IPv6 address |

Example:

```xml
<q:set name="cardNumber" type="string" validate="creditcard" />
<q:set name="ipAddress" type="string" validate="ipv4" />
```

## Error Handling

Handle validation errors gracefully:

```xml
<q:function name="handleSubmit">
  <q:try>
    <!-- Validation that might fail -->
    <q:set name="email" value="{form.email}" validate="email" required="true" />

    <!-- Success path -->
    <q:return value="success" />

  <q:catch var="error">
    <!-- Handle validation error -->
    <q:log message="Validation failed: {error.message}" level="warn" />
    <q:set name="errors.email" value="{error.message}" />
    <q:return value="error" />
  </q:catch>
  </q:try>
</q:function>
```

## Accessibility

Quantum's validation system includes accessibility features:

- Error messages are associated with inputs using `aria-describedby`
- Invalid fields are marked with `aria-invalid="true"`
- Focus moves to the first invalid field on form submission
- Screen readers announce error messages

## Best Practices

1. **Provide clear error messages** - Tell users exactly what's wrong and how to fix it
2. **Validate on blur** - Give immediate feedback without being intrusive
3. **Use both client and server validation** - Client for UX, server for security
4. **Mark required fields** - Use visual indicators (asterisk) for required fields
5. **Group related validations** - Use `ui:validator` for reusable rules
6. **Handle all error states** - Consider network errors, server errors, etc.
7. **Support keyboard navigation** - Ensure form is fully accessible

## Related Documentation

- [Form Components](/ui/forms) - UI form components
- [State Management](/guide/state-management) - `q:set` validation attributes
- [Actions](/guide/actions) - Form submission handling
