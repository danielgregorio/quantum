# Form Components

Quantum provides comprehensive form components for user input with built-in validation and data binding.

## Form

`ui:form` is the container for form elements with submission handling and validation.

### Basic Usage

```xml
<ui:form on-submit="handleSubmit">
  <ui:formitem label="Name">
    <ui:input bind="userName" required="true" />
  </ui:formitem>
  <ui:formitem label="Email">
    <ui:input type="email" bind="userEmail" required="true" />
  </ui:formitem>
  <ui:button type="submit" variant="primary">Submit</ui:button>
</ui:form>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `on-submit` | string | none | Handler function name |
| `validation` | boolean | true | Enable validation |
| `layout` | string | "vertical" | Form layout (vertical, horizontal, inline) |

### Form Layouts

```xml
<!-- Vertical (default) - Labels above inputs -->
<ui:form layout="vertical">
  <ui:formitem label="Name">
    <ui:input bind="name" />
  </ui:formitem>
</ui:form>

<!-- Horizontal - Labels beside inputs -->
<ui:form layout="horizontal">
  <ui:formitem label="Name" labelWidth="120px">
    <ui:input bind="name" />
  </ui:formitem>
</ui:form>

<!-- Inline - All in one row -->
<ui:form layout="inline">
  <ui:formitem label="Search">
    <ui:input bind="query" />
  </ui:formitem>
  <ui:button type="submit">Search</ui:button>
</ui:form>
```

## FormItem

`ui:formitem` wraps a form control with a label.

### Basic Usage

```xml
<ui:formitem label="Username" required="true">
  <ui:input bind="username" placeholder="Enter username" />
</ui:formitem>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `label` | string | none | Label text |
| `required` | boolean | false | Show required indicator |
| `labelWidth` | string | "120px" | Label width (horizontal layout) |
| `help` | string | none | Helper text below input |
| `error` | string | none | Error message |

### With Helper Text

```xml
<ui:formitem label="Password" help="Must be at least 8 characters">
  <ui:input type="password" bind="password" minlength="8" />
</ui:formitem>
```

### With Error Message

```xml
<ui:formitem label="Email" error="{emailError}">
  <ui:input type="email" bind="email" />
</ui:formitem>
```

## Input

`ui:input` is a text input field with various types.

### Basic Usage

```xml
<ui:input bind="name" placeholder="Enter your name" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | string | none | Variable to bind |
| `type` | string | "text" | Input type |
| `placeholder` | string | none | Placeholder text |
| `value` | string | none | Initial value |
| `disabled` | boolean | false | Disable input |
| `readonly` | boolean | false | Read-only mode |
| `required` | boolean | false | Required field |
| `minlength` | number | none | Minimum length |
| `maxlength` | number | none | Maximum length |
| `min` | number | none | Minimum value (number type) |
| `max` | number | none | Maximum value (number type) |
| `pattern` | string | none | Regex pattern |
| `autocomplete` | string | none | Autocomplete hint |
| `size` | string | "md" | Size (sm, md, lg) |

### Input Types

```xml
<!-- Text (default) -->
<ui:input type="text" bind="name" />

<!-- Email with validation -->
<ui:input type="email" bind="email" />

<!-- Password (masked) -->
<ui:input type="password" bind="password" />

<!-- Number with min/max -->
<ui:input type="number" bind="age" min="0" max="120" />

<!-- Date picker -->
<ui:input type="date" bind="birthdate" />

<!-- Time picker -->
<ui:input type="time" bind="meetingTime" />

<!-- DateTime -->
<ui:input type="datetime-local" bind="appointment" />

<!-- URL -->
<ui:input type="url" bind="website" />

<!-- Phone -->
<ui:input type="tel" bind="phone" />

<!-- Search with clear button -->
<ui:input type="search" bind="query" />

<!-- Color picker -->
<ui:input type="color" bind="themeColor" />

<!-- File upload -->
<ui:input type="file" bind="avatar" accept="image/*" />
```

### Input Sizes

```xml
<ui:input size="sm" placeholder="Small input" />
<ui:input size="md" placeholder="Medium input (default)" />
<ui:input size="lg" placeholder="Large input" />
```

### Input with Icons

```xml
<ui:input bind="search" placeholder="Search...">
  <ui:icon slot="prefix" name="search" />
</ui:input>

<ui:input bind="amount" type="number">
  <ui:icon slot="prefix" name="dollar" />
  <ui:text slot="suffix">.00</ui:text>
</ui:input>
```

## Textarea

Multi-line text input.

```xml
<ui:textarea bind="description" rows="4" placeholder="Enter description..." />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | string | none | Variable to bind |
| `rows` | number | 3 | Number of visible rows |
| `maxlength` | number | none | Maximum characters |
| `resize` | string | "vertical" | Resize behavior (none, vertical, horizontal, both) |

## Button

`ui:button` triggers actions or submits forms.

### Basic Usage

