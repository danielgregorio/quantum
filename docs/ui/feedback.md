# Feedback Components

Components for providing user feedback, including alerts, loading states, progress indicators, and badges.

## Alert

`ui:alert` displays informational, success, warning, or error messages.

### Basic Usage

```xml
<ui:alert variant="info">
  This is an informational message.
</ui:alert>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "info" | Style variant (info, success, warning, danger) |
| `title` | string | none | Alert title |
| `dismissible` | boolean | false | Show close button |
| `icon` | boolean | true | Show icon |
| `on-dismiss` | string | none | Dismiss handler |

### Alert Variants

```xml
<!-- Info (default) -->
<ui:alert variant="info">
  Your settings have been saved.
</ui:alert>

<!-- Success -->
<ui:alert variant="success">
  Order placed successfully!
</ui:alert>

<!-- Warning -->
<ui:alert variant="warning">
  Your subscription expires in 3 days.
</ui:alert>

<!-- Danger/Error -->
<ui:alert variant="danger">
  Failed to process payment. Please try again.
</ui:alert>
```

### With Title

```xml
<ui:alert variant="success" title="Payment Successful">
  Your payment of $50.00 has been processed. A receipt has been sent to your email.
</ui:alert>
```

### Dismissible Alert

```xml
<q:set name="showAlert" value="true" />

<q:if condition="showAlert">
  <ui:alert
    variant="info"
    dismissible="true"
    on-dismiss="hideAlert"
  >
    Click the X to dismiss this alert.
  </ui:alert>
</q:if>

<q:function name="hideAlert">
  <q:set name="showAlert" value="false" />
</q:function>
```

### Alert with Actions

```xml
<ui:alert variant="warning" title="Confirm Deletion">
  <ui:text>Are you sure you want to delete this item?</ui:text>
  <ui:hbox gap="sm" padding="md 0 0">
    <ui:button size="sm" variant="danger" on-click="confirmDelete">Delete</ui:button>
    <ui:button size="sm" on-click="cancelDelete">Cancel</ui:button>
  </ui:hbox>
</ui:alert>
```

## Loading

`ui:loading` displays a loading spinner or indicator.

### Basic Usage

```xml
<ui:loading>Loading...</ui:loading>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `size` | string | "md" | Spinner size (sm, md, lg) |
| `variant` | string | "primary" | Color variant |
| `text` | string | none | Loading text |
| `fullscreen` | boolean | false | Fullscreen overlay |

### Loading Sizes

```xml
<ui:loading size="sm" />
<ui:loading size="md">Loading data...</ui:loading>
<ui:loading size="lg">Please wait...</ui:loading>
```

### Fullscreen Loading

```xml
<q:if condition="isLoading">
  <ui:loading fullscreen="true">
    Processing your request...
  </ui:loading>
</q:if>
```

### Inline Loading

```xml
<ui:button disabled="{isSubmitting}">
  <q:if condition="isSubmitting">
    <ui:loading size="sm" /> Saving...
  </q:if>
  <q:else>
    Save Changes
  </q:else>
</ui:button>
```

### Loading with Fetch

```xml
<q:fetch name="data" url="/api/data">
  <q:loading>
    <ui:vbox align="center" padding="xl">
      <ui:loading size="lg">Loading data...</ui:loading>
    </ui:vbox>
  </q:loading>
  <q:success>
    <!-- Display data -->
  </q:success>
</q:fetch>
```

## Progress

`ui:progress` displays a progress bar.

### Basic Usage

```xml
<ui:progress value="75" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `value` | number | 0 | Current progress (0-100) |
| `max` | number | 100 | Maximum value |
| `variant` | string | "primary" | Color variant |
| `showLabel` | boolean | false | Show percentage label |
| `striped` | boolean | false | Striped pattern |
| `animated` | boolean | false | Animated stripes |
| `size` | string | "md" | Bar height (sm, md, lg) |

### Progress Variants

```xml
<ui:progress value="25" variant="primary" />
<ui:progress value="50" variant="success" />
<ui:progress value="75" variant="warning" />
<ui:progress value="90" variant="danger" />
```

### With Label

```xml
<ui:progress value="65" showLabel="true" />
<!-- Displays: [==========>    ] 65% -->
```

### Animated Progress

```xml
<ui:progress value="80" striped="true" animated="true" />
```

### Progress with Text

```xml
<ui:vbox gap="xs">
  <ui:hbox justify="between">
    <ui:text size="sm">Upload Progress</ui:text>
    <ui:text size="sm">{uploadProgress}%</ui:text>
  </ui:hbox>
  <ui:progress value="{uploadProgress}" />
</ui:vbox>
```

### Multi-Segment Progress

```xml
<ui:progress>
  <ui:segment value="30" variant="success" label="Completed" />
  <ui:segment value="20" variant="warning" label="In Progress" />
  <ui:segment value="10" variant="danger" label="Failed" />
