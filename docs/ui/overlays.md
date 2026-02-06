# Overlay Components

Components that appear above other content, including modals, tooltips, and dropdowns.

## Modal

`ui:modal` displays content in a dialog overlay.

### Basic Usage

```xml
<q:set name="showModal" value="false" />

<ui:button on-click="openModal">Open Modal</ui:button>

<ui:modal open="{showModal}" on-close="closeModal" title="My Modal">
  <ui:text>Modal content goes here.</ui:text>

  <ui:modalfooter>
    <ui:button on-click="closeModal">Cancel</ui:button>
    <ui:button variant="primary" on-click="confirm">Confirm</ui:button>
  </ui:modalfooter>
</ui:modal>

<q:function name="openModal">
  <q:set name="showModal" value="true" />
</q:function>

<q:function name="closeModal">
  <q:set name="showModal" value="false" />
</q:function>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `open` | boolean | false | Modal visibility |
| `title` | string | none | Modal title |
| `size` | string | "md" | Size (sm, md, lg, xl, full) |
| `closable` | boolean | true | Show close button |
| `closeOnEscape` | boolean | true | Close on Escape key |
| `closeOnOverlay` | boolean | true | Close on overlay click |
| `on-close` | string | none | Close handler |

### Modal Sizes

```xml
<!-- Small modal -->
<ui:modal open="{show}" size="sm" title="Confirm">
  <ui:text>Are you sure?</ui:text>
</ui:modal>

<!-- Medium modal (default) -->
<ui:modal open="{show}" size="md" title="Details">
  <ui:text>Standard modal content</ui:text>
</ui:modal>

<!-- Large modal -->
<ui:modal open="{show}" size="lg" title="Form">
  <ui:form>...</ui:form>
</ui:modal>

<!-- Extra large modal -->
<ui:modal open="{show}" size="xl" title="Data Table">
  <ui:table data="{items}" />
</ui:modal>

<!-- Full screen modal -->
<ui:modal open="{show}" size="full" title="Editor">
  <ui:textarea rows="20" />
</ui:modal>
```

### Modal with Form

```xml
<q:set name="showUserModal" value="false" />
<q:set name="newUser" value='{"name": "", "email": ""}' />

<ui:button on-click="openUserModal" variant="primary">Add User</ui:button>

<ui:modal
  open="{showUserModal}"
  title="Add New User"
  on-close="closeUserModal"
>
  <ui:form on-submit="createUser">
    <ui:vbox gap="md">
      <ui:formitem label="Name" required="true">
        <ui:input bind="newUser.name" placeholder="Full name" />
      </ui:formitem>
      <ui:formitem label="Email" required="true">
        <ui:input type="email" bind="newUser.email" placeholder="email@example.com" />
      </ui:formitem>
    </ui:vbox>
  </ui:form>

  <ui:modalfooter>
    <ui:button on-click="closeUserModal">Cancel</ui:button>
    <ui:button variant="primary" on-click="createUser">Create User</ui:button>
  </ui:modalfooter>
</ui:modal>
```

### Confirm Modal

```xml
<q:set name="showConfirm" value="false" />
<q:set name="itemToDelete" value="" />

<q:function name="confirmDelete">
  <q:param name="itemId" />
  <q:set name="itemToDelete" value="{itemId}" />
  <q:set name="showConfirm" value="true" />
</q:function>

<q:function name="executeDelete">
  <!-- Delete the item -->
  <q:set name="showConfirm" value="false" />
</q:function>

<ui:modal
  open="{showConfirm}"
  title="Confirm Deletion"
  size="sm"
  on-close="cancelDelete"
>
  <ui:vbox gap="md" align="center">
    <ui:icon name="alert-triangle" size="xl" color="danger" />
    <ui:text>Are you sure you want to delete this item?</ui:text>
    <ui:text color="muted" size="sm">This action cannot be undone.</ui:text>
  </ui:vbox>

  <ui:modalfooter>
    <ui:button on-click="cancelDelete">Cancel</ui:button>
    <ui:button variant="danger" on-click="executeDelete">Delete</ui:button>
  </ui:modalfooter>
</ui:modal>
```

### Modal with Scrolling Content

```xml
<ui:modal open="{show}" title="Terms of Service" size="lg">
  <ui:scrollbox maxHeight="400px">
    <ui:text>
      <!-- Long content here -->
    </ui:text>
  </ui:scrollbox>

  <ui:modalfooter>
    <ui:checkbox bind="accepted">I agree to the terms</ui:checkbox>
    <ui:spacer />
    <ui:button variant="primary" disabled="{!accepted}">Accept</ui:button>
  </ui:modalfooter>