```xml
<ui:button on-click="handleClick">Click Me</ui:button>
<ui:button type="submit" variant="primary">Submit</ui:button>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "default" | Style variant |
| `type` | string | "button" | Button type (button, submit, reset) |
| `size` | string | "md" | Size (xs, sm, md, lg, xl) |
| `disabled` | boolean | false | Disable button |
| `loading` | boolean | false | Show loading state |
| `width` | string | "auto" | Button width |
| `on-click` | string | none | Click handler |

### Button Variants

```xml
<!-- Default (outlined) -->
<ui:button variant="default">Default</ui:button>

<!-- Primary (filled) -->
<ui:button variant="primary">Primary</ui:button>

<!-- Secondary -->
<ui:button variant="secondary">Secondary</ui:button>

<!-- Success -->
<ui:button variant="success">Success</ui:button>

<!-- Danger -->
<ui:button variant="danger">Delete</ui:button>

<!-- Warning -->
<ui:button variant="warning">Warning</ui:button>

<!-- Ghost (no background) -->
<ui:button variant="ghost">Ghost</ui:button>

<!-- Link (looks like text link) -->
<ui:button variant="link">Link</ui:button>
```

### Button Sizes

```xml
<ui:button size="xs">Extra Small</ui:button>
<ui:button size="sm">Small</ui:button>
<ui:button size="md">Medium</ui:button>
<ui:button size="lg">Large</ui:button>
<ui:button size="xl">Extra Large</ui:button>
```

### Button States

```xml
<!-- Disabled -->
<ui:button disabled="true">Disabled</ui:button>

<!-- Loading -->
<ui:button loading="true">Saving...</ui:button>

<!-- Full width -->
<ui:button width="fill" variant="primary">Full Width</ui:button>
```

### Button with Icon

```xml
<ui:button variant="primary">
  <ui:icon name="save" /> Save
</ui:button>

<ui:button variant="danger">
  Delete <ui:icon name="trash" />
</ui:button>
```

## Checkbox

`ui:checkbox` for boolean selections.

### Basic Usage

```xml
<ui:checkbox bind="agreeToTerms">I agree to the terms</ui:checkbox>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | string | none | Boolean variable to bind |
| `checked` | boolean | false | Initial checked state |
| `disabled` | boolean | false | Disable checkbox |
| `indeterminate` | boolean | false | Indeterminate state |
| `on-change` | string | none | Change handler |

### Checkbox Group

```xml
<q:set name="selectedFruits" value='[]' type="array" />

<ui:vbox gap="sm">
  <ui:checkbox bind="selectedFruits" value="apple">Apple</ui:checkbox>
  <ui:checkbox bind="selectedFruits" value="banana">Banana</ui:checkbox>
  <ui:checkbox bind="selectedFruits" value="cherry">Cherry</ui:checkbox>
</ui:vbox>

<ui:text>Selected: {selectedFruits.join(', ')}</ui:text>
```

## Switch

`ui:switch` is a toggle switch for on/off states.

### Basic Usage

```xml
<ui:switch bind="darkMode">Dark Mode</ui:switch>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | string | none | Boolean variable to bind |
| `checked` | boolean | false | Initial state |
| `disabled` | boolean | false | Disable switch |
| `size` | string | "md" | Size (sm, md, lg) |
| `on-change` | string | none | Change handler |

### Switch Examples

```xml
<ui:formitem label="Notifications">
  <ui:switch bind="notificationsEnabled" />
</ui:formitem>

<ui:formitem label="Email Updates">
  <ui:switch bind="emailUpdates" size="sm" />
</ui:formitem>
```

## Select

`ui:select` for dropdown selections.

### Basic Usage

```xml
<ui:select bind="country">
  <ui:option value="">Select a country</ui:option>
  <ui:option value="us">United States</ui:option>
  <ui:option value="uk">United Kingdom</ui:option>
  <ui:option value="ca">Canada</ui:option>
</ui:select>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | string | none | Variable to bind |
| `placeholder` | string | none | Placeholder text |
| `disabled` | boolean | false | Disable select |
| `multiple` | boolean | false | Allow multiple selections |
| `searchable` | boolean | false | Enable search |
| `size` | string | "md" | Size (sm, md, lg) |
| `on-change` | string | none | Change handler |

### Dynamic Options

```xml
<q:set name="countries" value='[
  {"value": "us", "label": "United States"},
  {"value": "uk", "label": "United Kingdom"},
  {"value": "ca", "label": "Canada"}
]' />

<ui:select bind="selectedCountry" options="{countries}" />
```

### Option Groups

```xml
<ui:select bind="product">
  <ui:optgroup label="Electronics">
    <ui:option value="phone">Phone</ui:option>
    <ui:option value="laptop">Laptop</ui:option>
  </ui:optgroup>
  <ui:optgroup label="Clothing">
    <ui:option value="shirt">Shirt</ui:option>
    <ui:option value="pants">Pants</ui:option>
  </ui:optgroup>
</ui:select>
```

### Multiple Selection

```xml
<ui:select bind="tags" multiple="true">
  <ui:option value="javascript">JavaScript</ui:option>
  <ui:option value="python">Python</ui:option>
  <ui:option value="rust">Rust</ui:option>
</ui:select>
```