</ui:progress>
```

## Badge

`ui:badge` displays a small status indicator.

### Basic Usage

```xml
<ui:badge>Default</ui:badge>
<ui:badge variant="primary">Primary</ui:badge>
<ui:badge variant="success">Success</ui:badge>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "default" | Color variant |
| `size` | string | "md" | Size (sm, md, lg) |
| `rounded` | boolean | false | Pill shape |
| `dot` | boolean | false | Show as dot indicator |

### Badge Variants

```xml
<ui:badge variant="default">Default</ui:badge>
<ui:badge variant="primary">Primary</ui:badge>
<ui:badge variant="secondary">Secondary</ui:badge>
<ui:badge variant="success">Success</ui:badge>
<ui:badge variant="danger">Danger</ui:badge>
<ui:badge variant="warning">Warning</ui:badge>
<ui:badge variant="info">Info</ui:badge>
```

### Badge Sizes

```xml
<ui:badge size="sm">Small</ui:badge>
<ui:badge size="md">Medium</ui:badge>
<ui:badge size="lg">Large</ui:badge>
```

### Rounded (Pill) Badge

```xml
<ui:badge rounded="true" variant="primary">New</ui:badge>
<ui:badge rounded="true" variant="success">Active</ui:badge>
```

### Dot Badge

```xml
<ui:hbox align="center" gap="sm">
  <ui:badge dot="true" variant="success" />
  <ui:text>Online</ui:text>
</ui:hbox>

<ui:hbox align="center" gap="sm">
  <ui:badge dot="true" variant="danger" />
  <ui:text>Offline</ui:text>
</ui:hbox>
```

### Badge in Context

```xml
<!-- In navigation -->
<ui:menuitem>
  Messages
  <ui:badge variant="primary" size="sm">5</ui:badge>
</ui:menuitem>

<!-- With avatar -->
<ui:avatar src="{user.avatar}" name="{user.name}">
  <ui:badge slot="status" dot="true" variant="success" />
</ui:avatar>

<!-- Status indicator -->
<ui:table data="{orders}">
  <ui:column field="status" header="Status">
    <ui:template>
      <ui:badge variant="{row.status == 'paid' ? 'success' : 'warning'}">
        {row.status}
      </ui:badge>
    </ui:template>
  </ui:column>
</ui:table>
```

## Skeleton

`ui:skeleton` displays placeholder loading content.

### Basic Usage

```xml
<ui:skeleton type="text" />
<ui:skeleton type="circle" />
<ui:skeleton type="rect" />
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | "text" | Shape type (text, circle, rect, card) |
| `width` | string | "100%" | Skeleton width |
| `height` | string | varies | Skeleton height |
| `lines` | number | 1 | Number of text lines |
| `animated` | boolean | true | Show animation |

### Text Skeleton

```xml
<!-- Single line -->
<ui:skeleton type="text" />

<!-- Multiple lines -->
<ui:skeleton type="text" lines="3" />

<!-- Paragraph with varied widths -->
<ui:skeleton type="text" lines="4" lastLineWidth="60%" />
```

### Shape Skeletons

```xml
<!-- Circle (avatar placeholder) -->
<ui:skeleton type="circle" width="48px" height="48px" />

<!-- Rectangle (image placeholder) -->
<ui:skeleton type="rect" width="100%" height="200px" />
```

### Card Skeleton

```xml
<ui:skeleton type="card">
  <!-- Renders a card-shaped skeleton with header and content areas -->
</ui:skeleton>
```

### Custom Skeleton Layout

```xml
<ui:hbox gap="md" padding="md">
  <!-- Avatar -->
  <ui:skeleton type="circle" width="48px" height="48px" />

  <!-- Content -->
  <ui:vbox gap="sm" width="fill">
    <ui:skeleton type="text" width="150px" />
    <ui:skeleton type="text" width="250px" />
  </ui:vbox>
</ui:hbox>
```

### Skeleton Table

```xml
<ui:skeleton type="table" rows="5" columns="4" />
```

### Conditional Skeleton

```xml
<q:fetch name="user" url="/api/user/{userId}">
  <q:loading>
    <ui:hbox gap="md">
      <ui:skeleton type="circle" width="64px" height="64px" />
      <ui:vbox gap="sm">
        <ui:skeleton type="text" width="200px" />
        <ui:skeleton type="text" width="150px" />
      </ui:vbox>
    </ui:hbox>
  </q:loading>
  <q:success>
    <ui:hbox gap="md">
      <ui:avatar src="{user.data.avatar}" size="lg" />
      <ui:vbox>
        <ui:text weight="bold">{user.data.name}</ui:text>
        <ui:text color="muted">{user.data.email}</ui:text>
      </ui:vbox>
    </ui:hbox>
  </q:success>
</q:fetch>
```

## Toast (Notifications)

`ui:toast` displays temporary notification messages.

### Programmatic Toasts

```xml
<q:function name="showSuccess">
  <q:toast variant="success">Operation completed!</q:toast>