</ui:modal>
```

## Tooltip

`ui:tooltip` displays information on hover.

### Basic Usage

```xml
<ui:tooltip content="This is a tooltip">
  <ui:button>Hover me</ui:button>
</ui:tooltip>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | string | required | Tooltip text |
| `position` | string | "top" | Position (top, bottom, left, right) |
| `delay` | number | 200 | Show delay in ms |
| `maxWidth` | string | "200px" | Maximum width |

### Tooltip Positions

```xml
<ui:hbox gap="lg">
  <ui:tooltip content="Tooltip on top" position="top">
    <ui:button>Top</ui:button>
  </ui:tooltip>

  <ui:tooltip content="Tooltip on bottom" position="bottom">
    <ui:button>Bottom</ui:button>
  </ui:tooltip>

  <ui:tooltip content="Tooltip on left" position="left">
    <ui:button>Left</ui:button>
  </ui:tooltip>

  <ui:tooltip content="Tooltip on right" position="right">
    <ui:button>Right</ui:button>
  </ui:tooltip>
</ui:hbox>
```

### Rich Tooltip Content

```xml
<ui:tooltip position="bottom">
  <ui:tooltipContent>
    <ui:vbox gap="xs">
      <ui:text weight="bold">Pro Feature</ui:text>
      <ui:text size="sm">Upgrade to unlock this feature.</ui:text>
      <ui:button size="xs" variant="primary">Upgrade Now</ui:button>
    </ui:vbox>
  </ui:tooltipContent>

  <ui:button variant="ghost" disabled="true">
    <ui:icon name="lock" /> Premium
  </ui:button>
</ui:tooltip>
```

### Tooltip on Icons

```xml
<ui:hbox gap="sm">
  <ui:tooltip content="Edit">
    <ui:button variant="ghost" size="sm">
      <ui:icon name="edit" />
    </ui:button>
  </ui:tooltip>

  <ui:tooltip content="Delete">
    <ui:button variant="ghost" size="sm" color="danger">
      <ui:icon name="trash" />
    </ui:button>
  </ui:tooltip>

  <ui:tooltip content="Share">
    <ui:button variant="ghost" size="sm">
      <ui:icon name="share" />
    </ui:button>
  </ui:tooltip>
</ui:hbox>
```

## Dropdown

`ui:dropdown` displays a menu on click.

### Basic Usage

```xml
<ui:dropdown>
  <ui:trigger>
    <ui:button>Options <ui:icon name="chevron-down" /></ui:button>
  </ui:trigger>

  <ui:dropdownmenu>
    <ui:dropdownitem on-click="handleEdit">Edit</ui:dropdownitem>
    <ui:dropdownitem on-click="handleDuplicate">Duplicate</ui:dropdownitem>
    <ui:dropdowndivider />
    <ui:dropdownitem on-click="handleDelete" color="danger">Delete</ui:dropdownitem>
  </ui:dropdownmenu>
</ui:dropdown>
```

### Attributes (ui:dropdown)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `position` | string | "bottom-start" | Menu position |
| `trigger` | string | "click" | Trigger type (click, hover) |
| `closeOnSelect` | boolean | true | Close on item selection |

### Attributes (ui:dropdownitem)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `on-click` | string | none | Click handler |
| `icon` | string | none | Item icon |
| `disabled` | boolean | false | Disable item |
| `color` | string | none | Text color |

### Dropdown with Icons

```xml
<ui:dropdown>
  <ui:trigger>
    <ui:button variant="ghost">
      <ui:icon name="more-vertical" />
    </ui:button>
  </ui:trigger>

  <ui:dropdownmenu>
    <ui:dropdownitem icon="edit" on-click="edit">Edit</ui:dropdownitem>
    <ui:dropdownitem icon="copy" on-click="duplicate">Duplicate</ui:dropdownitem>
    <ui:dropdownitem icon="archive" on-click="archive">Archive</ui:dropdownitem>
    <ui:dropdowndivider />
    <ui:dropdownitem icon="trash" color="danger" on-click="delete">Delete</ui:dropdownitem>
  </ui:dropdownmenu>
</ui:dropdown>
```

### Dropdown with Sections

