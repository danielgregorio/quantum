# State Persistence

Quantum provides declarative state persistence, allowing variables to survive page reloads and be synchronized across browser tabs or desktop sessions. This is configured using the `persist` attribute on `q:set` or the `q:persist` tag.

## Overview

State persistence in Quantum supports:

- **Local storage** - Persists in browser localStorage
- **Session storage** - Persists for the browser session
- **Sync storage** - Synchronizes across tabs/windows
- **TTL expiration** - Automatic expiration of stored values
- **Encryption** - Optional encryption for sensitive data
- **Desktop file storage** - Persists to file system in desktop apps

## Basic Usage

### Using the `persist` Attribute

The simplest way to persist state is adding the `persist` attribute to `q:set`:

```xml
<!-- Persist to localStorage -->
<q:set name="theme" value="dark" persist="local" />

<!-- Persist to sessionStorage -->
<q:set name="formDraft" value="{draftData}" persist="session" />

<!-- Sync across tabs -->
<q:set name="cartItems" value="[]" type="array" persist="sync" />
```

## Persistence Scopes

### Local Storage (`local`)

Data persists indefinitely in the browser's localStorage until explicitly cleared.

```xml
<q:set name="userPreferences" type="struct" persist="local" value='{
  "theme": "dark",
  "language": "en",
  "notifications": true
}' />
```

Best for:
- User preferences
- Application settings
- Cached data
- Shopping cart contents

### Session Storage (`session`)

Data persists for the browser session only. Cleared when the tab/window closes.

```xml
<q:set name="wizardStep" type="integer" value="1" persist="session" />
<q:set name="formProgress" type="struct" persist="session" value="{}" />
```

Best for:
- Multi-step form progress
- Temporary UI state
- Session-specific data
- Draft content

### Sync Storage (`sync`)

Data synchronizes across all tabs/windows of the same origin in real-time.

```xml
<q:set name="cartItems" type="array" persist="sync" value="[]" />
<q:set name="userStatus" type="string" persist="sync" value="online" />
```

Best for:
- Shopping carts
- User presence/status
- Shared application state
- Real-time collaboration

## Persistence Attributes

### Custom Storage Key

By default, the storage key is derived from the variable name. Override with `persistKey`:

```xml
<q:set name="theme"
       value="light"
       persist="local"
       persistKey="app_v2_theme" />
```

### Encryption

Enable encryption for sensitive data with `persistEncrypt`:

```xml
<q:set name="userToken"
       value="{token}"
       persist="local"
       persistEncrypt="true" />

<q:set name="savedCredentials"
       type="struct"
       persist="local"
       persistEncrypt="true"
       value='{"username": "", "rememberMe": false}' />
```

Note: Encryption uses AES-256-GCM with a key derived from the application ID.

### TTL Expiration

Set automatic expiration with the `q:persist` tag:

```xml
<q:persist scope="local" prefix="cache_">
  <q:var name="apiResponse" ttl="3600" />  <!-- Expires in 1 hour -->
  <q:var name="userSession" ttl="86400" /> <!-- Expires in 24 hours -->
</q:persist>
```

TTL values are in seconds.

## The `q:persist` Tag

For more control, use `q:persist` to configure multiple variables:

```xml
<q:persist scope="local" prefix="myapp_" encrypt="false">
  <q:var name="theme" />
  <q:var name="language" />
  <q:var name="sidebarCollapsed" />
</q:persist>
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | enum | `local` | Storage scope: `local`, `session`, `sync` |
| `prefix` | string | `""` | Prefix for storage keys |
| `key` | string | - | Custom storage key (single variable) |
| `encrypt` | boolean | `false` | Enable encryption |
| `ttl` | integer | - | Time-to-live in seconds |

### Examples

```xml
<!-- Group related persisted variables -->
<q:persist scope="local" prefix="user_prefs_">
  <q:var name="theme" />
  <q:var name="fontSize" />
  <q:var name="colorScheme" />
</q:persist>

<!-- Session data with encryption -->
<q:persist scope="session" encrypt="true">
  <q:var name="tempToken" />
  <q:var name="pendingAction" />
</q:persist>

<!-- Cached data with TTL -->
<q:persist scope="local" prefix="cache_">
  <q:var name="userProfile" ttl="3600" />      <!-- 1 hour -->
  <q:var name="dashboardData" ttl="300" />     <!-- 5 minutes -->
  <q:var name="notificationCount" ttl="60" />  <!-- 1 minute -->