</q:function>

<q:function name="showError">
  <q:toast variant="danger" duration="5000">
    Something went wrong. Please try again.
  </q:toast>
</q:function>

<ui:button on-click="showSuccess">Show Success</ui:button>
<ui:button on-click="showError">Show Error</ui:button>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `variant` | string | "info" | Toast type |
| `duration` | number | 3000 | Display duration (ms) |
| `position` | string | "top-right" | Screen position |
| `dismissible` | boolean | true | Allow manual dismiss |

### Toast Container

```xml
<ui:toastcontainer position="top-right" />

<!-- Toasts will appear in this container -->
```

## Complete Feedback Example

```xml
<q:application id="feedback-demo" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="isSubmitting" value="false" />
  <q:set name="submitResult" value="" />
  <q:set name="uploadProgress" value="0" />

  <q:function name="simulateSubmit">
    <q:set name="isSubmitting" value="true" />
    <q:set name="submitResult" value="" />
    <!-- Simulate async operation -->
    <q:set name="isSubmitting" value="false" />
    <q:set name="submitResult" value="success" />
  </q:function>

  <ui:window title="Feedback Components Demo">
    <ui:vbox padding="lg" gap="lg">

      <!-- Alert Examples -->
      <ui:panel title="Alerts">
        <ui:vbox gap="md">
          <ui:alert variant="info" title="Information">
            This is an informational message for the user.
          </ui:alert>

          <q:if condition="submitResult == 'success'">
            <ui:alert variant="success" dismissible="true">
              Your changes have been saved successfully!
            </ui:alert>
          </q:if>

          <q:if condition="submitResult == 'error'">
            <ui:alert variant="danger" title="Error">
              Failed to save changes. Please try again.
            </ui:alert>
          </q:if>
        </ui:vbox>
      </ui:panel>

      <!-- Loading States -->
      <ui:panel title="Loading States">
        <ui:hbox gap="xl">
          <ui:vbox align="center" gap="sm">
            <ui:loading size="sm" />
            <ui:text size="sm">Small</ui:text>
          </ui:vbox>
          <ui:vbox align="center" gap="sm">
            <ui:loading size="md" />
            <ui:text size="sm">Medium</ui:text>
          </ui:vbox>
          <ui:vbox align="center" gap="sm">
            <ui:loading size="lg" />
            <ui:text size="sm">Large</ui:text>
          </ui:vbox>
        </ui:hbox>
      </ui:panel>

      <!-- Progress Bars -->
      <ui:panel title="Progress">
        <ui:vbox gap="md">
          <ui:vbox gap="xs">
            <ui:text size="sm">Upload Progress</ui:text>
            <ui:progress value="{uploadProgress}" showLabel="true" />
          </ui:vbox>

          <ui:vbox gap="xs">
            <ui:text size="sm">Project Status</ui:text>
            <ui:progress>
              <ui:segment value="40" variant="success" />
              <ui:segment value="30" variant="warning" />
              <ui:segment value="10" variant="danger" />
            </ui:progress>
          </ui:vbox>
        </ui:vbox>
      </ui:panel>

      <!-- Badges -->
      <ui:panel title="Badges">
        <ui:hbox gap="md" wrap="true">
          <ui:badge>Default</ui:badge>
          <ui:badge variant="primary">Primary</ui:badge>
          <ui:badge variant="secondary">Secondary</ui:badge>
          <ui:badge variant="success">Success</ui:badge>
          <ui:badge variant="danger">Danger</ui:badge>
          <ui:badge variant="warning">Warning</ui:badge>
          <ui:badge rounded="true" variant="primary">Pill</ui:badge>
        </ui:hbox>
      </ui:panel>

      <!-- Skeleton Loading -->
      <ui:panel title="Skeleton Loading">
        <ui:hbox gap="lg">
          <ui:skeleton type="circle" width="64px" height="64px" />
          <ui:vbox gap="sm" width="fill">
            <ui:skeleton type="text" width="200px" />
            <ui:skeleton type="text" width="300px" />
            <ui:skeleton type="text" width="150px" />
          </ui:vbox>
        </ui:hbox>
      </ui:panel>

      <!-- Submit Button with Loading -->
      <ui:panel title="Async Action">
        <ui:button
          variant="primary"
          on-click="simulateSubmit"
          disabled="{isSubmitting}"
        >
          <q:if condition="isSubmitting">
            <ui:loading size="sm" /> Saving...
          </q:if>
          <q:else>
            Save Changes
          </q:else>
        </ui:button>
      </ui:panel>

    </ui:vbox>
  </ui:window>

</q:application>
```

## Related Documentation

- [Form Components](/ui/forms) - Form input handling
- [Data Fetching](/guide/data-fetching) - Loading states with fetch
- [Layout Components](/ui/layout) - Container components