## Radio

`ui:radio` for single selection from options.

### Basic Usage

```xml
<ui:radiogroup bind="size">
  <ui:radio value="sm">Small</ui:radio>
  <ui:radio value="md">Medium</ui:radio>
  <ui:radio value="lg">Large</ui:radio>
</ui:radiogroup>
```

### Horizontal Layout

```xml
<ui:radiogroup bind="plan" direction="horizontal">
  <ui:radio value="free">Free</ui:radio>
  <ui:radio value="pro">Pro</ui:radio>
  <ui:radio value="enterprise">Enterprise</ui:radio>
</ui:radiogroup>
```

### Radio Cards

```xml
<ui:radiogroup bind="plan" variant="cards">
  <ui:radio value="free">
    <ui:text weight="bold">Free</ui:text>
    <ui:text color="muted">Basic features</ui:text>
  </ui:radio>
  <ui:radio value="pro">
    <ui:text weight="bold">Pro - $10/mo</ui:text>
    <ui:text color="muted">All features</ui:text>
  </ui:radio>
</ui:radiogroup>
```

## Range/Slider

```xml
<ui:range bind="volume" min="0" max="100" step="1" />

<ui:formitem label="Volume: {volume}%">
  <ui:range bind="volume" />
</ui:formitem>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bind` | string | none | Variable to bind |
| `min` | number | 0 | Minimum value |
| `max` | number | 100 | Maximum value |
| `step` | number | 1 | Step increment |
| `showValue` | boolean | false | Show current value |

## Complete Form Example

```xml
<q:application id="registration" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="form" value='{
    "name": "",
    "email": "",
    "password": "",
    "confirmPassword": "",
    "country": "",
    "agreeToTerms": false,
    "newsletter": true
  }' />

  <q:set name="errors" value='{}' />
  <q:set name="isSubmitting" value="false" />

  <q:function name="validateForm">
    <q:set name="errors" value='{}' />

    <q:if condition="form.name.length < 2">
      <q:set name="errors.name" value="Name must be at least 2 characters" />
    </q:if>

    <q:if condition="!form.email.includes('@')">
      <q:set name="errors.email" value="Invalid email address" />
    </q:if>

    <q:if condition="form.password.length < 8">
      <q:set name="errors.password" value="Password must be at least 8 characters" />
    </q:if>

    <q:if condition="form.password != form.confirmPassword">
      <q:set name="errors.confirmPassword" value="Passwords do not match" />
    </q:if>

    <q:if condition="!form.agreeToTerms">
      <q:set name="errors.agreeToTerms" value="You must agree to the terms" />
    </q:if>

    <q:return value="{Object.keys(errors).length == 0}" />
  </q:function>

  <q:function name="handleSubmit">
    <q:if condition="validateForm()">
      <q:set name="isSubmitting" value="true" />
      <!-- Submit form data -->
    </q:if>
  </q:function>

  <ui:window title="Registration">
    <ui:vbox padding="xl" gap="lg" align="center">
      <ui:panel title="Create Account" width="400px">
        <ui:form on-submit="handleSubmit">
          <ui:vbox gap="md">

            <ui:formitem label="Full Name" required="true" error="{errors.name}">
              <ui:input bind="form.name" placeholder="John Doe" />
            </ui:formitem>

            <ui:formitem label="Email" required="true" error="{errors.email}">
              <ui:input type="email" bind="form.email" placeholder="john@example.com" />
            </ui:formitem>

            <ui:formitem
              label="Password"
              required="true"
              error="{errors.password}"
              help="At least 8 characters"
            >
              <ui:input type="password" bind="form.password" />
            </ui:formitem>

            <ui:formitem label="Confirm Password" required="true" error="{errors.confirmPassword}">
              <ui:input type="password" bind="form.confirmPassword" />
            </ui:formitem>

            <ui:formitem label="Country">
              <ui:select bind="form.country">
                <ui:option value="">Select your country</ui:option>
                <ui:option value="us">United States</ui:option>
                <ui:option value="uk">United Kingdom</ui:option>
                <ui:option value="ca">Canada</ui:option>
              </ui:select>
            </ui:formitem>

            <ui:checkbox bind="form.agreeToTerms">
              I agree to the Terms of Service and Privacy Policy
            </ui:checkbox>
            <q:if condition="errors.agreeToTerms">
              <ui:text color="danger" size="sm">{errors.agreeToTerms}</ui:text>
            </q:if>

            <ui:checkbox bind="form.newsletter">
              Subscribe to our newsletter
            </ui:checkbox>

            <ui:button
              type="submit"
              variant="primary"
              width="fill"
              loading="{isSubmitting}"
            >
              Create Account
            </ui:button>

          </ui:vbox>
        </ui:form>
      </ui:panel>
    </ui:vbox>
  </ui:window>

</q:application>
```

## Related Documentation

- [Form Validation](/features/form-validation) - Advanced validation
- [Layout Components](/ui/layout) - Form layout patterns
- [Data Binding](/guide/databinding) - Two-way binding