</q:persist>
```

## Cross-Tab Synchronization

The `sync` scope enables real-time synchronization across browser tabs:

```xml
<q:application id="myapp" type="ui">
  <!-- This value syncs across all open tabs -->
  <q:set name="cartItems" type="array" persist="sync" value="[]" />
  <q:set name="unreadCount" type="integer" persist="sync" value="0" />

  <ui:window title="Shopping">
    <ui:badge variant="danger">{unreadCount}</ui:badge>

    <ui:button on-click="addToCart">
      Add to Cart ({cartItems.length} items)
    </ui:button>
  </ui:window>

  <q:function name="addToCart">
    <q:param name="item" type="struct" />
    <!-- Update in one tab, reflected in all tabs -->
    <q:set name="cartItems" operation="append" value="{item}" />
  </q:function>
</q:application>
```

### Sync Events

React to changes from other tabs:

```xml
<q:set name="sharedCounter"
       type="integer"
       persist="sync"
       value="0"
       on-sync="handleSync" />

<q:function name="handleSync">
  <q:param name="newValue" />
  <q:param name="source" />  <!-- "local" or "remote" -->

  <q:if condition="{source == 'remote'}">
    <q:log message="Counter updated in another tab: {newValue}" />
  </q:if>
</q:function>
```

## Desktop File Storage

In desktop applications (pywebview), persistence uses the file system:

```xml
<q:application id="desktop-app" type="ui" target="desktop">
  <!-- Stored in: ~/.myapp/preferences.json -->
  <q:set name="preferences"
         type="struct"
         persist="local"
         persistKey="preferences"
         value='{
           "windowSize": {"width": 1024, "height": 768},
           "recentFiles": [],
           "theme": "system"
         }' />
</q:application>
```

### Desktop Storage Location

| Platform | Location |
|----------|----------|
| Windows | `%APPDATA%/<app-id>/` |
| macOS | `~/Library/Application Support/<app-id>/` |
| Linux | `~/.config/<app-id>/` |

### Binary Data Storage

For binary data (files, images), use the file API:

```xml
<q:set name="recentDocuments"
       type="array"
       persist="local"
       value="[]" />

<q:function name="addRecentDocument">
  <q:param name="path" type="string" />

  <!-- Store file path, not content -->
  <q:set name="recentDocuments"
         operation="prepend"
         value="{path}" />

  <!-- Limit to 10 recent files -->
  <q:if condition="{recentDocuments.length > 10}">
    <q:set name="recentDocuments"
           value="{recentDocuments.slice(0, 10)}" />
  </q:if>
</q:function>
```

## Complete Examples

### User Preferences

```xml
<q:component name="SettingsPage">
  <!-- Persisted preferences -->
  <q:set name="preferences" type="struct" persist="local" value='{
    "theme": "system",
    "language": "en",
    "fontSize": "medium",
    "notifications": true,
    "autoSave": true
  }' />

  <ui:panel title="Settings">
    <ui:form>
      <ui:formitem label="Theme">
        <ui:select bind="preferences.theme" options="system,light,dark" />
      </ui:formitem>

      <ui:formitem label="Language">
        <ui:select bind="preferences.language" options="en,es,pt,fr,de" />
      </ui:formitem>

      <ui:formitem label="Font Size">
        <ui:radio bind="preferences.fontSize" options="small,medium,large" />
      </ui:formitem>

      <ui:formitem label="Notifications">
        <ui:switch bind="preferences.notifications" />
      </ui:formitem>

      <ui:formitem label="Auto-save">
        <ui:switch bind="preferences.autoSave" />
      </ui:formitem>
    </ui:form>
  </ui:panel>
</q:component>
```

### Shopping Cart with Sync

```xml
<q:application id="shop" type="ui">
  <!-- Cart syncs across tabs -->
  <q:set name="cart" type="struct" persist="sync" value='{
    "items": [],
    "total": 0
  }' />

  <ui:window title="Shop">
    <ui:hbox justify="between" padding="md">
      <ui:text size="xl">Products</ui:text>
      <ui:badge variant="primary">{cart.items.length} items - ${cart.total}</ui:badge>
    </ui:hbox>

    <ui:grid columns="3" gap="md">
      <q:loop var="product" items="{products}">
        <ui:card title="{product.name}">
          <ui:text>${product.price}</ui:text>
          <ui:button on-click="addToCart(product)">Add to Cart</ui:button>
        </ui:card>
      </q:loop>
    </ui:grid>
  </ui:window>

  <q:function name="addToCart">
    <q:param name="product" type="struct" />

    <q:set name="cart.items" operation="append" value="{product}" />
    <q:set name="cart.total" value="{cart.total + product.price}" />
  </q:function>