```xml
<ui:dropdown>
  <ui:trigger>
    <ui:button>Account</ui:button>
  </ui:trigger>

  <ui:dropdownmenu width="200px">
    <ui:dropdownsection>
      <ui:vbox padding="sm" gap="xs">
        <ui:text weight="bold">{user.name}</ui:text>
        <ui:text size="sm" color="muted">{user.email}</ui:text>
      </ui:vbox>
    </ui:dropdownsection>

    <ui:dropdowndivider />

    <ui:dropdownitem icon="user" on-click="goToProfile">Profile</ui:dropdownitem>
    <ui:dropdownitem icon="settings" on-click="goToSettings">Settings</ui:dropdownitem>
    <ui:dropdownitem icon="help" on-click="goToHelp">Help</ui:dropdownitem>

    <ui:dropdowndivider />

    <ui:dropdownitem icon="log-out" color="danger" on-click="logout">
      Sign Out
    </ui:dropdownitem>
  </ui:dropdownmenu>
</ui:dropdown>
```

### Hover Dropdown

```xml
<ui:dropdown trigger="hover">
  <ui:trigger>
    <ui:navlink>Products</ui:navlink>
  </ui:trigger>

  <ui:dropdownmenu>
    <ui:dropdownitem href="/products/electronics">Electronics</ui:dropdownitem>
    <ui:dropdownitem href="/products/clothing">Clothing</ui:dropdownitem>
    <ui:dropdownitem href="/products/books">Books</ui:dropdownitem>
  </ui:dropdownmenu>
</ui:dropdown>
```

### Dropdown Positions

```xml
<!-- Bottom left (default) -->
<ui:dropdown position="bottom-start">...</ui:dropdown>

<!-- Bottom right -->
<ui:dropdown position="bottom-end">...</ui:dropdown>

<!-- Top left -->
<ui:dropdown position="top-start">...</ui:dropdown>

<!-- Top right -->
<ui:dropdown position="top-end">...</ui:dropdown>

<!-- Right -->
<ui:dropdown position="right-start">...</ui:dropdown>
```

## Popover

`ui:popover` displays rich content in a floating container.

### Basic Usage

```xml
<ui:popover>
  <ui:trigger>
    <ui:button>Show Details</ui:button>
  </ui:trigger>

  <ui:popovercontent title="User Details">
    <ui:vbox gap="sm">
      <ui:text><strong>Name:</strong> John Doe</ui:text>
      <ui:text><strong>Email:</strong> john@example.com</ui:text>
      <ui:text><strong>Role:</strong> Administrator</ui:text>
    </ui:vbox>
  </ui:popovercontent>
</ui:popover>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `position` | string | "bottom" | Popover position |
| `trigger` | string | "click" | Trigger type |
| `width` | string | "280px" | Content width |
| `closeOnClickOutside` | boolean | true | Close on outside click |

### Popover with Actions

```xml
<ui:popover>
  <ui:trigger>
    <ui:button variant="ghost">
      <ui:icon name="share" />
    </ui:button>
  </ui:trigger>

  <ui:popovercontent title="Share">
    <ui:vbox gap="md">
      <ui:formitem label="Link">
        <ui:hbox gap="sm">
          <ui:input value="{shareUrl}" readonly="true" width="fill" />
          <ui:button size="sm" on-click="copyLink">Copy</ui:button>
        </ui:hbox>
      </ui:formitem>

      <ui:text size="sm" color="muted">Or share on:</ui:text>

      <ui:hbox gap="sm">
        <ui:button variant="ghost" on-click="shareTwitter">
          <ui:icon name="twitter" />
        </ui:button>
        <ui:button variant="ghost" on-click="shareFacebook">
          <ui:icon name="facebook" />
        </ui:button>
        <ui:button variant="ghost" on-click="shareLinkedin">
          <ui:icon name="linkedin" />
        </ui:button>
      </ui:hbox>
    </ui:vbox>
  </ui:popovercontent>
</ui:popover>
```

## Drawer

`ui:drawer` displays content in a sliding panel.

### Basic Usage

```xml
<q:set name="showDrawer" value="false" />

<ui:button on-click="openDrawer">Open Drawer</ui:button>