</q:application>
```

### Form Draft Auto-Save

```xml
<q:component name="ArticleEditor">
  <!-- Draft saved to session, auto-restored on reload -->
  <q:set name="draft" type="struct" persist="session" value='{
    "title": "",
    "content": "",
    "tags": [],
    "lastSaved": null
  }' />

  <q:set name="autoSaveInterval" value="30000" /> <!-- 30 seconds -->

  <ui:panel title="Write Article">
    <ui:form>
      <ui:formitem label="Title">
        <ui:input bind="draft.title" placeholder="Article title" />
      </ui:formitem>

      <ui:formitem label="Content">
        <ui:textarea bind="draft.content" rows="20" />
      </ui:formitem>

      <ui:formitem label="Tags">
        <ui:input bind="draft.tags" placeholder="Comma-separated tags" />
      </ui:formitem>

      <ui:hbox justify="between">
        <ui:text size="sm" color="muted">
          Last saved: {draft.lastSaved || 'Never'}
        </ui:text>
        <ui:hbox gap="md">
          <ui:button variant="secondary" on-click="clearDraft">Discard</ui:button>
          <ui:button variant="primary" on-click="publish">Publish</ui:button>
        </ui:hbox>
      </ui:hbox>
    </ui:form>
  </ui:panel>

  <!-- Auto-save timer -->
  <q:interval ms="{autoSaveInterval}" on-tick="saveDraft" />

  <q:function name="saveDraft">
    <q:set name="draft.lastSaved" value="{new Date().toLocaleString()}" />
    <q:log message="Draft auto-saved" level="debug" />
  </q:function>

  <q:function name="clearDraft">
    <q:set name="draft" value='{
      "title": "",
      "content": "",
      "tags": [],
      "lastSaved": null
    }' />
  </q:function>
</q:component>
```

### Cached API Data with TTL

```xml
<q:component name="Dashboard">
  <!-- Configure persistence with TTL -->
  <q:persist scope="local" prefix="dashboard_cache_">
    <q:var name="userData" ttl="3600" />        <!-- 1 hour -->
    <q:var name="statsData" ttl="300" />        <!-- 5 minutes -->
    <q:var name="notificationsData" ttl="60" /> <!-- 1 minute -->
  </q:persist>

  <!-- Initialize from cache or fetch -->
  <q:set name="userData" type="struct" value="{}" />
  <q:set name="statsData" type="struct" value="{}" />
  <q:set name="loading" type="boolean" value="true" />

  <!-- Fetch data on load if cache expired -->
  <q:if condition="{!userData.id}">
    <q:invoke name="fetchData" function="loadUserData" />
    <q:set name="userData" value="{fetchData}" />
  </q:if>

  <q:if condition="{!statsData.lastUpdated}">
    <q:invoke name="fetchStats" function="loadStats" />
    <q:set name="statsData" value="{fetchStats}" />
  </q:if>

  <q:set name="loading" value="false" />

  <ui:window title="Dashboard">
    <q:if condition="{loading}">
      <ui:loading text="Loading dashboard..." />
    <q:else>
      <ui:text size="xl">Welcome, {userData.name}!</ui:text>
      <ui:text>Last stats update: {statsData.lastUpdated}</ui:text>
    </q:else>
    </q:if>
  </ui:window>
</q:component>
```

## Storage Limits

Be aware of browser storage limits:

| Storage Type | Typical Limit |
|--------------|---------------|
| localStorage | 5-10 MB |
| sessionStorage | 5-10 MB |
| Desktop (file) | Disk space |

Handle storage quota errors:

```xml
<q:function name="saveData">
  <q:try>
    <q:set name="largeData" value="{data}" persist="local" />
  <q:catch var="error">
    <q:if condition="{error.name == 'QuotaExceededError'}">
      <q:log message="Storage quota exceeded, clearing old data" level="warn" />
      <q:invoke function="clearOldCache" />
      <!-- Retry -->
      <q:set name="largeData" value="{data}" persist="local" />
    </q:if>
  </q:catch>
  </q:try>
</q:function>
```

## Best Practices

1. **Use appropriate scope** - `local` for permanent, `session` for temporary, `sync` for shared
2. **Set TTL for cached data** - Prevent stale data issues
3. **Encrypt sensitive data** - Use `persistEncrypt` for tokens, credentials
4. **Handle storage errors** - Catch quota exceeded errors
5. **Namespace your keys** - Use prefixes to avoid conflicts
6. **Don't store large blobs** - Store references, not file contents
7. **Clear on logout** - Remove sensitive persisted data on user logout
8. **Test sync behavior** - Verify cross-tab sync works correctly

## Related Documentation

- [State Management](/guide/state-management) - Variables and `q:set`
- [Form Validation](/features/form-validation) - Form handling
- [Desktop Target](/ui-engine/targets/desktop) - Desktop app persistence