<ui:drawer open="{showDrawer}" on-close="closeDrawer" title="Settings">
  <ui:vbox gap="md" padding="md">
    <ui:formitem label="Theme">
      <ui:select bind="theme">
        <ui:option value="light">Light</ui:option>
        <ui:option value="dark">Dark</ui:option>
      </ui:select>
    </ui:formitem>
    <ui:formitem label="Notifications">
      <ui:switch bind="notifications" />
    </ui:formitem>
  </ui:vbox>

  <ui:drawerfooter>
    <ui:button variant="primary" width="fill">Save Changes</ui:button>
  </ui:drawerfooter>
</ui:drawer>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `open` | boolean | false | Drawer visibility |
| `title` | string | none | Drawer title |
| `position` | string | "right" | Position (left, right, top, bottom) |
| `size` | string | "md" | Size (sm, md, lg, xl) |
| `on-close` | string | none | Close handler |

### Drawer Positions

```xml
<!-- Right drawer (default) -->
<ui:drawer position="right" open="{show}">...</ui:drawer>

<!-- Left drawer -->
<ui:drawer position="left" open="{show}">...</ui:drawer>

<!-- Bottom drawer (sheet) -->
<ui:drawer position="bottom" open="{show}">...</ui:drawer>

<!-- Top drawer -->
<ui:drawer position="top" open="{show}">...</ui:drawer>
```

## Complete Overlay Example

```xml
<q:application id="overlay-demo" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="showModal" value="false" />
  <q:set name="showDrawer" value="false" />
  <q:set name="showConfirm" value="false" />

  <ui:window title="Overlay Components">
    <ui:vbox padding="lg" gap="lg">

      <ui:panel title="Overlays Demo">
        <ui:hbox gap="md" wrap="true">

          <!-- Modal Button -->
          <ui:button on-click="openModal">Open Modal</ui:button>

          <!-- Drawer Button -->
          <ui:button on-click="openDrawer">Open Drawer</ui:button>

          <!-- Dropdown -->
          <ui:dropdown>
            <ui:trigger>
              <ui:button>Dropdown Menu</ui:button>
            </ui:trigger>
            <ui:dropdownmenu>
              <ui:dropdownitem icon="edit">Edit</ui:dropdownitem>
              <ui:dropdownitem icon="copy">Duplicate</ui:dropdownitem>
              <ui:dropdowndivider />
              <ui:dropdownitem icon="trash" color="danger">Delete</ui:dropdownitem>
            </ui:dropdownmenu>
          </ui:dropdown>

          <!-- Tooltip -->
          <ui:tooltip content="This button has a tooltip">
            <ui:button>Hover for Tooltip</ui:button>
          </ui:tooltip>

          <!-- Popover -->
          <ui:popover>
            <ui:trigger>
              <ui:button>Click for Popover</ui:button>
            </ui:trigger>
            <ui:popovercontent title="Popover Title">
              <ui:text>This is popover content with more details.</ui:text>
            </ui:popovercontent>
          </ui:popover>

        </ui:hbox>
      </ui:panel>

      <!-- Modal -->
      <ui:modal open="{showModal}" title="Example Modal" on-close="closeModal">
        <ui:vbox gap="md">
          <ui:text>This is a modal dialog.</ui:text>
          <ui:formitem label="Name">
            <ui:input placeholder="Enter name" />
          </ui:formitem>
        </ui:vbox>
        <ui:modalfooter>
          <ui:button on-click="closeModal">Cancel</ui:button>
          <ui:button variant="primary">Save</ui:button>
        </ui:modalfooter>
      </ui:modal>

      <!-- Drawer -->
      <ui:drawer open="{showDrawer}" title="Settings" on-close="closeDrawer">
        <ui:vbox gap="md" padding="md">
          <ui:formitem label="Option 1">
            <ui:switch />
          </ui:formitem>
          <ui:formitem label="Option 2">
            <ui:switch />
          </ui:formitem>
        </ui:vbox>
      </ui:drawer>

    </ui:vbox>
  </ui:window>

  <q:function name="openModal">
    <q:set name="showModal" value="true" />
  </q:function>

  <q:function name="closeModal">
    <q:set name="showModal" value="false" />
  </q:function>

  <q:function name="openDrawer">
    <q:set name="showDrawer" value="true" />
  </q:function>

  <q:function name="closeDrawer">
    <q:set name="showDrawer" value="false" />
  </q:function>

</q:application>
```

## Related Documentation

- [Form Components](/ui/forms) - Form inputs in modals
- [Navigation](/ui/navigation) - Dropdown menus
- [Layout Components](/ui/layout) - Container components
